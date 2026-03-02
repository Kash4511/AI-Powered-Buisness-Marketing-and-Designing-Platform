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
from .services import DocRaptorService
from .perplexity_client import PerplexityClient
from .services import render_template
from .models import Template

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


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get user's lead magnets
        user_lead_magnets = LeadMagnet.objects.filter(owner=user)
        
        # Calculate stats
        total_lead_magnets = user_lead_magnets.count()
        active_lead_magnets = user_lead_magnets.filter(
            Q(status='completed') | Q(status='in-progress')
        ).count()
        
        # Get total downloads for user's lead magnets
        from .models import Download, Lead
        total_downloads = Download.objects.filter(
            lead_magnet__owner=user
        ).count()
        
        # Get total leads generated for user's lead magnets
        leads_generated = Lead.objects.filter(
            lead_magnet__owner=user
        ).count()
        
        stats = {
            'total_lead_magnets': total_lead_magnets,
            'active_lead_magnets': active_lead_magnets,
            'total_downloads': total_downloads,
            'leads_generated': leads_generated
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

class LeadMagnetListCreateView(generics.ListCreateAPIView):
    serializer_class = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LeadMagnet.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class LeadMagnetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeadMagnetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LeadMagnet.objects.filter(owner=self.request.user)

class FirmProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = FirmProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        user = self.request.user
        profile, created = FirmProfile.objects.get_or_create(
            user=user,
            defaults={
                'firm_name': (user.email.split('@')[0] if getattr(user, 'email', '') else 'Firm'),
                'work_email': getattr(user, 'email', '') or 'no-reply@example.com',
                'phone_number': '',
                'firm_website': '',
                'firm_size': '1-2',
                'industry_specialties': [],
                'primary_brand_color': '',
                'secondary_brand_color': '',
                'preferred_font_style': 'no-preference',
                'branding_guidelines': '',
                'location': '',
            }
        )
        return profile

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Log the incoming data for debugging
        logger.debug(f"PATCH FirmProfile for user {request.user.email}")
        
        # Start with a copy of the data
        data = request.data.copy()
        
        # 1. Handle industry_specialties if it's coming from multipart/form-data
        if hasattr(request.data, 'getlist'):
            # Reconstruct the data correctly for QueryDict
            processed_data = {}
            for key in request.data.keys():
                if key == 'industry_specialties':
                    specialties = request.data.getlist(key)
                    # Handle case where it's a single string like '["A", "B"]'
                    if len(specialties) == 1 and isinstance(specialties[0], str) and specialties[0].startswith('['):
                        try:
                            processed_data[key] = json.loads(specialties[0])
                        except json.JSONDecodeError:
                            processed_data[key] = specialties
                    else:
                        processed_data[key] = specialties
                else:
                    processed_data[key] = request.data.get(key)
            data = processed_data

        # 2. Sanitize fields: empty strings should be null or removed if they violate constraints
        # Especially for ImageFields and URLFields
        for key in list(data.keys()):
            val = data[key]
            if val == "" or val == "null" or val == "undefined":
                # Fields that allow NULL
                if key in ['logo', 'preferred_cover_image']:
                    data[key] = None
                # Fields that do NOT allow NULL but allow BLANK (empty string)
                elif key in ['firm_website', 'primary_brand_color', 'secondary_brand_color', 
                           'phone_number', 'location', 'branding_guidelines']:
                    data[key] = ""
            
            # Special handling for URLField (firm_website)
            if key == 'firm_website' and data[key] and isinstance(data[key], str):
                url = data[key].strip().lower()
                if url and not url.startswith(('http://', 'https://')):
                    data[key] = f"https://{url}"
        
        # 3. Handle logo/image fields specifically if they are strings (URLs)
        for key in ['logo', 'preferred_cover_image']:
            if key in data and isinstance(data[key], str):
                # If it's a URL string, remove it from the update payload
                data.pop(key)
        
        # 4. Ensure industry_specialties is a list
        if 'industry_specialties' in data and data['industry_specialties'] is None:
            data['industry_specialties'] = []

        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        
        # Log detailed errors for debugging
        error_msg = f"❌ FirmProfile update validation failed for user {request.user.email}: {serializer.errors}"
        logger.error(error_msg)
        print(error_msg) # Ensure it shows up in stdout
        
        return Response(
            {
                'error': 'Firm profile update failed',
                'details': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


def _run_generation_job(job_id, body, user_id):
    """
    Background job to generate a PDF for a lead magnet.
    """
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
        
        # 1. Extract and Validate Inputs
        template_id = body.get('template_id')
        lead_magnet_id = body.get('lead_magnet_id')
        use_ai_content = bool(body.get('use_ai_content', True))
        user_answers = body.get('user_answers', {}) or {}

        if not template_id or not lead_magnet_id:
            _set_job(job_id, status="failed", error="template_id and lead_magnet_id are required")
            return

        _set_job(job_id, status="processing", progress=5, message="Parsing...", lead_magnet_id=lead_magnet_id)

        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=user)
        except LeadMagnet.DoesNotExist:
            _set_job(job_id, status="failed", error="Lead magnet not found")
            return

        # 3. SEMANTIC IGNORE (Step 1 of Pipeline)
        gen_data = getattr(lead_magnet, 'generation_data', None)
        if not gen_data:
            _set_job(job_id, status="failed", error="Lead magnet is missing generation data")
            return

        ai_client = PerplexityClient()
        
        # Merge generation_data with user_answers
        all_answers = {
            'lead_magnet_type': gen_data.lead_magnet_type,
            'main_topic': gen_data.main_topic,
            'target_audience': gen_data.target_audience,
            'audience_pain_points': gen_data.audience_pain_points,
            'desired_outcome': gen_data.desired_outcome,
            'call_to_action': gen_data.call_to_action,
            'special_requests': gen_data.special_requests,
        }
        if isinstance(user_answers, dict):
            all_answers.update(user_answers)

        # Convert fields to interpreted signals (Semantic Ignore happens here)
        signals = ai_client.get_semantic_signals(all_answers)
        
        # 4. PREPARE FIRM PROFILE
        try:
            fp = FirmProfile.objects.get(user=user)
            firm_profile = {
                'firm_name': fp.firm_name or user.email.split('@')[0],
                'work_email': fp.work_email or user.email,
                'phone_number': fp.phone_number,
                'firm_website': fp.firm_website,
                'primary_brand_color': fp.primary_brand_color,
                'secondary_brand_color': fp.secondary_brand_color,
                'logo_url': fp.logo.url if fp.logo else '',
                'industry': 'Architecture',
            }
        except FirmProfile.DoesNotExist:
            firm_profile = {
                'firm_name': user.email.split('@')[0],
                'work_email': user.email,
                'phone_number': '',
                'firm_website': '',
                'primary_brand_color': '',
                'secondary_brand_color': '',
                'logo_url': '',
                'industry': 'Architecture',
            }

        # 5. AI CALL & NORMALIZATION (Steps 2 & 3 of Pipeline)
        template_vars = {}

        if use_ai_content:
            try:
                _set_job(job_id, status="processing", progress=15, message="Generating AI content... (~45s)")
                start_ai = time.time()
                # 5.1 AI Call
                logger.info("🤖 AI Generation Start (Step 2)")
                raw_ai_content = ai_client.generate_lead_magnet_json(signals, firm_profile)
                ai_duration = time.time() - start_ai
                
                # Mandatory Logging: AI raw type and duration
                logger.info(f"📊 AI RAW TYPE: {type(raw_ai_content)} | Duration: {ai_duration:.2f}s")

                _set_job(job_id, status="processing", progress=55, message="Structuring content...")
                # 5.2 Mandatory Normalization Layer (Step 3)
                start_norm = time.time()
                ai_content = ai_client.normalize_ai_output(raw_ai_content)
                norm_duration = time.time() - start_norm
                
                # Mandatory Logging: Section count after normalization
                sections = ai_content.get('sections', [])
                logger.info(f"✅ AI Content Normalized. Count: {len(sections)} | Duration: {norm_duration:.2f}s")
                
                _set_job(job_id, status="processing", progress=65, message="Validating...")
                # 5.3 CONTENT GUARANTEE LAYER (Step 4)
                # Ensures every section has meaningful content (120-250 words)
                start_guarantee = time.time()
                ai_content['sections'] = ai_client.ensure_section_content(sections, signals, firm_profile)
                guarantee_duration = time.time() - start_guarantee
                logger.info(f"🛡️ Content Guarantee Layer Complete. Duration: {guarantee_duration:.2f}s")

                # 5.4 Map to Template Variables (Safety Layer)
                # PDF layer must NEVER consume raw AI output. 
                # It only consumes normalized 'ai_content'.
                architectural_images = body.get('architectural_images', [])
                template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, signals, architectural_images)
                
            except Exception as e:
                # Mandatory Logging: Traceback on failure
                logger.error(f"❌ AI Pipeline Error: {str(e)}\n{traceback.format_exc()}")
                _set_job(job_id, status="failed", error=f"AI generation failed: {str(e)}")
                return
        else:
            # Basic non-AI mapping using signals
            def clean_sig(s): return s.replace("REINTERPRET: ", "") if s.startswith("REINTERPRET") else ""
            template_vars = {
                'primaryColor': firm_profile.get('primary_brand_color') or '',
                'secondaryColor': firm_profile.get('secondary_brand_color') or '',
                'companyName': firm_profile.get('firm_name') or '',
                'mainTitle': clean_sig(signals.get('main_topic')) or lead_magnet.title,
                'documentSubtitle': clean_sig(signals.get('desired_outcome')) or 'Professional Insights',
                'emailAddress': firm_profile.get('work_email') or '',
                'phoneNumber': firm_profile.get('phone_number') or '',
                'website': firm_profile.get('firm_website') or '',
            }

        # 6. PDF RENDERING (Step 4 of Pipeline)
        # PDF renderer only receives plain strings (enforced in map_to_template_vars)
        template_service = DocRaptorService()
        try:
            _set_job(job_id, status="processing", progress=80, message="Rendering PDF...")
            start_pdf = time.time()
            logger.info("📄 PDF Generation Start (Step 4)")
            result = template_service.generate_pdf(template_id, template_vars)
            pdf_duration = time.time() - start_pdf
            
            if not result.get('success'):
                err = result.get('error', 'PDF generation failed')
                logger.error(f"❌ PDF Failure: {err} | Duration: {pdf_duration:.2f}s")
                _set_job(job_id, status="failed", error=err)
                return
            
            _set_job(job_id, status="processing", progress=92, message="Saving...")
            pdf_data = result.get('pdf_data')
            filename = result.get('filename', f'lead-magnet-{lead_magnet_id}.pdf')
            
            # Save to model
            lead_magnet.pdf_file.save(filename, ContentFile(pdf_data), save=True)
            lead_magnet.status = 'completed'
            lead_magnet.save(update_fields=['status'])
            
            logger.info(f"✅ PDF Generation Success | Duration: {pdf_duration:.2f}s")
            
            # Use the protected download route instead of the storage URL to ensure 
            # consistent serving across environments and proper authentication handling.
            pdf_url = f"/api/lead-magnets/{lead_magnet_id}/download/"
            _set_job(job_id, status="complete", progress=100, pdf_url=pdf_url, message="Success!")

        except Exception as e:
            # Mandatory Logging: Traceback on failure
            logger.error(f"❌ PDF Rendering Error: {str(e)}\n{traceback.format_exc()}")
            _set_job(job_id, status="failed", error=f"PDF generation failed: {str(e)}")
            return

    except Exception as exc:
        logger.critical(f"❌ Critical View Error: {str(exc)}\n{traceback.format_exc()}")
        _set_job(job_id, status="failed", error=str(exc))

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_start(request):
    body = request.data
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None)
    
    # Extract user ID to avoid passing request object to thread
    user_id = request.user.id
    
    threading.Thread(target=_run_generation_job, args=(job_id, body, user_id), daemon=True).start()
    return Response({"job_id": job_id, "status": "pending"}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
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

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_compat(request):
    """
    Compatibility endpoint for frontend expecting POST /generate-pdf/ returning 202 and polling by lead_magnet_id.
    """
    # Delegate to job-based start while returning 202
    body = request.data
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="pending", progress=0, pdf_url=None, error=None, lead_magnet_id=body.get('lead_magnet_id'))
    threading.Thread(target=_run_generation_job, args=(job_id, body, request.user.id), daemon=True).start()
    # Provide a status_url hint while staying compatible with caller behavior
    status_url = request.build_absolute_uri(f"/api/generate-pdf/status/?lead_magnet_id={body.get('lead_magnet_id')}&job_id={job_id}")
    return Response({
        'status': 'in_progress',
        'message': 'PDF generation started',
        'lead_magnet_id': body.get('lead_magnet_id'),
        'status_url': status_url,
        'retry_after_seconds': 3
    }, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf_status_compat(request):
    """
    Compatibility endpoint for frontend polling GET /generate-pdf/status/?lead_magnet_id=...
    Translates job-based state to legacy shape: {status: 'ready'|'pending'|'error', pdf_url?}
    """
    lead_magnet_id = request.query_params.get('lead_magnet_id')
    job_id = request.query_params.get('job_id')
    if not lead_magnet_id:
        return Response({'error': 'lead_magnet_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    # If job_id provided, prefer job state
    job = None
    if job_id:
        job = _get_job(job_id)
    else:
        # Find latest job matching lead_magnet_id
        with _JOBS_LOCK:
            for k, v in reversed(list(_JOBS.items())):
                if str(v.get('lead_magnet_id')) == str(lead_magnet_id):
                    job = dict(v)
                    break
    # Fallback to model state if job not found
    try:
        lm = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
    except LeadMagnet.DoesNotExist:
        return Response({'error': 'Lead magnet not found'}, status=status.HTTP_404_NOT_FOUND)
    # If model has completed PDF, return ready with download route
    if str(lm.status) == 'completed' and lm.pdf_file:
        download_url = f"/api/lead-magnets/{lead_magnet_id}/download/"
        return Response({'status': 'ready', 'pdf_url': download_url}, status=status.HTTP_200_OK)
    # Otherwise use job state
    if job:
        if job.get('status') == 'complete' and lm.pdf_file:
            download_url = f"/api/lead-magnets/{lead_magnet_id}/download/"
            return Response({'status': 'ready', 'pdf_url': download_url}, status=status.HTTP_200_OK)
        if job.get('status') in ('failed', 'error'):
            return Response({'status': 'error', 'error': job.get('error', 'Generation failed')}, status=status.HTTP_200_OK)
        return Response({'status': 'pending'}, status=status.HTTP_200_OK)
    # No job and not completed yet
    return Response({'status': 'pending'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_lead_magnet_pdf(request, lead_magnet_id: int):
    """
    Serve the generated PDF file for a given lead magnet.
    Resilient implementation that handles Cloudinary and local storage.
    """
    try:
        # 1. Fetch LeadMagnet with ownership check
        try:
            lm = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
        except LeadMagnet.DoesNotExist:
            logger.warning(f"Download failed: LeadMagnet {lead_magnet_id} not found for user {request.user.id}")
            return Response({'error': 'Lead magnet not found'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Check if file exists
        if not lm.pdf_file:
            logger.warning(f"Download failed: No PDF file for LeadMagnet {lead_magnet_id}")
            return Response({'error': 'PDF not generated yet'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Serving Logic
        filename = os.path.basename(lm.pdf_file.name) or f"lead-magnet-{lead_magnet_id}.pdf"
        
        # If storage provides a URL (e.g. Cloudinary), proxy the file content.
        # This prevents 401 errors when Axios follows redirects with Authorization headers.
        if hasattr(lm.pdf_file, 'url') and (lm.pdf_file.url.startswith('http') or lm.pdf_file.url.startswith('https')):
            logger.info(f"Proxying Cloudinary URL for LeadMagnet {lead_magnet_id}: {lm.pdf_file.url}")
            try:
                # Stream the file from Cloudinary to the client
                # Use a standard User-Agent to avoid blocks
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                proxy_resp = requests.get(lm.pdf_file.url, stream=True, timeout=30, headers=headers)
                proxy_resp.raise_for_status()
                
                # Create a FileResponse from the requests response stream
                response = FileResponse(proxy_resp.raw, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                # Pass through relevant headers from Cloudinary
                if 'Content-Length' in proxy_resp.headers:
                    response['Content-Length'] = proxy_resp.headers['Content-Length']
                return response
            except Exception as e:
                logger.error(f"Cloudinary proxy failed for LeadMagnet {lead_magnet_id}: {str(e)}")
                # DO NOT redirect as it causes 401 leaks on frontend.
                # Instead, return a descriptive error so we can debug.
                return Response({
                    'error': 'Storage access failed',
                    'details': str(e) if settings.DEBUG else 'Failed to retrieve file from storage'
                }, status=status.HTTP_502_BAD_GATEWAY)

        try:
            # Fallback: Serve via FileResponse (local storage)
            file_handle = lm.pdf_file.open('rb')
            response = FileResponse(file_handle, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            logger.error(f"FileResponse failed for LeadMagnet {lead_magnet_id}: {str(e)}")
            
            # Final fallback: Read into memory and serve via HttpResponse
            try:
                logger.info(f"Attempting memory-buffered fallback for LeadMagnet {lead_magnet_id}")
                lm.pdf_file.open('rb')
                content = lm.pdf_file.read()
                lm.pdf_file.close()
                
                response = HttpResponse(content, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e2:
                logger.error(f"Memory fallback failed: {str(e2)}")
                raise e2

    except Exception as exc:
        logger.critical(f"Critical error in download view: {str(exc)}\n{traceback.format_exc()}")
        return Response({
            'error': 'Internal server error during download',
            'details': str(exc) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class CreateLeadMagnetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            serializer = CreateLeadMagnetSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            lead_magnet = serializer.save()
            return Response(LeadMagnetSerializer(lead_magnet).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            trace = traceback.format_exc() if settings.DEBUG else None
            payload = {
                'error': 'Failed to create lead magnet',
                'details': str(e),
            }
            if trace:
                payload['trace'] = trace
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def options(self, request, *args, **kwargs):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class ListTemplatesView(APIView):
    """Get all available PDF templates from DocRaptor service"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            db_templates = Template.objects.all()
            if db_templates.exists():
                data = TemplateSerializer(db_templates, many=True, context={'request': request}).data
                return Response({'success': True, 'templates': data, 'count': len(data)})

            template_service = DocRaptorService()
            templates = template_service.list_templates()

            for template in templates:
                template_id = template['id']
                preview_filename = f"{template_id}.jpg"
                preview_path = os.path.join(settings.MEDIA_ROOT, 'template_previews', preview_filename)

                if os.path.exists(preview_path):
                    template['preview_url'] = request.build_absolute_uri(
                        f"{settings.MEDIA_URL}template_previews/{preview_filename}"
                    )
                else:
                    template['preview_url'] = request.build_absolute_uri(
                        f"{settings.MEDIA_URL}template_previews/default.jpg"
                    )

            return Response({'success': True, 'templates': templates, 'count': len(templates)})

        except ValueError as e:
            return Response({
                'success': False,
                'error': 'API configuration error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'success': False, 'error': 'Unexpected error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SelectTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        lead_magnet_id = request.data.get('lead_magnet_id')
        template_id = request.data.get('template_id')
        template_name = request.data.get('template_name')
        template_thumbnail = request.data.get('template_thumbnail', '')
        captured_answers = request.data.get('captured_answers', {})
        source = request.data.get('source', 'create-lead-magnet')
        
        if not all([lead_magnet_id, template_id, template_name]):
            return Response({
                'error': 'lead_magnet_id, template_id, and template_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate source is one of the permitted choices
        valid_sources = [choice[0] for choice in TemplateSelection.SOURCE_CHOICES]
        if source not in valid_sources:
            return Response({
                'error': f'Invalid source. Must be one of: {", ".join(valid_sources)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the lead magnet
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
            
            # Create or update template selection
            template_selection, created = TemplateSelection.objects.update_or_create(
                lead_magnet=lead_magnet,
                defaults={
                    'user': request.user,
                    'template_id': template_id,
                    'template_name': template_name,
                    'template_thumbnail': template_thumbnail,
                    'captured_answers': captured_answers,
                    'image_upload_preference': request.data.get('image_upload_preference', 'no'),
                    'source': source,
                    'status': 'template-selected'
                }
            )
            
            # Do not mark lead magnet as in-progress on template selection.
            # Status will be set to in-progress when PDF generation starts.
            
            return Response({
                'success': True,
                'template_selection_id': template_selection.id,
                'message': 'Template selected successfully'
            }, status=status.HTTP_201_CREATED)
            
        except LeadMagnet.DoesNotExist:
            return Response({
                'error': 'Lead magnet not found'
            }, status=status.HTTP_404_NOT_FOUND)

class GenerateSloganView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user_answers = request.data.get('user_answers', {}) or {}
            fp = FirmProfile.objects.filter(user=request.user).first()
            firm_name = (fp.firm_name if fp and fp.firm_name else request.user.email.split('@')[0])
            topic = str(user_answers.get('main_topic', '')).strip() or 'Design'
            slogan = f"{firm_name}: {topic}"
            return Response({'success': True, 'slogan': slogan}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            trace = traceback.format_exc() if settings.DEBUG else None
            payload = {'error': 'Slogan generation failed', 'details': str(e)}
            if trace:
                payload['trace'] = trace
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PreviewTemplateView(APIView):
    """Preview template with custom variables"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        template_id = request.data.get('template_id')
        variables = request.data.get('variables', {})
        
        if not template_id:
            return Response({
                'error': 'template_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            template_service = DocRaptorService()
            preview_html = template_service.preview_template(template_id, variables)
            
            return Response({
                'success': True,
                'preview_html': preview_html
            })
            
        except Exception as e:
            return Response({
                'error': 'Preview generation failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

    def options(self, request, *args, **kwargs):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class FormaAIConversationView(APIView):
    """Handle Forma AI conversations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        message = request.data.get('message')
        files = request.data.get('files', [])
        conversation_id = request.data.get('conversation_id')
        # Optional PDF generation flags
        generate_pdf = request.data.get('generate_pdf', True)
        template_id = request.data.get('template_id', 'modern-guide')
        
        # Handle architectural images from FormData
        architectural_images = []
        for i in range(1, 4):  # Handle up to 3 architectural images
            image_key = f'architectural_image_{i}'
            if image_key in request.FILES:
                architectural_images.append(request.FILES[image_key])
        
        if not message:
            return Response({
                'error': 'Message is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if generate_pdf and not template_id:
            return Response({
                'error': 'Template selection is required for PDF generation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = FormaAIConversation.objects.get(
                    id=conversation_id,
                    user=request.user
                )
            except FormaAIConversation.DoesNotExist:
                return Response({
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            conversation = FormaAIConversation.objects.create(
                user=request.user,
                messages=[]
            )
        
        # Add user message to conversation
        conversation.messages.append({
            'role': 'user',
            'content': message,
            'files': files
        })
        
        # Build firm profile similar to PDF generation flow
        firm_profile = {}
        try:
            fp = FirmProfile.objects.get(user=request.user)
            firm_profile = {
                'firm_name': fp.firm_name,
                'work_email': fp.work_email,
                'phone_number': fp.phone_number,
                'firm_website': fp.firm_website,
                'primary_brand_color': fp.primary_brand_color,
                'secondary_brand_color': fp.secondary_brand_color,
                'logo_url': fp.logo.url if fp.logo else '',
                'industry': 'Architecture'
            }
        except FirmProfile.DoesNotExist:
            firm_profile = {
                'firm_name': request.user.email.split('@')[0],
                'work_email': request.user.email,
                'primary_brand_color': '',
                'secondary_brand_color': '',
                'logo_url': '',
                'industry': 'Architecture'
            }

        # Convert the chat message into minimal user_answers for AI JSON
        def _derive_outcome_from_message(msg: str) -> str:
            m = (msg or '').strip()
            # Keep it concise and user-centered; avoid stock phrases
            m = m.replace('\n', ' ')
            m = m.strip(' .;:')
            # If very short, add a minimal context
            if len(m.split()) <= 3:
                return f"{m}"
            return m

        user_answers = {
            'main_topic': message,
            'lead_magnet_type': 'Custom Guide',
            'desired_outcome': _derive_outcome_from_message(message),
            'industry': '',
            'brand_primary_color': firm_profile.get('primary_brand_color', ''),
            'brand_secondary_color': firm_profile.get('secondary_brand_color', ''),
            'brand_logo_url': firm_profile.get('logo_url', ''),
        }

        ai_client = PerplexityClient()
        template_service = DocRaptorService()

        try:
            # Step 1: Signals (Derived from message)
            signals = ai_client.get_semantic_signals(user_answers)
            
            # Step 2: AI Call
            raw_ai_content = ai_client.generate_lead_magnet_json(signals, firm_profile)
            
            # Step 3: Mandatory Normalization
            ai_content = ai_client.normalize_ai_output(raw_ai_content)
            
            # Step 4: Content Guarantee Layer
            # Ensure no empty sections before rendering
            ai_content['sections'] = ai_client.ensure_section_content(ai_content.get('sections', []), signals, firm_profile)
            
        except Exception as e:
            ai_error = f"AI generation failed: {str(e)}"
            logger.error(f"FormaAI AI Error: {ai_error}\n{traceback.format_exc()}")
            conversation.messages.append({'role': 'assistant', 'content': ai_error})
            conversation.save()
            return Response({'error': 'AI content generation failed', 'details': ai_error}, status=status.HTTP_502_BAD_GATEWAY)

        # Map AI JSON to template variables (Structure Safe)
        template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, signals)

        # Clean stock subtitle phrasing if the model echoed inputs
        import re
        sub = (template_vars.get('documentSubtitle') or '').strip()
        if sub:
            # Remove leading 'Generate professional PDF content' and optional connectors
            sub = re.sub(r"^\s*generate\s+professional\s+pdf\s+content\s*(showcasing|about|on)?\s*",
                         "", sub, flags=re.IGNORECASE)
            # Avoid hardcoded architecture bias tails like 'for architecture'
            sub = re.sub(r"\s*(for|in)\s+architecture\b.*$", "", sub, flags=re.IGNORECASE)
            sub = sub.strip(' -:;')
            template_vars['documentSubtitle'] = sub
        # Ensure critical cover/contact fields are never empty
        template_vars['companyName'] = template_vars.get('companyName') or (firm_profile.get('firm_name') or 'Your Company')
        template_vars['emailAddress'] = template_vars.get('emailAddress') or firm_profile.get('work_email', '')
        template_vars['phoneNumber'] = template_vars.get('phoneNumber') or firm_profile.get('phone_number', '')
        template_vars['website'] = template_vars.get('website') or firm_profile.get('firm_website', '')

        # Add sections array when present
        if 'sections' in ai_content and isinstance(ai_content['sections'], list) and ai_content['sections']:
            template_vars['sections'] = ai_content['sections']

        # Professional title fallback and subtitle punctuation
        if not template_vars.get('mainTitle'):
            topic = user_answers.get('main_topic') or ai_content.get('cover', {}).get('title') or 'Architectural Design'
            lm_type = user_answers.get('lead_magnet_type') or 'Guide'
            def title_case(s):
                return ' '.join([w.capitalize() for w in str(s).split()])
            template_vars['mainTitle'] = f"The {title_case(topic)} {title_case(lm_type)}"

        if template_vars.get('documentSubtitle'):
            sub = str(template_vars['documentSubtitle']).strip()
            if not sub.endswith(('.', '!', '?')):
                sub = sub.rstrip(';,:-–—')
                template_vars['documentSubtitle'] = sub + '.'
        
        # Add architectural images to template variables if provided
        if architectural_images:
            template_vars['architecturalImages'] = []
            for i, image in enumerate(architectural_images[:3]):  # Limit to 3 images
                # Convert image to base64 for embedding in template
                import base64
                image_data = base64.b64encode(image.read()).decode('utf-8')
                image_extension = image.name.split('.')[-1].lower()
                mime_type = f'image/{image_extension}' if image_extension in ['jpg', 'jpeg', 'png', 'gif'] else 'image/jpeg'
                template_vars['architecturalImages'].append({
                    'src': f'data:{mime_type};base64,{image_data}',
                    'alt': f'Architectural Image {i + 1}'
                })

        # Compose assistant message summary
        summary_title = template_vars.get('mainTitle') or ai_content.get('cover', {}).get('title') or 'Generated Document'
        ai_response = f"Generated AI content: {summary_title}."
        conversation.messages.append({'role': 'assistant', 'content': ai_response})
        conversation.save()

        # If requested, generate PDF and return as file response
        if generate_pdf:
            try:
                result = template_service.generate_pdf_with_ai_content(template_id, template_vars)
                if result.get('success'):
                    pdf_data = result.get('pdf_data', b'')
                    response = HttpResponse(pdf_data, content_type=result.get('content_type', 'application/pdf'))
                    filename = result.get('filename', f'forma-ai-{template_id}.pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                else:
                    return Response({'error': result.get('error', 'PDF generation failed'), 'details': result.get('details', '')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({'error': 'PDF generation failed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Otherwise return chat response and AI mapping summary
        return Response({
            'success': True,
            'conversation_id': conversation.id,
            'response': ai_response,
            'messages': conversation.messages,
            'template_id': template_id,
            'template_vars': template_vars
        })

class GenerateDocumentPreviewView(APIView):
    """Generate dynamic HTML preview using AI JSON and Jinja2 without fallbacks"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user_answers = request.data.get('user_answers')
            firm_profile = request.data.get('firm_profile')
            template_id = request.data.get('template_id', 'modern-guide')

            if not isinstance(user_answers, dict) or not isinstance(firm_profile, dict):
                return Response({'error': 'user_answers and firm_profile must be provided as objects'}, status=status.HTTP_400_BAD_REQUEST)

            ai_client = PerplexityClient()
            # Structure-Safe Pipeline
            signals = ai_client.get_semantic_signals(user_answers)
            raw_ai_data = ai_client.generate_lead_magnet_json(signals, firm_profile)
            ai_data = ai_client.normalize_ai_output(raw_ai_data)
            
            # Content Guarantee Layer
            ai_data['sections'] = ai_client.ensure_section_content(ai_data.get('sections', []), signals, firm_profile)
            
            template_vars = ai_client.map_to_template_vars(ai_data, firm_profile, signals)

            # Load template HTML
            templates_dir = os.path.join(settings.BASE_DIR, 'lead_magnets', 'templates')
            template_path = os.path.join(templates_dir, 'Template.html')
            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()

            final_html = render_template(template_html, template_vars)

            return Response({
                'success': True,
                'preview_html': final_html
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"❌ GenerateDocumentPreviewView error: {e}\n{traceback.format_exc()}")
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class BrandAssetsPDFPreviewView(APIView):
    """Generate a PDF preview of saved brand assets (company info, colors, logo)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            try:
                fp = FirmProfile.objects.get(user=user)
            except FirmProfile.DoesNotExist:
                return Response({'error': 'Firm profile not found. Please save brand assets first.'}, status=status.HTTP_400_BAD_REQUEST)

            def abs_url(url: str) -> str:
                try:
                    return request.build_absolute_uri(url) if url else ''
                except Exception:
                    return url or ''

            variables = {
                'companyName': fp.firm_name or '',
                'phone': fp.phone_number or '',
                'email': fp.work_email or '',
                'website': fp.firm_website or '',
                'primaryColor': fp.primary_brand_color or '#2a5766',
                'secondaryColor': fp.secondary_brand_color or '#FFFFFF',
                'logoUrl': abs_url(fp.logo.url) if fp.logo else '',
                'brandGuidelines': fp.branding_guidelines or ''
            }

            # Validate required fields
            required = ['companyName', 'phone', 'email', 'primaryColor', 'secondaryColor']
            missing = [k for k in required if not variables.get(k)]
            if missing:
                return Response({'error': 'Missing required fields', 'missing': missing}, status=status.HTTP_400_BAD_REQUEST)

            # Validate color format
            import re
            hex_re = re.compile(r'^#([A-Fa-f0-9]{6})$')
            invalid_colors = [c for c in ['primaryColor', 'secondaryColor'] if not hex_re.match(variables.get(c, ''))]
            if invalid_colors:
                return Response({'error': 'Invalid color formats', 'invalid_colors': invalid_colors}, status=status.HTTP_400_BAD_REQUEST)

            # Generate PDF from brand-assets template
            template_service = DocRaptorService()
            result = template_service.generate_pdf('brand-assets', variables)
            if result.get('success'):
                pdf_data = result.get('pdf_data', b'')
                resp = HttpResponse(pdf_data, content_type='application/pdf')
                resp['Content-Disposition'] = 'attachment; filename="brand-assets-preview.pdf"'
                return resp
            else:
                return Response({'error': 'PDF generation failed', 'details': result.get('details', '')}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            return Response({'error': 'Unexpected error', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
