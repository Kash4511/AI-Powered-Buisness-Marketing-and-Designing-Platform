import json
import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock weasyprint before importing services that depend on it
mock_weasyprint_mod = MagicMock()
sys.modules['weasyprint'] = mock_weasyprint_mod
sys.modules['weasyprint.text'] = MagicMock()
sys.modules['weasyprint.text.fonts'] = MagicMock()

from django.conf import settings

# Configure minimal Django settings before importing anything that depends on them
if not settings.configured:
    settings.configure(
        BASE_DIR='/mock/base/dir',
        MEDIA_ROOT='/mock/media/root',
        INSTALLED_APPS=['lead_magnets'],
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
    )

import os
os.environ['GROQ_API_KEY'] = 'mock_key'

from lead_magnets.services.ai_generator import LeadMagnetAIService
from lead_magnets.services.services import WeasyPrintService

@pytest.fixture
def mock_groq_client():
    with patch('lead_magnets.services.ai_generator.Groq') as mock:
        client_instance = mock.return_value
        yield client_instance

@pytest.fixture
def mock_weasyprint():
    with patch('lead_magnets.services.services.HTML') as mock_html:
        mock_instance = mock_html.return_value
        mock_instance.write_pdf.return_value = b"%PDF-1.4 Mock Data"
        yield mock_html

def test_full_pdf_generation_flow(mock_groq_client, mock_weasyprint):
    """
    Test the full AI -> Template -> WeasyPrint pipeline.
    Mocks external APIs to verify logic and validation.
    """
    # 1. Setup Mock Groq Response
    mock_ai_content = {
        "title": "Urban Placemaking Guide",
        "subtitle": "Strategic Insights for Smart Cities",
        "target_audience_summary": "City planners and developers",
        "audience_analysis": {
            "commercial_label": "Developers",
            "commercial_text": "Commercial focus..."
        },
        "key_pain_points": [{"title": "Complexity", "description": "High barrier to entry"}],
        "solutions": [{"title": "Smart Design", "implementation_steps": ["Step 1"], "expected_outcome": "Reduced cost"}],
        "roi_section": {"cost_savings": "20%", "time_savings": "10%"},
        "call_to_action": "Contact us today"
    }
    
    # Mock base generation
    mock_groq_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_ai_content)
    
    # Mock expansion generation
    mock_expansion = {
        "chapter_1": {"title": "CH1", "intro": "Intro 1", "body_a": "Body text " * 600, "body_b": "Body text " * 600},
        "chapter_2": {"title": "CH2", "intro": "Intro 2", "body_a": "Body text " * 600, "body_b": "Body text " * 600},
        "chapter_3": {"title": "CH3", "intro": "Intro 3", "body_a": "Body text " * 600, "body_b": "Body text " * 600},
        "chapter_4": {"title": "CH4", "intro": "Intro 4", "body_a": "Body text " * 600, "body_b": "Body text " * 600},
        "chapter_5": {"title": "CH5", "intro": "Intro 5", "body_a": "Body text " * 600, "body_b": "Body text " * 600},
        "roi_detailed_analysis": "ROI detailed analysis text.",
        "conclusion_strategy": "Conclusion strategy text.",
        "drop_caps": ["S", "F", "C", "M", "T"],
        "image_labels": ["A", "B", "C"]
    }
    
    # Mock expansion call
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(mock_ai_content)))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(mock_expansion)))])
    ]

    ai_service = LeadMagnetAIService()
    ai_result = ai_service.generate_lead_magnet({"main_topic": "Urban Placemaking"})
    ai_result = ai_service.expand_content_sections(ai_result, {"main_topic": "Urban Placemaking"})
    
    assert ai_result['title'] == "Urban Placemaking Guide"
    assert 'expansions' in ai_result

    # 2. Setup Mock WeasyPrint
    weasyprint_service = WeasyPrintService()
    
    # Variables mapping (simplified for test)
    variables = {
        'mainTitle': ai_result['title'],
        'companyName': 'Test Firm',
        'architecturalImages': ["data:image/png;base64,mock_data"]
    }

    pdf_result = weasyprint_service.generate_pdf('modern-guide', variables)
    
    assert pdf_result['success'] is True
    assert pdf_result['pdf_data'] == b"%PDF-1.4 Mock Data"
    assert mock_weasyprint.called
