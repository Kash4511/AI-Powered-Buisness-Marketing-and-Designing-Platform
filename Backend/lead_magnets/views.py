import os
import re
import logging
import json
import uuid
import time
import traceback
import threading
from datetime import datetime
from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.db.models import Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
import requests
from django.db import connection
from .models import (
    LeadMagnet, Lead, Download, FirmProfile,
    FormaAIConversation, TemplateSelection, Template,
    PDFGenerationJob, LeadMagnetGeneration,
)
from .serializers import (
    LeadMagnetSerializer, LeadSerializer, DashboardStatsSerializer,
    FirmProfileSerializer, LeadMagnetGenerationSerializer,
    CreateLeadMagnetSerializer, TemplateSerializer,
)
from .services import WeasyPrintService, render_template
from .groq_client import GroqClient

logger = logging.getLogger(__name__)

def _set_job(job_id: str, **kwargs):
    """
    Sets or updates a PDFGenerationJob. 
    Ensures lead_magnet_id is preserved if already set and not provided in kwargs.
    """
    # Normalize lead_magnet vs lead_magnet_id
    if 'lead_magnet' in kwargs:
        lm = kwargs.pop('lead_magnet')
        if lm:
            kwargs['lead_magnet_id'] = lm.id if hasattr(lm, 'id') else lm

    # If lead_magnet_id is still not provided, try to find it from existing job
    if not kwargs.get('lead_magnet_id'):
        try:
            existing_lm_id = PDFGenerationJob.objects.filter(
                job_id=job_id
            ).values_list('lead_magnet_id', flat=True).first()
            if existing_lm_id:
                kwargs['lead_magnet_id'] = existing_lm_id
        except Exception:
            pass
            
    # Use update_or_create to handle both new and existing jobs
    # We use job_id as the lookup field
    PDFGenerationJob.objects.update_or_create(
        job_id=job_id, 
        defaults=kwargs
    )


def _get_job(job_id: str) -> dict:
    try:
        job = PDFGenerationJob.objects.get(job_id=job_id)
        return {
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "pdf_url": job.pdf_url,
            "error": job.error,
            "lead_magnet_id": job.lead_magnet_id,
        }
    except PDFGenerationJob.DoesNotExist:
        return {}


def _should_stop(job_id: str) -> bool:
    try:
        return PDFGenerationJob.objects.get(job_id=job_id).stop_requested
    except PDFGenerationJob.DoesNotExist:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET', 'HEAD'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Simple health check endpoint that returns 200 OK.
    Used by Render to verify the service is running.
    Handles HEAD requests to prevent 405 Method Not Allowed errors in logs.
    """
    if request.method == 'HEAD':
        return Response(status=status.HTTP_200_OK)

    return Response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

TARGET_CHARS_PER_PAGE = 2200
MAX_CHARS_PER_PAGE = 2800
MIN_FILL_RATIO = 0.4

def _cld_url(public_id, **kwargs):
    import cloudinary.utils
    return cloudinary.utils.cloudinary_url(public_id, **kwargs)


def create_page_html(content_html, page_num, kicker, title, image_html=""):
    num_str = str(page_num).zfill(2)
    return f"""
        <div class="page content-page" style="clear: both;">
            <div class="string-container">
                <span class="page-header-kicker">{kicker}</span>
                <div class="page-header-title">{title}</div>
            </div>

            <div class="page-body">
                <div class="section-intro-block">
                    <div class="section-intro-num">{num_str}</div>
                    <div class="section-headline">{title}</div>
                </div>
                
                {image_html}
                
                <div class="section-content">
                    {content_html}
                </div>
            </div>
        </div>
    """


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
        try:
            user = request.user
            ulm  = LeadMagnet.objects.filter(owner=user)
            
            # Calculate real AI Credit stats from PDFGenerationJob
            total_credits = 10000000
            if user.is_superuser:
                total_credits = 999999999
                
            from django.db.models import Sum
            # Count tokens from ALL jobs associated with the user, regardless of status
            used_credits = PDFGenerationJob.objects.filter(
                lead_magnet__owner=user
            ).aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0
            
            remaining_credits = max(0, total_credits - used_credits)

            return Response(DashboardStatsSerializer({
                "total_lead_magnets":  ulm.count(),
                "active_lead_magnets": ulm.filter(Q(status="completed") | Q(status="in-progress")).count(),
                "total_downloads":     Download.objects.filter(lead_magnet__owner=user).count(),
                "leads_generated":     Lead.objects.filter(lead_magnet__owner=user).count(),
                "ai_credits":          total_credits,
                "ai_credits_used":     used_credits,
                "ai_credits_remaining": remaining_credits,
            }).data)
        except Exception as e:
            logger.error(f"❌ [STATS ERROR] {user.email if 'user' in locals() else 'unknown'}: {e}\n{traceback.format_exc()}")
            return Response({"error":"Failed to fetch dashboard stats","details":str(e)}, status=500)


class LeadMagnetListCreateView(generics.ListCreateAPIView):
    serializer_class   = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self): 
        try:
            user = self.request.user
            if not user or user.is_anonymous:
                logger.warning("Attempt to access lead magnets by anonymous user")
                return LeadMagnet.objects.none()
            
            qs = LeadMagnet.objects.filter(owner=user).select_related('generation_data')
            logger.info(f"Fetching {qs.count()} lead magnets for user {user.email}")
            return qs
        except Exception as e:
            user_email = getattr(self.request.user, "email", "anonymous")
            logger.error(f"❌ [LM LIST ERROR] {user_email}: {e}\n{traceback.format_exc()}")
            raise
            
    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ [LM LIST VIEW ERROR]: {e}\n{traceback.format_exc()}")
            return Response({
                "error": "Failed to fetch lead magnets",
                "details": str(e)
            }, status=500)

    def perform_create(self, s): 
        try:
            s.save(owner=self.request.user)
        except Exception as e:
            logger.error(f"❌ [LM CREATE ERROR] {self.request.user.email}: {e}\n{traceback.format_exc()}")
            raise


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

class DBStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            connection.ensure_connection()
            info = {
                'vendor': connection.vendor,
                'name': connection.settings_dict.get('NAME'),
                'host': connection.settings_dict.get('HOST'),
                'port': connection.settings_dict.get('PORT'),
            }
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                cursor.execute("SELECT 1")
                cursor.fetchone()
            try:
                from accounts.models import User
                user_count = User.objects.count()
            except Exception:
                user_count = None
            return Response({
                'ok': True,
                'db': info,
                'server_version': version,
                'user_count': user_count,
            })
        except Exception as e:
            logger.exception("DB status check failed")
            return Response({'ok': False, 'error': str(e)}, status=500)


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

def run_pdf_generation_task(lead_magnet_id, user_id, template_id, use_ai_content, user_answers, architectural_images, job_id):
    """Background task for PDF generation to avoid HTTP timeouts"""
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
        lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id)
        template_selection = TemplateSelection.objects.filter(lead_magnet=lead_magnet).first()
        
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
            answers_for_ai = user_answers or (template_selection.captured_answers if template_selection else {})
            if not answers_for_ai:
                try:
                    gen_data = lead_magnet.generation_data
                    answers_for_ai = {
                        'lead_magnet_type': gen_data.lead_magnet_type,
                        'main_topic': gen_data.main_topic,
                        'target_audience': gen_data.target_audience,
                        'audience_pain_points': gen_data.audience_pain_points,
                        'desired_outcome': gen_data.desired_outcome,
                        'call_to_action': gen_data.call_to_action,
                        'special_requests': gen_data.special_requests,
                    }
                except Exception:
                    pass

            if isinstance(answers_for_ai, dict):
                raw_desc = getattr(lead_magnet, "description", "") or ""
                answers_for_ai.setdefault("lead_magnet_description", raw_desc)
                # Normalize placeholder/sentinel values like 'h' to empty strings
                for key in ['desired_outcome', 'call_to_action', 'main_topic']:
                    val = answers_for_ai.get(key)
                    if isinstance(val, str) and val.strip().lower() in ('h', 'na', 'n/a'):
                        answers_for_ai[key] = ''

            try:
                _set_job(job_id, status="processing", progress=15,
                         message="Generating AI content — 11 sections (~3–12 min)...")
                t0 = time.time()

                signals        = ai_client.get_semantic_signals(ai_input)
                
                # Callback to update tokens in real-time
                def _on_tokens(t):
                    _set_job(job_id, tokens_used=t)

                try:
                    raw_ai         = ai_client.generate_lead_magnet_json(signals, firm_profile, on_token_update=_on_tokens)
                except Exception as e:
                    logger.error(f"AI Generation Failed: {e}")
                    _set_job(job_id, status="failed", error=str(e)); return

                if _should_stop(job_id):
                    logger.info(f"🛑 Job {job_id} terminated during AI generation"); return
                
                ai_content     = ai_client.normalize_ai_output(raw_ai)
                tokens_used    = raw_ai.get("tokens_used", 0)
                
                # Final token update for the job
                _set_job(job_id, tokens_used=tokens_used)

                logger.info(f"✅ AI done | {time.time()-t0:.1f}s | Tokens: {tokens_used}")

                empty = [k for k, *_ in ai_client.SECTIONS if not ai_content.get(k)]
                if len(empty) == len(ai_client.SECTIONS):
                    logger.error("❌ All AI sections returned empty. Failing job.")
                    error_msg = (
                        "AI failed to generate any content. This usually means your API keys are "
                        "invalid, expired, or missing on Render. Please verify 'GROQ_API_KEY' or 'OPENAI_API_KEY' "
                        "is correctly set in your environment variables."
                    )
                    _set_job(job_id, status="failed", error=error_msg); return
                elif empty:
                    logger.warning(f"⚠️ Some sections are empty: {empty}")

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

                # ── CONSTRUCT DYNAMIC SECTIONS HTML (NATURAL LAYOUT) ──────
                doc_type = ai_input.get("document_type", "guide")
                actual_sections = ai_client.TYPE_CONFIGS.get(doc_type, {}).get("sections", ai_client.GUIDE_SECTIONS)
                
                sections_html_list = []
                toc_html_list = []
                
                # Image usage tracking
                used_image_indices = set()
                
                def get_next_image(is_vertical=False):
                    for i in range(len(architectural_images)):
                        if i not in used_image_indices:
                            used_image_indices.add(i)
                            url = _resolve_image_url(architectural_images[i])
                            if not url: continue
                            
                            # Determine style
                            if is_vertical:
                                style = "vertical left" if len(used_image_indices) % 2 == 1 else "vertical right"
                            else:
                                style = "horizontal center"
                            
                            return f'<div class="img-block {style}"><img src="{url}" alt=""></div>'
                    return ""

                def create_section_html(content_html, section_idx, kicker, title, image_html=""):
                    num_str = str(section_idx + 1).zfill(2) # Section number
                    
                    return f"""
                        <div class="page content-page" id="sec-{section_idx}" style="clear: both;">
                            <div class="string-container">
                                <span class="page-header-kicker">{kicker}</span>
                                <div class="page-header-title">{title}</div>
                            </div>

                            <div class="page-body">
                                <div class="section-intro-block">
                                    <div class="section-intro-num">{num_str}</div>
                                    <div class="section-headline">{title}</div>
                                </div>
                                
                                {image_html}
                                
                                <div class="section-content">
                                    {content_html}
                                </div>
                            </div>
                        </div>
                    """

                for idx, (key, dtitle, dkicker, dlabel, dicon) in enumerate(actual_sections):
                    section_html = template_vars.get(f"section_{key}_full_html", "")
                    section_title = template_vars.get(f"customTitle{idx+1}", dtitle)
                    section_kicker = template_vars.get(f"section_{key}_kicker", dkicker)
                    
                    # Add to TOC using target-counter
                    toc_html_list.append(f"""
                        <div class="toc-item">
                            <span class="toc-num">{str(idx+1).zfill(2)}</span><span class="toc-label">{section_title}</span>
                            <span class="toc-dots"></span><span class="toc-pg"><a href="#sec-{idx}" class="toc-link" style="text-decoration:none; color:inherit;"></a></span>
                        </div>
                    """)
                    
                    # Strategically insert image
                    image_html = get_next_image(is_vertical=(idx % 2 == 1))
                    
                    # Pass the entire section and let WeasyPrint naturally paginate it
                    sections_html_list.append(create_section_html(section_html, idx, section_kicker, section_title, image_html))

                template_vars["sections_html"] = "\n".join(sections_html_list)
                template_vars["toc_html"]      = "\n".join(toc_html_list)

                # Verify content vars
                missing = [f"section_{k}_full_html" for k, *_ in actual_sections
                           if not template_vars.get(f"section_{k}_full_html")]
                if missing:
                    logger.warning(f"⚠️ Missing _full_html vars for {doc_type}: {missing}")
                else:
                    logger.info(f"✅ All {len(actual_sections)} section_*_full_html vars populated for {doc_type}")

            except Exception as e:
                logger.error(f"AI Pipeline Error: {e}\n{traceback.format_exc()}")
                _set_job(job_id, status="failed", error=f"AI generation failed: {e}"); return

        else:
            # Fallback for manual content (no AI)
            doc_type = ai_input.get("document_type", "guide")
            actual_sections = ai_client.TYPE_CONFIGS.get(doc_type, {}).get("sections", ai_client.GUIDE_SECTIONS)
            
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
                "toc_html": "",
                "sections_html": "",
                "termsTitle": "Terms of Use", "termsSummary": "",
                "termsParagraph1":"","termsParagraph2":"","termsParagraph3":"",
                "termsParagraph4":"","termsParagraph5":"",
                "contentsTitle": "Table of Contents",
                "documentTypeLabel": ai_input.get("lead_magnet_type", "Strategic Guide")
            }
            
            sections_html_list = []
            toc_html_list = []
            page_count = 4
            for idx, (key, dtitle, dkicker, dlabel, dicon) in enumerate(actual_sections):
                num_str = str(idx + 1).zfill(2)
                page_num = str(page_count).zfill(2)
                
                # TOC Item
                toc_html_list.append(f"""
                    <div class="toc-item">
                        <span class="toc-num">{num_str}</span><span class="toc-label">{dtitle}</span>
                        <span class="toc-dots"></span><span class="toc-pg">{page_num}</span>
                    </div>
                """)

        # ── PDF RENDERING ──────────────────────────────────────────────────
        pdf_service = WeasyPrintService()
        try:
            _set_job(job_id, status="processing", progress=75, message="Rendering PDF via WeasyPrint...")
            t0 = time.time()

            # Prepare template variables
            pdf_vars = template_vars.copy()

            # ── Image URL safety: do NOT overwrite non-empty with empty ────
            for i in range(1, 7):
                existing  = pdf_vars.get(f"image_{i}_url","")
                firm_url  = firm_profile.get(f"image_{i}_url","")
                if not existing and firm_url:
                    pdf_vars[f"image_{i}_url"] = firm_url
                elif not existing and not firm_url:
                    # Remove key entirely → {{#if}} evaluates falsy → no broken block
                    pdf_vars.pop(f"image_{i}_url", None)

            # Colour defaults
            pdf_vars.setdefault("primaryColor",   "#1a365d")
            pdf_vars.setdefault("secondaryColor", "#c5a059")
            pdf_vars.setdefault("accentColor",    "#f8fafc")
            pdf_vars.setdefault("highlightColor", "#f4f7f9")
            pdf_vars.setdefault("lightColor",     "#f1f5f9")
            pdf_vars.setdefault("whiteColor",     "#ffffff")
            pdf_vars.setdefault("textColor",      "#1e293b")
            pdf_vars.setdefault("textLightColor", "#64748b")
            pdf_vars.setdefault("bodyBackground", "#ffffff")
            pdf_vars.setdefault("borderRadius",   "8px")

            _set_job(job_id, status="processing", progress=82, message="WeasyPrint rendering PDF...")
            if _should_stop(job_id):
                logger.info(f"🛑 Job {job_id} terminated before rendering"); return
            
            # Strict type mapping: use documentType if template_id is default/none
            actual_template_id = template_id
            if actual_template_id in [None, "modern-guide", "default"]:
                actual_template_id = pdf_vars.get("documentType", "guide")
                
            result = pdf_service.generate_pdf(actual_template_id, pdf_vars)

            if not result.get("success"):
                err = result.get("error","PDF generation failed")
                _set_job(job_id, status="failed", error=f"{err}: {result.get('details','')}"); return

            _set_job(job_id, status="processing", progress=92, message="Saving to cloud storage...")
            if _should_stop(job_id):
                logger.info(f"🛑 Job {job_id} terminated before upload"); return
            pdf_data = result["pdf_data"]
            filename = result.get("filename", f"lead-magnet-{lead_magnet_id}.pdf")

            try:
                import cloudinary.uploader
                up = cloudinary.uploader.upload(
                    pdf_data, resource_type="raw", folder="lead_magnets",
                    public_id=f"lead-magnet-{lead_magnet_id}-{uuid.uuid4().hex[:8]}.pdf",
                )
                lead_magnet.pdf_file = up.get("public_id")
                lead_magnet.status   = "completed"
                lead_magnet.save(update_fields=["pdf_file","status"])
                _set_job(job_id, status="complete", progress=100, message="PDF ready!", pdf_url=up.get("secure_url"))
            except Exception as ue:
                logger.error(f"Cloudinary fallback: {ue}")
                lead_magnet.pdf_file.save(filename, ContentFile(pdf_data), save=True)
                lead_magnet.status = "completed"
                lead_magnet.save(update_fields=["status"])
                _set_job(job_id, status="complete", progress=100, message="PDF ready (local storage fallback)!")

            logger.info(f"✅ PDF done | {time.time()-t0:.1f}s")
            _set_job(job_id, status="complete", progress=100,
                     pdf_url=f"/api/lead-magnets/{lead_magnet_id}/download/",
                     message="Your PDF is ready!")

        except Exception as e:
            logger.error(f"❌ [PDF ERROR] {e}", exc_info=True)
            _set_job(job_id, status="failed", error=str(e))
            try:
                lm = LeadMagnet.objects.get(id=lead_magnet_id)
                lm.status = "failed"
                lm.save(update_fields=["status"])
            except: pass

    except Exception as exc:
        logger.critical(f"Critical job error: {exc}\n{traceback.format_exc()}")
        _set_job(job_id, status="failed", error=str(exc))

from django.views.decorators.clickjacking import xframe_options_exempt

@api_view(['GET'])
@xframe_options_exempt
@permission_classes([permissions.IsAuthenticated])
def download_lead_magnet_pdf(request, lead_magnet_id):
    try:
        lm = LeadMagnet.objects.get(id=lead_magnet_id)
    except LeadMagnet.DoesNotExist:
        return Response({"error":"Lead magnet not found"}, status=404)
    
    try:
        if not lm.pdf_file:
            return Response({"error":"PDF not generated yet"}, status=404)

        # ── 1. Resolve Public ID ──────────────────────────────────────────
        raw_id = str(lm.pdf_file.name)
        public_id = raw_id
        
        # If it's a full URL, extract the part after /upload/
        if "http" in raw_id:
            import re as _re
            # Extract everything after the version (e.g., v123456789/) or after /upload/
            match = _re.search(r'/upload/(?:v\d+/)?(.+)$', raw_id)
            if match:
                public_id = match.group(1)
        
        # Cloudinary specific: sometimes the folder is part of the name, sometimes not.
        # We ensure we don't double up the folder prefix.
        if public_id.startswith('lead_magnets/lead_magnets/'):
            public_id = public_id.replace('lead_magnets/lead_magnets/', 'lead_magnets/')
        
        # ── 2. Proxy Request with Fallbacks ──────────────────────────────
        # We try 'raw' first, then 'image' if that fails.
        success_proxy = None
        last_url = ""
        
        for rtype in ["raw", "image"]:
            try:
                # Use cloudinary.utils.cloudinary_url directly for better control
                import cloudinary.utils
                signed_url, _ = cloudinary.utils.cloudinary_url(
                    public_id, 
                    resource_type=rtype, 
                    sign_url=True, 
                    secure=True
                )
                last_url = signed_url
                
                logger.info(f"PDF Proxy attempt ({rtype}): {public_id}")
                
                # Use a smaller timeout for the first attempt
                proxy_res = requests.get(signed_url, stream=True, timeout=10)
                if proxy_res.status_code == 200:
                    success_proxy = proxy_res
                    break
                else:
                    logger.warning(f"Proxy ({rtype}) failed with status {proxy_res.status_code}")
            except Exception as e:
                logger.error(f"Proxy error ({rtype}): {e}")

        if not success_proxy:
            # Mask the signature in the URL for the error response
            masked_url = last_url.split('?')[0] if '?' in last_url else last_url
            return Response({
                "error": "Could not retrieve PDF from Cloudinary",
                "details": f"Checked raw and image types for ID: {public_id}",
                "last_url_tried": masked_url,
                "hint": "Ensure the file was uploaded correctly and the public_id matches."
            }, status=502)

        # ── 3. Return FileResponse ────────────────────────────────────────
        filename = os.path.basename(public_id) or f"lead-magnet-{lead_magnet_id}.pdf"
        if not filename.lower().endswith(".pdf"): filename += ".pdf"
        
        resp = FileResponse(success_proxy.raw, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        # Security Headers for Cross-Domain Framing (Vercel -> Render)
        # We set these very explicitly to override any middleware
        resp["X-Frame-Options"] = "ALLOWALL"
        resp["Content-Security-Policy"] = "frame-ancestors *"
        resp["Access-Control-Allow-Origin"] = "*"
        
        if "Content-Length" in success_proxy.headers:
            resp["Content-Length"] = success_proxy.headers["Content-Length"]
            
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
            tmpls = []
            existing_ids = set()

            # 1. Get database templates (Primary Source)
            db_templates = Template.objects.all()
            if db_templates.exists():
                db_data = TemplateSerializer(db_templates, many=True, context={"request": request}).data
                for dbt in db_data:
                    tmpls.append(dbt)
                    existing_ids.add(dbt['id'])
            
            # 2. Get disk templates (Fallback/Discovery)
            svc = WeasyPrintService()
            disk_tmpls = svc.list_templates()
            for t in disk_tmpls:
                # Deduplicate: Skip if already in DB
                if t['id'] in existing_ids:
                    continue
                
                # Special Case: Skip generic 'template' if we already have specific templates
                # This prevents "Template" from appearing alongside "Modern Guide"
                if t['id'] == 'template' and len(tmpls) > 0:
                    continue
                
                p = os.path.join(settings.MEDIA_ROOT, "template_previews", f"{t['id']}.jpg")
                t["preview_url"] = request.build_absolute_uri(
                    f"{settings.MEDIA_URL}template_previews/{t['id']}.jpg" if os.path.exists(p) else f"{settings.MEDIA_URL}template_previews/default.jpg"
                )
                tmpls.append(t)
                existing_ids.add(t['id'])
            
            return Response({"success": True, "templates": tmpls, "count": len(tmpls)})

        except Exception as e:
            logger.error(f"❌ [LIST TEMPLATES ERROR]: {e}")
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
            return Response({"success":True,"preview_html":WeasyPrintService().preview_template(tid,request.data.get("variables",{}))})
        except Exception as e:
            return Response({"error":"Preview failed","details":str(e)}, status=500)


class HealthView(APIView):
    permission_classes     = [permissions.AllowAny]
    authentication_classes = []
    def get(self, request): return Response({"status":"ok"})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_start(request):
    lm_id = request.data.get("lead_magnet_id")
    if not lm_id:
        return Response({"error": "lead_magnet_id is required"}, status=400)
    
    # Cancel existing jobs for this lead magnet
    PDFGenerationJob.objects.filter(lead_magnet_id=lm_id, status__in=["pending", "processing"]).update(
        status="cancelled", stop_requested=True
    )

    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, message="Initializing...", lead_magnet_id=lm_id)
    
    # Start thread
    thread = threading.Thread(
        target=run_pdf_generation_task,
        args=(
            lm_id, 
            request.user.id, 
            request.data.get("template_id", "modern-guide"),
            request.data.get("use_ai_content", True),
            request.data.get("user_answers"),
            request.data.get("architectural_images", []),
            job_id
        ),
        daemon=True
    )
    thread.start()
    
    return Response({"job_id": job_id}, status=202)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status(request, job_id):
    return Response(_get_job(job_id))

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_stop(request, job_id):
    PDFGenerationJob.objects.filter(job_id=job_id).update(status="terminated", stop_requested=True)
    return Response({"status": "ok"})

# Compatibility routes
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_compat(request):
    return generate_pdf_start(request)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status_compat(request):
    lm_id = request.query_params.get("lead_magnet_id")
    if not lm_id:
        return Response({"error": "lead_magnet_id is required"}, status=400)
    
    latest_job = PDFGenerationJob.objects.filter(lead_magnet_id=lm_id).order_by("-created_at").first()
    if not latest_job:
        return Response({"status": "not_found"}, status=404)
    
    return Response(_get_job(latest_job.job_id))

def _get_ai_client():
    """Helper to get GroqClient with validation."""
    try:
        ai = GroqClient()
        if not ai.client:
            logger.warning("GroqClient initialized but no primary client (GROQ_API_KEY missing)")
        return ai
    except Exception as e:
        logger.error(f"Failed to instantiate GroqClient: {e}\n{traceback.format_exc()}")
        raise RuntimeError(f"AI Service Initialization Error: {str(e)}")


"""
Replace the FormaAIChatView class in your views.py with this.
URL: path('api/ai-chat/', FormaAIChatView.as_view()),

What this does:
- Parses the user's message to detect lead magnet type and business description
- Returns a 400 error if no lead magnet type is mentioned
- Creates LeadMagnet + PDFGenerationJob atomically (lead_magnet_id never null)
- Generates a deep, business-specific PDF using the detected type
"""

# ── Lead magnet type keywords → model values ──────────────────────────────
LM_TYPE_MAP = {
    "guide":            ["guide", "how to", "how-to", "handbook", "manual"],
    "case-study":       ["case study", "case-study", "success story", "success stories", "example"],
    "checklist":        ["checklist", "check list", "checklists", "list of steps", "step by step", "step-by-step"],
    "roi-calculator":   ["roi", "calculator", "return on investment", "roi calculator"],
    "trends-report":    ["trends", "trend report", "trends report", "industry report", "market report", "insights report"],
    "onboarding-flow":  ["onboarding", "onboard", "welcome flow", "getting started", "client onboarding"],
    "design-portfolio": ["portfolio", "design portfolio", "showcase", "work samples"],
    "custom":           ["custom", "other"],
}

def _detect_lm_type(message: str):
    """Return (type_value, type_label) or (None, None) if not found."""
    msg = message.lower()
    for type_value, keywords in LM_TYPE_MAP.items():
        for kw in keywords:
            if kw in msg:
                label_map = {
                    "guide": "Guide",
                    "case-study": "Case Study",
                    "checklist": "Checklist",
                    "roi-calculator": "ROI Calculator",
                    "trends-report": "Trends Report",
                    "onboarding-flow": "Client Onboarding Flow",
                    "design-portfolio": "Design Portfolio",
                    "custom": "Custom",
                }
                return type_value, label_map[type_value]
    return None, None


class FormaAIChatView(APIView):
    """
    Forma AI — business description → deep PDF lead magnet.

    User must mention their business AND the type of lead magnet they want.
    If no type is detected, returns a helpful 400 with examples.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        try:
            message     = (request.data.get("message") or "").strip()
            template_id = request.data.get("template_id") or "modern-guide"
            arch_images = request.data.get("architectural_images", [])  # base64 strings

            if not message:
                return Response({"error": "Please describe your business and what type of lead magnet you want."}, status=400)

            # ── Detect lead magnet type from message ──────────────────────
            lm_type, lm_label = _detect_lm_type(message)

            if not lm_type:
                return Response({
                    "error": (
                        "Please mention the type of lead magnet you want. For example:\n\n"
                        "• \"...create a Guide about my perfume business\"\n"
                        "• \"...make a Checklist for my architecture firm\"\n"
                        "• \"...build a Trends Report for my real estate agency\"\n"
                        "• \"...generate a Case Study for my consulting firm\"\n"
                        "• \"...write an ROI Calculator for my SaaS product\"\n"
                        "• \"...create a Client Onboarding Flow for my agency\"\n\n"
                        "Available types: Guide, Case Study, Checklist, ROI Calculator, "
                        "Trends Report, Client Onboarding Flow, Design Portfolio, Custom"
                    )
                }, status=400)

            # ── 1. Create LeadMagnet first (FK anchor) ────────────────────
            lm = LeadMagnet.objects.create(
                owner=request.user,
                title=f"{lm_label}: {message[:80]}",
                status="processing",
            )

            # ── 2. Create PDFGenerationJob with lead_magnet set ───────────
            job_id = str(uuid.uuid4())
            PDFGenerationJob.objects.create(
                job_id=job_id,
                lead_magnet=lm,
                status="pending",
                progress=0,
                message="Queued — AI is reading your business description...",
            )

            # ── 3. Log conversation ───────────────────────────────────────
            conv = FormaAIConversation.objects.create(
                user=request.user,
                messages=[{"role": "user", "content": message}],
                lead_magnet=lm,
            )

            # ── 4. Fire background thread ─────────────────────────────────
            threading.Thread(
                target=FormaAIChatView._run,
                args=(job_id, lm.id, request.user.id, conv.id,
                      message, lm_type, lm_label, template_id, arch_images),
                daemon=True,
            ).start()

            return Response({
                "success":         True,
                "job_id":          job_id,
                "lead_magnet_id":  lm.id,
                "conversation_id": conv.id,
                "lm_type":         lm_type,
                "lm_label":        lm_label,
                "message": (
                    f"Got it! Creating a **{lm_label}** based on your business description. "
                    f"This usually takes 2–5 minutes. Check your dashboard when it's ready."
                ),
            }, status=202)

        except Exception as e:
            logger.error(f"FormaAIChatView.post error: {e}\n{traceback.format_exc()}")
            return Response({"error": str(e)}, status=500)

    # ── Background PDF generation worker ─────────────────────────────────
    @staticmethod
    def _run(job_id, lm_id, user_id, conv_id, message, lm_type, lm_label, template_id, arch_images):

        def upd(**kw):
            """Update job — always preserves lead_magnet_id."""
            kw["lead_magnet_id"] = lm_id
            try:
                PDFGenerationJob.objects.filter(job_id=job_id).update(**kw)
            except Exception as e:
                logger.warning(f"upd() failed: {e}")

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            lm   = LeadMagnet.objects.get(id=lm_id)
            conv = FormaAIConversation.objects.get(id=conv_id)

            firm = _build_firm_profile(user)

            # ── Resolve base64 architectural images → Cloudinary URLs ─────
            import cloudinary.uploader, base64 as _b64, re as _re
            from io import BytesIO

            for i, b64str in enumerate(arch_images[:6]):
                try:
                    raw  = _re.sub(r'^data:image/[^;]+;base64,', '', b64str)
                    data = _b64.b64decode(raw)
                    up   = cloudinary.uploader.upload(
                        BytesIO(data),
                        folder="architectural_images",
                        public_id=f"forma_ai_{user_id}_{uuid.uuid4().hex[:6]}",
                    )
                    firm[f"image_{i+1}_url"] = up.get("secure_url", "")
                    logger.info(f"Uploaded image {i+1} for user {user_id}")
                except Exception as ie:
                    logger.warning(f"Image {i+1} upload failed: {ie}")

            # ── Build AI input from the user's business description ───────
            # The full message IS the business description — AI uses it all
            ua = {
                "lead_magnet_type": lm_type,
                "main_topic":       "custom",
                "target_audience":  ["Potential clients"],
                "audience_pain_points": ["Finding the right service provider"],
                "desired_outcome":  f"Reader understands {firm.get('firm_name','the business')} and takes action",
                "call_to_action":   f"Contact {firm.get('firm_name','us')} today",
                "special_requests": message,   # ← full business description goes here
                "industry":         "Business",
                "document_type":    lm_type,
            }

            ai  = _get_ai_client()
            svc = WeasyPrintService()

            upd(status="processing", progress=10,
                message="AI is analysing your business description...")

            # ── Extract signals from description ─────────────────────────
            extracted = ai.extract_business_signals(message, lm_label)
            
            ua = {
                "lead_magnet_type": lm_type,
                "main_topic":       extracted.get("topic", "custom"),
                "target_audience":  extracted.get("audience", "Potential clients"),
                "audience_pain_points": extracted.get("pain_points", ["Finding the right service provider"]),
                "desired_outcome":  extracted.get("desired_outcome", ""),
                "call_to_action":   extracted.get("call_to_action", f"Contact {firm.get('firm_name','us')} today"),
                "special_requests": message,
                "industry":         extracted.get("industry", "Business"),
                "document_type":    lm_type,
            }

            signals = ai.get_semantic_signals(ua)

            upd(status="processing", progress=25,
                message=f"Generating deep {lm_label} content...")

            raw_ai  = ai.generate_lead_magnet_json(signals, firm)
            content = ai.normalize_ai_output(raw_ai)

            tokens_used = raw_ai.get("tokens_used", 0)
            upd(status="processing", progress=60,
                message="Mapping content to template...",
                tokens_used=tokens_used)

            tvars = ai.map_to_template_vars(content, firm, signals)
            tvars.setdefault("companyName",        firm.get("firm_name", ""))
            tvars.setdefault("emailAddress",        firm.get("work_email", ""))
            tvars.setdefault("website",             firm.get("firm_website", ""))
            tvars.setdefault("documentTypeLabel",   lm_label)

            # ── Build sections HTML ───────────────────────────────────────
            doc_type        = lm_type
            actual_sections = ai.TYPE_CONFIGS.get(
                doc_type, {}
            ).get("sections", ai.GUIDE_SECTIONS)

            sections_html, toc_html = [], []

            for idx, (key, dtitle, dkicker, dlabel, dicon) in enumerate(actual_sections):
                section_title = tvars.get(f"customTitle{idx+1}", dtitle)
                content_html  = tvars.get(f"section_{key}_full_html", "")
                num = str(idx + 1).zfill(2)

                toc_html.append(
                    f'<div class="toc-item">'
                    f'<span class="toc-num">{num}</span>'
                    f'<span class="toc-label">{section_title}</span>'
                    f'<span class="toc-dots"></span>'
                    f'<span class="toc-pg">'
                    f'<a href="#sec-{idx}" class="toc-link" style="text-decoration:none;color:inherit;"></a>'
                    f'</span></div>'
                )

                # Image: alternate placement every 2 sections
                img_url = firm.get(f"image_{(idx % 6) + 1}_url", "")
                img_html = (
                    f'<div class="img-block horizontal center">'
                    f'<img src="{img_url}" alt=""></div>'
                ) if img_url else ""

                sections_html.append(
                    f'<div class="page content-page" id="sec-{idx}" style="clear:both;">'
                    f'<div class="string-container">'
                    f'<span class="page-header-kicker">{dkicker}</span>'
                    f'<div class="page-header-title">{section_title}</div></div>'
                    f'<div class="page-body">'
                    f'<div class="section-intro-block">'
                    f'<div class="section-intro-num">{num}</div>'
                    f'<div class="section-headline">{section_title}</div></div>'
                    f'{img_html}'
                    f'<div class="section-content">{content_html}</div>'
                    f'</div></div>'
                )

            tvars["sections_html"] = "\n".join(sections_html)
            tvars["toc_html"]      = "\n".join(toc_html)

            upd(status="processing", progress=78, message="Rendering PDF...")

            pdf_res = svc.generate_pdf(template_id, tvars)
            if not pdf_res.get("success"):
                raise Exception(f"PDF render failed: {pdf_res.get('details', 'unknown error')}")

            # ── Save PDF ──────────────────────────────────────────────────
            pdf_url = ""
            try:
                import cloudinary.uploader as _cup
                up = _cup.upload(
                    pdf_res["pdf_data"],
                    resource_type="raw",
                    folder="lead_magnets",
                    public_id=f"ai-chat-{lm_id}-{uuid.uuid4().hex[:6]}.pdf",
                )
                lm.pdf_file = up.get("public_id", "")
                pdf_url     = up.get("secure_url", "")
            except Exception as ce:
                logger.warning(f"Cloudinary upload failed, using local: {ce}")
                from django.core.files.base import ContentFile
                lm.pdf_file.save(
                    f"ai_chat_{lm_id}.pdf",
                    ContentFile(pdf_res["pdf_data"])
                )
                pdf_url = lm.pdf_file.url

            lm.title  = tvars.get("mainTitle", lm.title)
            lm.status = "completed"
            lm.save()

            # ── Save generation data ──────────────────────────────────────
            LeadMagnetGeneration.objects.get_or_create(
                lead_magnet=lm,
                defaults={
                    "lead_magnet_type":     lm_type,
                    "main_topic":           ua["main_topic"],
                    "target_audience":      ua["target_audience"],
                    "audience_pain_points": ua["audience_pain_points"],
                    "desired_outcome":      ua["desired_outcome"],
                    "call_to_action":       ua["call_to_action"],
                    "special_requests":     message,
                },
            )

            # ── Update conversation ───────────────────────────────────────
            conv.messages.append({
                "role":    "assistant",
                "content": (
                    f"Your **{lm_label}** is ready! "
                    f"Find it in your dashboard as \"{lm.title}\"."
                ),
            })
            conv.save()

            upd(status="complete", progress=100,
                message=f"{lm_label} PDF ready! Opening preview…",
                pdf_url=f"/api/lead-magnets/{lm_id}/download/",
                tokens_used=tokens_used)

            logger.info(f"✅ PDF URL for frontend: /api/lead-magnets/{lm_id}/download/")

            logger.info(f"✅ FormaAI PDF complete | job={job_id} | lm={lm_id} | type={lm_type}")

        except Exception as e:
            logger.error(f"FormaAIChatView._run error: {e}\n{traceback.format_exc()}")
            PDFGenerationJob.objects.filter(job_id=job_id).update(
                status="failed",
                error=str(e),
                lead_magnet_id=lm_id,
            )
            try:
                LeadMagnet.objects.filter(id=lm_id).update(status="error")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND WORKER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _run_pdf_generation(job_id, lm_id, user_id, conv_id, message, template_id, arch_images):
    def upd(**kw):
        """Safe job updater that always preserves lead_magnet_id."""
        kw.setdefault("lead_magnet_id", lm_id)
        PDFGenerationJob.objects.filter(job_id=job_id).update(**kw)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        lm   = LeadMagnet.objects.get(id=lm_id)
        
        ai = GroqClient()
        sections_html, toc_html = [], []
        doc_type       = "guide"
        actual_sections = ai.TYPE_CONFIGS.get(doc_type, {}).get("sections", ai.GUIDE_SECTIONS)

        for idx, (key, dtitle, dkicker, dlabel, dicon) in enumerate(actual_sections):
            section_title = dtitle
            content_html  = ""
            num = str(idx + 1).zfill(2)
            toc_html.append(
                f'<div class="toc-item"><span class="toc-num">{num}</span>'
                f'<span class="toc-label">{section_title}</span>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-pg"><a href="#sec-{idx}" class="toc-link" style="text-decoration:none;color:inherit;"></a></span></div>'
            )
            sections_html.append(
                f'<div class="page content-page" id="sec-{idx}" style="clear:both;">'
                f'<div class="string-container"><span class="page-header-kicker">{dkicker}</span>'
                f'<div class="page-header-title">{section_title}</div></div>'
                f'<div class="page-body"><div class="section-intro-block">'
                f'<div class="section-intro-num">{num}</div>'
                f'<div class="section-headline">{section_title}</div></div>'
                f'<div class="section-content">{content_html}</div></div></div>'
            )

        upd(status="completed", progress=100, message="PDF generation ready.")

    except Exception as e:
        logger.error(f"Background worker error: {e}")
        upd(status="failed", error=str(e))


class GenerateDocumentPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            ua = request.data.get("user_answers")
            fp = request.data.get("firm_profile")
            if not isinstance(ua,dict) or not isinstance(fp,dict):
                return Response({"error":"user_answers and firm_profile must be objects"}, status=400)

            ai   = _get_ai_client()
            sig  = ai.get_semantic_signals(ua)
            raw  = ai.generate_lead_magnet_json(sig, fp)
            cont = ai.normalize_ai_output(raw)
            tvars= ai.map_to_template_vars(cont, fp, sig)

            svc  = WeasyPrintService()
            html = svc.preview_template(request.data.get("template_id", "modern-guide"), tvars)

            return Response({"success":True,"preview_html":html})
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

            res = WeasyPrintService().generate_pdf("brand-assets", variables)
            if res.get("success"):
                r = HttpResponse(res.get("pdf_data",b""), content_type="application/pdf")
                r["Content-Disposition"] = 'attachment; filename="brand-assets-preview.pdf"'
                return r
            return Response({"error":"PDF failed","details":res.get("details","")}, status=502)
        except Exception as e:
            return Response({"error":"Unexpected error","details":str(e)}, status=500)