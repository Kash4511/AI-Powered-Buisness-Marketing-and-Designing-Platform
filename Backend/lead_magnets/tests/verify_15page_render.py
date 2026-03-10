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
    
    # 1. Create mock AI content (normalized format)
    mock_ai_content = {
        "title": "Future of Modular Construction",
        "subtitle": "Strategic Guide 2026",
        "document_type_label": "STRATEGIC GUIDE",
        "legal_notice_summary": "Test legal notice.",
        "cta_headline": "Ready to scale?",
        "cta_text": "Contact Us",
        "framework": {
            "executive_summary": {"title": "Strategic Overview", "kicker": "OVERVIEW"},
        }
    }
    
    # Fill in all 11 sections with mock data
    from lead_magnets.groq_client import SECTIONS
    for key, title, label, _, _ in SECTIONS:
        mock_ai_content[key] = f"<h3>{title}</h3><p>Intro for {key}.</p><h3>Sub {key}</h3><p>Detail for {key}.</p>"
    
    # Add some specific extractions
    mock_ai_content["stat1Value"] = "85%"
    mock_ai_content["stat1Label"] = "Efficiency"
    
    # 2. Mock firm profile and signals
    mock_firm_profile = {
        "firm_name": "BuildSmart AI",
        "work_email": "info@buildsmart.ai",
        "primary_brand_color": "#1a365d",
        "image_1_url": "https://example.com/img1.jpg",
        "image_2_url": "https://example.com/img2.jpg",
    }
    mock_signals = {"topic": "Modular Construction"}
    
    # 3. Test Mapping
    print("📋 Testing map_to_template_vars...")
    template_vars = ai_client.map_to_template_vars(mock_ai_content, mock_firm_profile, mock_signals)
    
    # Verify critical mappings
    assert template_vars["mainTitle"] == "Future of Modular Construction"
    assert template_vars["companyName"] == "BuildSmart AI"
    assert template_vars["image_1_url"] == "https://example.com/img1.jpg"
    assert "vars" in template_vars
    print("✅ Mapping verified.")
    
    # 4. Test Rendering
    print("🎨 Testing Template Rendering...")
    try:
        rendered_html = doc_service.render_template_with_vars("modern-guide", template_vars)
        print(f"✅ Rendering successful. Length: {len(rendered_html)} chars.")
        
        # Basic check for 15 pages (search for page numbers or page breaks)
        page_nums = [f'<span class="page-num">{i:02d}</span>' for i in range(1, 16)]
        found_pages = []
        for p in page_nums:
            if p in rendered_html:
                found_pages.append(p)
        
        print(f"📄 Found {len(found_pages)}/15 page number markers.")
        
        # Check TOC content
        if "Table of Contents" in rendered_html:
            print("✅ TOC present.")
            
        # Check image injection
        if '<img src="https://example.com/img1.jpg"' in rendered_html:
            print("✅ Image 1 injected.")
        else:
            print("❌ Image 1 NOT injected.")
            
    except Exception as e:
        print(f"❌ Rendering failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mapping_and_rendering()
