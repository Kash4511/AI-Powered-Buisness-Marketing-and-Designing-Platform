from rest_framework import serializers
from .models import LeadMagnet, Lead, Download, FirmProfile, LeadMagnetGeneration, Template

from rest_framework import serializers
from .models import LeadMagnet, LeadMagnetGeneration, FirmProfile


# ---- Sub Serializers ----
class FirmProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmProfile
        fields = "__all__"
        read_only_fields = ["user"]

    def create(self, validated_data):
        from django.core.files.storage import default_storage
        logo = validated_data.get('logo')
        if logo is not None:
            print(f"[Cloudinary Debug] Default storage: {default_storage.__class__.__name__}")
            print(f"[Cloudinary Debug] Uploading logo file: {getattr(logo, 'name', str(logo))}")
        instance = super().create(validated_data)
        try:
            if getattr(instance, 'logo', None):
                print(f"[Cloudinary Debug] Logo stored URL: {instance.logo.url}")
        except Exception as e:
            print(f"[Cloudinary Debug] Unable to read logo URL after save: {e}")
        return instance

    def update(self, instance, validated_data):
        from django.core.files.storage import default_storage
        logo = validated_data.get('logo')
        if logo is not None:
            print(f"[Cloudinary Debug] Default storage: {default_storage.__class__.__name__}")
            print(f"[Cloudinary Debug] Uploading new logo file: {getattr(logo, 'name', str(logo))}")
        instance = super().update(instance, validated_data)
        try:
            if getattr(instance, 'logo', None):
                print(f"[Cloudinary Debug] Logo stored URL: {instance.logo.url}")
        except Exception as e:
            print(f"[Cloudinary Debug] Unable to read logo URL after update: {e}")
        return instance


class LeadMagnetGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadMagnetGeneration
        fields = [
            "lead_magnet_type",
            "main_topic",
            "target_audience",
            "audience_pain_points",
            "desired_outcome",
            "call_to_action",
            "special_requests",
        ]


# ---- Main Create Serializer ----
class CreateLeadMagnetSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    firm_profile = FirmProfileSerializer(required=False)
    generation_data = LeadMagnetGenerationSerializer()

    def create(self, validated_data):
        generation_data = validated_data.pop("generation_data")
        firm_profile_data = validated_data.pop("firm_profile", None)
        user = self.context["request"].user

        # Optionally update/create firm profile if data provided
        if firm_profile_data:
            existing_profile = FirmProfile.objects.filter(user=user).first()
            if existing_profile:
                fp_serializer = FirmProfileSerializer(existing_profile, data=firm_profile_data, partial=True)
                fp_serializer.is_valid(raise_exception=True)
                fp_serializer.save()
            else:
                # Create with user from context
                fp_serializer = FirmProfileSerializer(data=firm_profile_data)
                fp_serializer.is_valid(raise_exception=True)
                fp_serializer.save(user=user)

        # Create LeadMagnet first
        lead_magnet = LeadMagnet.objects.create(
            owner=user,
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            status="draft",
        )

        # Create related generation data
        LeadMagnetGeneration.objects.create(lead_magnet=lead_magnet, **generation_data)

        return lead_magnet


# ---- Read Serializer ----
class LeadMagnetSerializer(serializers.ModelSerializer):
    generation_data = serializers.SerializerMethodField()

    def get_generation_data(self, obj):
        try:
            if hasattr(obj, 'generation_data'):
                return LeadMagnetGenerationSerializer(obj.generation_data).data
        except Exception:
            pass
        return None

    class Meta:
        model = LeadMagnet
        fields = [
            "id",
            "title",
            "description",
            "status",
            "created_at",
            "generation_data",
        ]


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'email', 'name', 'company', 'created_at']
        read_only_fields = ['id', 'created_at']

class DashboardStatsSerializer(serializers.Serializer):
    total_lead_magnets = serializers.IntegerField()
    active_lead_magnets = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    leads_generated = serializers.IntegerField()
    # Groq Token Credits
    ai_credits = serializers.IntegerField(default=10000000)
    ai_credits_used = serializers.IntegerField(default=0)
    ai_credits_remaining = serializers.IntegerField(default=10000000)


class TemplateSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()

    def get_preview_url(self, obj: Template):
        try:
            if obj.preview_image:
                request = self.context.get('request')
                url = obj.preview_image.url
                # Ensure absolute URL
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    class Meta:
        model = Template
        fields = ['id', 'name', 'preview_url']

# class FirmProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FirmProfile
#         fields = [
#             'id', 'firm_name', 'work_email', 'phone_number', 'firm_website',
#             'firm_size', 'industry_specialties', 'logo', 'primary_brand_color',
#             'secondary_brand_color', 'preferred_font_style', 'branding_guidelines',
#             'preferred_cover_image', 'location', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']

# class LeadMagnetGenerationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LeadMagnetGeneration
#         fields = [
#             'id', 'lead_magnet_type', 'main_topic', 'target_audience',
#             'audience_pain_points', 'desired_outcome', 'call_to_action',
#             'special_requests', 'created_at'
#         ]
#         read_only_fields = ['id', 'created_at']

# class CreateLeadMagnetSerializer(serializers.Serializer):
#     # Firm profile data (if needed)
#     firm_profile = FirmProfileSerializer(required=False)
    
#     # Lead magnet generation data
#     generation_data = LeadMagnetGenerationSerializer()
    
#     # Basic lead magnet info
#     title = serializers.CharField(max_length=255)
#     description = serializers.CharField(required=False, allow_blank=True)
