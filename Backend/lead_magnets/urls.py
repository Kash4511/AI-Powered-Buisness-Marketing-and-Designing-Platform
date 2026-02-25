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
    path('generate-pdf/start/', views.generate_pdf_start, name='generate_pdf_start'),
    path('generate-pdf/status/<str:job_id>/', views.generate_pdf_status, name='generate_pdf_status'),
    path('ping/', ping, name='ping'),
    path('health/', views.HealthView.as_view(), name='health'),
    path('brand-assets/preview-pdf/', views.BrandAssetsPDFPreviewView.as_view(), name='brand-assets-preview-pdf'),
    path('preview-template/', views.PreviewTemplateView.as_view(), name='preview-template'),
    path('generate-document-preview/', views.GenerateDocumentPreviewView.as_view(), name='generate-document-preview'),
    
    # AI Conversation
    path('ai-conversation/', views.FormaAIConversationView.as_view(), name='ai-conversation'),
]
