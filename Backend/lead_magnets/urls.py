from django.urls import path
from . import views
from .tests_ping import ping

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
    path('generate-pdf/', views.generate_pdf, name='generate-pdf'),
    path('generate-pdf/start/', views.generate_pdf, name='generate-pdf-start'),
    path('ping/', ping, name='ping'),
    path('lead-magnets/<int:lead_magnet_id>/download/', views.DownloadPDFView.as_view(), name='download-pdf'),
    path('generate-pdf/status/', views.GeneratePDFStatusView.as_view(), name='generate-pdf-status'),
    path('health/', views.HealthView.as_view(), name='health'),
    path('brand-assets/preview-pdf/', views.BrandAssetsPDFPreviewView.as_view(), name='brand-assets-preview-pdf'),
    path('preview-template/', views.PreviewTemplateView.as_view(), name='preview-template'),
    path('generate-document-preview/', views.GenerateDocumentPreviewView.as_view(), name='generate-document-preview'),
    
    # AI Conversation
    path('ai-conversation/', views.FormaAIConversationView.as_view(), name='ai-conversation'),
    path('db-status/', views.DBStatusView.as_view(), name='db-status'),
]
