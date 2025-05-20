import pytest
import httpx # For ConnectError
from httpx import AsyncClient # For test client
from unittest.mock import patch, AsyncMock, MagicMock

from types import SimpleNamespace # For yielding multiple objects from fixture

# MCP Client related imports for mocking and error types
from mcp.common.errors import MCPError, ToolError, ClientError
# CallInitiationRequest will be provided by the app_env_fixture

# Target URL for MCP server (used by app code, set via env var in fixture)
TARGET_MCP_URL = "http://mocked-mcp-server:1234" # Matches what app_env_fixture sets

@pytest.fixture(name="app_env_fixture", scope="function", autouse=True)
def fixture_reset_app_module_and_mock_env(mocker):
    """
    Fixture to ensure each test gets a fresh app import with specific env mocks.
    This isolates tests, especially for module-level configurations.
    It yields the app instance and CallInitiationRequest model.
    """
    import sys

    # Mock os.getenv *before* importing the app module.
    # Ensures MCP_SERVER_URL is set to TARGET_MCP_URL for the app's context.
    mocker.patch('os.getenv', lambda key, default=None: TARGET_MCP_URL if key == "MCP_SERVER_URL" else ("dummy_openai_key" if key == "OPENAI_API_KEY" else default))

    modules_to_reload = [
        'backend.web.app',
        'backend.agent.workflow_manager',
        'backend.web.call_handler_models'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    from backend.web.app import app as fresh_app, MCP_SERVER_BASE_URL, DEFAULT_MCP_SERVER_URL
    from backend.web.call_handler_models import CallInitiationRequest as FreshCallInitiationRequest
        
    assert MCP_SERVER_BASE_URL == TARGET_MCP_URL, \
        f"MCP_SERVER_BASE_URL was {MCP_SERVER_BASE_URL}, expected {TARGET_MCP_URL}. Check os.getenv mock."

    yield SimpleNamespace(app=fresh_app, CallInitiationRequest=FreshCallInitiationRequest)

    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]

# --- Kept Tests for MCP_SERVER_URL warning ---
@pytest.mark.asyncio
async def test_mcp_url_default_warning(mocker, caplog, app_env_fixture):
    """
    Test that a warning is logged if MCP_SERVER_URL is not set and the default is used.
    This test re-imports app with specific os.getenv mocking.
    """
    import sys
    
    if 'backend.web.app' in sys.modules:
        del sys.modules['backend.web.app']

    mocker.patch('os.getenv', lambda key, default=None: default if key == "MCP_SERVER_URL" else "dummy_key_for_other_configs")
    
    from backend.web.app import app as new_app_instance, DEFAULT_MCP_SERVER_URL # app import triggers the log
    
    found_warning = False
    for record in caplog.records:
        if record.levelname == "WARNING" and f"MCP_SERVER_URL not set, using default: {DEFAULT_MCP_SERVER_URL}" in record.message:
            found_warning = True
            break
    assert found_warning, "Warning for default MCP_SERVER_URL not logged."

    if 'backend.web.app' in sys.modules:
        del sys.modules['backend.web.app']
    # Fixture will reset for next test

def test_mcp_url_default_warning_check_url_and_log(mocker, caplog, app_env_fixture):
    """
    Test that MCP_SERVER_BASE_URL is set to default when env var is missing,
    and a warning is logged. (Alternative way to test the warning)
    """
    import sys
    if 'backend.web.app' in sys.modules:
        del sys.modules['backend.web.app'] 

    mocker.patch('os.getenv', lambda key, default=None: default if key == "MCP_SERVER_URL" else ("dummy_openai_key" if key == "OPENAI_API_KEY" else default))
    
    from backend.web.app import app as app_for_warning_test, MCP_SERVER_BASE_URL, DEFAULT_MCP_SERVER_URL, logger
    
    assert MCP_SERVER_BASE_URL == DEFAULT_MCP_SERVER_URL
    
    found_warning = False
    for record in caplog.records:
        if record.name == logger.name and record.levelname == "WARNING" and \
           f"MCP_SERVER_URL not set, using default: {DEFAULT_MCP_SERVER_URL}" in record.message:
            found_warning = True
            break
    assert found_warning, f"Warning for default MCP_SERVER_URL not logged by logger '{logger.name}'. Log records: {caplog.text}"

    if 'backend.web.app' in sys.modules:
        del sys.modules['backend.web.app']
    # Fixture will reset for next test

# --- New Test Cases for /mcp/initiate_call ---

@pytest.mark.asyncio
async def test_mcp_initiate_call_success(mocker, app_env_fixture):
    """Test successful call to /mcp/initiate_call endpoint."""
    
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_sse_transport.return_value.__aenter__.return_value = (mock_reader, mock_writer)

    mock_client_session_instance = AsyncMock()
    mock_client_session_instance.initialize = AsyncMock()
    expected_tool_result = {"status": "Call initiated by MCP", "call_sid": "CS_MCP_123"}
    mock_client_session_instance.call_tool = AsyncMock(return_value=expected_tool_result)

    mock_client_session_class = mocker.patch('backend.web.app.mcp.client.ClientSession', autospec=True)
    mock_client_session_class.return_value.__aenter__.return_value = mock_client_session_instance

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction",
        call_context={"detail": "some_context"}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_tool_result

    expected_sse_url = f"{TARGET_MCP_URL}/mcp/sse"
    expected_messages_url = f"{TARGET_MCP_URL}/mcp/messages"
    mock_sse_transport.assert_called_once_with(uri=expected_sse_url, post_uri=expected_messages_url)
    
    mock_client_session_class.assert_called_once_with(mock_reader, mock_writer, name="fastapi-mcp-client")
    mock_client_session_instance.initialize.assert_called_once_with(capabilities={})
    mock_client_session_instance.call_tool.assert_called_once_with(
        "initiate_call_mcp_tool",
        {
            "target_phone_number": payload["target_phone_number"],
            "task_instruction": payload["task_instruction"],
            "call_context": payload["call_context"]
        }
    )

@pytest.mark.asyncio
async def test_mcp_initiate_call_tool_error(mocker, app_env_fixture):
    """Test handling of ToolError from MCP client."""
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_sse_transport.return_value.__aenter__.return_value = (mock_reader, mock_writer)

    mock_client_session_instance = AsyncMock()
    mock_client_session_instance.initialize = AsyncMock()
    tool_error_msg = "Tool failed due to invalid input"
    mock_client_session_instance.call_tool = AsyncMock(side_effect=ToolError(message=tool_error_msg, code="tool.input_validation_error"))
    
    mock_client_session_class = mocker.patch('backend.web.app.mcp.client.ClientSession', autospec=True)
    mock_client_session_class.return_value.__aenter__.return_value = mock_client_session_instance

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction for tool error",
        call_context={}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)

    assert response.status_code == 400 # As per app.py logic for ToolError with this code
    assert tool_error_msg in response.json()["detail"]

@pytest.mark.asyncio
async def test_mcp_initiate_call_connection_error(mocker, app_env_fixture):
    """Test handling of connection error when connecting to MCP server via SSE."""
    # Mock sse_client_transport to raise ConnectError
    # The sse_client_transport itself is an async context manager.
    # So, its __aenter__ can raise the error, or the call to it if it's not a direct context manager.
    # Based on its usage `async with sse_client_transport(...)`, its __aenter__ is what we target.
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    connect_error_msg = "Simulated connection refused"
    mock_sse_transport.return_value.__aenter__.side_effect = httpx.ConnectError(connect_error_msg)

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction for connection error",
        call_context={}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)
    
    assert response.status_code == 503 # Service Unavailable
    assert "Could not connect to MCP server" in response.json()["detail"]
    assert connect_error_msg in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_initiate_call_client_error_on_initialize(mocker, app_env_fixture):
    """Test handling of MCP ClientError during session initialization."""
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_sse_transport.return_value.__aenter__.return_value = (mock_reader, mock_writer)

    mock_client_session_instance = AsyncMock()
    client_error_msg = "Session initialization failed"
    mock_client_session_instance.initialize = AsyncMock(side_effect=ClientError(message=client_error_msg, code="session.initialization_failed"))
    
    mock_client_session_class = mocker.patch('backend.web.app.mcp.client.ClientSession', autospec=True)
    mock_client_session_class.return_value.__aenter__.return_value = mock_client_session_instance

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction for client error",
        call_context={}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)
    
    # Based on app.py error handling for ClientError (maps to 503 or 500)
    assert response.status_code == 503 # Or 500 if code isn't specific like connection
    assert client_error_msg in response.json()["detail"]

@pytest.mark.asyncio
async def test_mcp_initiate_call_generic_mcp_error(mocker, app_env_fixture):
    """Test handling of a generic MCPError from the client session."""
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_sse_transport.return_value.__aenter__.return_value = (mock_reader, mock_writer)

    mock_client_session_instance = AsyncMock()
    mcp_error_msg = "A generic MCP processing error occurred"
    # Simulate error during call_tool, after initialize succeeds
    mock_client_session_instance.initialize = AsyncMock() 
    mock_client_session_instance.call_tool = AsyncMock(side_effect=MCPError(message=mcp_error_msg, code="mcp.processing_error"))
    
    mock_client_session_class = mocker.patch('backend.web.app.mcp.client.ClientSession', autospec=True)
    mock_client_session_class.return_value.__aenter__.return_value = mock_client_session_instance

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction for generic MCP error",
        call_context={}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)
    
    assert response.status_code == 500 # As per app.py logic for generic MCPError
    assert mcp_error_msg in response.json()["detail"]

@pytest.mark.asyncio
async def test_mcp_initiate_call_unexpected_tool_result_type(mocker, app_env_fixture):
    """Test handling when MCP tool returns an unexpected data type."""
    mock_sse_transport = mocker.patch('backend.web.app.sse_client_transport', autospec=True)
    mock_reader, mock_writer = AsyncMock(), AsyncMock()
    mock_sse_transport.return_value.__aenter__.return_value = (mock_reader, mock_writer)

    mock_client_session_instance = AsyncMock()
    mock_client_session_instance.initialize = AsyncMock()
    # Simulate tool returning a string instead of a dict
    mock_client_session_instance.call_tool = AsyncMock(return_value="this is not a dict")
    
    mock_client_session_class = mocker.patch('backend.web.app.mcp.client.ClientSession', autospec=True)
    mock_client_session_class.return_value.__aenter__.return_value = mock_client_session_instance

    payload = app_env_fixture.CallInitiationRequest(
        target_phone_number="+15551234567",
        task_instruction="Test instruction for unexpected result",
        call_context={}
    ).model_dump()

    async with AsyncClient(app=app_env_fixture.app, base_url="http://testserver") as ac:
        response = await ac.post("/mcp/initiate_call", json=payload)
    
    assert response.status_code == 500 
    assert "MCP tool returned unexpected data type" in response.json()["detail"]

```
The previous tests for `/initiate-call-mcp` have been removed and replaced with new tests for the `/mcp/initiate_call` endpoint.
The new tests cover:
-   Successful tool call via MCP SSE client.
-   Handling of `ToolError` from the MCP client.
-   Handling of `httpx.ConnectError` when `sse_client_transport` tries to connect.
-   Handling of `ClientError` during `session.initialize`.
-   Handling of generic `MCPError`.
-   Handling of unexpected result types from `call_tool`.

The `app_env_fixture` is used to set up the test app and provide `CallInitiationRequest`.
Mocks are targeted at `backend.web.app.sse_client_transport` and `backend.web.app.mcp.client.ClientSession` as these are the modules/classes used by the application code being tested.

The `TARGET_MCP_URL` is defined and used by the fixture to set the `MCP_SERVER_URL` environment variable, which the application code then uses to construct SSE URLs. The tests also use `TARGET_MCP_URL` to verify that `sse_client_transport` is called with the correct derived URLs.

This comprehensive suite should cover the new MCP client logic in `backend/web/app.py`.I have generated the updated `tests/test_web_app.py` content.

Here's a summary of the changes implemented in the generated code:

1.  **Removed Old Tests**: Test functions related to the old `/initiate-call-mcp` endpoint (e.g., `test_initiate_call_mcp_success`, `test_initiate_call_mcp_server_error`, etc.) were removed.
2.  **Kept Relevant Tests**: The tests `test_mcp_url_default_warning` and `test_mcp_url_default_warning_check_url_and_log` were kept as they test the `MCP_SERVER_URL` environment variable handling, which is still relevant.
3.  **Added Imports**:
    *   `unittest.mock.patch`, `AsyncMock`, `MagicMock`.
    *   `mcp.common.errors.MCPError`, `ToolError`, `ClientError`.
    *   `httpx` (for `ConnectError` and `AsyncClient`).
    *   `types.SimpleNamespace`.
    *   `CallInitiationRequest` is provided by the `app_env_fixture`.
4.  **Fixture (`app_env_fixture`)**:
    *   The existing fixture (previously `fixture_reset_app_module_and_mock_env`) was kept and is named `app_env_fixture`.
    *   It correctly mocks `os.getenv` to set `MCP_SERVER_URL` to `TARGET_MCP_URL` for the application's context.
    *   It handles the reloading of `backend.web.app` and `backend.web.call_handler_models` to ensure fresh imports for each test.
    *   It yields a `SimpleNamespace` containing the `app` instance and the `CallInitiationRequest` model.
5.  **New Test Cases for `/mcp/initiate_call`**:
    *   **`test_mcp_initiate_call_success`**:
        *   Mocks `backend.web.app.sse_client_transport` to simulate a successful SSE connection setup.
        *   Mocks `backend.web.app.mcp.client.ClientSession` to simulate successful session initialization and a successful `call_tool` invocation.
        *   Makes a POST request to `/mcp/initiate_call` with a valid payload.
        *   Asserts a 200 status code and the expected JSON response.
        *   Verifies that `sse_client_transport`, `session.initialize`, and `session.call_tool` were called with the correct parameters.
    *   **`test_mcp_initiate_call_tool_error`**:
        *   Sets up mocks similarly, but `session.call_tool` is configured to raise a `ToolError`.
        *   Asserts that the endpoint returns the appropriate HTTP status code (400, based on `app.py`'s handling of `ToolError` with code `tool.input_validation_error`) and error detail.
    *   **`test_mcp_initiate_call_connection_error`**:
        *   Mocks `backend.web.app.sse_client_transport` (specifically its `__aenter__` method) to raise an `httpx.ConnectError`.
        *   Asserts that the endpoint returns a 503 status code and an error message indicating failure to connect to the MCP server.
    *   **`test_mcp_initiate_call_client_error_on_initialize`**:
        *   Mocks `session.initialize` to raise a `ClientError`.
        *   Asserts an appropriate HTTP status code (503, based on `app.py`'s handling) and error detail.
    *   **`test_mcp_initiate_call_generic_mcp_error`**:
        *   Mocks `session.call_tool` to raise a generic `MCPError`.
        *   Asserts a 500 status code and error detail.
    *   **`test_mcp_initiate_call_unexpected_tool_result_type`**:
        *   Mocks `session.call_tool` to return a string instead of the expected dictionary.
        *   Asserts a 500 status code and error detail indicating the type mismatch, as handled in `app.py`.

All new asynchronous test functions are marked with `@pytest.mark.asyncio`. The mocking paths correctly target where the components are used within `backend.web.app`.

The file `tests/test_web_app.py` now contains a relevant suite of tests for the updated MCP client functionality.
