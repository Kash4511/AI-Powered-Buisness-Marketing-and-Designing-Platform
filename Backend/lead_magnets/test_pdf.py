from django.test import TestCase
from .services.ai_generator import LeadMagnetAIService
from .services import DocRaptorService
from django.conf import settings
import os
import re

class PDFGenerationTests(TestCase):
    def setUp(self):
        self.ai_client = LeadMagnetAIService()
        self.doc_service = DocRaptorService()
        self.user_answers = {
            'firm_name': 'Test Firm',
            'work_email': 'test@example.com',
            'phone_number': '123456789',
            'firm_website': 'www.test.com',
            'main_topic': 'Smart Home Design',
            'lead_magnet_type': 'Guide',
            'target_audience': 'Homeowners',
            'desired_outcome': 'A beautiful smart home',
            'call_to_action': 'Contact us today'
        }
        self.firm_profile = {
            'firm_name': 'Test Firm',
            'work_email': 'test@example.com',
            'phone_number': '123456789',
            'firm_website': 'www.test.com',
            'primary_brand_color': '#2a5766',
            'secondary_brand_color': '#FFFFFF'
        }

    def test_variable_mapping_completeness(self):
        """Test that all required Template.html variables are mapped"""
        # Mock AI content
        ai_content = {
            'title': 'Test Title',
            'subtitle': 'Test Subtitle',
            'target_audience_summary': 'Test Summary',
            'key_pain_points': [{'title': 'P1', 'description': 'D1'}],
            'solutions': [{'title': 'S1', 'implementation_steps': ['Step 1'], 'expected_outcome': 'O1'}],
            'roi_section': {'cost_savings': 'C1', 'time_savings': 'T1', 'competitive_advantage': 'A1'},
            'call_to_action': 'CTA'
        }
        
        # Manually map to maintain template compatibility for now
        template_vars = {
            'mainTitle': ai_content.get('title'),
            'documentSubtitle': ai_content.get('subtitle'),
            'companyName': self.firm_profile.get('firm_name'),
            'emailAddress': self.firm_profile.get('work_email'),
            'phoneNumber': self.firm_profile.get('phone_number'),
            'website': self.firm_profile.get('firm_website'),
            'primaryColor': self.firm_profile.get('primary_brand_color'),
            'secondaryColor': self.firm_profile.get('secondary_brand_color'),
            'summary': ai_content.get('target_audience_summary'),
            'key_pain_points': ai_content.get('key_pain_points'),
            'solutions': ai_content.get('solutions'),
            'roi': ai_content.get('roi_section'),
            'cta': ai_content.get('call_to_action'),
        }
        
        # Load Template.html and find all {{variable}}
        template_path = os.path.join(settings.BASE_DIR, 'lead_magnets', 'templates', 'Template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        placeholders = re.findall(r'\{\{\s*(\w+)\s*\}\}', html_content)
        unique_placeholders = set(placeholders)
        
        missing_vars = [p for p in unique_placeholders if p not in template_vars]
        
        self.assertEqual(len(missing_vars), 0, f"Missing variables in mapping: {missing_vars}")

    def test_cover_title_positioning_css(self):
        """Test that CSS for cover title positioning is correctly set to centered-left"""
        template_path = os.path.join(settings.BASE_DIR, 'lead_magnets', 'templates', 'Template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Check for cv-body positioning
        self.assertIn('justify-content: center; /* Center vertically */', html_content)
        self.assertIn('align-items: flex-start; /* Align horizontally to the left */', html_content)
        
        # Check for text alignment
        self.assertIn('text-align: left; /* Ensure left alignment */', html_content)
        
    def test_pdf_rendering_not_blank(self):
        """Test that rendered HTML contains expected content and is not blank"""
        ai_content = {
            'title': 'Test Title',
            'subtitle': 'Test Subtitle',
            'target_audience_summary': 'Test Summary',
            'key_pain_points': [{'title': 'P1', 'description': 'D1'}],
            'solutions': [{'title': 'S1', 'implementation_steps': ['Step 1'], 'expected_outcome': 'O1'}],
            'roi_section': {'cost_savings': 'C1', 'time_savings': 'T1', 'competitive_advantage': 'A1'},
            'call_to_action': 'CTA'
        }
        
        template_vars = {
            'mainTitle': ai_content.get('title'),
            'documentSubtitle': ai_content.get('subtitle'),
            'companyName': self.firm_profile.get('firm_name'),
            'emailAddress': self.firm_profile.get('work_email'),
            'phoneNumber': self.firm_profile.get('phone_number'),
            'website': self.firm_profile.get('firm_website'),
            'primaryColor': self.firm_profile.get('primary_brand_color'),
            'secondaryColor': self.firm_profile.get('secondary_brand_color'),
            'summary': ai_content.get('target_audience_summary'),
            'key_pain_points': ai_content.get('key_pain_points'),
            'solutions': ai_content.get('solutions'),
            'roi': ai_content.get('roi_section'),
            'cta': ai_content.get('call_to_action'),
        }
        
        rendered_html = self.doc_service.render_template_with_vars('modern-guide', template_vars)
        
        # Check for key content presence
        self.assertIn('Test Title', rendered_html)
        self.assertIn('Test Firm', rendered_html)
        self.assertIn('Test Summary', rendered_html)
        self.assertIn('CTA', rendered_html)
        
        # Check for image presence
        self.assertIn('data:image/png;base64', rendered_html)
        
        # Check for font size increase
        self.assertIn('font-size: 1.15rem;', rendered_html)
        
        # Ensure no unrendered tags
        self.assertNotIn('{{', rendered_html)
