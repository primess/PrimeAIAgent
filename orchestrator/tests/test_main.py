import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Import the app instance from orchestrator.main
# Ensure main.py is structured to allow importing 'app' without running the server directly
# (The current structure seems okay for this)
from orchestrator.main import app, GraphState, AIMessage, HumanMessage # Keep AIMessage, HumanMessage

# Create a single TestClient instance using the imported app
client = TestClient(app)

# --- Test Cases ---

def test_read_root():
    """Test the GET / endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

# Define standard required details for pizza example used in main.py placeholders
PIZZA_REQUIRED_DETAILS = ["pizza_size", "toppings", "delivery_address", "phone_number"]

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_initial_request_asks_detail(mock_graph_invoke, mock_getenv):
    """Test initial request triggers asking for the first missing detail."""
    mock_getenv.return_value = "DUMMY_API_KEY"

    # Simulate graph state after analyze_task -> ask_for_details
    mock_ai_question = "Okay, got it. What about the pizza size?"
    mock_final_state = GraphState(
        conversation_history=[
            HumanMessage(content="I want to order a pizza"),
            AIMessage(content=mock_ai_question) # AI asks the first question
        ],
        task_description="Order a pizza",
        required_details=PIZZA_REQUIRED_DETAILS,
        gathered_details={},
        missing_details=["pizza_size", "toppings", "delivery_address", "phone_number"] # All missing initially
    )
    mock_graph_invoke.return_value = mock_final_state

    request_data = {"message": "I want to order a pizza", "history": []}
    response = client.post("/chat", json=request_data)

    assert response.status_code == 200
    # Check only the 'response' part, ignore the 'state' key for this assertion
    assert response.json().get("response") == mock_ai_question

    # Verify graph input
    mock_graph_invoke.assert_called_once()
    call_args, _ = mock_graph_invoke.call_args
    assert "conversation_history" in call_args[0]
    assert len(call_args[0]["conversation_history"]) == 1
    assert call_args[0]["conversation_history"][0].content == "I want to order a pizza"
    # Other state fields are initialized by the graph nodes in this flow

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_provides_detail_asks_next(mock_graph_invoke, mock_getenv):
    """Test providing one detail triggers asking for the next missing detail."""
    mock_getenv.return_value = "DUMMY_API_KEY"

    # Simulate graph state after user provides size -> analyze_task -> ask_for_details (for toppings)
    mock_ai_question = "Okay, got it. What about the toppings?"
    mock_final_state = GraphState(
        conversation_history=[
            HumanMessage(content="I want to order a pizza"),
            AIMessage(content="Okay, got it. What about the pizza size?"),
            HumanMessage(content="Make it large"),
            AIMessage(content=mock_ai_question) # AI asks the next question
        ],
        task_description="Order a pizza",
        required_details=PIZZA_REQUIRED_DETAILS,
        gathered_details={"pizza_size": "mentioned"}, # Size gathered (placeholder value)
        missing_details=["toppings", "delivery_address", "phone_number"] # Toppings is next
    )
    mock_graph_invoke.return_value = mock_final_state

    request_data = {
        "message": "Make it large",
        "history": [
            {"role": "user", "content": "I want to order a pizza"},
            {"role": "assistant", "content": "Okay, got it. What about the pizza size?"}
        ]
    }
    response = client.post("/chat", json=request_data)

    assert response.status_code == 200
    # Check only the 'response' part, ignore the 'state' key for this assertion
    assert response.json().get("response") == mock_ai_question

    # Verify graph input
    mock_graph_invoke.assert_called_once()
    call_args, _ = mock_graph_invoke.call_args
    assert "conversation_history" in call_args[0]
    assert len(call_args[0]["conversation_history"]) == 3 # Initial + Q + A
    assert call_args[0]["conversation_history"][2].content == "Make it large"

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_provides_last_detail_confirms(mock_graph_invoke, mock_getenv):
    """Test providing the last detail triggers the confirmation message."""
    mock_getenv.return_value = "DUMMY_API_KEY"

    # Simulate graph state after user provides last detail -> analyze_task -> confirm_task
    mock_ai_confirmation = "Great! Just to confirm Order a pizza: pizza size: mentioned, toppings: mentioned, delivery address: mentioned, phone number: mentioned. Is that correct?"
    mock_final_state = GraphState(
        conversation_history=[
            # ... previous turns ...
            HumanMessage(content="My number is 555-1234"),
            AIMessage(content=mock_ai_confirmation) # AI confirms
        ],
        task_description="Order a pizza",
        required_details=PIZZA_REQUIRED_DETAILS,
        gathered_details={ # All details gathered (placeholder values)
            "pizza_size": "mentioned",
            "toppings": "mentioned",
            "delivery_address": "mentioned",
            "phone_number": "mentioned"
        },
        missing_details=[] # No details missing
    )
    mock_graph_invoke.return_value = mock_final_state

    request_data = {
        "message": "My number is 555-1234",
        "history": [
            {"role": "user", "content": "I want to order a pizza"},
            {"role": "assistant", "content": "Okay, got it. What about the pizza size?"},
            {"role": "user", "content": "Make it large"},
            {"role": "assistant", "content": "Okay, got it. What about the toppings?"},
            {"role": "user", "content": "Pepperoni please"},
            {"role": "assistant", "content": "Okay, got it. What about the delivery address?"},
            {"role": "user", "content": "123 Main St"},
            {"role": "assistant", "content": "Okay, got it. What about the phone number?"},
        ]
    }
    response = client.post("/chat", json=request_data)

    assert response.status_code == 200
    # Check only the 'response' part, ignore the 'state' key for this assertion
    assert response.json().get("response") == mock_ai_confirmation

    # Verify graph input
    mock_graph_invoke.assert_called_once()
    call_args, _ = mock_graph_invoke.call_args
    assert "conversation_history" in call_args[0]
    assert len(call_args[0]["conversation_history"]) == 9 # Full history + new message
    assert call_args[0]["conversation_history"][-1].content == "My number is 555-1234"

@patch('orchestrator.main.os.getenv')
def test_chat_endpoint_missing_api_key(mock_getenv):
    """Test the POST /chat endpoint when OPENAI_API_KEY is not set at the endpoint level."""
    mock_getenv.return_value = None # Simulate missing key for the endpoint check
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 500
    assert response.json() == {"detail": "OpenAI API key not configured."}

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_graph_invoke_raises_api_key_error(mock_graph_invoke, mock_getenv):
    """Test when the graph invocation itself raises an API key error (e.g., from _get_llm)."""
    mock_getenv.return_value = "DUMMY_API_KEY" # Key is present for endpoint check
    # Simulate the graph invoke raising the ValueError due to missing key internally
    mock_graph_invoke.side_effect = ValueError("OpenAI API key not found in environment variables.")

    request_data = {"message": "hello", "history": []}
    response = client.post("/chat", json=request_data)

    assert response.status_code == 500
    assert response.json() == {"detail": "OpenAI API key not found in environment variables."}
    mock_graph_invoke.assert_called_once() # Ensure invoke was still called

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_graph_invoke_raises_unexpected_error(mock_graph_invoke, mock_getenv):
    """Test handling of unexpected errors during graph invocation."""
    mock_getenv.return_value = "DUMMY_API_KEY"
    mock_graph_invoke.side_effect = Exception("Something went wrong inside the graph")

    request_data = {"message": "hello", "history": []}
    response = client.post("/chat", json=request_data)

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal error occurred during graph execution."}
    mock_graph_invoke.assert_called_once()

def test_chat_endpoint_invalid_missing_message():
    """Test the POST /chat endpoint with invalid data (missing 'message' field)."""
    response = client.post("/chat", json={"history": []}) # Missing 'message'
    assert response.status_code == 422 # FastAPI validation error
    # Check that the error detail points to the missing 'message' field
    assert response.json()['detail'][0]['loc'] == ['body', 'message']