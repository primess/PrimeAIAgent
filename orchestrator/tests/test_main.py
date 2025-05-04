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
from orchestrator.main import app, GraphState, AIMessage, HumanMessage

# Create a single TestClient instance using the imported app
client = TestClient(app)

# --- Test Cases ---

def test_read_root():
    """Test the GET / endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_valid_mocked(mock_graph_invoke, mock_getenv):
    """Test the POST /chat endpoint with mocking the LangGraph invocation."""
    # Mock os.getenv to return a dummy API key
    mock_getenv.return_value = "DUMMY_API_KEY"

    # Define the mock response from the graph
    mock_ai_response = "This is a mocked AI response."
    mock_final_state = GraphState(messages=[
        HumanMessage(content="hello"),
        AIMessage(content=mock_ai_response)
    ])
    mock_graph_invoke.return_value = mock_final_state

    # Send request to the endpoint
    request_data = {"message": "hello", "history": []}
    response = client.post("/chat", json=request_data)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"response": mock_ai_response}

    # Check if the graph was invoked correctly
    mock_graph_invoke.assert_called_once()
    call_args, _ = mock_graph_invoke.call_args
    # Check the structure of the input passed to invoke
    assert "messages" in call_args[0]
    assert isinstance(call_args[0]["messages"], list)
    assert len(call_args[0]["messages"]) == 1 # Only the new message in this case
    assert isinstance(call_args[0]["messages"][0], HumanMessage)
    assert call_args[0]["messages"][0].content == "hello"

@patch('orchestrator.main.os.getenv')
@patch('orchestrator.main.app_graph.invoke')
def test_chat_valid_with_history_mocked(mock_graph_invoke, mock_getenv):
    """Test the POST /chat endpoint with history, mocking the LangGraph invocation."""
    # Mock os.getenv
    mock_getenv.return_value = "DUMMY_API_KEY"

    # Define mock response
    mock_ai_response = "Mocked response considering history."
    # Simulate the state the graph *would* return
    mock_final_state = GraphState(messages=[
        HumanMessage(content="previous user message"),
        AIMessage(content="previous ai response"),
        HumanMessage(content="new user message"),
        AIMessage(content=mock_ai_response)
    ])
    mock_graph_invoke.return_value = mock_final_state

    # Send request
    request_data = {
        "message": "new user message",
        "history": [
            {"role": "user", "content": "previous user message"},
            {"role": "assistant", "content": "previous ai response"} # Use 'assistant' or 'ai'
        ]
    }
    response = client.post("/chat", json=request_data)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"response": mock_ai_response}

    # Check graph invocation arguments
    mock_graph_invoke.assert_called_once()
    call_args, _ = mock_graph_invoke.call_args
    assert "messages" in call_args[0]
    assert len(call_args[0]["messages"]) == 3 # History (2) + New Message (1)
    assert isinstance(call_args[0]["messages"][0], HumanMessage)
    assert isinstance(call_args[0]["messages"][1], AIMessage)
    assert isinstance(call_args[0]["messages"][2], HumanMessage)
    assert call_args[0]["messages"][2].content == "new user message"


@patch('orchestrator.main.os.getenv')
def test_chat_missing_api_key(mock_getenv):
    """Test the POST /chat endpoint when OPENAI_API_KEY is not set."""
    # Mock os.getenv to return None, simulating a missing key
    mock_getenv.return_value = None

    # Send request
    response = client.post("/chat", json={"message": "hello"})

    # Assertions
    assert response.status_code == 500 # Expecting Internal Server Error
    assert response.json() == {"detail": "OpenAI API key not configured."}


def test_chat_invalid_missing_message():
    """Test the POST /chat endpoint with invalid data (missing message field)."""
    response = client.post("/chat", json={"other_field": "value"})
    # FastAPI should return 422 for validation errors
    assert response.status_code == 422
    # You could add more specific checks for the validation error details if needed
    # e.g., assert "message" in response.json()["detail"][0]["loc"]