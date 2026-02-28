#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from lead_magnets.models import LeadMagnet, LeadMagnetGeneration
from lead_magnets.services import DocRaptorService
from lead_magnets.perplexity_client import PerplexityClient

def test_pdf_workflow_with_placeholders():
    User = get_user_model()
    email = "pdf-test@example.com"
    user, _ = User.objects.get_or_create(email=email, defaults={"name": "PDF Tester", "password": "ignored"})
    lm = LeadMagnet.objects.create(title="Sustainable Architecture Guide", description="", owner=user, status="draft")
    LeadMagnetGeneration.objects.create(
        lead_magnet=lm,
        lead_magnet_type="guide",
        main_topic="sustainable-architecture",
        target_audience=["Architects/Peers"],
        audience_pain_points=["budget", "timeline"],
        desired_outcome="h",
        call_to_action="h",
        special_requests="",
    )
    client = PerplexityClient()
    service = DocRaptorService()
    answers = {
        "lead_magnet_type": "guide",
        "main_topic": "sustainable-architecture",
        "target_audience": ["Architects/Peers"],
        "audience_pain_points": ["budget", "timeline"],
        "desired_outcome": "h",
        "call_to_action": "h",
        "special_requests": "",
        "lead_magnet_description": "A professional guide"
    }
    firm_profile = {
        "firm_name": "Test Firm",
        "work_email": "team@example.com",
        "phone_number": "123",
        "firm_website": "https://example.com",
        "primary_brand_color": "#222",
        "secondary_brand_color": "#555",
        "industry": "Architecture"
    }
    # Normalize placeholders
    for key in ["desired_outcome", "call_to_action", "main_topic"]:
        val = answers.get(key)
        if isinstance(val, str) and val.strip().lower() == "h":
            answers[key] = ""
    try:
        ai_json = client.generate_lead_magnet_json(answers, firm_profile)
    except Exception as e:
        print("AI generation failed in test, using fallback:", str(e))
        title = (answers.get('main_topic') or lm.title or 'Professional Guide')
        subtitle = (answers.get('desired_outcome') or '').strip()
        cover = {"title": title, "subtitle": subtitle, "company_name": firm_profile.get('firm_name', '')}
        contact = {
            "title": "Contact & Next Steps",
            "email": firm_profile.get("work_email", ""),
            "phone": firm_profile.get("phone_number", ""),
            "website": firm_profile.get("firm_website", ""),
            "offer_name": "Strategy Session",
            "action_cta": (answers.get('call_to_action') or '').strip()
        }
        contents = {"title": "Contents", "items": [str(answers.get('main_topic') or 'Overview')]}
        sections = [
            {"title": "Overview", "content": (lm.description or "This guide provides actionable steps.")},
            {"title": "Key Considerations", "content": "Benefits, trade-offs, and pitfalls to avoid."},
            {"title": "Implementation", "content": "Recommendations and next steps."},
            {"title": "Examples", "content": "Illustrative scenarios showing application."},
        ]
        terms = {"title": "Terms of Use", "summary": "For internal use; no warranty.", "paragraphs": ["Use responsibly."]}
        ai_json = {"style": {}, "cover": cover, "contents": contents, "sections": sections, "contact": contact, "terms": terms, "brand": {"logo_url": firm_profile.get("logo_url", "")}}
    vars = client.map_to_template_vars(ai_json, firm_profile, answers)
    result = service.generate_pdf_with_ai_content("modern-guide", vars)
    assert result.get("success"), f"PDF generation failed: {result}"
    print("PDF workflow test passed; mock:", result.get("mock", False))

if __name__ == "__main__":
    test_pdf_workflow_with_placeholders()
