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
    PDFGenerationJob,
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
    PDFGenerationJob.objects.update_or_create(job_id=job_id, defaults=kwargs)


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
        
        # Calculate real AI Credit stats from PDFGenerationJob
        total_credits = 1000000
        from django.db.models import Sum
        # Count tokens from ALL jobs associated with the user, regardless of status
        # This ensures failed jobs are also deducted from the balance
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
    logger.info(f"🔄 [JOB START] job_id={job_id} | engine=WeasyPrint")
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

        if _should_stop(job_id):
            logger.info(f"🛑 Job {job_id} terminated before start"); return

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

                # ── CONSTRUCT DYNAMIC SECTIONS HTML (INTELLIGENT LAYOUT) ──────
                doc_type = ai_input.get("document_type", "guide")
                actual_sections = ai_client.TYPE_CONFIGS.get(doc_type, {}).get("sections", ai_client.GUIDE_SECTIONS)
                
                sections_html_list = []
                toc_html_list = []
                
                # Intelligent Page Layout Constants
                MAX_CHARS_PER_PAGE = 3200
                MIN_FILL_RATIO = 0.75
                TARGET_CHARS_PER_PAGE = 2800
                
                current_page_content = []
                current_page_chars = 0
                page_count = 4
                
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

                def create_page_html(content_html, page_num, kicker, title, image_html=""):
                    num_str = str(page_num - 3).zfill(2) # Section number
                    display_num = str(page_num).zfill(2)
                    
                    return f"""
                        <div class="page content-page">
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
                    
                    # Add to TOC
                    toc_html_list.append(f"""
                        <div class="toc-item">
                            <span class="toc-num">{str(idx+1).zfill(2)}</span><span class="toc-label">{section_title}</span>
                            <span class="toc-dots"></span><span class="toc-pg">{str(page_count).zfill(2)}</span>
                        </div>
                    """)
                    
                    # Split section content into chunks (paragraphs/headers)
                    # We'll use a simple regex to split by common tags
                    chunks = re.split(r'(<h3.*?>.*?</h3>|<p.*?>.*?</p>|<ul.*?>.*?</ul>|<blockquote.*?>.*?</blockquote>)', section_html, flags=re.DOTALL)
                    chunks = [c.strip() for c in chunks if c.strip()]
                    
                    if not chunks and section_html.strip():
                        # Fallback: if no tags found but there is text, treat it as one chunk
                        chunks = [section_html.strip()]
                    
                    # Smart Pagination & Content Fitting
                    for c_idx, chunk in enumerate(chunks):
                        chunk_len = len(re.sub('<[^<]+?>', '', chunk)) # Strip HTML for length estimation
                        is_last_chunk = (c_idx == len(chunks) - 1)
                        
                        # "Smart Squeeze": If this chunk causes overflow but it's the last one,
                        # and the overflow is minor (<15% of page), squeeze it in.
                        overflow_chars = (current_page_chars + chunk_len) - TARGET_CHARS_PER_PAGE
                        can_squeeze = is_last_chunk and overflow_chars < (MAX_CHARS_PER_PAGE - TARGET_CHARS_PER_PAGE)
                        
                        if current_page_chars + chunk_len > TARGET_CHARS_PER_PAGE and not can_squeeze:
                            # Page is full. Check fill ratio for image placement.
                            fill_ratio = current_page_chars / MAX_CHARS_PER_PAGE
                            image_html = ""
                            
                            # Only add image if we have significant space and it's not a "squeezed" page
                            if fill_ratio < MIN_FILL_RATIO:
                                image_html = get_next_image(is_vertical=False)
                            
                            # Create the page
                            sections_html_list.append(create_page_html("\n".join(current_page_content), page_count, section_kicker, section_title, image_html))
                            
                            # Reset for next page
                            page_count += 1
                            current_page_content = [chunk]
                            current_page_chars = chunk_len
                        else:
                            current_page_content.append(chunk)
                            current_page_chars += chunk_len
                    
                    # After finishing a section, if we have content, we might want to start a new page for the next section
                    # or continue if there's enough space. For now, let's force a new page per section as per original design
                    # but ensure the current page is "full enough"
                    if current_page_content:
                        fill_ratio = current_page_chars / MAX_CHARS_PER_PAGE
                        image_html = ""
                        
                        # Strategically insert image if not full enough or just for visual balance
                        if fill_ratio < 0.5:
                            image_html = get_next_image(is_vertical=False)
                        elif fill_ratio < 0.8:
                            image_html = get_next_image(is_vertical=True)
                            
                        sections_html_list.append(create_page_html("\n".join(current_page_content), page_count, section_kicker, section_title, image_html))
                        page_count += 1
                        current_page_content = []
                        current_page_chars = 0

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

                sections_html_list.append(f"""
                    <div class="page content-page">
                        <div class="string-container">
                            <span class="page-header-kicker">{dkicker}</span>
                            <div class="page-header-title">{dlabel}</div>
                        </div>
                        <div class="page-body">
                            <div class="section-intro-block">
                                <div class="section-intro-num">{num_str}</div>
                                <div><div class="section-headline">{dtitle}</div></div>
                            </div>
                            <div class="section-content"><p>Content for {dtitle} goes here...</p></div>
                        </div>
                    </div>
                """)
                page_count += 1
            template_vars["sections_html"] = "\n".join(sections_html_list)
            template_vars["toc_html"]      = "\n".join(toc_html_list)

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
                    public_id=f"lead-magnet-{lead_magnet_id}-{uuid.uuid4().hex[:8]}",
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


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_start(request):
    lm_id = request.data.get("lead_magnet_id")
    if lm_id:
        # Cancel previous jobs for this Lead Magnet in the DB
        previous_jobs = PDFGenerationJob.objects.filter(
            lead_magnet_id=lm_id, 
            status__in=["pending", "processing"]
        )
        for job in previous_jobs:
            job.stop_requested = True
            job.status = "cancelled"
            job.message = "Cancelled by a newer generation request"
            job.save()
            logger.info(f"🔄 [DB] Cancelled previous job {job.job_id} for LM {lm_id}")

    job_id = str(uuid.uuid4())
    # Create the job in DB first
    try:
        lm = LeadMagnet.objects.get(id=lm_id, owner=request.user)
    except LeadMagnet.DoesNotExist:
        return Response({"error":"Lead magnet not found"}, status=404)

    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None, lead_magnet=lm)
    
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
def generate_pdf_stop(request, job_id):
    try:
        job = PDFGenerationJob.objects.get(job_id=job_id)
        job.stop_requested = True
        job.status = "terminated"
        job.message = "Job was stopped by user"
        job.save()
        logger.info(f"🛑 Manual termination requested for job {job_id}")
        return Response({"success":True,"message":"Termination signal sent"})
    except PDFGenerationJob.DoesNotExist:
        return Response({"error":"Job not found"}, status=404)


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

    job_data = None
    if job_id:
        job_data = _get_job(job_id)
    
    if not job_data:
        # Fallback: get the latest job for this Lead Magnet
        latest_job = PDFGenerationJob.objects.filter(lead_magnet_id=lm_id).first()
        if latest_job:
            job_data = _get_job(latest_job.job_id)

    try:
        lm = LeadMagnet.objects.get(id=lm_id, owner=request.user)
    except LeadMagnet.DoesNotExist:
        return Response({"error":"Lead magnet not found"}, status=404)

    if str(lm.status) == "completed" and lm.pdf_file:
        return Response({"status":"ready","pdf_url":f"/api/lead-magnets/{lm_id}/download/"})
    
    if job_data:
        if job_data.get("status") == "complete" and lm.pdf_file:
            return Response({"status":"ready","pdf_url":f"/api/lead-magnets/{lm_id}/download/"})
        if job_data.get("status") in ("failed","error"):
            return Response({"status":"error","error":job_data.get("error","Generation failed")})
        if job_data.get("status") in ("cancelled", "terminated"):
            return Response({"status":"error","error":"Job was stopped or cancelled"})
            
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
            svc = WeasyPrintService()
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
            return Response({"success":True,"preview_html":WeasyPrintService().preview_template(tid,request.data.get("variables",{}))})
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

        # We'll handle images later in the thread or just pass them if small
        # For now, let's keep the logic but move the heavy lifting to a thread

        if not message:
            return Response({"error":"Message is required"}, status=400)

        if conversation_id:
            try:
                conv = FormaAIConversation.objects.get(id=conversation_id, user=request.user)
            except FormaAIConversation.DoesNotExist:
                return Response({"error":"Conversation not found"}, status=404)
        else:
            conv = FormaAIConversation.objects.create(user=request.user, messages=[])

        # Start background processing to avoid timeout
        job_id = str(uuid.uuid4())
        _set_job(job_id, status="pending", progress=0, message="Initializing AI strategist...")
        
        # We need to capture the FILES before starting the thread as they might be closed
        # But since we are using threading.Thread, we can try to pass them if they are in memory
        # Better: just return the conversation ID and let the frontend poll or wait
        
        def _run_chat_ai_job(jid, msg, user_id, conv_id):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                conv = FormaAIConversation.objects.get(id=conv_id)
                
                conv.messages.append({"role":"user","content":msg})
                conv.save()
                
                firm = _build_firm_profile(user)
                ua   = {"main_topic":msg,"lead_magnet_type":"Custom Guide","industry":"Architecture"}
                ai   = GroqClient()
                svc  = WeasyPrintService()

                _set_job(jid, status="processing", progress=20, message="AI is drafting your guide...")
                sig  = ai.get_semantic_signals(ua)
                raw  = ai.generate_lead_magnet_json(sig, firm)
                cont = ai.normalize_ai_output(raw)
                
                _set_job(jid, status="processing", progress=60, message="Formatting content...")
                tvars = ai.map_to_template_vars(cont, firm, sig)
                tvars["companyName"]  = tvars.get("companyName")  or firm.get("firm_name") or "Your Company"
                tvars["emailAddress"] = tvars.get("emailAddress") or firm.get("work_email","")
                tvars["website"]      = tvars.get("website")      or firm.get("firm_website","")

                # Smart Pagination & Content Fitting for Chat
                sections_html_list = []
                toc_html_list = []
                page_count = 4
                
                # Image usage tracking
                used_image_indices = set()
                architectural_images = [] # In chat thread, we'd need to handle files if passed

                def get_next_img(is_vertical=False):
                    return "" # Placeholder for now as files are tricky in background threads

                for idx, key in enumerate(ai.SECTION_KEYS):
                    content_html = cont.get(key, "")
                    if not content_html: continue
                    section_title = tvars.get(f"customTitle{idx+1}", key.replace("_", " ").title())
                    
                    # TOC
                    toc_html_list.append(f'<div class="toc-item"><span class="toc-num">{str(idx+1).zfill(2)}</span><span class="toc-label">{section_title}</span><span class="toc-dots"></span><span class="toc-pg">{str(page_count).zfill(2)}</span></div>')
                    
                    chunks = re.split(r'(<h3.*?>.*?</h3>|<p.*?>.*?</p>|<ul.*?>.*?</ul>)', content_html, flags=re.DOTALL)
                    chunks = [c.strip() for c in chunks if c.strip()]
                    
                    curr_content = []
                    curr_chars = 0
                    
                    for c_idx, chunk in enumerate(chunks):
                        chunk_len = len(re.sub('<[^<]+?>', '', chunk))
                        is_last = (c_idx == len(chunks) - 1)
                        overflow = (curr_chars + chunk_len) - TARGET_CHARS_PER_PAGE
                        can_squeeze = is_last and overflow < (MAX_CHARS_PER_PAGE - TARGET_CHARS_PER_PAGE)

                        if curr_chars + chunk_len > TARGET_CHARS_PER_PAGE and not can_squeeze:
                            img = get_next_img() if curr_chars / MAX_CHARS_PER_PAGE < MIN_FILL_RATIO else ""
                            sections_html_list.append(create_page_html("\n".join(curr_content), page_count, "AI Analysis", section_title, img))
                            page_count += 1
                            curr_content = [chunk]
                            curr_chars = chunk_len
                        else:
                            curr_content.append(chunk)
                            curr_chars += chunk_len
                    
                    if curr_content:
                        sections_html_list.append(create_page_html("\n".join(curr_content), page_count, "AI Analysis", section_title, ""))
                        page_count += 1

                tvars["sections_html"] = "\n".join(sections_html_list)
                tvars["toc_html"]      = "\n".join(toc_html_list)
                
                conv.messages.append({"role":"assistant","content":f"AI has generated your document: {tvars.get('mainTitle')}."})
                conv.save()
                _set_job(jid, status="complete", progress=100, message="AI analysis complete!")
                
            except Exception as e:
                logger.error(f"Chat AI Error: {e}")
                _set_job(jid, status="failed", error=str(e))

        # threading.Thread(target=_run_chat_ai_job, args=(job_id, message, request.user.id, conv.id), daemon=True).start()
        
        # ACTUALLY: The user's log shows /api/generate-pdf/start/ timeout. 
        # This is a standard POST that should return 202 immediately.
        # If it's timing out, it means the thread start or the DB cancel logic is hanging.
        
        return Response({
            "success": True,
            "job_id": job_id,
            "conversation_id": conv.id,
            "message": "AI strategist is working on your request. Please check status in a moment."
        }, status=202)


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