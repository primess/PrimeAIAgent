import pytest
import httpx # Moved import to the top
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage

# Adjust imports based on your project structure
from backend.agent.state import GraphState
from backend.agent.nodes import analyze_task, confirm_task, trigger_call
# Assuming get_llm is in config, adjust if different
from backend.agent.config import get_llm


# --- Mocks ---

@pytest.fixture
def mock_llm():
    """Fixture to mock the LLM calls."""
    mock = MagicMock()
    # Configure mock responses as needed per test
    return mock

@pytest.fixture(autouse=True)
def patch_get_llm(mock_llm):
    """
    Auto-patches get_llm to use the mock_llm fixture.
    The primary import in nodes.py is 'from .config import get_llm',
    so we patch where it's looked up by nodes.py.
    """
    # nodes.py does: from .config import get_llm
    # So, the lookup for get_llm within nodes.py is effectively backend.agent.nodes.get_llm
    # However, get_llm itself is defined in backend.agent.config.
    # The most robust way to patch is where it's *used*.
    # If nodes.py has `from .config import get_llm`, then patching `backend.agent.nodes.get_llm`
    # or `backend.agent.config.get_llm` can both work depending on Python's import mechanics.
    # Let's try patching at the source definition first, then where it's imported if needed.
    # For simplicity and directness, patching where it's defined in config.py is often cleaner.
    # However, the original attempt patched 'backend.agent.nodes.get_llm', let's stick to that path
    # as it's where the nodes module will look for it.
    with patch('backend.agent.nodes.get_llm', return_value=mock_llm) as patched_nodes_get_llm:
        # If get_llm was also imported as `from backend.agent.config import get_llm` somewhere else
        # and that's the one being called, this second patch might be needed.
        # For now, assuming the first one covers the usage in nodes.py.
        # If errors persist related to unmocked LLM calls, we might need to add:
        # with patch('backend.agent.config.get_llm', return_value=mock_llm):
        yield patched_nodes_get_llm


# --- Tests for analyze_task ---

def test_analyze_task_identifies_phone_and_sets_state(mock_llm):
    """
    Test that analyze_task correctly identifies a phone number requirement,
    extracts it, and sets state.target_phone_number.
    """
    # Mock LLM Call 1 (Identify task and required details)
    mock_llm.invoke.side_effect = [
        MagicMock(content='{"task_description": "Call customer", "required_details": ["customer_name", "reason", "contact_number"]}'),
        # Mock LLM Call 2 (Extract details from latest message)
        MagicMock(content='{"customer_name": "Test User", "contact_number": "+15551234567"}')
    ]

    initial_state = GraphState(
        conversation_history=[
            HumanMessage(content="Call Test User at +15551234567 about their order.")
        ],
        gathered_details={},
        task_description=None,
        required_details=[],
        target_phone_number=None # Explicitly start with None
    )
    
    updated_state = analyze_task(initial_state)

    assert updated_state["task_description"] == "Call customer"
    assert "contact_number" in updated_state["required_details"]
    assert updated_state["gathered_details"].get("customer_name") == "Test User"
    assert updated_state["gathered_details"].get("contact_number") == "+15551234567"
    assert updated_state["target_phone_number"] == "+15551234567", "target_phone_number was not set in state"
    assert "contact_number" not in updated_state["missing_details"]

def test_analyze_task_phone_key_variation(mock_llm):
    """Test analyze_task with a different key for phone number like 'phone'."""
    mock_llm.invoke.side_effect = [
        MagicMock(content='{"task_description": "Call supplier", "required_details": ["supplier_id", "phone"]}'),
        MagicMock(content='{"supplier_id": "S123", "phone": "+15557654321"}')
    ]
    initial_state = GraphState(
        conversation_history=[HumanMessage(content="Call supplier S123, their number is +15557654321")],
        target_phone_number=None
    )
    updated_state = analyze_task(initial_state)
    assert updated_state["target_phone_number"] == "+15557654321"

# --- Tests for confirm_task ---

def test_confirm_task_passes_instructions_and_phone(mock_llm):
    """
    Test that confirm_task correctly constructs final_instructions
    and passes target_phone_number in its returned state update.
    """
    mock_llm.invoke.return_value = MagicMock(content="Summary: Size Large, Toppings Pepperoni, Call +15551112222. Is that correct?")

    initial_state = GraphState(
        conversation_history=[],
        task_description="Order a pizza",
        gathered_details={"size": "Large", "toppings": "Pepperoni"}, # No phone here initially
        target_phone_number="+15551112222", # Phone number is in dedicated state field
        final_instructions=None # Should be set by confirm_task
    )

    updated_state_parts = confirm_task(initial_state)

    assert "final_instructions" in updated_state_parts
    expected_instructions = "Please action the following task: Order a pizza. Details are: size: Large; toppings: Pepperoni. Target phone number is +15551112222."
    assert updated_state_parts["final_instructions"] == expected_instructions
    assert updated_state_parts["target_phone_number"] == "+15551112222"
    assert isinstance(updated_state_parts["conversation_history"][0], AIMessage)
    assert "Call +15551112222. Is that correct?" in updated_state_parts["conversation_history"][0].content

def test_confirm_task_no_phone_number(mock_llm):
    """Test confirm_task when target_phone_number is not set in state."""
    mock_llm.invoke.return_value = MagicMock(content="Summary: Task is to research. Is that correct?")
    initial_state = GraphState(
        conversation_history=[],
        task_description="Research topic",
        gathered_details={"topic": "AI"},
        target_phone_number=None, # No phone number
        final_instructions=None
    )
    updated_state_parts = confirm_task(initial_state)
    expected_instructions = "Please action the following task: Research topic. Details are: topic: AI."
    assert updated_state_parts["final_instructions"] == expected_instructions
    assert updated_state_parts["target_phone_number"] is None

# --- Tests for trigger_call ---

@pytest.mark.asyncio
async def test_trigger_call_uses_state_values_and_succeeds():
    """
    Test trigger_call correctly uses final_instructions and target_phone_number
    from the state and mocks a successful API call.
    """
    initial_state = GraphState(
        conversation_history=[],
        gathered_details={"item": "Book", "quantity": 1},
        final_instructions="Order this book now.",
        target_phone_number="+15558889999",
        task_description="Order book" # Added for completeness
    )

    # --- Mocking httpx.AsyncClient ---
    # This mock will be returned when httpx.AsyncClient is called.
    # It needs to support the async context manager protocol (__aenter__, __aexit__)
    # and have a 'post' method.
    
    mock_client_context_manager = AsyncMock() # Mock for the AsyncClient constructor's return value

    # Mock for the response object that client.post will return
    mock_response_success = AsyncMock() # The response object itself can be an AsyncMock if other methods on it are async
    mock_response_success.status_code = 200
    # json() is now a sync method in the code under test, so its mock should be a MagicMock that returns the dict
    mock_response_success.json = MagicMock(return_value={"call_sid": "CA_test_sid_123", "status": "initiated"})
    # raise_for_status() is a sync method on the response
    mock_response_success.raise_for_status = MagicMock() # Does nothing for success

    # The 'client' object yielded by 'async with' should have a 'post' method
    # This 'post' method is async and returns the mock_response_success
    mock_client_object_yielded_by_aenter = AsyncMock()
    mock_client_object_yielded_by_aenter.post = AsyncMock(return_value=mock_response_success)

    # Configure the context manager mock
    # __aenter__ should return the object that has the .post method
    mock_client_context_manager.__aenter__ = AsyncMock(return_value=mock_client_object_yielded_by_aenter)
    mock_client_context_manager.__aexit__ = AsyncMock(return_value=None) # __aexit__ usually returns None

    # Patch httpx.AsyncClient constructor to return our context manager mock
    with patch('backend.agent.nodes.httpx.AsyncClient', return_value=mock_client_context_manager) as mock_AsyncClient_constructor:
        result_state = await trigger_call(initial_state)

    mock_AsyncClient_constructor.assert_called_once() # httpx.AsyncClient() was called
    mock_client_context_manager.__aenter__.assert_called_once() # Entered the 'async with'
    mock_client_object_yielded_by_aenter.post.assert_called_once() # client.post was called
    
    args, kwargs = mock_client_object_yielded_by_aenter.post.call_args
    assert args[0] == "http://localhost:5002/order" # URL is the first positional argument, expecting port 5002
    expected_request_body = {
        "order_details": {"item": "Book", "quantity": 1},
        "task_instruction": "Order this book now.",
        "target_phone_number": "+15558889999",
    }
    assert kwargs['json'] == expected_request_body
    
    assert result_state.get("call_sid") == "CA_test_sid_123"
    assert result_state.get("error") is None

@pytest.mark.asyncio
async def test_trigger_call_missing_phone_number_in_state():
    """Test trigger_call returns error if target_phone_number is missing in state."""
    initial_state = GraphState(
        conversation_history=[],
        gathered_details={"item": "Book"},
        final_instructions="Order this book.",
        target_phone_number=None, # Phone number is None
        task_description="Order book"
    )
    result_state = await trigger_call(initial_state)
    assert "error" in result_state
    assert result_state["error"] == "Cannot trigger call: Target phone number is missing in state."
    assert result_state.get("call_sid") is None

@pytest.mark.asyncio
async def test_trigger_call_api_failure():
    """Test trigger_call handles API failure (e.g., HTTP 500)."""
    initial_state = GraphState(
        conversation_history=[],
        gathered_details={},
        final_instructions="Test API failure.",
        target_phone_number="+15550001111",
        task_description="Test"
    )
    mock_client_context_manager = AsyncMock()

    # Mock for the response object for failure
    mock_response_failure = AsyncMock()
    mock_response_failure.status_code = 500
    mock_response_failure.text = "Internal Server Error"
    mock_response_failure.json = MagicMock(return_value={}) # json() is sync, so MagicMock
    
    # Import the actual exception or a very close mock
    # For now, using a custom mock exception that the code's except block can catch
    # if it's a generic Exception, or we ensure it's an httpx.HTTPStatusError
    # The code specifically catches `httpx.HTTPStatusError`.
    # We need to mock this properly.
    
    # Create a mock that quacks like an httpx.Response for the error
    mock_error_response_obj_for_exception = MagicMock()
    mock_error_response_obj_for_exception.status_code = 500
    mock_error_response_obj_for_exception.text = "Internal Server Error from mock"
    
    mock_response_failure.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            message=f"Mock HTTP error {mock_response_failure.status_code}",
            request=MagicMock(), # Mock request object
            response=mock_error_response_obj_for_exception # Mock response object for the exception
        )
    )

    mock_client_object_yielded_by_aenter = AsyncMock()
    mock_client_object_yielded_by_aenter.post = AsyncMock(return_value=mock_response_failure)

    mock_client_context_manager.__aenter__ = AsyncMock(return_value=mock_client_object_yielded_by_aenter)
    mock_client_context_manager.__aexit__ = AsyncMock(return_value=None)

    with patch('backend.agent.nodes.httpx.AsyncClient', return_value=mock_client_context_manager):
        result_state = await trigger_call(initial_state)
    
    assert "error" in result_state
    assert result_state["error"] is not None, "Error message should not be None"
    assert f"API call failed with status code: {mock_response_failure.status_code}" in result_state["error"]
    assert result_state.get("call_sid") is None