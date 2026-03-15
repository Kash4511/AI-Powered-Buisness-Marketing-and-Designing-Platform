import os
import logging
import json
import uuid
import time
import traceback
import threading
from datetime import datetime, timedelta
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.http import FileResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import requests
from .models import (
    LeadMagnet, Lead, Download, FirmProfile, LeadMagnetGeneration,
    FormaAIConversation, TemplateSelection
)
from .serializers import (
    LeadMagnetSerializer, LeadSerializer, DashboardStatsSerializer,
    FirmProfileSerializer, LeadMagnetGenerationSerializer, CreateLeadMagnetSerializer,
    TemplateSerializer
)
from .services import DocRaptorService, render_template
from .reportlab_service import ReportLabService
from .groq_client import GroqClient
from .models import Template
from .config_helper import get_config

logger = logging.getLogger(__name__)

_JOBS = {}
_JOBS_LOCK = threading.Lock()


def _set_job(job_id, **kwargs):
    with _JOBS_LOCK:
        if job_id not in _JOBS:
            _JOBS[job_id] = {"created_at": datetime.utcnow()}
        _JOBS[job_id].update(kwargs)


def _get_job(job_id):
    with _JOBS_LOCK:
        return dict(_JOBS.get(job_id, {}))


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE RENDERER — replaces {{var}} and {{#if var}}...{{/if}} blocks
# ─────────────────────────────────────────────────────────────────────────────

import re as _re


def _render_template_vars(html: str, vars_dict: dict) -> str:
    """
    Two-pass renderer:
      Pass 1 — resolve {{#if key}}...{{/if}} blocks
      Pass 2 — replace {{key}} with values (HTML-safe for section HTML, escaped elsewhere)
    """
    # Pass 1: conditional blocks  {{#if key}}...{{/if}}
    def _resolve_if(m):
        key      = m.group(1).strip()
        content  = m.group(2)
        val      = vars_dict.get(key, "")
        # Explicit check for truthiness — empty string, None, False are falsy
        return content if (val and str(val).strip()) else ""

    html = _re.sub(
        r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}',
        _resolve_if,
        html,
        flags=_re.DOTALL,
    )

    # Pass 2: simple {{key}} substitution
    def _replace_var(m):
        key = m.group(1).strip()
        val = vars_dict.get(key, "")
        if val is None:
            val = ""
        val_str = str(val)
        # All keys ending in _html or starting with customTitle contain raw content
        if key.endswith("_html") or key.startswith("customTitle"):
            return val_str
        # All other values are plain text — must be HTML-escaped
        return val_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html = _re.sub(r'\{\{(\w+)\}\}', _replace_var, html)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_company_name(name: str, email: str = "") -> str:
    """
    Detects username-style strings (no spaces, all lowercase, has digits) 
    and derives a better name from the email domain or title-cases the username.
    """
    default_company = get_config("default_company_name", "Your Company")
    if not email:
        return name or default_company
        
    username = email.split("@")[0]
    # If name is missing or matches the username fallback
    if not name or name == username:
        # Check if username looks like a 'kaashifameen32' style string
        is_username_style = username.islower() and any(c.isdigit() for c in username) and " " not in username
        
        if is_username_style:
            domain_part = email.split("@")[-1].split(".")[0]
            # If domain isn't a common provider, use it
            common_providers = get_config("common_email_providers", ["gmail", "outlook", "hotmail", "yahoo", "icloud", "me"])
            if domain_part.lower() not in common_providers:
                return domain_part.title()
            # Fallback: title case the username and strip digits
            return _re.sub(r'\d+', '', username).title()
        return username.title()
    return name


def _resolve_image_url(img) -> str:
    if not img:
        return ""
    if isinstance(img, str):
        return img.strip()
    if isinstance(img, dict):
        return (img.get("src") or img.get("url") or "").strip()
    return ""


def _build_firm_profile(user, fp_obj=None) -> dict:
    """Build a consistent firm_profile dict from a FirmProfile ORM object or defaults."""
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
            "industry":              get_config("default_industry", "Architecture"),
            "branding_guidelines":   fp_obj.branding_guidelines or "",
        }
    return {
        "firm_name":             _clean_company_name("", email),
        "work_email":            email,
        "phone_number":          "",
        "firm_website":          "",
        "primary_brand_color":   "",
        "secondary_brand_color": "",
        "logo_url":              "",
        "industry":              get_config("default_industry", "Architecture"),
        "branding_guidelines":   "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# STANDARD VIEWS (unchanged API surface)
# ─────────────────────────────────────────────────────────────────────────────

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_lead_magnets    = LeadMagnet.objects.filter(owner=user)
        total_lead_magnets   = user_lead_magnets.count()
        active_lead_magnets  = user_lead_magnets.filter(Q(status="completed") | Q(status="in-progress")).count()
        total_downloads      = Download.objects.filter(lead_magnet__owner=user).count()
        leads_generated      = Lead.objects.filter(lead_magnet__owner=user).count()
        stats = {
            "total_lead_magnets":  total_lead_magnets,
            "active_lead_magnets": active_lead_magnets,
            "total_downloads":     total_downloads,
            "leads_generated":     leads_generated,
        }
        return Response(DashboardStatsSerializer(stats).data)


class LeadMagnetListCreateView(generics.ListCreateAPIView):
    serializer_class   = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeadMagnet.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LeadMagnetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeadMagnet.objects.filter(owner=self.request.user)


class FirmProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = FirmProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        profile, _ = FirmProfile.objects.get_or_create(
            user=user,
            defaults={
                "firm_name":             user.email.split("@")[0] if getattr(user, "email", "") else "Firm",
                "work_email":            getattr(user, "email", "") or "no-reply@example.com",
                "phone_number":          "",
                "firm_website":          "",
                "firm_size":             "1-2",
                "industry_specialties":  [],
                "primary_brand_color":   "",
                "secondary_brand_color": "",
                "preferred_font_style":  "no-preference",
                "branding_guidelines":   "",
                "location":              "",
            },
        )
        return profile

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        data     = request.data.copy()

        if hasattr(request.data, "getlist"):
            processed_data = {}
            for key in request.data.keys():
                if key == "industry_specialties":
                    specialties = request.data.getlist(key)
                    if len(specialties) == 1 and isinstance(specialties[0], str) and specialties[0].startswith("["):
                        try:
                            processed_data[key] = json.loads(specialties[0])
                        except json.JSONDecodeError:
                            processed_data[key] = specialties
                    else:
                        processed_data[key] = specialties
                else:
                    processed_data[key] = request.data.get(key)
            data = processed_data

        for key in list(data.keys()):
            val = data[key]
            if val in ("", "null", "undefined"):
                if key in ("logo", "preferred_cover_image"):
                    data[key] = None
                elif key in ("firm_website", "primary_brand_color", "secondary_brand_color",
                             "phone_number", "location", "branding_guidelines"):
                    data[key] = ""
            if key == "firm_website" and data[key] and isinstance(data[key], str):
                url = data[key].strip().lower()
                if url and not url.startswith(("http://", "https://")):
                    data[key] = f"https://{url}"

        for key in ("logo", "preferred_cover_image"):
            if key in data and isinstance(data[key], str):
                data.pop(key)

        if "industry_specialties" in data and data["industry_specialties"] is None:
            data["industry_specialties"] = []

        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)

        logger.error(f"FirmProfile update failed for {request.user.email}: {serializer.errors}")
        return Response(
            {"error": "Firm profile update failed", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_theme_palette(request):
    """
    Returns hex values for primary, secondary, surface, and on-surface colors.
    Reacts to user preferences or system dark-mode toggles (if provided).
    """
    is_dark_mode = request.query_params.get('mode') == 'dark'
    
    # Defaults
    palette = {
        "primary":    get_config("palette_primary", "#1a365d"),
        "secondary":  get_config("palette_secondary", "#c5a059"),
        "surface":    get_config("palette_surface", "#ffffff"),
        "onSurface":  get_config("palette_on_surface", "#1a202c"),
        "accent":     get_config("palette_accent", "#f8fafc"),
        "highlight":  get_config("palette_highlight", "#e8f4f8"),
    }
    
    # Try fetching from user's firm profile
    try:
        fp = FirmProfile.objects.get(user=request.user)
        if fp.primary_brand_color:
            palette["primary"] = fp.primary_brand_color
        if fp.secondary_brand_color:
            palette["secondary"] = fp.secondary_brand_color
    except FirmProfile.DoesNotExist:
        pass
        
    # Dark mode adjustments
    if is_dark_mode:
        palette.update(get_config("palette_dark_mode", {
            "surface":   "#1a202c",
            "onSurface": "#f7fafc",
            "accent":    "#2d3748",
            "highlight": "#4a5568",
        }))
        
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
        user_answers         = body.get("user_answers", {}) or {}
        architectural_images = body.get("architectural_images", [])

        if not template_id or not lead_magnet_id:
            _set_job(job_id, status="failed", error="template_id and lead_magnet_id are required")
            return

        _set_job(job_id, status="processing", progress=5, message=get_config("job_msg_parsing", "Parsing request..."), lead_magnet_id=lead_magnet_id)

        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=user)
        except LeadMagnet.DoesNotExist:
            _set_job(job_id, status="failed", error=get_config("job_err_not_found", "Lead magnet not found"))
            return

        gen_data = getattr(lead_magnet, "generation_data", None)
        if not gen_data:
            _set_job(job_id, status="failed", error=get_config("job_err_missing_data", "Lead magnet is missing generation data"))
            return

        ai_client = GroqClient()

        ai_input_data = {
            "main_topic":       gen_data.main_topic,
            "target_audience":  gen_data.target_audience,
            "pain_points": (
                gen_data.audience_pain_points
                if isinstance(gen_data.audience_pain_points, list)
                else [gen_data.audience_pain_points]
            ),
            "tone":             get_config("default_tone", "Professional and Institutional"),
            "industry":         get_config("default_industry", "Architecture"),
            "document_type":    gen_data.lead_magnet_type or get_config("default_doc_type", "guide"),
            "lead_magnet_type": gen_data.lead_magnet_type or get_config("default_lead_magnet_type_label", "Strategic Guide"),
        }


        logger.info(f"🔍 gen_data.lead_magnet_type = '{gen_data.lead_magnet_type}'")
        logger.info(f"🔍 ai_input_data document_type = '{ai_input_data['document_type']}'")

        # Build firm profile
        firm_profile = _build_firm_profile(user)

        # Inject architectural image URLs
        for i in range(1, 7):
            raw_img = architectural_images[i - 1] if len(architectural_images) >= i else ""
            url     = _resolve_image_url(raw_img)
            firm_profile[f"image_{i}_url"]     = url
            firm_profile[f"image_{i}_caption"] = f"{get_config('default_image_caption_prefix', 'Project Insight')} {i}"

        template_vars: dict = {}

        if use_ai_content:
            try:
                _set_job(job_id, status="processing", progress=15,
                         message=get_config("job_msg_generating", "Generating deep AI content via Groq... (~20s)"))
                start_ai = time.time()
                logger.info("🤖 AI Generation Start via Groq")

                signals        = ai_client.get_semantic_signals(ai_input_data)
                raw_ai_content = ai_client.generate_lead_magnet_json(signals, firm_profile)
                ai_content     = ai_client.normalize_ai_output(raw_ai_content)

                logger.info(f"📊 AI Generation Success | {time.time() - start_ai:.2f}s")

                # Guard: verify all 11 sections produced content
                empty_sections = [
                    key for key, *_ in ai_client.SECTIONS
                    if not ai_content.get(key)
                ]
                if empty_sections:
                    logger.warning(f"⚠️ Empty sections after generation: {empty_sections}")

                _set_job(job_id, status="processing", progress=65, message=get_config("job_msg_mapping", "Mapping content to template..."))

                template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, signals)

                # ── CRITICAL: inject full section HTML for the template renderer ──
                # The template uses {{section_<key>_html}} for each of the 11 sections.
                for key, *_ in ai_client.SECTIONS:
                    html_key = f"section_{key}_html"
                    if not template_vars.get(html_key):
                        template_vars[html_key] = ai_content.get(key, "")

                # Ensure firm data is never empty
                topic = signals.get("topic", get_config("default_topic", "Industry"))
                template_vars["companyName"]  = template_vars.get("companyName")  or firm_profile.get("firm_name") or f"{topic} {get_config('default_company_suffix', 'Experts')}"
                template_vars["emailAddress"] = template_vars.get("emailAddress") or firm_profile.get("work_email", "")
                template_vars["phoneNumber"]  = template_vars.get("phoneNumber")  or firm_profile.get("phone_number", "")
                template_vars["website"]      = template_vars.get("website")      or firm_profile.get("firm_website", "")


                # Page numbers
                for n in range(2, 16):
                    template_vars[f"pageNumber{n}"]       = str(n).zfill(2)
                    template_vars[f"pageNumberHeader{n}"] = str(n).zfill(2)

                logger.info(f"[DEBUG] template_vars keys: {len(template_vars)}")
                logger.info(f"[DEBUG] sample: { {k: str(v)[:50] for k, v in list(template_vars.items())[:8]} }")

            except ValueError as ve:
                err = str(ve)
                if "max completion tokens" in err:
                    err = "Content too long for one pass. Try a shorter topic or contact support."
                _set_job(job_id, status="failed", error=f"AI Error: {err}")
                return
            except Exception as e:
                logger.error(f"AI Pipeline Error: {e}\n{traceback.format_exc()}")
                _set_job(job_id, status="failed", error=f"AI generation failed: {e}")
                return
        else:
            template_vars = {
                "primaryColor":     firm_profile.get("primary_brand_color") or get_config("palette_primary", "#1a365d"),
                "secondaryColor":   firm_profile.get("secondary_brand_color") or get_config("palette_secondary", "#c5a059"),
                "companyName":      firm_profile.get("firm_name") or "",
                "mainTitle":        lead_magnet.title,
                "documentSubtitle": get_config("default_subtitle_label", "Professional Insights"),
                "emailAddress":     firm_profile.get("work_email") or "",
                "phoneNumber":      firm_profile.get("phone_number") or "",
                "website":          firm_profile.get("firm_website") or "",
            }
            for key, *_ in GroqClient.SECTIONS:
                template_vars[f"section_{key}_html"] = ""

        # ── PDF RENDERING ──────────────────────────────────────────────────────
        pdf_service = DocRaptorService()
        try:
            _set_job(job_id, status="processing", progress=75,
                     message=get_config("job_msg_rendering", "Rendering PDF via DocRaptor..."))
            start_pdf = time.time()

            docraptor_vars = template_vars.copy()

            # Ensure images pass through
            for i in range(1, 7):
                docraptor_vars[f"image_{i}_url"]     = firm_profile.get(f"image_{i}_url", "")
                docraptor_vars[f"image_{i}_caption"] = firm_profile.get(f"image_{i}_caption", f"{get_config('default_image_caption_prefix', 'Project Insight')} {i}")

            # Ensure colours are set
            docraptor_vars["primaryColor"]   = template_vars.get("primaryColor")   or get_config("palette_primary", "#2a5766")
            docraptor_vars["secondaryColor"] = template_vars.get("secondaryColor") or get_config("palette_secondary", "#c5a059")
            docraptor_vars["accentColor"]    = template_vars.get("accentColor")    or get_config("palette_accent", "#f8fafc")

            # Pass architectural_images list for any Jinja2-style conditional in templates
            docraptor_vars["architecturalImages"] = architectural_images

            _set_job(job_id, status="processing", progress=82,
                     message=get_config("job_msg_docraptor", "DocRaptor rendering your 15-page PDF..."))
            result      = pdf_service.generate_pdf("modern-guide", docraptor_vars)
            pdf_duration = time.time() - start_pdf

            if not result.get("success"):
                err     = result.get("error", get_config("job_err_pdf_failed", "PDF generation failed"))
                details = result.get("details", "")
                logger.error(f"PDF Failure: {err} | {details} | {pdf_duration:.2f}s")
                _set_job(job_id, status="failed", error=f"{err}: {details}")
                return

            _set_job(job_id, status="processing", progress=92, message=get_config("job_msg_saving", "Saving to cloud storage..."))

            pdf_data = result.get("pdf_data")
            filename = result.get("filename", f"lead-magnet-{lead_magnet_id}.pdf")

            try:
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(
                    pdf_data,
                    resource_type="raw",
                    folder="lead_magnets",
                    public_id=f"lead-magnet-{lead_magnet_id}-{uuid.uuid4().hex[:8]}",
                )
                public_id            = upload_result.get("public_id")
                lead_magnet.pdf_file = public_id
                lead_magnet.status   = "completed"
                lead_magnet.save(update_fields=["pdf_file", "status"])
                logger.info(f"✅ Cloudinary upload: {public_id}")
            except Exception as upload_err:
                logger.error(f"Cloudinary upload failed, falling back: {upload_err}")
                lead_magnet.pdf_file.save(filename, ContentFile(pdf_data), save=True)
                lead_magnet.status = "completed"
                lead_magnet.save(update_fields=["status"])

            logger.info(f"✅ PDF complete | {pdf_duration:.2f}s")
            _set_job(job_id, status="complete", progress=100,
                     pdf_url=f"/api/lead-magnets/{lead_magnet_id}/download/",
                     message=get_config("job_msg_complete", "Your PDF is ready!"))

        except Exception as e:
            logger.error(f"PDF Rendering Error: {e}\n{traceback.format_exc()}")
            _set_job(job_id, status="failed", error=f"PDF rendering failed: {e}")
            return

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
    body   = request.data
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None)
    threading.Thread(
        target=_run_generation_job,
        args=(job_id, body, request.user.id),
        daemon=True,
    ).start()
    return Response({"job_id": job_id, "status": "pending"}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status(request, job_id):
    job = _get_job(job_id)
    if not job:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response({
        "job_id":   job_id,
        "status":   job.get("status"),
        "progress": job.get("progress", 0),
        "message":  job.get("message", ""),
        "pdf_url":  job.get("pdf_url"),
        "error":    job.get("error"),
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_compat(request):
    body   = request.data
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None,
             lead_magnet_id=body.get("lead_magnet_id"))
    threading.Thread(
        target=_run_generation_job,
        args=(job_id, body, request.user.id),
        daemon=True,
    ).start()
    status_url = request.build_absolute_uri(
        f"/api/generate-pdf/status/?lead_magnet_id={body.get('lead_magnet_id')}&job_id={job_id}"
    )
    return Response({
        "status":              "in_progress",
        "message":             "PDF generation started",
        "lead_magnet_id":      body.get("lead_magnet_id"),
        "status_url":          status_url,
        "retry_after_seconds": 3,
    }, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status_compat(request):
    lead_magnet_id = request.query_params.get("lead_magnet_id")
    job_id         = request.query_params.get("job_id")
    if not lead_magnet_id:
        return Response({"error": "lead_magnet_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    job = None
    if job_id:
        job = _get_job(job_id)
    else:
        with _JOBS_LOCK:
            for k, v in reversed(list(_JOBS.items())):
                if str(v.get("lead_magnet_id")) == str(lead_magnet_id):
                    job = dict(v)
                    break

    try:
        lm = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
    except LeadMagnet.DoesNotExist:
        return Response({"error": "Lead magnet not found"}, status=status.HTTP_404_NOT_FOUND)

    if str(lm.status) == "completed" and lm.pdf_file:
        return Response({"status": "ready", "pdf_url": f"/api/lead-magnets/{lead_magnet_id}/download/"})

    if job:
        if job.get("status") == "complete" and lm.pdf_file:
            return Response({"status": "ready", "pdf_url": f"/api/lead-magnets/{lead_magnet_id}/download/"})
        if job.get("status") in ("failed", "error"):
            return Response({"status": "error", "error": job.get("error", "Generation failed")})
        return Response({"status": "pending"})

    return Response({"status": "pending"})


from cloudinary.utils import cloudinary_url as get_cloudinary_url


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def download_lead_magnet_pdf(request, lead_magnet_id: int):
    try:
        try:
            lm = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
        except LeadMagnet.DoesNotExist:
            return Response({"error": "Lead magnet not found"}, status=status.HTTP_404_NOT_FOUND)

        if not lm.pdf_file:
            return Response({"error": "PDF not generated yet"}, status=status.HTTP_404_NOT_FOUND)

        try:
            public_id  = lm.pdf_file.name
            signed_url, _ = get_cloudinary_url(
                public_id, resource_type="raw", sign_url=True, secure=True
            )
            proxy_resp = requests.get(signed_url, stream=True, timeout=30)
            proxy_resp.raise_for_status()
            filename = os.path.basename(lm.pdf_file.name) or f"lead-magnet-{lead_magnet_id}.pdf"
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            response                    = FileResponse(proxy_resp.raw, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            if "Content-Length" in proxy_resp.headers:
                response["Content-Length"] = proxy_resp.headers["Content-Length"]
            return response
        except Exception as e:
            logger.error(f"Signed URL / stream error for LM {lead_magnet_id}: {e}")
            return Response(
                {"error": "Failed to retrieve file", "details": str(e) if settings.DEBUG else None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as exc:
        logger.critical(f"Critical download error: {exc}\n{traceback.format_exc()}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateLeadMagnetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            serializer = CreateLeadMagnetSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            lead_magnet = serializer.save()
            return Response(LeadMagnetSerializer(lead_magnet).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = {"error": "Failed to create lead magnet", "details": str(e)}
            if settings.DEBUG:
                payload["trace"] = traceback.format_exc()
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def options(self, request, *args, **kwargs):
        return Response({"status": "ok"})


class ListTemplatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            db_templates = Template.objects.all()
            if db_templates.exists():
                data = TemplateSerializer(db_templates, many=True, context={"request": request}).data
                return Response({"success": True, "templates": data, "count": len(data)})

            template_service = DocRaptorService()
            templates        = template_service.list_templates()
            for template in templates:
                template_id      = template["id"]
                preview_path     = os.path.join(settings.MEDIA_ROOT, "template_previews", f"{template_id}.jpg")
                template["preview_url"] = request.build_absolute_uri(
                    f"{settings.MEDIA_URL}template_previews/{''+template_id+'.jpg' if os.path.exists(preview_path) else 'default.jpg'}"
                )
            return Response({"success": True, "templates": templates, "count": len(templates)})

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SelectTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        lead_magnet_id     = request.data.get("lead_magnet_id")
        template_id        = request.data.get("template_id")
        template_name      = request.data.get("template_name")
        template_thumbnail = request.data.get("template_thumbnail", "")
        captured_answers   = request.data.get("captured_answers", {})
        source             = request.data.get("source", "create-lead-magnet")

        if not all([lead_magnet_id, template_id, template_name]):
            return Response(
                {"error": "lead_magnet_id, template_id, and template_name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_sources = [choice[0] for choice in TemplateSelection.SOURCE_CHOICES]
        if source not in valid_sources:
            return Response({"error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"}, status=400)

        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
            ts, created = TemplateSelection.objects.update_or_create(
                lead_magnet=lead_magnet,
                defaults={
                    "user":                    request.user,
                    "template_id":             template_id,
                    "template_name":           template_name,
                    "template_thumbnail":      template_thumbnail,
                    "captured_answers":        captured_answers,
                    "image_upload_preference": request.data.get("image_upload_preference", "no"),
                    "source":                  source,
                    "status":                  "template-selected",
                },
            )
            return Response({"success": True, "template_selection_id": ts.id, "message": "Template selected"}, status=201)
        except LeadMagnet.DoesNotExist:
            return Response({"error": "Lead magnet not found"}, status=status.HTTP_404_NOT_FOUND)


class GenerateSloganView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user_answers = request.data.get("user_answers", {}) or {}
            fp           = FirmProfile.objects.filter(user=request.user).first()
            firm_name    = fp.firm_name if fp and fp.firm_name else request.user.email.split("@")[0]
            topic        = str(user_answers.get("main_topic", "")).strip() or "Design"
            slogan       = f"{firm_name}: {topic}"
            return Response({"success": True, "slogan": slogan})
        except Exception as e:
            return Response({"error": "Slogan generation failed", "details": str(e)}, status=500)


class PreviewTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        template_id = request.data.get("template_id")
        variables   = request.data.get("variables", {})
        if not template_id:
            return Response({"error": "template_id is required"}, status=400)
        try:
            template_service = DocRaptorService()
            preview_html     = template_service.preview_template(template_id, variables)
            return Response({"success": True, "preview_html": preview_html})
        except Exception as e:
            return Response({"error": "Preview failed", "details": str(e)}, status=500)


class HealthView(APIView):
    permission_classes     = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})

    def options(self, request, *args, **kwargs):
        return Response({"status": "ok"})


class FormaAIConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        message              = request.data.get("message")
        files                = request.data.get("files", [])
        conversation_id      = request.data.get("conversation_id")
        generate_pdf         = request.data.get("generate_pdf", True)
        template_id          = request.data.get("template_id", "modern-guide")
        architectural_images = []

        for i in range(1, 4):
            image_key = f"architectural_image_{i}"
            if image_key in request.FILES:
                architectural_images.append(request.FILES[image_key])

        if not message:
            return Response({"error": "Message is required"}, status=400)

        if conversation_id:
            try:
                conversation = FormaAIConversation.objects.get(id=conversation_id, user=request.user)
            except FormaAIConversation.DoesNotExist:
                return Response({"error": "Conversation not found"}, status=404)
        else:
            conversation = FormaAIConversation.objects.create(user=request.user, messages=[])

        conversation.messages.append({"role": "user", "content": message, "files": files})

        firm_profile = _build_firm_profile(request.user)
        user_answers = {
            "main_topic":            message,
            "lead_magnet_type":      get_config("forma_ai_default_type", "Custom Guide"),
            "desired_outcome":       message.strip().replace("\n", " "),
            "industry":              get_config("default_industry", "Architecture"),
            "brand_primary_color":   firm_profile.get("primary_brand_color", ""),
            "brand_secondary_color": firm_profile.get("secondary_brand_color", ""),
            "brand_logo_url":        firm_profile.get("logo_url", ""),
        }

        ai_client        = GroqClient()
        template_service = ReportLabService()

        try:
            signals        = ai_client.get_semantic_signals(user_answers)
            raw_ai_content = ai_client.generate_lead_magnet_json(signals, firm_profile)
            ai_content     = ai_client.normalize_ai_output(raw_ai_content)
        except Exception as e:
            err = f"AI generation failed: {e}"
            logger.error(f"{err}\n{traceback.format_exc()}")
            conversation.messages.append({"role": "assistant", "content": err})
            conversation.save()
            return Response({"error": err}, status=502)

        template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, signals)

        # Inject full section HTML
        for key, *_ in ai_client.SECTIONS:
            html_key = f"section_{key}_html"
            if not template_vars.get(html_key):
                template_vars[html_key] = ai_content.get(key, "")

        # Firm overrides
        template_vars["companyName"]  = template_vars.get("companyName")  or firm_profile.get("firm_name") or "Your Company"
        template_vars["emailAddress"] = template_vars.get("emailAddress") or firm_profile.get("work_email", "")
        template_vars["phoneNumber"]  = template_vars.get("phoneNumber")  or firm_profile.get("phone_number", "")
        template_vars["website"]      = template_vars.get("website")      or firm_profile.get("firm_website", "")

        # Subtitle cleanup
        sub = (template_vars.get("documentSubtitle") or "").strip()
        sub = re.sub(r"^\s*generate\s+professional\s+pdf.*?(showcasing|about|on)?\s*", "", sub, flags=re.I)
        sub = re.sub(r"\s*(for|in)\s+architecture\b.*$", "", sub, flags=re.I).strip(" -:;")
        if sub:
            template_vars["documentSubtitle"] = sub

        # Title fallback
        if not template_vars.get("mainTitle"):
            topic   = user_answers.get("main_topic") or "Architectural Design"
            lm_type = user_answers.get("lead_magnet_type") or "Guide"
            template_vars["mainTitle"] = " ".join(w.capitalize() for w in f"The {topic} {lm_type}".split())

        # Architectural images as base64
        if architectural_images:
            template_vars["architecturalImages"] = []
            for i, image in enumerate(architectural_images[:3]):
                import base64
                img_data  = base64.b64encode(image.read()).decode("utf-8")
                ext       = image.name.split(".")[-1].lower()
                mime      = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "gif") else "image/jpeg"
                src       = f"data:{mime};base64,{img_data}"
                template_vars["architecturalImages"].append({"src": src, "alt": f"Image {i+1}"})
                template_vars[f"image_{i+1}_url"] = src

        summary_title = template_vars.get("mainTitle") or "Generated Document"
        conversation.messages.append({"role": "assistant", "content": f"Generated: {summary_title}."})
        conversation.save()

        if generate_pdf:
            try:
                result = template_service.generate_pdf(template_id, template_vars)
                if result.get("success"):
                    pdf_data = result.get("pdf_data", b"")
                    response = HttpResponse(pdf_data, content_type=result.get("content_type", "application/pdf"))
                    response["Content-Disposition"] = f'attachment; filename="{result.get("filename", "document.pdf")}"'
                    return response
                return Response({"error": result.get("error", "PDF failed"), "details": result.get("details", "")}, status=500)
            except Exception as e:
                return Response({"error": "PDF failed", "details": str(e)}, status=500)

        return Response({
            "success":         True,
            "conversation_id": conversation.id,
            "response":        f"Generated: {summary_title}.",
            "messages":        conversation.messages,
            "template_id":     template_id,
            "template_vars":   template_vars,
        })


class GenerateDocumentPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user_answers = request.data.get("user_answers")
            firm_profile = request.data.get("firm_profile")
            template_id  = request.data.get("template_id", "modern-guide")

            if not isinstance(user_answers, dict) or not isinstance(firm_profile, dict):
                return Response({"error": "user_answers and firm_profile must be objects"}, status=400)

            ai_client     = GroqClient()
            signals       = ai_client.get_semantic_signals(user_answers)
            raw_ai_data   = ai_client.generate_lead_magnet_json(signals, firm_profile)
            ai_data       = ai_client.normalize_ai_output(raw_ai_data)
            template_vars = ai_client.map_to_template_vars(ai_data, firm_profile, signals)

            # Inject section HTML
            for key, *_ in ai_client.SECTIONS:
                html_key = f"section_{key}_html"
                if not template_vars.get(html_key):
                    template_vars[html_key] = ai_data.get(key, "")

            template_path = os.path.join(settings.BASE_DIR, "lead_magnets", "templates", "Template.html")
            with open(template_path, "r", encoding="utf-8") as f:
                template_html = f.read()

            final_html = _render_template_vars(template_html, template_vars)
            return Response({"success": True, "preview_html": final_html})
        except Exception as e:
            logger.error(f"GenerateDocumentPreviewView error: {e}\n{traceback.format_exc()}")
            return Response({"error": str(e)}, status=502)


class BrandAssetsPDFPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            try:
                fp = FirmProfile.objects.get(user=user)
            except FirmProfile.DoesNotExist:
                return Response({"error": "Firm profile not found."}, status=400)

            def abs_url(url):
                try:
                    return request.build_absolute_uri(url) if url else ""
                except Exception:
                    return url or ""

            variables = {
                "companyName":     fp.firm_name or "",
                "phone":           fp.phone_number or "",
                "email":           fp.work_email or "",
                "website":         fp.firm_website or "",
                "primaryColor":    fp.primary_brand_color or get_config("palette_primary", "#2a5766"),
                "secondaryColor":  fp.secondary_brand_color or get_config("palette_white", "#FFFFFF"),
                "logoUrl":         abs_url(fp.logo.url) if fp.logo else "",
                "brandGuidelines": fp.branding_guidelines or "",
            }

            missing = [k for k in ("companyName", "phone", "email", "primaryColor", "secondaryColor") if not variables.get(k)]
            if missing:
                return Response({"error": "Missing fields", "missing": missing}, status=400)

            import re as _re2
            hex_re = _re2.compile(r"^#([A-Fa-f0-9]{6})$")
            invalid = [c for c in ("primaryColor", "secondaryColor") if not hex_re.match(variables.get(c, ""))]
            if invalid:
                return Response({"error": "Invalid color formats", "invalid_colors": invalid}, status=400)

            template_service = DocRaptorService()
            result           = template_service.generate_pdf("brand-assets", variables)
            if result.get("success"):
                resp                        = HttpResponse(result.get("pdf_data", b""), content_type="application/pdf")
                resp["Content-Disposition"] = 'attachment; filename="brand-assets-preview.pdf"'
                return resp
            return Response({"error": "PDF failed", "details": result.get("details", "")}, status=502)
        except Exception as e:
            return Response({"error": "Unexpected error", "details": str(e)}, status=500)