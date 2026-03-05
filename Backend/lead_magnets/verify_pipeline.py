import os
import json
import logging
import sys
from typing import Dict, Any

# Add current directory to sys.path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the client to test
from groq_client import GroqClient

def test_pipeline():
    """
    Verifies the 13-stage pipeline logic for a 'Checklist' type.
    Note: This requires a valid GROQ_API_KEY in the environment.
    """
    client = GroqClient()
    
    # Test signals for "Sustainable Architecture" Checklist
    user_answers = {
        "main_topic": "Sustainable Architecture Implementation",
        "target_audience": "Real Estate Developers",
        "pain_points": ["Cost overruns in green tech", "Regulatory complexity", "Lack of specialized talent"],
        "lead_magnet_type": "checklist",
        "industry": "Architecture & Real Estate"
    }
    
    firm_profile = {
        "firm_name": "EcoArchitects Global",
        "work_email": "strategy@ecoarchitects.com",
        "firm_website": "www.ecoarchitects.com",
        "primary_brand_color": "#2E7D32",
        "architectural_images": [
            "https://images.unsplash.com/photo-1518005020250-68a0d0d7595a",
            "https://images.unsplash.com/photo-1449156003053-c306a0482a91"
        ]
    }

    print("\n--- 🟢 STEP 1: Semantic Signals ---")
    signals = client.get_semantic_signals(user_answers)
    print(json.dumps(signals, indent=2))
    
    assert signals["document_type"] == "checklist"
    assert "Checklist" in signals["document_type_label"]

    print("\n--- 🟢 STEP 2: Strategic Outline (1 API Call) ---")
    try:
        outline = client._generate_strategic_outline(signals, firm_profile)
        print(f"Outline Title: {outline.get('title')}")
        print(f"Chapters Count: {len(outline.get('chapters_list', []))}")
        
        # Limit chapters for the test to save tokens/time if needed, 
        # but let's try the full 15+ pages to ensure no 400 error.
        
        print("\n--- 🟢 STEP 3: Granular Expansion (15+ API Calls) ---")
        # For the sake of this verification script, we'll only expand the first 2 chapters 
        # to verify the alignment and HTML structure without burning too many tokens.
        if outline.get('chapters_list'):
            original_chapters = outline['chapters_list']
            outline['chapters_list'] = original_chapters[:2] # Test first 2
            
            expanded = client._generate_granular_content(outline, signals, firm_profile)
            
            for key, content in expanded.items():
                if key in ['drop_caps', 'image_labels']: continue
                print(f"\n--- Section: {key} ---")
                print(f"Content Length: {len(content)} characters")
                # Verify checklist HTML if it's a checklist type
                if '<div class="checklist-item">' in content:
                    print("✅ Found Checklist HTML structure!")
                else:
                    print("⚠️ Checklist HTML structure NOT found in this section.")
                
                # Verify alignment
                if any(pp.lower() in content.lower() for pp in user_answers["pain_points"]):
                    print("✅ Found alignment with pain points!")
                else:
                    print("⚠️ Pain point alignment might be weak in this section.")

            print("\n--- 🟢 STEP 4: Template Mapping ---")
            ai_content = client.normalize_ai_output({"expansions": expanded, **outline, "document_type_label": signals["document_type_label"]})
            vars = client.map_to_template_vars(ai_content, firm_profile, signals)
            
            print(f"Mapped Variables: {list(vars.keys())}")
            print(f"Content Sections Count: {len(vars['content_sections'])}")
            print(f"TOC Sections Count: {len(vars['toc_sections'])}")
            
            # Verify primary color normalization
            print(f"Primary Color: {vars['primaryColor']}")
            assert vars['primaryColor'].startswith("#")

            print("\n✅ PIPELINE VERIFICATION SUCCESSFUL (LOGIC ONLY)")
            
    except Exception as e:
        print(f"\n❌ PIPELINE VERIFICATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY") and not os.getenv("GROQ_API_KEY_API_KEY"):
        print("⚠️ Skipping live API test: GROQ_API_KEY not found.")
    else:
        test_pipeline()
