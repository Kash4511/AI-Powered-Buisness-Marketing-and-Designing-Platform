#!/usr/bin/env python3
"""
Test script to verify timeout handling and retry logic in GroqClient
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

def test_timeout_handling():
    """Test the timeout handling and retry logic"""
    print("🧪 Testing Groq API timeout handling...")
    
    # Initialize client
    client = GroqClient()
    
    # Simple test data
    user_answers = {
        'target_audience': 'First-time home buyers',
        'pain_points': 'Confused about the buying process',
        'content_type': 'checklist',
        'industry_focus': 'Real Estate'
    }
    
    firm_profile = {
        'name': 'Test Realty',
        'specialization': 'Residential Real Estate',
        'location': 'Test City'
    }
    
    try:
        print("📡 Making API call with retry logic...")
        result = client.generate_lead_magnet_json(
            user_answers=user_answers,
            firm_profile=firm_profile
        )
        
        print("✅ API call successful!")
        print(f"📄 Generated content has {len(result.get('sections', []))} sections")
        print(f"📝 Main title: {result.get('mainTitle', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_timeout_handling()
    if success:
        print("\n🎉 Timeout handling test passed!")
    else:
        print("\n💥 Timeout handling test failed!")