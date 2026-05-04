#!/usr/bin/env python
"""
Test the full AI content generation workflow with the Groq API key.
This script tests the actual GroqClient class used in the lead magnet generation.
"""

import os
import sys
import django
import json
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Import after Django setup
from lead_magnets.groq_client import GroqClient

def test_ai_workflow():
    print("🚀 Testing Full AI Content Generation Workflow...")
    print("=" * 60)
    
    try:
        # Initialize the GroqClient
        print("🔧 Initializing GroqClient...")
        client = GroqClient()
        
        # Test sample lead magnet generation
        print("📝 Testing lead magnet content generation...")
        
        # Sample data similar to what would come from the frontend
        test_data = {
            "industry": "Real Estate",
            "target_audience": "First-time home buyers",
            "pain_points": ["Understanding the buying process", "Finding the right mortgage", "Navigating paperwork"],
            "lead_magnet_type": "Checklist",
            "company_name": "Dream Home Realty",
            "tone": "Professional yet approachable"
        }
        
        # Create a prompt for lead magnet generation
        prompt = f"""
        Create a comprehensive {test_data['lead_magnet_type'].lower()} for {test_data['industry']} targeting {test_data['target_audience']}.
        
        Company: {test_data['company_name']}
        Tone: {test_data['tone']}
        
        Address these pain points:
        {', '.join(test_data['pain_points'])}
        
        Please provide:
        1. A compelling title
        2. 8-10 actionable checklist items
        3. Brief explanations for each item
        4. A call-to-action at the end
        
        Keep it practical and valuable for the target audience.
        """
        
        print(f"🎯 Generating content for: {test_data['industry']} - {test_data['lead_magnet_type']}")
        print(f"👥 Target audience: {test_data['target_audience']}")
        
        # Prepare test data in the format expected by the client
        user_answers = {
            "industry": test_data["industry"],
            "target_audience": test_data["target_audience"],
            "pain_points": test_data["pain_points"],
            "lead_magnet_type": test_data["lead_magnet_type"],
            "tone": test_data["tone"]
        }
        
        firm_profile = {
            "company_name": test_data["company_name"],
            "industry": test_data["industry"]
        }
        
        # Generate content using the client
        response = client.generate_lead_magnet_json(user_answers, firm_profile)
        
        if response:
            print("✅ AI content generation successful!")
            print("\n📄 Generated Content Preview:")
            print("-" * 40)
            
            # Handle JSON response
            if isinstance(response, dict):
                # Show key fields from the JSON response
                if 'mainTitle' in response:
                    print(f"Title: {response['mainTitle']}")
                if 'sections' in response and response['sections']:
                    print(f"Sections: {len(response['sections'])} sections generated")
                    if response['sections']:
                        first_section = response['sections'][0]
                        if 'title' in first_section:
                            print(f"First section: {first_section['title']}")
                
                # Convert to string for preview
                response_str = json.dumps(response, indent=2)
                preview = response_str[:500] + "..." if len(response_str) > 500 else response_str
            else:
                preview = str(response)[:500] + "..." if len(str(response)) > 500 else str(response)
            
            print(preview)
            print("-" * 40)
            
            # Save full content to file for review
            output_file = "ai_generated_content_test.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                if isinstance(response, dict):
                    json.dump({
                        "test_metadata": {
                            "industry": test_data['industry'],
                            "type": test_data['lead_magnet_type'],
                            "target": test_data['target_audience'],
                            "company": test_data['company_name']
                        },
                        "generated_content": response
                    }, f, indent=2, ensure_ascii=False)
                else:
                    f.write(str(response))
            
            print(f"💾 Full content saved to: {output_file}")
            return True
        else:
            print("❌ AI content generation failed - no response received")
            return False
            
    except Exception as e:
        print(f"❌ Error in AI workflow test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 AI Content Generation Workflow Test")
    print("=" * 60)
    
    # Test the full workflow
    workflow_success = test_ai_workflow()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Full Workflow: {'✅ PASS' if workflow_success else '❌ FAIL'}")
    
    if workflow_success:
        print("\n🎉 AI workflow test passed! Groq API is fully functional.")
        print("✅ The Groq API is working correctly for lead magnet generation.")
    else:
        print("\n💥 Workflow test failed. Please check the error messages above.")
    
    print("=" * 60)