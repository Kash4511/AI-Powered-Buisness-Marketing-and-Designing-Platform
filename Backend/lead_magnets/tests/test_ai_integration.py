import unittest
import os
from Backend.lead_magnets.perplexity_client import PerplexityClient

class TestAIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = PerplexityClient()
        self.signals = {
            "main_topic": "Strategic Property Repurposing",
            "lead_magnet_type": "Executive Guide",
            "target_audience": "Real Estate Investors",
            "audience_pain_points": "High vacancy, ROI uncertainty",
            "desired_outcome": "Unlock hidden asset value",
            "call_to_action": "Book a strategic consultation",
            "special_requests": "Focus on adaptive reuse potential."
        }
        self.firm_profile = {
            "firm_name": "Institutional Advisory Group",
            "work_email": "consultant@institutional.com",
            "phone_number": "+1 555-987-6543",
            "firm_website": "www.institutionaladvisory.com",
            "primary_brand_color": "#2a5766",
            "secondary_brand_color": "#FFFFFF"
        }

    def test_full_ai_generation_flow(self):
        """Test the full AI generation flow with real API calls if an API key is present."""
        if not self.client.api_key:
            self.skipTest("AI API key (GEMINI_API_KEY or PERPLEXITY_API_KEY) is missing. Skipping integration test.")
            
        print(f"🚀 Running full AI generation integration test via {self.client.provider}...")
        
        try:
            # Generate AI content
            ai_content = self.client.generate_lead_magnet_json(self.signals, self.firm_profile)
            
            # Verify structure and content
            self.assertIn("title", ai_content)
            self.assertIn("sections", ai_content)
            self.assertEqual(len(ai_content["sections"]), 9, "AI generation should return exactly 9 sections.")
            
            # Map to template variables
            # Note: We need some architectural images for mapping
            mock_images = ["https://example.com/img1.jpg", "https://example.com/img2.jpg", "https://example.com/img3.jpg"]
            template_vars = self.client.map_to_template_vars(ai_content, self.firm_profile, self.signals, mock_images)
            
            # Verify mapping
            self.assertEqual(template_vars["mainTitle"], ai_content["title"])
            self.assertEqual(template_vars["companyName"], self.firm_profile["firm_name"])
            self.assertIn("primaryColor", template_vars)
            
            print(f"✅ AI integration test passed successfully via {self.client.provider}.")
            
        except Exception as e:
            self.fail(f"AI integration test failed with error: {str(e)}")

if __name__ == '__main__':
    unittest.main()
