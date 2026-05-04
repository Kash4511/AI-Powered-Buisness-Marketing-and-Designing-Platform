import pytest
from lead_magnets.groq_client import GroqClient, TYPE_CONFIGS, DOC_TYPE_LABELS
from lead_magnets.services.services import WeasyPrintService

@pytest.fixture
def groq_client():
    return GroqClient()

@pytest.fixture
def firm_profile():
    return {
        "name": "Test Firm",
        "work_email": "test@firm.com",
        "primary_brand_color": "#1a365d",
        "secondary_brand_color": "#c5a059",
    }

@pytest.mark.parametrize("doc_type", TYPE_CONFIGS.keys())
def test_lead_magnet_type_fidelity(groq_client, doc_type, firm_profile):
    """
    Verify that each lead magnet type produces the correct sections and labels.
    """
    signals = {
        "topic": "Digital Transformation",
        "audience": "Enterprise Leaders",
        "document_type": doc_type
    }
    
    # Check signal mapping
    mapped_signals = groq_client.get_semantic_signals({
        "main_topic": "Digital Transformation",
        "target_audience": "Enterprise Leaders",
        "document_type": doc_type
    })
    assert mapped_signals["document_type"] == doc_type
    
    # Check section configuration
    config = TYPE_CONFIGS[doc_type]
    sections = config["sections"]
    assert len(sections) > 0
    
    # Check label
    label = DOC_TYPE_LABELS.get(doc_type)
    assert label is not None

def test_template_mapping_fidelity():
    """
    Verify that the service correctly maps types to their corresponding template files.
    """
    service = WeasyPrintService()
    for doc_type, expected_template in service.TEMPLATE_REGISTRY.items():
        path = service._get_template_path(doc_type)
        assert path.endswith(expected_template)
        # Ensure the file actually exists (we created them earlier)
        import os
        assert os.path.exists(path), f"Template file for {doc_type} does not exist at {path}"

def test_variable_injection_contains_type(groq_client, firm_profile):
    """
    Verify that the injected variables contain the correct document type.
    """
    doc_type = "checklist"
    sections = TYPE_CONFIGS[doc_type]["sections"]
    ai_content = {
        "title": "Test Title",
        "subtitle": "Test Subtitle",
        "document_type": doc_type,
        "document_type_label": "Implementation Checklist",
        "sections": {
            s[0]: {"content": "<p>Content</p>", "title": s[1], "label": s[2]}
            for s in sections
        },
        "content": {s[0]: "<p>Content</p>" for s in sections}
    }
    # We need to normalize first to get the framework structure
    normalized = groq_client.normalize_ai_output(ai_content)
    vars = groq_client.map_to_template_vars(normalized, firm_profile, {"topic": "Test"})
    
    assert vars["documentType"] == doc_type
    assert vars["documentTypeLabel"] == "Implementation Checklist"
