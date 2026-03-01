from django.test import TestCase
from .perplexity_client import PerplexityClient
from .services import DocRaptorService
from django.conf import settings
import os
import re

class PDFGenerationTests(TestCase):
    def setUp(self):
        self.ai_client = PerplexityClient()
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
        """Test that all required Template.html variables are mapped in PerplexityClient"""
        # Mock AI content
        ai_content = {
            'title': 'Test Title',
            'summary': 'Test Summary',
            'sections': [{'title': f'Section {i}', 'content': f'Content {i}'} for i in range(10)],
            'cta': {'headline': 'CTA', 'description': 'CTA Desc'}
        }
        signals = self.ai_client.get_semantic_signals(self.user_answers)
        template_vars = self.ai_client.map_to_template_vars(ai_content, self.firm_profile, signals)
        
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
            'summary': 'Test Summary',
            'sections': [{'title': f'Section {i}', 'content': f'Content {i}'} for i in range(10)],
            'cta': {'headline': 'CTA', 'description': 'CTA Desc'}
        }
        signals = self.ai_client.get_semantic_signals(self.user_answers)
        architectural_images = ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="]
        template_vars = self.ai_client.map_to_template_vars(ai_content, self.firm_profile, signals, architectural_images)
        
        rendered_html = self.doc_service.render_template_with_vars('modern-guide', template_vars)
        
        # Check for key content presence
        self.assertIn('Test Title', rendered_html)
        self.assertIn('Test Firm', rendered_html)
        self.assertIn('Section 1', rendered_html)
        self.assertIn('Content 1', rendered_html)
        
        # Check for image presence
        self.assertIn('data:image/png;base64', rendered_html)
        
        # Check for font size increase
        self.assertIn('font-size: 1.15rem;', rendered_html)
        
        # Ensure no unrendered tags
        self.assertNotIn('{{', rendered_html)
