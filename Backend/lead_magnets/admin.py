from django.contrib import admin
from .models import (
    LeadMagnet, Lead, Download, BrandAsset, FirmProfile, 
    LeadMagnetGeneration, FormaAIConversation, Template, 
    TemplateSelection, SystemConfiguration, PDFGenerationJob
)

@admin.register(PDFGenerationJob)
class PDFGenerationJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'lead_magnet', 'status', 'progress', 'created_at')
    list_filter = ('status',)
    search_fields = ('job_id', 'lead_magnet__title')

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'config_type', 'updated_at')
    search_fields = ('key', 'description')
    list_filter = ('config_type',)

@admin.register(LeadMagnet)
class LeadMagnetAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'owner__email')

@admin.register(FirmProfile)
class FirmProfileAdmin(admin.ModelAdmin):
    list_display = ('firm_name', 'user', 'work_email', 'updated_at')
    search_fields = ('firm_name', 'user__email', 'work_email')

@admin.register(LeadMagnetGeneration)
class LeadMagnetGenerationAdmin(admin.ModelAdmin):
    list_display = ('lead_magnet', 'lead_magnet_type', 'main_topic', 'created_at')
    list_filter = ('lead_magnet_type', 'main_topic')

admin.site.register(Lead)
admin.site.register(Download)
admin.site.register(BrandAsset)
admin.site.register(FormaAIConversation)
admin.site.register(Template)
admin.site.register(TemplateSelection)
