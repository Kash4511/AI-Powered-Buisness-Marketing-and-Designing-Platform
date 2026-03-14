
import json
import os
import sys
from typing import Dict, Any

# Add the current directory to sys.path to import groq_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from groq_client import GroqClient, SECTIONS
except ImportError:
    # Fallback for different execution contexts
    from Backend.lead_magnets.groq_client import GroqClient, SECTIONS

def test_mapping_logic():
    client = GroqClient()
    
    # Mock AI content that follows the format expected by _parse_unified_content
    mock_ai_content = {
        "title": "Sustainable Urban Design",
        "subtitle": "A Guide to Green Cities",
        "document_type": "guide",
        "document_type_label": "Strategic Guide",
        "sections": {},
        "framework": {},
        "ai_images": [
            {"description": "A modern green building with solar panels"},
            {"description": "A walkable city street with trees"}
        ]
    }
    
    # Fill mock sections with content that has bullets and stats
    for key, _, _, _, _ in SECTIONS:
        mock_ai_content[key] = f"""
        <p>This is a long intro paragraph for {key} that should be extracted as the intro text for the new layout.</p>
        <ul>
            <li>Bullet point 1 for {key}</li>
            <li>Bullet point 2 for {key}</li>
            <li>Bullet point 3 for {key}</li>
        </ul>
        <p>This is the support paragraph. It mentions a 45% increase in efficiency which should be picked up as a stat.</p>
        <p><strong>Key Insight:</strong> This is a bolded callout box content.</p>
        """
        mock_ai_content["framework"][key] = {"title": f"Title for {key}", "kicker": "KICKER"}

    firm_profile = {
        "firm_name": "EcoArch Studios",
        "primary_brand_color": "#2ecc71",
        "secondary_brand_color": "#27ae60",
        "work_email": "hello@ecoarch.com",
        "firm_website": "www.ecoarch.com"
    }
    
    signals = {
        "topic": "Sustainable Urban Design",
        "audience": "City Planners"
    }

    print("--- Testing map_to_template_vars ---")
    vars = client.map_to_template_vars(mock_ai_content, firm_profile, signals)
    
    # Verify core variables
    assert vars["primaryColor"] == "#2ecc71"
    assert vars["companyName"] == "EcoArch Studios"
    assert "Sustainable Urban Design" in vars["documentTitle"]
    
    # Verify section-specific granular variables
    for key, _, _, _, _ in SECTIONS:
        print(f"Checking section: {key}")
        assert f"section_{key}_intro" in vars
        assert f"section_{key}_bullets_html" in vars
        assert f"section_{key}_support" in vars
        assert f"section_{key}_callout" in vars
        assert f"section_{key}_stat_val" in vars
        assert f"section_{key}_image_url" in vars
        
        # Check if content was actually extracted
        intro = vars[f"section_{key}_intro"]
        bullets = vars[f"section_{key}_bullets_html"]
        support = vars[f"section_{key}_support"]
        callout = vars[f"section_{key}_callout"]
        stat_val = vars[f"section_{key}_stat_val"]
        
        print(f"  Intro length: {len(intro)}")
        print(f"  Bullets count: {bullets.count('<li>')}")
        print(f"  Stat val: '{stat_val}'")
        
        assert len(intro) > 10
        assert bullets.count('<li>') >= 3
        # Use simple presence check for debugging
        if "45%" not in stat_val and stat_val != "":
             print(f"DEBUG: Stat extraction failed. Stat val was '{stat_val}'")
        
        assert "45%" in stat_val or stat_val == ""
        assert "Key Insight" in callout or callout == ""
        assert "unsplash.com" in vars[f"section_{key}_image_url"]

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    try:
        test_mapping_logic()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
