import os
import re
import logging
import json
import uuid
import time
import traceback
import threading
from datetime import datetime
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
import requests

from .models import (
    LeadMagnet, Lead, Download, FirmProfile,
    FormaAIConversation, TemplateSelection, Template,
)
from .serializers import (
    LeadMagnetSerializer, LeadSerializer, DashboardStatsSerializer,
    FirmProfileSerializer, LeadMagnetGenerationSerializer,
    CreateLeadMagnetSerializer, TemplateSerializer,
)
from .services import DocRaptorService, render_template
from .groq_client import GroqClient

logger = logging.getLogger(__name__)

_JOBS: dict = {}
_JOBS_LOCK  = threading.Lock()


def _set_job(job_id: str, **kwargs):
    with _JOBS_LOCK:
        if job_id not in _JOBS:
            _JOBS[job_id] = {"created_at": datetime.utcnow()}
        _JOBS[job_id].update(kwargs)


def _get_job(job_id: str) -> dict:
    with _JOBS_LOCK:
        return dict(_JOBS.get(job_id, {}))


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE RENDERER
#
# Rules:
#   • Any key ending in _html  → raw injection (no HTML escaping)
#   • toc_sections_html / toc_html → raw injection
#   • Everything else → HTML-escaped plain text
#   • {{#if key}} treats empty string / None / 0 as FALSY
# ─────────────────────────────────────────────────────────────────────────────

def _is_raw_html_key(key: str) -> bool:
    return key.endswith("_html") or key in {"toc_html", "toc_sections_html"}


def _render_template_vars(html: str, vars_dict: dict) -> str:
    # Pass 1: {{#if key}}...{{/if}}
    def _resolve_if(m):
        key     = m.group(1).strip()
        content = m.group(2)
        val     = vars_dict.get(key)
        truthy  = bool(val) and str(val).strip() not in ("", "0", "None")
        return content if truthy else ""

    html = re.sub(
        r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}',
        _resolve_if, html, flags=re.DOTALL,
    )

    # Pass 2: {{key}}
    def _replace_var(m):
        key = m.group(1).strip()
        val = vars_dict.get(key)
        if val is None:
            return ""
        val_str = str(val)
        if _is_raw_html_key(key):
            return val_str
        return (
            val_str
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    return re.sub(r'\{\{\s*(\w+)\s*\}\}', _replace_var, html)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Simple health check endpoint that returns 200 OK.
    Used by Render to verify the service is running.
    """
    return Response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_image_url(img) -> str:
    if not img:
        return ""
    if isinstance(img, str):
        return img.strip()
    if isinstance(img, dict):
        return (img.get("src") or img.get("url") or "").strip()
    return ""


def _clean_company_name(name: str, email: str = "") -> str:
    """Detect username-style strings and produce a proper company name."""
    if not name:
        if email and "@" in email:
            domain = email.split("@")[-1].split(".")[0]
            if domain.lower() not in ("gmail","yahoo","hotmail","outlook","icloud","me","mac"):
                return domain.replace("-"," ").replace("_"," ").title()
        return name or ""
    is_username = (
        " " not in name.strip() and "@" not in name
        and (re.search(r'\d', name) or name == name.lower())
    )
    if not is_username:
        return name
    if email and "@" in email:
        domain = email.split("@")[-1].split(".")[0]
        if domain.lower() not in ("gmail","yahoo","hotmail","outlook","icloud","me","mac"):
            return domain.replace("-"," ").replace("_"," ").title()
    return re.sub(r'\d+$', '', name).title() or name


def _build_firm_profile(user, fp_obj=None) -> dict:
    if fp_obj is None:
        try:
            fp_obj = FirmProfile.objects.get(user=user)
        except FirmProfile.DoesNotExist:
            fp_obj = None

    email = getattr(user, "email", "")
    if fp_obj:
        return {
            "firm_name":             _clean_company_name(fp_obj.firm_name, email),
            "work_email":            fp_obj.work_email or email,
            "phone_number":          fp_obj.phone_number or "",
            "firm_website":          fp_obj.firm_website or "",
            "primary_brand_color":   fp_obj.primary_brand_color or "",
            "secondary_brand_color": fp_obj.secondary_brand_color or "",
            "logo_url":              fp_obj.logo.url if fp_obj.logo else "",
            "industry":              "Architecture",
            "branding_guidelines":   fp_obj.branding_guidelines or "",
        }
    return {
        "firm_name":             _clean_company_name("", email),
        "work_email":            email,
        "phone_number":          "", "firm_website":          "",
        "primary_brand_color":   "", "secondary_brand_color": "",
        "logo_url":              "", "industry":              "Architecture",
        "branding_guidelines":   "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# STANDARD VIEWS
# ─────────────────────────────────────────────────────────────────────────────

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        ulm  = LeadMagnet.objects.filter(owner=user)
        return Response(DashboardStatsSerializer({
            "total_lead_magnets":  ulm.count(),
            "active_lead_magnets": ulm.filter(Q(status="completed") | Q(status="in-progress")).count(),
            "total_downloads":     Download.objects.filter(lead_magnet__owner=user).count(),
            "leads_generated":     Lead.objects.filter(lead_magnet__owner=user).count(),
        }).data)


class LeadMagnetListCreateView(generics.ListCreateAPIView):
    serializer_class   = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return LeadMagnet.objects.filter(owner=self.request.user)
    def perform_create(self, s): s.save(owner=self.request.user)


class LeadMagnetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return LeadMagnet.objects.filter(owner=self.request.user)


class FirmProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = FirmProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = FirmProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "firm_name":"","work_email":getattr(self.request.user,"email","") or "no-reply@example.com",
                "phone_number":"","firm_website":"","firm_size":"1-2","industry_specialties":[],
                "primary_brand_color":"","secondary_brand_color":"","preferred_font_style":"no-preference",
                "branding_guidelines":"","location":"",
            },
        )
        return profile

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        if hasattr(request.data, "getlist"):
            processed = {}
            for k in request.data.keys():
                if k == "industry_specialties":
                    sp = request.data.getlist(k)
                    processed[k] = json.loads(sp[0]) if len(sp)==1 and isinstance(sp[0],str) and sp[0].startswith("[") else sp
                else:
                    processed[k] = request.data.get(k)
            data = processed
        for k in list(data.keys()):
            v = data[k]
            if v in ("","null","undefined"):
                data[k] = None if k in ("logo","preferred_cover_image") else ""
            if k=="firm_website" and data[k] and isinstance(data[k],str):
                u = data[k].strip().lower()
                if u and not u.startswith(("http://","https://")):
                    data[k] = f"https://{u}"
        for k in ("logo","preferred_cover_image"):
            if k in data and isinstance(data[k],str): data.pop(k)
        if "industry_specialties" in data and data["industry_specialties"] is None:
            data["industry_specialties"] = []
        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        logger.error(f"FirmProfile update failed: {serializer.errors}")
        return Response({"error":"Firm profile update failed","details":serializer.errors}, status=400)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_theme_palette(request):
    is_dark = request.query_params.get("mode") == "dark"
    palette = {
        "primary":   "#1a365d",
        "secondary": "#c5a059",
        "surface":   "#ffffff",
        "onSurface": "#1a202c",
        "accent":    "#f8fafc",
        "highlight": "#e8f4f8",
    }
    try:
        fp = FirmProfile.objects.get(user=request.user)
        if fp.primary_brand_color:   palette["primary"]   = fp.primary_brand_color
        if fp.secondary_brand_color: palette["secondary"] = fp.secondary_brand_color
    except FirmProfile.DoesNotExist:
        pass
    if is_dark:
        palette.update({"surface":"#1a202c","onSurface":"#f7fafc","accent":"#2d3748","highlight":"#4a5568"})
    return Response(palette)


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND GENERATION JOB
# ─────────────────────────────────────────────────────────────────────────────

def _run_generation_job(job_id: str, body: dict, user_id):
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)

        template_id          = body.get("template_id")
        lead_magnet_id       = body.get("lead_magnet_id")
        use_ai_content       = bool(body.get("use_ai_content", True))
        architectural_images = body.get("architectural_images", [])

        if not template_id or not lead_magnet_id:
            _set_job(job_id, status="failed", error="template_id and lead_magnet_id are required")
            return

        _set_job(job_id, status="processing", progress=5, message="Parsing request...", lead_magnet_id=lead_magnet_id)

        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=user)
        except LeadMagnet.DoesNotExist:
            _set_job(job_id, status="failed", error="Lead magnet not found"); return

        gen_data = getattr(lead_magnet, "generation_data", None)
        if not gen_data:
            _set_job(job_id, status="failed", error="Lead magnet is missing generation data"); return

        ai_client = GroqClient()

        ai_input = {
            "main_topic":       gen_data.main_topic,
            "target_audience":  gen_data.target_audience,
            "pain_points": (
                gen_data.audience_pain_points
                if isinstance(gen_data.audience_pain_points, list)
                else [gen_data.audience_pain_points]
            ),
            "desired_outcome":  gen_data.desired_outcome,
            "call_to_action":   gen_data.call_to_action,
            "special_requests": gen_data.special_requests or "",
            "tone":             "Professional and Institutional",
            "industry":         "Architecture",
            "document_type":    gen_data.lead_magnet_type or "guide",
            "lead_magnet_type": gen_data.lead_magnet_type or "Strategic Guide",
        }

        firm_profile = _build_firm_profile(user)

        # ── Image slots — only set when URL is non-empty ───────────────────
        # Absent key → {{#if image_N_url}} evaluates falsy → no broken block
        for i in range(1, 7):
            raw = architectural_images[i-1] if len(architectural_images) >= i else ""
            url = _resolve_image_url(raw)
            if url:
                firm_profile[f"image_{i}_url"] = url

        if use_ai_content:
            try:
                _set_job(job_id, status="processing", progress=15,
                         message="Generating AI content — 11 sections (~3–12 min)...")
                t0 = time.time()

                signals        = ai_client.get_semantic_signals(ai_input)
                raw_ai         = ai_client.generate_lead_magnet_json(signals, firm_profile)
                ai_content     = ai_client.normalize_ai_output(raw_ai)

                logger.info(f"✅ AI done | {time.time()-t0:.1f}s")

                empty = [k for k, *_ in ai_client.SECTIONS if not ai_content.get(k)]
                if empty:
                    logger.warning(f"⚠️ Empty sections: {empty}")

                # ── DIAGNOSTIC: log exact content lengths so we can see what Groq returned
                for k, *_ in ai_client.SECTIONS:
                    content = ai_content.get(k, "")
                    logger.info(f"  [CONTENT] {k}: {len(content)} chars | preview: {content[:80].replace(chr(10),' ')!r}")

                _set_job(job_id, status="processing", progress=65, message="Mapping content to template...")

                template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, signals)

                # Firm data fallbacks
                topic = signals.get("topic", "Industry")
                template_vars["companyName"]  = template_vars.get("companyName")  or firm_profile.get("firm_name") or f"{topic} Experts"
                template_vars["emailAddress"] = template_vars.get("emailAddress") or firm_profile.get("work_email","")
                template_vars["phoneNumber"]  = template_vars.get("phoneNumber")  or firm_profile.get("phone_number","")
                template_vars["website"]      = template_vars.get("website")      or firm_profile.get("firm_website","")

                for n in range(2, 16):
                    template_vars[f"pageNumber{n}"]       = str(n).zfill(2)
                    template_vars[f"pageNumberHeader{n}"] = str(n).zfill(2)

                # Verify content vars
                missing = [f"section_{k}_full_html" for k, *_ in ai_client.SECTIONS
                           if not template_vars.get(f"section_{k}_full_html")]
                if missing:
                    logger.warning(f"⚠️ Missing _full_html vars: {missing}")
                else:
                    logger.info(f"✅ All 11 section_*_full_html vars populated")

            except Exception as e:
                logger.error(f"AI Pipeline Error: {e}\n{traceback.format_exc()}")
                _set_job(job_id, status="failed", error=f"AI generation failed: {e}"); return
        else:
            template_vars = {
                "primaryColor":   firm_profile.get("primary_brand_color") or "#1a365d",
                "secondaryColor": firm_profile.get("secondary_brand_color") or "#c5a059",
                "highlightColor": "#f4f7f9", "lightColor": "#f1f5f9",
                "whiteColor": "#ffffff", "textColor": "#1e293b",
                "textLightColor": "#64748b", "bodyBackground": "#ffffff",
                "borderRadius": "8px", "accentColor": "#f8fafc",
                "companyName":      firm_profile.get("firm_name") or "",
                "mainTitle":        lead_magnet.title,
                "documentSubtitle": "Professional Insights",
                "emailAddress":     firm_profile.get("work_email") or "",
                "phoneNumber":      firm_profile.get("phone_number") or "",
                "website":          firm_profile.get("firm_website") or "",
                "toc_sections_html": "",
                "termsTitle": "Terms of Use", "termsSummary": "",
                "termsParagraph1":"","termsParagraph2":"","termsParagraph3":"",
                "termsParagraph4":"","termsParagraph5":"",
                "contentsTitle": "Table of Contents",
            }
            for idx, (key, dtitle, *_) in enumerate(GroqClient.SECTIONS):
                template_vars[f"section_{key}_full_html"] = ""
                template_vars[f"section_{key}_id"]        = f"section-{key}"
                template_vars[f"customTitle{idx+1}"]      = dtitle

        # ── PDF RENDERING ──────────────────────────────────────────────────
        pdf_service = DocRaptorService()
        try:
            _set_job(job_id, status="processing", progress=75, message="Rendering PDF via DocRaptor...")
            t0 = time.time()

            docraptor_vars = template_vars.copy()

            # ── Image URL safety: do NOT overwrite non-empty with empty ────
            for i in range(1, 7):
                existing  = docraptor_vars.get(f"image_{i}_url","")
                firm_url  = firm_profile.get(f"image_{i}_url","")
                if not existing and firm_url:
                    docraptor_vars[f"image_{i}_url"] = firm_url
                elif not existing and not firm_url:
                    # Remove key entirely → {{#if}} evaluates falsy → no broken block
                    docraptor_vars.pop(f"image_{i}_url", None)

            # Colour defaults
            docraptor_vars.setdefault("primaryColor",   "#1a365d")
            docraptor_vars.setdefault("secondaryColor", "#c5a059")
            docraptor_vars.setdefault("accentColor",    "#f8fafc")
            docraptor_vars.setdefault("highlightColor", "#f4f7f9")
            docraptor_vars.setdefault("lightColor",     "#f1f5f9")
            docraptor_vars.setdefault("whiteColor",     "#ffffff")
            docraptor_vars.setdefault("textColor",      "#1e293b")
            docraptor_vars.setdefault("textLightColor", "#64748b")
            docraptor_vars.setdefault("bodyBackground", "#ffffff")
            docraptor_vars.setdefault("borderRadius",   "8px")

            _set_job(job_id, status="processing", progress=82, message="DocRaptor rendering PDF...")
            result = pdf_service.generate_pdf("modern-guide", docraptor_vars)

            if not result.get("success"):
                err = result.get("error","PDF generation failed")
                _set_job(job_id, status="failed", error=f"{err}: {result.get('details','')}"); return

            _set_job(job_id, status="processing", progress=92, message="Saving to cloud storage...")
            pdf_data = result["pdf_data"]
            filename = result.get("filename", f"lead-magnet-{lead_magnet_id}.pdf")

            try:
                import cloudinary.uploader
                up = cloudinary.uploader.upload(
                    pdf_data, resource_type="raw", folder="lead_magnets",
                    public_id=f"lead-magnet-{lead_magnet_id}-{uuid.uuid4().hex[:8]}",
                )
                lead_magnet.pdf_file = up.get("public_id")
                lead_magnet.status   = "completed"
                lead_magnet.save(update_fields=["pdf_file","status"])
            except Exception as ue:
                logger.error(f"Cloudinary fallback: {ue}")
                lead_magnet.pdf_file.save(filename, ContentFile(pdf_data), save=True)
                lead_magnet.status = "completed"
                lead_magnet.save(update_fields=["status"])

            logger.info(f"✅ PDF done | {time.time()-t0:.1f}s")
            _set_job(job_id, status="complete", progress=100,
                     pdf_url=f"/api/lead-magnets/{lead_magnet_id}/download/",
                     message="Your PDF is ready!")

        except Exception as e:
            logger.error(f"PDF Rendering Error: {e}\n{traceback.format_exc()}")
            _set_job(job_id, status="failed", error=f"PDF rendering failed: {e}")

    except Exception as exc:
        logger.critical(f"Critical job error: {exc}\n{traceback.format_exc()}")
        _set_job(job_id, status="failed", error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_start(request):
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None)
    threading.Thread(target=_run_generation_job, args=(job_id,request.data,request.user.id), daemon=True).start()
    return Response({"job_id":job_id,"status":"pending"}, status=202)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status(request, job_id):
    job = _get_job(job_id)
    if not job:
        return Response({"error":"Job not found"}, status=404)
    return Response({"job_id":job_id,"status":job.get("status"),"progress":job.get("progress",0),
                     "message":job.get("message",""),"pdf_url":job.get("pdf_url"),"error":job.get("error")})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_compat(request):
    body   = request.data
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None,
             lead_magnet_id=body.get("lead_magnet_id"))
    threading.Thread(target=_run_generation_job, args=(job_id,body,request.user.id), daemon=True).start()
    return Response({
        "status":"in_progress","message":"PDF generation started",
        "lead_magnet_id":body.get("lead_magnet_id"),
        "status_url":request.build_absolute_uri(
            f"/api/generate-pdf/status/?lead_magnet_id={body.get('lead_magnet_id')}&job_id={job_id}"),
        "retry_after_seconds":3,
    }, status=202)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status_compat(request):
    lm_id  = request.query_params.get("lead_magnet_id")
    job_id = request.query_params.get("job_id")
    if not lm_id:
        return Response({"error":"lead_magnet_id is required"}, status=400)

    job = _get_job(job_id) if job_id else None
    if not job:
        with _JOBS_LOCK:
            for _, v in reversed(list(_JOBS.items())):
                if str(v.get("lead_magnet_id")) == str(lm_id):
                    job = dict(v); break

    try:
        lm = LeadMagnet.objects.get(id=lm_id, owner=request.user)
    except LeadMagnet.DoesNotExist:
        return Response({"error":"Lead magnet not found"}, status=404)

    if str(lm.status) == "completed" and lm.pdf_file:
        return Response({"status":"ready","pdf_url":f"/api/lead-magnets/{lm_id}/download/"})
    if job:
        if job.get("status") == "complete" and lm.pdf_file:
            return Response({"status":"ready","pdf_url":f"/api/lead-magnets/{lm_id}/download/"})
        if job.get("status") in ("failed","error"):
            return Response({"status":"error","error":job.get("error","Generation failed")})
    return Response({"status":"pending"})


from cloudinary.utils import cloudinary_url as _cld_url

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def download_lead_magnet_pdf(request, lead_magnet_id: int):
    try:
        try:
            lm = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
        except LeadMagnet.DoesNotExist:
            return Response({"error":"Lead magnet not found"}, status=404)
        if not lm.pdf_file:
            return Response({"error":"PDF not generated yet"}, status=404)

        signed_url, _ = _cld_url(lm.pdf_file.name, resource_type="raw", sign_url=True, secure=True)
        proxy = requests.get(signed_url, stream=True, timeout=30)
        proxy.raise_for_status()
        filename = os.path.basename(lm.pdf_file.name) or f"lead-magnet-{lead_magnet_id}.pdf"
        if not filename.endswith(".pdf"): filename += ".pdf"
        resp = FileResponse(proxy.raw, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        if "Content-Length" in proxy.headers:
            resp["Content-Length"] = proxy.headers["Content-Length"]
        return resp
    except Exception as e:
        logger.error(f"Download error LM {lead_magnet_id}: {e}")
        return Response({"error":"Failed to retrieve file"}, status=500)


class CreateLeadMagnetView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            s = CreateLeadMagnetSerializer(data=request.data, context={"request":request})
            s.is_valid(raise_exception=True)
            return Response(LeadMagnetSerializer(s.save()).data, status=201)
        except Exception as e:
            p = {"error":"Failed to create lead magnet","details":str(e)}
            if settings.DEBUG: p["trace"] = traceback.format_exc()
            return Response(p, status=400)
    def options(self, request, *a, **k): return Response({"status":"ok"})


class ListTemplatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            db = Template.objects.all()
            if db.exists():
                return Response({"success":True,"templates":TemplateSerializer(db,many=True,context={"request":request}).data,"count":db.count()})
            svc = DocRaptorService()
            tmpls = svc.list_templates()
            for t in tmpls:
                p = os.path.join(settings.MEDIA_ROOT,"template_previews",f"{t['id']}.jpg")
                t["preview_url"] = request.build_absolute_uri(
                    f"{settings.MEDIA_URL}template_previews/{''+t['id']+'.jpg' if os.path.exists(p) else 'default.jpg'}")
            return Response({"success":True,"templates":tmpls,"count":len(tmpls)})
        except Exception as e:
            return Response({"success":False,"error":str(e)}, status=500)


class SelectTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @transaction.atomic
    def post(self, request):
        lm_id = request.data.get("lead_magnet_id")
        tid   = request.data.get("template_id")
        tname = request.data.get("template_name")
        src   = request.data.get("source","create-lead-magnet")
        if not all([lm_id, tid, tname]):
            return Response({"error":"lead_magnet_id, template_id, and template_name are required"}, status=400)
        valid = [c[0] for c in TemplateSelection.SOURCE_CHOICES]
        if src not in valid:
            return Response({"error":f"Invalid source. Must be one of: {', '.join(valid)}"}, status=400)
        try:
            lm = LeadMagnet.objects.get(id=lm_id, owner=request.user)
            ts, _ = TemplateSelection.objects.update_or_create(lead_magnet=lm, defaults={
                "user":request.user,"template_id":tid,"template_name":tname,
                "template_thumbnail":request.data.get("template_thumbnail",""),
                "captured_answers":request.data.get("captured_answers",{}),
                "image_upload_preference":request.data.get("image_upload_preference","no"),
                "source":src,"status":"template-selected",
            })
            return Response({"success":True,"template_selection_id":ts.id,"message":"Template selected"}, status=201)
        except LeadMagnet.DoesNotExist:
            return Response({"error":"Lead magnet not found"}, status=404)


class GenerateSloganView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            ua  = request.data.get("user_answers",{}) or {}
            fp  = FirmProfile.objects.filter(user=request.user).first()
            fn  = fp.firm_name if fp and fp.firm_name else request.user.email.split("@")[0]
            top = str(ua.get("main_topic","")).strip() or "Design"
            return Response({"success":True,"slogan":f"{fn}: {top}"})
        except Exception as e:
            return Response({"error":"Slogan generation failed","details":str(e)}, status=500)


class PreviewTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        tid  = request.data.get("template_id")
        if not tid: return Response({"error":"template_id is required"}, status=400)
        try:
            return Response({"success":True,"preview_html":DocRaptorService().preview_template(tid,request.data.get("variables",{}))})
        except Exception as e:
            return Response({"error":"Preview failed","details":str(e)}, status=500)


class HealthView(APIView):
    permission_classes     = [permissions.AllowAny]
    authentication_classes = []
    def get(self, request): return Response({"status":"ok"})
    def options(self, request, *a, **k): return Response({"status":"ok"})


class FormaAIConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        message         = request.data.get("message")
        files           = request.data.get("files",[])
        conversation_id = request.data.get("conversation_id")
        generate_pdf    = request.data.get("generate_pdf", True)
        template_id     = request.data.get("template_id","modern-guide")
        arch_imgs       = []

        for i in range(1,4):
            if f"architectural_image_{i}" in request.FILES:
                arch_imgs.append(request.FILES[f"architectural_image_{i}"])

        if not message:
            return Response({"error":"Message is required"}, status=400)

        if conversation_id:
            try:
                conv = FormaAIConversation.objects.get(id=conversation_id, user=request.user)
            except FormaAIConversation.DoesNotExist:
                return Response({"error":"Conversation not found"}, status=404)
        else:
            conv = FormaAIConversation.objects.create(user=request.user, messages=[])

        conv.messages.append({"role":"user","content":message,"files":files})
        firm  = _build_firm_profile(request.user)
        ua    = {"main_topic":message,"lead_magnet_type":"Custom Guide","desired_outcome":message.strip().replace("\n"," "),"industry":"Architecture"}
        ai    = GroqClient()
        svc   = DocRaptorService()

        try:
            sig  = ai.get_semantic_signals(ua)
            raw  = ai.generate_lead_magnet_json(sig, firm)
            cont = ai.normalize_ai_output(raw)
        except Exception as e:
            err = f"AI generation failed: {e}"
            logger.error(f"{err}\n{traceback.format_exc()}")
            conv.messages.append({"role":"assistant","content":err})
            conv.save()
            return Response({"error":err}, status=502)

        tvars = ai.map_to_template_vars(cont, firm, sig)
        tvars["companyName"]  = tvars.get("companyName")  or firm.get("firm_name") or "Your Company"
        tvars["emailAddress"] = tvars.get("emailAddress") or firm.get("work_email","")
        tvars["website"]      = tvars.get("website")      or firm.get("firm_website","")

        # Architectural images — only set when non-empty
        for i, img in enumerate(arch_imgs[:2]):
            import base64
            data = base64.b64encode(img.read()).decode("utf-8")
            ext  = img.name.split(".")[-1].lower()
            mime = f"image/{ext}" if ext in ("jpg","jpeg","png","gif") else "image/jpeg"
            tvars[f"image_{i+1}_url"] = f"data:{mime};base64,{data}"

        title = tvars.get("mainTitle") or "Generated Document"
        conv.messages.append({"role":"assistant","content":f"Generated: {title}."})
        conv.save()

        if generate_pdf:
            try:
                res = svc.generate_pdf(template_id, tvars)
                if res.get("success"):
                    r = HttpResponse(res["pdf_data"], content_type="application/pdf")
                    r["Content-Disposition"] = f'attachment; filename="{res.get("filename","document.pdf")}"'
                    return r
                return Response({"error":res.get("error","PDF failed"),"details":res.get("details","")}, status=500)
            except Exception as e:
                return Response({"error":"PDF failed","details":str(e)}, status=500)

        return Response({"success":True,"conversation_id":conv.id,"response":f"Generated: {title}.","messages":conv.messages,"template_id":template_id,"template_vars":tvars})


class GenerateDocumentPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            ua = request.data.get("user_answers")
            fp = request.data.get("firm_profile")
            if not isinstance(ua,dict) or not isinstance(fp,dict):
                return Response({"error":"user_answers and firm_profile must be objects"}, status=400)

            ai   = GroqClient()
            sig  = ai.get_semantic_signals(ua)
            raw  = ai.generate_lead_magnet_json(sig, fp)
            cont = ai.normalize_ai_output(raw)
            tvars= ai.map_to_template_vars(cont, fp, sig)

            path = os.path.join(settings.BASE_DIR,"lead_magnets","templates","Template.html")
            with open(path,"r",encoding="utf-8") as f:
                tmpl = f.read()

            return Response({"success":True,"preview_html":_render_template_vars(tmpl,tvars)})
        except Exception as e:
            logger.error(f"PreviewView: {e}\n{traceback.format_exc()}")
            return Response({"error":str(e)}, status=502)


class BrandAssetsPDFPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            try:
                fp = FirmProfile.objects.get(user=request.user)
            except FirmProfile.DoesNotExist:
                return Response({"error":"Firm profile not found."}, status=400)

            def abs_url(u):
                try: return request.build_absolute_uri(u) if u else ""
                except: return u or ""

            variables = {
                "companyName":fp.firm_name or "","phone":fp.phone_number or "",
                "email":fp.work_email or "","website":fp.firm_website or "",
                "primaryColor":fp.primary_brand_color or "#2a5766",
                "secondaryColor":fp.secondary_brand_color or "#FFFFFF",
                "logoUrl":abs_url(fp.logo.url) if fp.logo else "",
                "brandGuidelines":fp.branding_guidelines or "",
            }
            hex_re  = re.compile(r"^#([A-Fa-f0-9]{6})$")
            missing = [k for k in ("companyName","phone","email","primaryColor","secondaryColor") if not variables.get(k)]
            if missing: return Response({"error":"Missing fields","missing":missing}, status=400)
            invalid = [c for c in ("primaryColor","secondaryColor") if not hex_re.match(variables.get(c,""))]
            if invalid: return Response({"error":"Invalid color formats","invalid_colors":invalid}, status=400)

            res = DocRaptorService().generate_pdf("brand-assets", variables)
            if res.get("success"):
                r = HttpResponse(res.get("pdf_data",b""), content_type="application/pdf")
                r["Content-Disposition"] = 'attachment; filename="brand-assets-preview.pdf"'
                return r
            return Response({"error":"PDF failed","details":res.get("details","")}, status=502)
        except Exception as e:
            return Response({"error":"Unexpected error","details":str(e)}, status=500)