from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('lead-magnets/', views.LeadMagnetListCreateView.as_view(), name='lead-magnet-list-create'),
    path('lead-magnets/<int:pk>/', views.LeadMagnetDetailView.as_view(), name='lead-magnet-detail'),
    path('firm-profile/', views.FirmProfileView.as_view(), name='firm-profile'),
    path('create-lead-magnet/', views.CreateLeadMagnetView.as_view(), name='create-lead-magnet'),
    
    # Template management
    path('templates/', views.ListTemplatesView.as_view(), name='list-templates'),
    path('select-template/', views.SelectTemplateView.as_view(), name='select-template'),
    path('generate-slogan/', views.GenerateSloganView.as_view(), name='generate-slogan'),
    # New: compatibility routes for existing frontend calls
    path('generate-pdf/', views.generate_pdf_compat, name='generate-pdf'),
    path('generate-pdf/status/', views.generate_pdf_status_compat, name='generate-pdf-status-compat'),
    # Job-based routes (internal/advanced clients)
    path('generate-pdf/start/', views.generate_pdf_start, name='generate_pdf_start'),
    path('generate-pdf/status/<str:job_id>/', views.generate_pdf_status, name='generate_pdf_status'),
    path('generate-pdf/stop/<str:job_id>/', views.generate_pdf_stop, name='generate_pdf_stop'),
    path('health/', views.HealthView.as_view(), name='health'),
    path('brand-assets/preview-pdf/', views.BrandAssetsPDFPreviewView.as_view(), name='brand-assets-preview-pdf'),
    path('preview-template/', views.PreviewTemplateView.as_view(), name='preview-template'),
    path('generate-document-preview/', views.GenerateDocumentPreviewView.as_view(), name='generate-document-preview'),
    
    # AI Conversation
    path('ai-conversation/', views.FormaAIConversationView.as_view(), name='ai-conversation'),
    # Relative download route expected by frontend polling
    path('lead-magnets/<int:lead_magnet_id>/download/', views.download_lead_magnet_pdf, name='lead-magnet-download'),
    
    # Dynamic Theming
    path('theme/', views.get_theme_palette, name='theme-palette'),
]
