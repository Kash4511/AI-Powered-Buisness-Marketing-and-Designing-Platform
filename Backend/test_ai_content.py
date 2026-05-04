#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from lead_magnets.models import TemplateSelection, FirmProfile
from lead_magnets.groq_client import GroqClient
import json

def main():
    # Get the latest template selection
    ts = TemplateSelection.objects.last()
    if not ts:
        print("❌ No template selections found!")
        return
        
    print(f"📋 Template Selection ID: {ts.id}")
    print(f"📋 AI Content exists: {bool(ts.ai_generated_content)}")
    
    if not ts.ai_generated_content:
        print("❌ No AI content found!")
        return
        
    ai_content = ts.ai_generated_content
    print(f"📋 AI Content keys: {list(ai_content.keys())}")
    
    # Check sections specifically
    sections = ai_content.get('sections', [])
    print(f"📋 Sections count: {len(sections)}")
    
    for i, section in enumerate(sections):
        print(f"📋 Section {i+1}:")
        print(f"  Title: '{section.get('title', 'NO TITLE')}'")
        print(f"  Content length: {len(section.get('content', ''))}")
        print(f"  Content preview: '{section.get('content', '')[:100]}...'")
        subsections = section.get('subsections', [])
        print(f"  Subsections: {len(subsections)}")
        for j, sub in enumerate(subsections):
            print(f"    Sub {j+1}: '{sub.get('title', 'NO TITLE')}' - {len(sub.get('content', ''))} chars")
    
    # Test the mapping
    fp = FirmProfile.objects.filter(user=ts.user).first()
    firm_profile_dict = {
        'firm_name': fp.firm_name if fp else '',
        'work_email': fp.work_email if fp else '',
        'phone_number': fp.phone_number if fp else '',
        'firm_website': fp.firm_website if fp else '',
        'tagline': fp.tagline if fp else '',
    } if fp else {}
    
    client = GroqClient()
    template_vars = client.map_to_template_vars(ai_content, firm_profile_dict)
    
    print(f"\n🔍 Template Variables Summary:")
    print(f"Total variables: {len(template_vars)}")
    
    # Check key content variables
    content_vars = ['customContent1', 'customContent2', 'customContent3', 'customContent4', 'customContent5']
    for var in content_vars:
        value = template_vars.get(var, '')
        print(f"{var}: {len(value)} chars - '{value[:50]}{'...' if len(value) > 50 else ''}'")
    
    # Check section titles
    title_vars = ['customTitle1', 'customTitle2', 'customTitle3', 'customTitle4', 'customTitle5']
    for var in title_vars:
        value = template_vars.get(var, '')
        print(f"{var}: '{value}'")
        
    # Check main title and subtitle
    print(f"mainTitle: '{template_vars.get('mainTitle', '')}'")
    print(f"documentSubtitle: '{template_vars.get('documentSubtitle', '')}'")
    
    # Check if any content is actually there
    non_empty_content = {k: v for k, v in template_vars.items() if v and str(v).strip()}
    print(f"\n✅ Non-empty variables: {len(non_empty_content)}")
    
    # Show some non-empty variables
    for k, v in list(non_empty_content.items())[:10]:
        preview = str(v)[:30] + '...' if len(str(v)) > 30 else str(v)
        print(f"  {k}: '{preview}'")

if __name__ == '__main__':
    main()