# tests/test_main_connections.py

import pytest
import os
import websockets
import asyncio
from dotenv import load_dotenv

# Load environment variables once at the module level.
# override=True ensures that if .env is updated, subsequent loads (if any) or this load
# will use the fresh values from the .env file, not potentially cached ones by os.environ.
load_dotenv(override=True)

def _is_voice_ws_configured():
    """Helper function to check if voice WebSocket environment variables are set."""
    # Environment variables should be loaded by the module-level load_dotenv()
    url = os.getenv("OPENAI_WS_URL")
    api_key = os.getenv("OPENAI_API_KEY2")
    # For debugging skipif:
    # print(f"DEBUG: _is_voice_ws_configured: OPENAI_WS_URL='{url}', OPENAI_API_KEY2_is_set='{bool(api_key)}'")
    return bool(url and api_key)

@pytest.mark.skipif(
    not _is_voice_ws_configured(),
    reason="Voice WebSocket environment variables (OPENAI_WS_URL, OPENAI_API_KEY2) are not set. "
           "Please ensure they are defined in your .env file or environment."
)
@pytest.mark.asyncio
async def test_realtime_voice_websocket_connection():
    """
    Tests the real-time voice WebSocket connection to OPENAI_WS_URL.
    The test connects, and if successful, closes the connection.
    It fails if the connection cannot be established or an error occurs.
    """
    openai_ws_url = os.getenv("OPENAI_WS_URL")
    openai_api_key2 = os.getenv("OPENAI_API_KEY2")

    # These assertions are mainly for development/debugging; skipif should handle this.
    # If skipif is working, these should always pass when the test runs.
    assert openai_ws_url, "OPENAI_WS_URL not set (should have been caught by skipif)"
    assert openai_api_key2, "OPENAI_API_KEY2 not set (should have been caught by skipif)"

    print(f"\n[Test Info] Attempting to connect to voice WebSocket: {openai_ws_url}")
    # Mask API key in logs
    masked_api_key = f"{openai_api_key2[:4]}...{openai_api_key2[-4:]}" if openai_api_key2 and len(openai_api_key2) > 8 else "API_KEY_SHORT_OR_NOT_SET"
    print(f"[Test Info] Using API Key (masked): {masked_api_key}")

    headers = {"api-key": openai_api_key2}
    open_timeout = 10  # seconds

    try:
        print(f"[Test Info] Connecting with headers: {{'api-key': '{masked_api_key}'}} and open_timeout: {open_timeout}s")
        async with websockets.connect(
            openai_ws_url,
            extra_headers=headers,
            open_timeout=open_timeout
        ) as ws:
            print(f"[Test Success] Successfully connected to {openai_ws_url}. Connection object: {ws}")
            # The primary goal is to establish the connection.
            # Now, attempt to close it gracefully.
            try:
                await ws.close(code=1000, reason="Test complete")
                print(f"[Test Info] Connection to {openai_ws_url} closed gracefully.")
            except websockets.exceptions.ConnectionClosedError as cce:
                # This can happen if the server closes the connection immediately after handshake
                # or if the close handshake doesn't complete as expected.
                print(f"[Test Warning] WebSocket ConnectionClosedError during ws.close() for {openai_ws_url}: {cce}. This might be acceptable.")
            except Exception as e_close:
                # Other errors during close might be more concerning.
                print(f"[Test Warning] Unexpected error during graceful close of {openai_ws_url}: {type(e_close).__name__} - {e_close}")
                # Depending on strictness, this could be a fail, but the connection was established.

    except websockets.exceptions.InvalidStatusCode as e:
        error_message = f"Failed to connect to {openai_ws_url} due to invalid status code: {e.status_code}."
        # Attempt to get more details from the response
        if hasattr(e, 'response_headers') and e.response_headers:
            auth_header = e.response_headers.get('www-authenticate', '')
            if auth_header:
                error_message += f" WWW-Authenticate: '{auth_header}'."
        # Try to decode body if present
        body_str = ""
        if hasattr(e, 'response_body') and e.response_body:
            try:
                body_str = e.response_body.decode('utf-8', errors='replace')
                error_message += f" Response body (up to 200 chars): '{body_str[:200]}'"
            except Exception:
                error_message += " Response body present but could not be decoded/read as string."
        
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)
    
    except websockets.exceptions.WebSocketException as e: # Catches other websockets specific exceptions like ConnectionClosed, ProtocolError
        error_message = f"A WebSocket specific error occurred with {openai_ws_url}: {type(e).__name__} - {e}"
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)
        
    except ConnectionRefusedError:
        error_message = f"Connection to {openai_ws_url} was refused. Ensure the server is running and accessible."
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)
        
    except asyncio.TimeoutError: # This can be raised by websockets.connect with open_timeout
        error_message = f"Connection attempt to {openai_ws_url} timed out after {open_timeout} seconds."
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)
        
    except OSError as e: # Catch network-related OSErrors like "Host not found"
        error_message = f"An OS-level network error occurred while trying to connect to {openai_ws_url}: {type(e).__name__} - {e}"
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)

    except Exception as e: # Catch-all for any other unexpected errors during the connection phase
        error_message = f"An unexpected error occurred while attempting to connect to {openai_ws_url}: {type(e).__name__} - {e}"
        print(f"[Test Failure] {error_message}")
        pytest.fail(error_message)

    # If the code reaches here without pytest.fail(), the connection was successful.
    print(f"[Test Info] Test 'test_realtime_voice_websocket_connection' for {openai_ws_url} completed successfully.")