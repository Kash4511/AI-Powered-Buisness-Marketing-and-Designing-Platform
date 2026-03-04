import unittest
from unittest.mock import patch, MagicMock
import json
import os
from Backend.lead_magnets.perplexity_client import PerplexityClient

class TestPerplexityClient(unittest.TestCase):
    def setUp(self):
        # Ensure we have mock API keys for testing initialization
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test_gemini_key",
            "PERPLEXITY_API_KEY": "test_perplexity_key"
        }):
            self.client = PerplexityClient()

    def test_api_key_detection(self):
        """Test that the client correctly identifies available API keys and providers."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key", "PERPLEXITY_API_KEY": ""}):
            client = PerplexityClient()
            self.assertEqual(client.provider, "gemini")
            self.assertEqual(client.api_key, "test_gemini_key")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "PERPLEXITY_API_KEY": "test_perplexity_key"}):
            client = PerplexityClient()
            self.assertEqual(client.provider, "perplexity")
            self.assertEqual(client.api_key, "test_perplexity_key")

    def test_extract_json_robustness(self):
        """Test JSON extraction with various malformations."""
        # Test markdown fences
        raw_md = "Here is the JSON: ```json\n{\"key\": \"value\"}\n``` and some prose."
        self.assertEqual(self.client._extract_json(raw_md), "{\"key\": \"value\"}")

        # Test prose before and after
        raw_prose = "Intro text {\"key\": \"value\"} Outro text"
        self.assertEqual(self.client._extract_json(raw_prose), "{\"key\": \"value\"}")

        # Test nested braces
        raw_nested = "{\"outer\": {\"inner\": \"value\"}}"
        self.assertEqual(self.client._extract_json(raw_nested), raw_nested)

    def test_sanitize_json_content(self):
        """Test JSON sanitization logic."""
        # Unescaped newlines in strings
        malformed = '{"text": "Line 1\nLine 2"}'
        sanitized = self.client._sanitize_json_content(malformed)
        self.assertIn('\\n', sanitized)
        
        # Trailing commas
        trailing = '{"items": ["a", "b",],}'
        sanitized = self.client._sanitize_json_content(trailing)
        self.assertEqual(sanitized, '{"items": ["a", "b"]}')

    def test_repair_json(self):
        """Test JSON repair for truncated strings and missing braces."""
        # Unclosed string
        truncated_str = '{"key": "value'
        repaired = self.client._repair_json(truncated_str)
        self.assertEqual(repaired, '{"key": "value"}')

        # Missing closing brace
        missing_brace = '{"key": "value"'
        repaired = self.client._repair_json(missing_brace)
        self.assertEqual(repaired, '{"key": "value"}')

        # Complex truncation
        complex_trunc = '{"a": {"b": ["c"'
        repaired = self.client._repair_json(complex_trunc)
        self.assertEqual(repaired, '{"a": {"b": ["c"]}}')

    @patch('requests.post')
    def test_gemini_api_success(self, mock_post):
        """Test successful Gemini API response handling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Test Title",
                            "summary": "Summary",
                            "outcome_statement": "Outcome",
                            "commercial_analysis": "Commercial",
                            "government_analysis": "Gov",
                            "architect_analysis": "Arch",
                            "contractor_analysis": "Contractor",
                            "key_insights": ["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"],
                            "pull_quotes": ["Quote 1", "Quote 2", "Quote 3"],
                            "stats": {f"s{i}{suffix}": f"V{i}" for i in range(1, 10) for suffix in ["v", "l"]},
                            "checklists": [{"items": ["Item 1", "Item 2"]} for _ in range(3)],
                            "info_cards": [{"label": f"L{i}", "content": f"C{i}"} for i in range(7)],
                            "callouts": [{"label": f"CL{i}", "content": f"CB{i}"} for i in range(5)],
                            "sections": [{
                                "chapter_title": f"Title {i}",
                                "chapter_subtitle": f"Subtitle {i}",
                                "opening_paragraph": f"Unique Word {i} " * 100, # Ensure > 200 words
                                "root_causes": ["Cause"],
                                "quantified_impact": "Impact",
                                "intervention_framework": "Framework",
                                "benchmark_case": "Case",
                                "kpis": [{"before": "B", "after": "A"}],
                                "comparison_table": [{"factor": "F", "baseline": "B", "optimized": "O"}]
                            } for i in range(9)],
                            "call_to_action": {"headline": "H", "description": "D", "button_text": "B"}
                        })
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        self.client.provider = "gemini"
        result = self.client.generate_lead_magnet_json({}, {})
        self.assertEqual(result['title'], "Test Title")

    @patch('requests.post')
    def test_api_rate_limit_handling(self, mock_post):
        """Test handling of 429 Rate Limit error with retry."""
        # 1st response is 429
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.json.return_value = {"error": {"message": "Please retry in 0.1s"}}
        
        # 2nd response is 200 success
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "title": "Retry Title",
                            "summary": "Summary",
                            "outcome_statement": "Outcome",
                            "commercial_analysis": "Commercial",
                            "government_analysis": "Gov",
                            "architect_analysis": "Arch",
                            "contractor_analysis": "Contractor",
                            "key_insights": ["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"],
                            "pull_quotes": ["Quote 1", "Quote 2", "Quote 3"],
                            "stats": {f"s{i}{suffix}": f"V{i}" for i in range(1, 10) for suffix in ["v", "l"]},
                            "checklists": [{"items": ["Item 1", "Item 2"]} for _ in range(3)],
                            "info_cards": [{"label": f"L{i}", "content": f"C{i}"} for i in range(7)],
                            "callouts": [{"label": f"CL{i}", "content": f"CB{i}"} for i in range(5)],
                            "sections": [{
                                "chapter_title": f"Title {i}",
                                "chapter_subtitle": f"Subtitle {i}",
                                "opening_paragraph": f"Unique Word {i} " * 100, # Ensure > 200 words
                                "root_causes": ["Cause"],
                                "quantified_impact": "Impact",
                                "intervention_framework": "Framework",
                                "benchmark_case": "Case",
                                "kpis": [{"before": "B", "after": "A"}],
                                "comparison_table": [{"factor": "F", "baseline": "B", "optimized": "O"}]
                            } for i in range(9)],
                            "call_to_action": {"headline": "H", "description": "D", "button_text": "B"}
                        })
                    }]
                }
            }]
        }
        
        mock_post.side_effect = [mock_429, mock_200]
        
        # Speed up time for test
        with patch('time.sleep'):
            result = self.client.generate_lead_magnet_json({}, {})
            self.assertEqual(result['title'], "Retry Title")
            self.assertEqual(mock_post.call_count, 2)

    @patch('requests.post')
    def test_api_error_handling(self, mock_post):
        """Test API error response handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"message": "Permission Denied"}}
        mock_response.text = "Permission Denied"
        mock_post.return_value = mock_response
        
        # Suppress the error log during test to keep output clean
        with self.assertLogs('Backend.lead_magnets.perplexity_client', level='ERROR') as cm:
            with self.assertRaises(ValueError) as err:
                self.client.generate_lead_magnet_json({}, {})
            self.assertIn("Permission Denied", str(err.exception))
            self.assertIn("AI API Error (gemini): 403 - Permission Denied", cm.output[0])

if __name__ == '__main__':
    unittest.main()
