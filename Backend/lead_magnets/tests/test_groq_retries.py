import pytest
import json
import time
from unittest.mock import MagicMock, patch
from lead_magnets.groq_client import GroqClient

@pytest.fixture
def groq_client():
    with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
        return GroqClient()

def test_call_ai_success(groq_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"test": "data"})
    mock_response.choices[0].finish_reason = "stop"
    
    with patch.object(groq_client.client.chat.completions, 'create', return_value=mock_response):
        result = groq_client._call_ai("sys", "user")
        assert result == {"test": "data"}

def test_call_ai_rate_limit_retry_success(groq_client):
    mock_error = Exception("Rate limit exceeded (429)")
    mock_success = MagicMock()
    mock_success.choices[0].message.content = json.dumps({"test": "retry-success"})
    mock_success.choices[0].finish_reason = "stop"
    
    with patch.object(groq_client.client.chat.completions, 'create', side_effect=[mock_error, mock_success]):
        # Mock time.sleep to avoid waiting during tests
        with patch('time.sleep'):
            result = groq_client._call_ai("sys", "user")
            assert result == {"test": "retry-success"}
            assert groq_client.client.chat.completions.create.call_count == 2

def test_call_ai_500_retry_success(groq_client):
    mock_error = Exception("Internal Server Error (500)")
    mock_success = MagicMock()
    mock_success.choices[0].message.content = json.dumps({"test": "retry-500-success"})
    mock_success.choices[0].finish_reason = "stop"
    
    with patch.object(groq_client.client.chat.completions, 'create', side_effect=[mock_error, mock_success]):
        with patch('time.sleep'):
            result = groq_client._call_ai("sys", "user")
            assert result == {"test": "retry-500-success"}
            assert groq_client.client.chat.completions.create.call_count == 2

def test_call_ai_error_0_propagation(groq_client):
    # Error "0" should be converted to a more helpful message
    mock_error = Exception("0")
    
    with patch.object(groq_client.client.chat.completions, 'create', side_effect=mock_error):
        with pytest.raises(Exception) as excinfo:
            groq_client._call_ai("sys", "user")
        assert "Groq API connection failed or returned an empty error" in str(excinfo.value)

def test_call_ai_max_retries_exceeded(groq_client):
    mock_error = Exception("Rate limit exceeded (429)")
    
    with patch.object(groq_client.client.chat.completions, 'create', side_effect=[mock_error, mock_error, mock_error]):
        with patch('time.sleep'):
            with pytest.raises(Exception) as excinfo:
                groq_client._call_ai("sys", "user")
            assert "Rate limit exceeded" in str(excinfo.value)
            assert groq_client.client.chat.completions.create.call_count == 3

if __name__ == "__main__":
    # If run directly, try to use pytest
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
