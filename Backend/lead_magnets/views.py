import os
import logging
import json
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Q
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from django.core.files.base import ContentFile
import requests
import threading
from django.db import connection
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
        data = request.data.copy()
        specialties = data.get('industry_specialties')
        if isinstance(specialties, str):
            try:
                data['industry_specialties'] = json.loads(specialties)
            except json.JSONDecodeError:
                pass
        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(
            {
                'error': 'Firm profile update failed',
                'details': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

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

def run_pdf_generation_task(lead_magnet_id, user_id, template_id, use_ai_content, user_answers, architectural_images):
    """Background task for PDF generation to avoid HTTP timeouts"""
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
        lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id)
        template_selection = TemplateSelection.objects.filter(lead_magnet=lead_magnet).first()
        
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

        ai_client = PerplexityClient()
        template_service = DocRaptorService()
        template_vars = {}

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
                ai_content = ai_client.generate_lead_magnet_json(user_answers=answers_for_ai, firm_profile=firm_profile)
            except Exception as ai_err:
                logger.warning(f"AI content generation failed, using fallback: {ai_err}")
                # Minimal fallback AI content
                title = (answers_for_ai.get('main_topic') or lead_magnet.title or 'Professional Guide')
                subtitle = (answers_for_ai.get('desired_outcome') or '').strip()
                cover = {"title": title, "subtitle": subtitle, "company_name": firm_profile.get('firm_name', '')}
                contact = {
                    "title": "Contact & Next Steps",
                    "email": firm_profile.get("work_email", ""),
                    "phone": firm_profile.get("phone_number", ""),
                    "website": firm_profile.get("firm_website", ""),
                    "offer_name": "Strategy Session",
                    "action_cta": (answers_for_ai.get('call_to_action') or '').strip()
                }
                contents = {"title": "Contents", "items": [str(answers_for_ai.get('main_topic') or 'Overview')]}
                sections = [
                    {"title": "Overview", "content": (lead_magnet.description or "This guide provides actionable steps.")},
                    {"title": "Key Considerations", "content": "Benefits, trade-offs, and pitfalls to avoid."},
                    {"title": "Implementation", "content": "Recommendations and next steps."},
                    {"title": "Examples", "content": "Illustrative scenarios showing application."},
                ]
                terms = {"title": "Terms of Use", "summary": "For internal use; no warranty.", "paragraphs": ["Use responsibly."]}
                ai_content = {"style": {}, "cover": cover, "contents": contents, "sections": sections, "contact": contact, "terms": terms, "brand": {"logo_url": firm_profile.get("logo_url", "")}}
            template_vars = ai_client.map_to_template_vars(ai_content, firm_profile, answers_for_ai)
            if template_selection:
                template_selection.ai_generated_content = ai_content
                template_selection.captured_answers = answers_for_ai
                template_selection.save(update_fields=['ai_generated_content', 'captured_answers'])
        else:
            template_vars = {
                'primaryColor': firm_profile.get('primary_brand_color') or '',
                'secondaryColor': firm_profile.get('secondary_brand_color') or '',
                'companyName': firm_profile.get('firm_name') or '',
                'mainTitle': user_answers.get('main_topic') or '',
                'documentSubtitle': user_answers.get('desired_outcome') or '',
                'emailAddress': firm_profile.get('work_email') or '',
                'phoneNumber': firm_profile.get('phone_number') or '',
                'website': firm_profile.get('firm_website') or '',
            }

        if isinstance(architectural_images, list) and architectural_images:
            img_list = []
            for i, img in enumerate(architectural_images):
                src = ""
                if isinstance(img, str):
                    src = img
                elif isinstance(img, dict) and 'src' in img:
                    src = img['src']
                
                if src:
                    # Basic validation: check if it's a data URL or a web URL
                    if src.startswith('data:image/') or src.startswith('http'):
                        img_list.append({'src': src, 'alt': f'Architectural Image {i+1}'})
                        logger.info(f"Image {i+1} added to PDF task (type: {'base64' if src.startswith('data:') else 'URL'})")
                    else:
                        logger.warning(f"Image {i+1} rejected: invalid format")

            if img_list:
                # Add to template_vars so map_to_template_vars can use it
                template_vars['architecturalImages'] = img_list
                # Re-map images in case they were missed
                ai_client.map_images_to_vars(template_vars, img_list)

        for k, v in list(template_vars.items()):
            if isinstance(v, str) and len(v) > 8000:
                # Do not truncate image URLs or base64 data as it breaks them
                if not any(x in k.lower() for x in ['image', 'logo']):
                    template_vars[k] = v[:8000]

        result = template_service.generate_pdf_with_ai_content(template_id, template_vars)

        if result.get('success'):
            pdf_data = result.get('pdf_data', b'')
            filename = result.get('filename', f'lead-magnet-{lead_magnet_id}.pdf')
            
            logger.info(f"Background Task: Saving PDF for lead magnet {lead_magnet_id}...")
            # Save the file to the FileField
            lead_magnet.pdf_file.save(filename, ContentFile(pdf_data), save=True)
            
            # Re-fetch the lead magnet to ensure we have the latest data
            lead_magnet.refresh_from_db()
            lead_magnet.status = 'completed'
            lead_magnet.save(update_fields=['status'])
            
            logger.info(f"Background Task: PDF generation completed successfully for {lead_magnet_id}. URL: {lead_magnet.pdf_file.url if lead_magnet.pdf_file else 'None'}")
            
            if template_selection:
                template_selection.status = 'pdf-generated'
                template_selection.save(update_fields=['status'])
        else:
            lead_magnet.status = 'error'
            # Persist a short error reason for status endpoint consumption
            try:
                lead_magnet.description = f"PDF generation failed: {result.get('error', 'unknown')} | {str(result.get('details', ''))[:500]}"
            except Exception:
                pass
            lead_magnet.save(update_fields=['status'])
            
    except Exception as e:
        logger.error(f"Error in background PDF generation for lead magnet {lead_magnet_id}: {str(e)}", exc_info=True)
        try:
            lm = LeadMagnet.objects.get(id=lead_magnet_id)
            lm.status = 'error'
            try:
                lm.description = f"PDF generation exception: {str(e)}"
            except Exception:
                pass
            lm.save(update_fields=['status'])
        except Exception:
            pass
    finally:
        connection.close()

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_pdf(request):
    try:
        logger.info('GeneratePDFView: request received', extra={
            'user': str(getattr(request.user, 'id', 'anonymous')),
            'path': str(getattr(request, 'path', ''))
        })
        
        template_id = request.data.get('template_id')
        lead_magnet_id = request.data.get('lead_magnet_id')
        use_ai_content = bool(request.data.get('use_ai_content', True))
        user_answers = request.data.get('user_answers', {}) or {}
        architectural_images = request.data.get('architectural_images', []) or []

        if not template_id:
            return Response({'error': 'template_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not lead_magnet_id:
            return Response({'error': 'lead_magnet_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
        except LeadMagnet.DoesNotExist:
            return Response({'error': 'Lead magnet not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(lead_magnet.status) == 'in-progress':
            status_url = request.build_absolute_uri(f"/api/generate-pdf/status/?lead_magnet_id={lead_magnet_id}")
            return Response({
                'status': 'in_progress',
                'lead_magnet_id': lead_magnet_id,
                'status_url': status_url,
                'retry_after_seconds': 3
            }, status=status.HTTP_202_ACCEPTED)

        # Start background generation
        lead_magnet.status = 'in-progress'
        lead_magnet.save(update_fields=['status'])
        
        # Start thread
        thread = threading.Thread(
            target=run_pdf_generation_task,
            args=(lead_magnet_id, request.user.id, template_id, use_ai_content, user_answers, architectural_images)
        )
        thread.start()
        
        status_url = request.build_absolute_uri(f"/api/generate-pdf/status/?lead_magnet_id={lead_magnet_id}")
        return Response({
            'status': 'in_progress',
            'message': 'PDF generation started in background',
            'lead_magnet_id': lead_magnet_id,
            'status_url': status_url,
            'retry_after_seconds': 5
        }, status=status.HTTP_202_ACCEPTED) # Return 202 to trigger frontend polling

    except Exception as e:
        logger.exception('GeneratePDFView: unexpected exception')
        return Response({'error': 'PDF generation failed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect

class DownloadPDFView(APIView):
    """View to serve the generated PDF file directly, handling local vs cloud storage."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lead_magnet_id):
        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
            
            if not lead_magnet.pdf_file:
                logger.warning(f"DownloadPDFView: PDF not found for lead magnet {lead_magnet_id}")
                return Response({'error': 'PDF file not generated yet'}, status=status.HTTP_404_NOT_FOUND)
            
            # If it's a Cloudinary URL, redirect directly
            try:
                url = lead_magnet.pdf_file.url
                if url.startswith('http') and 'res.cloudinary.com' in url:
                    logger.info(f"DownloadPDFView: Redirecting to Cloudinary URL for lead magnet {lead_magnet_id}")
                    return HttpResponseRedirect(url)
            except Exception:
                pass
            
            # Serve local file from disk
            try:
                file_handle = lead_magnet.pdf_file.open('rb')
                response = FileResponse(file_handle, content_type='application/pdf')
                filename = os.path.basename(lead_magnet.pdf_file.name)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                logger.info(f"DownloadPDFView: Serving local PDF file for lead magnet {lead_magnet_id}")
                return response
            except FileNotFoundError:
                logger.error(f"DownloadPDFView: Local file not found on disk for {lead_magnet_id}")
                return Response({'error': 'PDF file not found on server disk'}, status=status.HTTP_404_NOT_FOUND)
                
        except LeadMagnet.DoesNotExist:
            return Response({'error': 'Lead magnet not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"DownloadPDFView: Unexpected error serving PDF for {lead_magnet_id}")
            return Response({'error': 'Failed to serve PDF', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GeneratePDFStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'OPTIONS':
            return [permissions.AllowAny()]
        return [permission() for permission in self.permission_classes]

    def get(self, request):
        lead_magnet_id = request.query_params.get('lead_magnet_id')
        if not lead_magnet_id:
            return Response({'error': 'lead_magnet_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            lead_magnet = LeadMagnet.objects.get(id=lead_magnet_id, owner=request.user)
        except LeadMagnet.DoesNotExist:
            return Response({'error': 'Lead magnet not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(lead_magnet.status) == 'in-progress':
            return Response({'status': 'in_progress'}, status=status.HTTP_200_OK)

        if str(lead_magnet.status) == 'error':
            details = ''
            try:
                details = (lead_magnet.description or '').strip()
            except Exception:
                pass
            payload = {'status': 'error', 'error': 'Generation failed'}
            if details:
                payload['details'] = details
            return Response(payload, status=status.HTTP_200_OK)

        if str(lead_magnet.status) == 'completed' and lead_magnet.pdf_file:
            try:
                # Use a relative URL so the frontend can handle it with its baseURL
                download_url = f"/api/lead-magnets/{lead_magnet_id}/download/"
                
                logger.info(f"GeneratePDFStatusView: PDF ready for lead magnet {lead_magnet_id}, download_url: {download_url}")
                return Response({'status': 'ready', 'pdf_url': download_url}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"GeneratePDFStatusView: Error generating download URL: {str(e)}")
                return Response({'status': 'error', 'error': 'Could not generate download URL'}, status=status.HTTP_200_OK)

        return Response({'status': 'pending'}, status=status.HTTP_200_OK)

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
            ai_content = ai_client.generate_lead_magnet_json(user_answers=user_answers, firm_profile=firm_profile)
            ai_client.debug_ai_content(ai_content)
        except Exception as e:
            ai_error = f"AI generation failed: {str(e)}"
            conversation.messages.append({'role': 'assistant', 'content': ai_error})
            conversation.save()
            return Response({'error': 'AI content generation failed', 'details': ai_error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Map AI JSON to template variables
        template_vars = ai_client.map_to_template_vars(ai_content, firm_profile)

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
            ai_data = ai_client.generate_lead_magnet_json(user_answers=user_answers, firm_profile=firm_profile)
            template_vars = ai_client.map_to_template_vars(ai_data, firm_profile)

            # Load template HTML
            templates_dir = os.path.join(settings.BASE_DIR, 'lead_magnets', 'templates')
            template_path = os.path.join(templates_dir, 'Template.html')
            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()

            final_html = render_template(template_html, template_vars)

            # Optionally save preview HTML alongside existing preview method
            service = DocRaptorService()
            preview_path = service._save_preview_html(template_id, final_html)

            return Response({
                'success': True,
                'preview_html': final_html,
                'preview_path': preview_path
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print(f"❌ GenerateDocumentPreviewView error: {e}")
            print(traceback.format_exc())
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
