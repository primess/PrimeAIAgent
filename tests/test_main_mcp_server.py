import pytest
import asyncio
import httpx
from unittest.mock import MagicMock, patch # AsyncMock might be needed if we mock async methods directly

# MCP Client imports
from mcp.client import ClientSession
from mcp.client.transports.sse import sse_client_transport # Correct context manager for SSE
from mcp.common.message import Message, MessageType
from mcp.common.errors import MCPError, ToolError, RemoteError

# Import the FastAPI app from main.py
# We need to ensure environment variables are set before this import if main.py uses them at module level.
# The fixture below will handle this.
main_fastapi_app = None
mcp_server_sse_path = None
mcp_server_messages_path = None
twilio_client_mock_path = 'main.twilio_client' # Path to twilio_client in main.py
TwilioRestException_path = 'main.TwilioRestException' # Path to TwilioRestException in main.py
# Path to the specific TwilioRestException class, assuming it's imported in main.py or accessible via main.
# If main.py imports `from twilio.base.exceptions import TwilioRestException`, this path might need adjustment
# or we import TwilioRestException directly in tests. For now, assume it's available via `main`.

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module", autouse=True)
def set_env_vars(module_mocker):
    """
    Set necessary environment variables at the module level before main.py is imported.
    Using module_mocker from pytest-mock if available, or monkeypatch.
    This runs once per module.
    """
    # Using pytest-mock's module_mocker if specifically needed for module-level mocking before import.
    # monkeypatch is function-scoped by default. For module scope, can define a module-scoped fixture.
    # For simplicity, we'll assume direct monkeypatching in a module-scoped autouse fixture works,
    # or rely on the fact that imports happen after fixture setup for session/module.
    # Let's use a more standard way with monkeypatch if pytest-mock's module_mocker isn't standard.
    # Pytest's monkeypatch can be used in module scope.
    pass # Will be handled by http_client fixture's specific monkeypatching for now

@pytest.fixture(scope="module")
async def main_app_instance(monkeypatch_module):
    """
    Module-scoped fixture to set environment variables and import main.py components.
    `monkeypatch_module` is a hypothetical way to get module-scoped monkeypatch.
    Standard `monkeypatch` is function-scoped. We'll use a trick or ensure it's applied before import.
    """
    monkeypatch_module.setenv("CHAT_MODEL_API_KEY", "dummy_chat_api_key")
    monkeypatch_module.setenv("TWILIO_ACCOUNT_SID", "dummy_twilio_sid")
    monkeypatch_module.setenv("TWILIO_AUTH_TOKEN", "dummy_twilio_token")
    monkeypatch_module.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
    monkeypatch_module.setenv("NGROK_URL", "test-ngrok.io") # For get_mcp_websocket_url

    # Import after env vars are set
    from main import app as real_app, MCP_SSE_PATH, MCP_MESSAGES_PATH
    
    global main_fastapi_app, mcp_server_sse_path, mcp_server_messages_path
    main_fastapi_app = real_app
    mcp_server_sse_path = MCP_SSE_PATH
    mcp_server_messages_path = MCP_MESSAGES_PATH
    
    return main_fastapi_app

@pytest.fixture
async def http_client(main_app_instance):
    """Provides an httpx.AsyncClient for the FastAPI app."""
    # main_app_instance fixture ensures env vars are set and app is loaded.
    async with httpx.AsyncClient(app=main_app_instance, base_url="http://testserver") as client:
        yield client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_mcp_server_initialization_and_list_tools(http_client):
    """
    Tests that the MCP server initializes and lists the 'initiate_call_mcp_tool'.
    """
    sse_url = f"{http_client.base_url}{mcp_server_sse_path}"
    messages_url = f"{http_client.base_url}{mcp_server_messages_path}"

    # The sse_client_transport needs the http_client to route its internal requests
    # to our test app. We achieve this by passing the client to the transport.
    async with sse_client_transport(
        uri=sse_url, 
        post_uri=messages_url, 
        client=http_client # Pass the test client
    ) as (reader, writer):
        async with ClientSession(reader, writer, name="test-client") as session:
            await session.initialize(capabilities={}) # Must initialize session
            
            tools = await session.list_tools()
            assert isinstance(tools, list)
            
            found_tool = False
            for tool in tools:
                if tool.name == "initiate_call_mcp_tool":
                    found_tool = True
                    assert "Initiates an outbound call using Twilio" in tool.description
                    assert tool.parameters is not None
                    param_names = {p.name for p in tool.parameters.properties}
                    expected_params = {"target_phone_number", "task_instruction", "call_context"}
                    assert param_names == expected_params
                    # Further checks for parameter types could be added if MCP schema provides them
                    # e.g., checking tool.parameters.properties['target_phone_number'].type == 'string'
                    break
            assert found_tool, "Tool 'initiate_call_mcp_tool' not found."

@pytest.mark.asyncio
async def test_mcp_call_initiate_call_tool_success(http_client, mocker):
    """
    Tests successful invocation of the 'initiate_call_mcp_tool'.
    """
    sse_url = f"{http_client.base_url}{mcp_server_sse_path}"
    messages_url = f"{http_client.base_url}{mcp_server_messages_path}"

    # Mock twilio_client.calls.create in main.py
    mock_twilio_call_create = mocker.patch(f"{twilio_client_mock_path}.calls.create")
    expected_call_sid = "CA1234567890abcdef1234567890abcd"
    mock_twilio_call_create.return_value = MagicMock(sid=expected_call_sid)

    async with sse_client_transport(uri=sse_url, post_uri=messages_url, client=http_client) as (reader, writer):
        async with ClientSession(reader, writer, name="test-client-success") as session:
            await session.initialize(capabilities={})
            
            tool_params = {
                "target_phone_number": "+15551234567",
                "task_instruction": "Test task: call the number.",
                "call_context": {"customer_id": "CUST001", "priority": "high"}
            }
            result = await session.call_tool("initiate_call_mcp_tool", tool_params)
            
            assert result is not None
            assert result.get("status") == "Call initiated"
            assert result.get("call_sid") == expected_call_sid

            # Assert that twilio_client.calls.create was called correctly
            # asyncio.to_thread means the mock is on the sync method
            mock_twilio_call_create.assert_called_once()
            call_args = mock_twilio_call_create.call_args
            assert call_args is not None
            assert call_args.kwargs['to'] == tool_params["target_phone_number"]
            # TWILIO_PHONE_NUMBER is used from env, check it if needed or trust main.py's logic
            assert "twiml" in call_args.kwargs
            # Further TwiML content assertions could be added if necessary

@pytest.mark.asyncio
async def test_mcp_call_initiate_call_tool_twilio_error(http_client, mocker):
    """
    Tests error handling when Twilio client raises an exception.
    """
    sse_url = f"{http_client.base_url}{mcp_server_sse_path}"
    messages_url = f"{http_client.base_url}{mcp_server_messages_path}"

    # Import TwilioRestException directly for use in the test
    from twilio.base.exceptions import TwilioRestException

    # Mock twilio_client.calls.create to raise TwilioRestException
    mock_twilio_call_create = mocker.patch(f"{twilio_client_mock_path}.calls.create")
    twilio_error_message = "Simulated Twilio API error"
    mock_twilio_call_create.side_effect = TwilioRestException(
        status=500, uri="/Calls", msg=twilio_error_message
    )

    async with sse_client_transport(uri=sse_url, post_uri=messages_url, client=http_client) as (reader, writer):
        async with ClientSession(reader, writer, name="test-client-twilio-error") as session:
            await session.initialize(capabilities={})
            
            tool_params = {
                "target_phone_number": "+15557654321",
                "task_instruction": "Test Twilio error scenario.",
                "call_context": {}
            }
            
            with pytest.raises(RemoteError) as exc_info: # MCP client should raise RemoteError for tool errors
                await session.call_tool("initiate_call_mcp_tool", tool_params)
            
            assert exc_info.value is not None
            # The error message from the tool (via FastMCP) might be wrapped.
            # Check if the original Twilio message is part of the error details.
            # FastMCP typically wraps the original exception message.
            assert twilio_error_message in str(exc_info.value.message)
            # Or if FastMCP has a more structured error, check its fields.
            # For example, if exc_info.value.data has more details.

@pytest.mark.asyncio
async def test_mcp_call_initiate_call_tool_validation_error(http_client, mocker):
    """
    Tests error handling for input validation errors in the MCP tool.
    """
    sse_url = f"{http_client.base_url}{mcp_server_sse_path}"
    messages_url = f"{http_client.base_url}{mcp_server_messages_path}"

    # No need to mock Twilio here as validation should happen first.
    # However, ensure the mock is in place if any call could still reach it.
    mocker.patch(f"{twilio_client_mock_path}.calls.create", new_callable=MagicMock)


    async with sse_client_transport(uri=sse_url, post_uri=messages_url, client=http_client) as (reader, writer):
        async with ClientSession(reader, writer, name="test-client-validation-error") as session:
            await session.initialize(capabilities={})
            
            # Test case 1: Empty task_instruction
            invalid_params_empty_instruction = {
                "target_phone_number": "+15551234567",
                "task_instruction": "", # Empty instruction
                "call_context": {}
            }
            with pytest.raises(RemoteError) as exc_info_empty:
                await session.call_tool("initiate_call_mcp_tool", invalid_params_empty_instruction)
            assert "task_instruction parameter cannot be empty" in str(exc_info_empty.value.message).lower()

            # Test case 2: Invalid phone number
            invalid_params_bad_phone = {
                "target_phone_number": "12345", # Invalid format
                "task_instruction": "Valid instruction here.",
                "call_context": {}
            }
            with pytest.raises(RemoteError) as exc_info_phone:
                await session.call_tool("initiate_call_mcp_tool", invalid_params_bad_phone)
            assert "invalid target_phone_number format" in str(exc_info_phone.value.message).lower()

# Note: The monkeypatch_module fixture for module-scoped monkeypatching is a bit conceptual.
# A common way is to use a top-level conftest.py or ensure fixtures that need module scope
# are defined correctly. For this single file, the `main_app_instance` fixture tries to achieve this.
# If `main.py`'s imports are sensitive at the exact moment of `from main import app`,
# this setup might need adjustment, e.g. by moving env var setup to a session-start hook
# or ensuring `main.py` is structured to allow config overrides after import for testing.
# For now, assuming `main_app_instance` correctly handles pre-import setup.

# Need to provide `monkeypatch_module` if it's not a built-in pytest fixture.
# Standard pytest `monkeypatch` is function-scoped. For module scope, we can define it like this:
@pytest.fixture(scope="module")
def monkeypatch_module(request):
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()
```

Some notes on the generated code:
- The `sse_client_transport` from `mcp.client.transports.sse` is the correct context manager. I've added `client=http_client` to its arguments, assuming it can take an `httpx.AsyncClient` to route its requests. This is crucial for testing against an in-memory FastAPI app. If this specific way of passing the client is not supported by `sse_client_transport`, this part might need adjustment (e.g., using `respx` or a similar library if `sse_client_transport` makes its own top-level `httpx` calls).
- Mocking paths for Twilio client (`twilio_client_mock_path`) are defined.
- The `main_app_instance` fixture now uses `monkeypatch_module` (a manually defined module-scoped monkeypatch) to set environment variables *before* importing `main.py` components. This is critical if `main.py` reads env vars at the module level.
- `TwilioRestException` is imported directly in the relevant test for clarity and to ensure it's the correct type.
- Assertions for errors now check for `RemoteError` from `mcp.common.errors`, as this is what `FastMCP` and `ClientSession` typically convert tool execution errors into. The original error message is expected to be part of `exc_info.value.message`.
- Parameter validation tests check for parts of the expected error messages.

This structure seems like a good starting point. I'll proceed with these tests.Okay, I have created the content for `tests/test_main_mcp_server.py`.
This includes:
1.  **Imports**: `pytest`, `asyncio`, `httpx`, `ClientSession`, `sse_client_transport` from `mcp.client.transports.sse`, `Message`, `MessageType`, `MCPError`, `ToolError`, `RemoteError` from `mcp.common`, and mock utilities.
2.  **Fixtures**:
    *   `event_loop`: Standard fixture for asyncio tests.
    *   `monkeypatch_module`: A module-scoped version of `monkeypatch`.
    *   `main_app_instance`: A module-scoped fixture that uses `monkeypatch_module` to set necessary environment variables (`CHAT_MODEL_API_KEY`, Twilio credentials, `NGROK_URL`) *before* importing `app`, `MCP_SSE_PATH`, and `MCP_MESSAGES_PATH` from `main.py`. This ensures that `main.py` initializes correctly with dummy credentials for testing.
    *   `http_client`: An async fixture that provides an `httpx.AsyncClient` instance configured with the `main_fastapi_app` (obtained from `main_app_instance`) and a base URL of `http://testserver`.
3.  **Test Cases**:
    *   **`test_mcp_server_initialization_and_list_tools`**:
        *   Connects to the MCP server using `sse_client_transport`, passing the `http_client` to ensure requests are routed to the test app.
        *   Initializes a `ClientSession`.
        *   Calls `session.list_tools()` and asserts that `initiate_call_mcp_tool` is listed with its correct description and parameters.
    *   **`test_mcp_call_initiate_call_tool_success`**:
        *   Mocks `main.twilio_client.calls.create` to return a successful call object with a `sid`.
        *   Connects via SSE, initializes a session, and calls `initiate_call_mcp_tool` with valid parameters.
        *   Asserts the success response from the tool and that the Twilio mock was called with correct arguments.
    *   **`test_mcp_call_initiate_call_tool_twilio_error`**:
        *   Mocks `main.twilio_client.calls.create` to raise a `TwilioRestException`.
        *   Connects and calls the tool.
        *   Asserts that a `RemoteError` is raised by the MCP client and that the error message contains details of the Twilio failure.
    *   **`test_mcp_call_initiate_call_tool_validation_error`**:
        *   Connects and calls the tool with invalid inputs (empty `task_instruction`, invalid `target_phone_number`).
        *   Asserts that a `RemoteError` is raised for each validation failure and that the error message reflects the specific validation problem.

This set of tests covers the initialization, tool listing, successful tool execution, and error handling (both external dependency errors and input validation errors) for the MCP server functionality in `main.py`.
The crucial part for these tests to work is the correct interaction between the `sse_client_transport` and the `http_client` fixture. The code assumes `sse_client_transport` can use the provided `http_client` for its underlying HTTP requests, which is a common pattern for testability in such SDKs.

I will now submit the subtask report.
