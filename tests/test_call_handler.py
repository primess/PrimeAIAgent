import pytest
import json
import xml.etree.ElementTree as ET # Added for TwiML parsing
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
# from twilio.twiml.voice_response import VoiceResponse # No longer needed

# Assuming your FastAPI app instance is named 'app' in 'main.py'
# Adjust the import path if your main file or app instance has a different name
try:
    from main import app
except ImportError:
    # Handle cases where the structure might be slightly different
    # or if running tests from a different root
    import sys
    import os
    # Add project root to path to allow importing 'main'
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from main import app


# Create a TestClient instance
client = TestClient(app)

# --- Test Data ---
VALID_PAYLOAD = {
    "target_phone_number": "+15551234567",
    "task_instruction": "Order a large pepperoni pizza.",
    "call_context": {"customer_name": "Alice", "pizza_size": "Large"}
}

# --- Mocks ---
# Mock the Twilio client's calls.create method globally for these tests
@pytest.fixture(autouse=True) # Corrected decorator
def mock_twilio_create():
    # Create a mock Call resource with a sid attribute
    mock_call_resource = MagicMock()
    mock_call_resource.sid = "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    with patch('main.twilio_client.calls.create', return_value=mock_call_resource) as mock_create:
        yield mock_create

# --- Tests for /order endpoint ---

def test_order_success(mock_twilio_create):
    """Test successful call initiation via POST /order"""
    response = client.post("/order", json=VALID_PAYLOAD)

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "Call initiated"
    assert "call_sid" in response_json
    assert response_json["call_sid"].startswith("CA")

    # Verify twilio_client.calls.create was called correctly
    mock_twilio_create.assert_called_once()
    call_args, call_kwargs = mock_twilio_create.call_args
    assert call_kwargs.get('to') == VALID_PAYLOAD["target_phone_number"]
    assert 'twiml' in call_kwargs

    # Parse TwiML and verify parameters more robustly
    twiml_str = call_kwargs['twiml']
    assert isinstance(twiml_str, str)
    root = ET.fromstring(twiml_str)
    stream_element = root.find('.//Connect/Stream')
    assert stream_element is not None, "Could not find <Stream> element in TwiML"
    assert stream_element.get('url') is not None, "<Stream> element missing 'url' attribute"

    params = {param.get('name'): param.get('value') for param in stream_element.findall('Parameter')}
    assert params.get('instructions') == VALID_PAYLOAD["task_instruction"], "Instructions parameter mismatch"

    # Check context parameter (value is JSON string)
    context_json_str = json.dumps(VALID_PAYLOAD["call_context"])
    assert params.get('context') == context_json_str, "Context parameter mismatch"

    # Check for fallback Say
    say_element = root.find('Say')
    assert say_element is not None and say_element.text, "Fallback <Say> element missing or empty"


def test_order_missing_phone_number():
    """Test validation error for missing target_phone_number"""
    payload = VALID_PAYLOAD.copy()
    del payload["target_phone_number"]
    response = client.post("/order", json=payload)
    assert response.status_code == 422 # FastAPI validation error


def test_order_missing_instruction():
    """Test validation error for missing task_instruction"""
    payload = VALID_PAYLOAD.copy()
    del payload["task_instruction"]
    response = client.post("/order", json=payload)
    assert response.status_code == 422 # FastAPI validation error


def test_order_invalid_phone_format():
    """Test validation error for invalid phone number format"""
    payload = VALID_PAYLOAD.copy()
    payload["target_phone_number"] = "invalid-number"
    response = client.post("/order", json=payload)
    assert response.status_code == 400 # Custom validation error
    assert "Invalid target_phone_number format" in response.json()["detail"]

def test_order_empty_instruction_string():
    """Test validation error for empty task_instruction string"""
    payload = VALID_PAYLOAD.copy()
    payload["task_instruction"] = ""
    response = client.post("/order", json=payload)
    assert response.status_code == 400 # Custom validation error
    assert "task_instruction parameter cannot be empty" in response.json()["detail"]
    
def test_order_empty_context(mock_twilio_create): # Correctly indented
    """Test successful call even with empty context"""
    payload = VALID_PAYLOAD.copy()
    payload["call_context"] = {}
    response = client.post("/order", json=payload)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "Call initiated"

    # Verify context parameter is present and is an empty JSON object by parsing TwiML
    mock_twilio_create.assert_called_once() # Now this should work
    call_args, call_kwargs = mock_twilio_create.call_args
    twiml_str = call_kwargs['twiml']
    root = ET.fromstring(twiml_str)
    stream_element = root.find('.//Connect/Stream')
    assert stream_element is not None
    params = {param.get('name'): param.get('value') for param in stream_element.findall('Parameter')}
    assert params.get('context') == '{}', "Context parameter should be empty JSON object string"

# Note: Testing the WebSocket '/media-stream' endpoint is more complex
# and often requires more involved mocking or integration testing setups.
# These tests focus on the synchronous '/order' endpoint modifications.