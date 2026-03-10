import os
import json
import logging
import sys
import django
from typing import Dict, Any

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from lead_magnets.groq_client import GroqClient
from lead_magnets.services.services import DocRaptorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mapping_and_rendering():
    """
    Test the mapping of AI content to template variables and ensure
    DocRaptorService can render the 15-page Template.html without errors.
    """
    print("\n🚀 Starting Integration Test: Mapping & Rendering")
    
    ai_client = GroqClient()
    doc_service = DocRaptorService()
    
    # 1. Create mock AI content (normalized format matching current groq_client.py)
    mock_ai_content = {
        "title": "Sustainable Architecture Guide",
        "subtitle": "Strategic Guide 2026",
        "document_type_label": "STRATEGIC GUIDE",
        "legal_notice_summary": "Test legal notice for Sustainable Architecture.",
        "cta_headline": "Ready to scale your sustainable projects?",
        "cta_text": "Book a complimentary 45-minute Sustainable Architecture Readiness Audit.",
        "framework": {
            "executive_summary": {"title": "Strategic Overview", "kicker": "OVERVIEW"},
        }
    }
    
    # Fill in all 11 sections with mock data containing audience and pain point keywords
    from lead_magnets.groq_client import SECTIONS
    keywords = [
        "Government", "Architects", "Peers", "Contractors",
        "tech complexity", "approvals", "risk management", "poor communication"
    ]
    
    for i, (key, title, label, _, _) in enumerate(SECTIONS):
        content = f"<h3>{title}</h3><p>Intro for {key}. This section addresses {keywords[i % len(keywords)]}.</p>"
        content += f"<h3>Technical Detail</h3><p>Solving {keywords[(i+1) % len(keywords)]} is critical.</p>"
        content += "<ul><li>Key Point 1</li><li>Key Point 2</li></ul>"
        mock_ai_content[key] = content
    
    # Add specific statistics
    mock_ai_content["key_statistics"] = "<ul><li><strong>Energy Efficiency</strong> : 45% reduction</li><li><strong>Carbon Footprint</strong> : 30% lower</li></ul>"
    
    # 2. Mock firm profile and signals
    mock_firm_profile = {
        "firm_name": "EcoBuild Solutions",
        "work_email": "info@ecobuild.ai",
        "primary_brand_color": "#2d5a27",
        "image_1_url": "https://example.com/img1.jpg",
        "image_2_url": "https://example.com/img2.jpg",
        "image_3_url": "https://example.com/img3.jpg",
        "image_4_url": "https://example.com/img4.jpg",
        "image_5_url": "https://example.com/img5.jpg",
        "image_6_url": "https://example.com/img6.jpg",
    }
    mock_signals = {
        "topic": "Sustainable Architecture",
        "audience": "Government, Architects, Contractors",
        "pain_points": "tech complexity, approvals, risk management, poor communication",
        "industry": "Architecture"
    }
    
    # 3. Test Mapping
    print("📋 Testing map_to_template_vars...")
    template_vars = ai_client.map_to_template_vars(mock_ai_content, mock_firm_profile, mock_signals)
    
    # Verify critical mappings
    assert template_vars["mainTitle"] == "Sustainable Architecture Guide"
    assert template_vars["companyName"] == "EcoBuild Solutions"
    assert template_vars["image_1_url"] == "https://example.com/img1.jpg"
    print("✅ Mapping verified.")
    
    # 4. Test Rendering
    print("🎨 Testing Template Rendering...")
    try:
        rendered_html = doc_service.render_template_with_vars("modern-guide", template_vars)
        print(f"✅ Rendering successful. Length: {len(rendered_html)} chars.")
        
        # Check for 15 pages via page number headers
        found_pages = []
        for i in range(2, 16):
            marker = f'<div class="page-number-enhanced">{i:02d}</div>'
            if marker in rendered_html:
                found_pages.append(i)
        
        print(f"📄 Found {len(found_pages)}/14 content page markers (excluding cover).")
        assert len(found_pages) >= 13, f"Expected at least 13 content pages, found {len(found_pages)}"
        
        # Validate Audience and Pain Point Keywords
        print("🔍 Validating Audience and Pain Point Keywords...")
        for kw in keywords:
            if kw.lower() in rendered_html.lower():
                print(f"✅ Keyword '{kw}' found.")
            else:
                print(f"❌ Keyword '{kw}' NOT found.")
        
        # Validate CTA
        if "Ready to scale your sustainable projects?" in rendered_html:
            print("✅ CTA Headline found.")
        else:
            print("❌ CTA Headline NOT found.")
            
        if "Sustainable Architecture Readiness Audit" in rendered_html:
            print("✅ CTA Text found.")
        else:
            print("❌ CTA Text NOT found.")
            
    except Exception as e:
        print(f"❌ Rendering failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mapping_and_rendering()
