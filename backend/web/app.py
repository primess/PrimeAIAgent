import os
import uvicorn
import logging
import httpx  # Still here, might be used by MCP client or other parts
from fastapi import FastAPI, HTTPException, Request
from backend.web.call_handler_models import CallInitiationRequest

# MCP Client Imports
import mcp.client
from mcp.client.transports.sse import sse_client_transport
from mcp.common.errors import MCPError, ToolError, ClientError # Added more specific MCP errors

# Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("app.log"), # Log to a file
#         logging.StreamHandler() # Also log to console
#     ]
# ) # Removed
logger = logging.getLogger(__name__) # Added

# Import the request model and the workflow manager
from .api_models import ChatMessage
# Adjust the import path based on how Python resolves modules from the root
# Assuming the project root is in PYTHONPATH or running with `python -m backend.web.app`
try:
    from backend.agent.workflow_manager import WorkflowManager
except ImportError:
    # Fallback for running script directly within backend/web (less ideal)
    import sys
    # Go up two levels to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend.agent.workflow_manager import WorkflowManager


# Initialize the FastAPI app
app = FastAPI()

# Instantiate the Workflow Manager
# This assumes WorkflowManager() handles its own setup (like loading the graph)
try:
    manager = WorkflowManager()
except Exception as e:
    logger.fatal(f"Failed to initialize WorkflowManager: {e}") # Changed
    # Decide if the app should exit or run in a degraded state
    # For now, let it potentially fail later if manager is None
    manager = None # Or raise the exception

# Configuration for MCP Server
DEFAULT_MCP_SERVER_URL = "http://localhost:5002"
MCP_SERVER_BASE_URL = os.getenv("MCP_SERVER_URL", DEFAULT_MCP_SERVER_URL)

if MCP_SERVER_BASE_URL == DEFAULT_MCP_SERVER_URL:
    logger.warning(f"MCP_SERVER_URL not set, using default: {DEFAULT_MCP_SERVER_URL}") # Added warning

# Root endpoint
@app.get("/")
async def read_root():
    return {"status": "running"}


# Chat endpoint using LangGraph via WorkflowManager
@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """
    Handles chat requests by delegating to the WorkflowManager.
    """
    if manager is None:
        raise HTTPException(status_code=500, detail="WorkflowManager failed to initialize.")

    # Basic check for OpenAI API Key before calling manager (optional, manager might handle it)
    # api_key = os.getenv("OPENAI_API_KEY")
    # if not api_key:
    #     raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    try:
        # Delegate processing to the manager
        result = await manager.process_chat(chat_message)

        # Check if the manager returned an error response
        if result.get("response", "").startswith("Error:"):
            # Determine appropriate status code based on error if possible
            status_code = 500 # Default internal server error
            if "API key" in result["response"]:
                status_code = 500 # Or 401/403 if auth-related
            raise HTTPException(status_code=status_code, detail=result["response"])

        return result

    except HTTPException as http_exc:
        # Re-raise HTTPException if already raised (e.g., by manager if it handled HTTP errors)
        raise http_exc
    except Exception as e:
        # Catch unexpected errors during the process_chat call
        logger.error(f"Error during chat processing: {e}", exc_info=True) # Changed
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

# --- MCP Client Service Logic ---
async def call_initiation_tool_on_mcp_server(params: CallInitiationRequest) -> dict:
    """
    Connects to the MCP server via SSE, initializes a session, and calls the
    'initiate_call_mcp_tool' with the provided parameters.
    """
    # Ensure MCP_SERVER_BASE_URL does not have a trailing slash for clean URL construction
    base_url = MCP_SERVER_BASE_URL.rstrip('/')
    mcp_sse_url = f"{base_url}/mcp/sse"
    mcp_messages_post_url = f"{base_url}/mcp/messages" # Required for sse_client_transport

    logger.info(f"Attempting to connect to MCP server via SSE at {mcp_sse_url} (POST to {mcp_messages_post_url})")

    try:
        # httpx.AsyncClient can be passed to sse_client_transport if specific httpx configs are needed
        # For now, let sse_client_transport manage its own client.
        async with sse_client_transport(
            uri=mcp_sse_url, 
            post_uri=mcp_messages_post_url
            # client=httpx.AsyncClient() # Optionally pass a pre-configured httpx client
        ) as (reader, writer):
            async with mcp.client.ClientSession(reader, writer, name="fastapi-mcp-client") as session:
                logger.info("MCP client session created. Initializing...")
                await session.initialize(capabilities={}) # Initialize with empty capabilities for now
                logger.info("MCP session initialized. Calling 'initiate_call_mcp_tool'.")

                tool_args = {
                    "target_phone_number": params.target_phone_number,
                    "task_instruction": params.task_instruction,
                    "call_context": params.call_context
                }
                
                tool_result = await session.call_tool("initiate_call_mcp_tool", tool_args)
                logger.info(f"Successfully called 'initiate_call_mcp_tool'. Result: {tool_result}")
                
                # Assuming tool_result is already a dict as per the tool's return type hint
                if not isinstance(tool_result, dict):
                    logger.error(f"Unexpected tool result type: {type(tool_result)}. Expected dict. Result: {tool_result}")
                    raise HTTPException(status_code=500, detail="MCP tool returned unexpected data type.")
                return tool_result

    except ClientError as e: # More specific MCP client-side errors (e.g., connection, protocol)
        logger.error(f"MCP Client Error calling 'initiate_call_mcp_tool': {e.code} - {e.message}", exc_info=True)
        # You might want to map e.code to specific HTTP status codes if needed
        status_code = 503 # Service Unavailable for connection issues
        if e.code in ["protocol.error", "serialization.error"]:
            status_code = 500 
        raise HTTPException(status_code=status_code, detail=f"MCP Client error: {e.message or str(e)}")
    except ToolError as e: # Errors originating from the tool itself (e.g., validation, execution)
        logger.error(f"MCP Tool Error from 'initiate_call_mcp_tool': {e.code} - {e.message}", exc_info=True)
        # ToolError often implies a client-side mistake (bad input) or server-side tool logic issue.
        # Mapping to 400 for validation-like errors or 500 for general tool execution errors.
        status_code = 400 if e.code in ["tool.input_validation_error"] else 500
        raise HTTPException(status_code=status_code, detail=f"MCP Tool error: {e.message or str(e)}")
    except MCPError as e: # Generic MCP errors
        logger.error(f"Generic MCP Error calling 'initiate_call_mcp_tool': {e.code} - {e.message}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"MCP Server error: {e.message or str(e)}")
    except httpx.ConnectError as e: # Specific error for connection failure if httpx is used directly or by MCP
        logger.error(f"HTTPX ConnectError: Failed to connect to MCP server at {mcp_sse_url}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Service unavailable: Could not connect to MCP server. {str(e)}")
    except Exception as e: # Catch-all for other unexpected errors
        logger.error(f"Unexpected error calling 'initiate_call_mcp_tool': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while communicating with the MCP service: {str(e)}")

# New FastAPI endpoint to trigger MCP client logic
@app.post("/mcp/initiate_call", response_model=dict)
async def mcp_initiate_call_endpoint(call_params: CallInitiationRequest):
    """
    Receives call parameters and uses the MCP client to request call initiation
    from the MCP server (main.py).
    """
    logger.info(f"Received request for /mcp/initiate_call with params: {call_params.model_dump(exclude_none=True)}")
    return await call_initiation_tool_on_mcp_server(call_params)


# Main execution block to run the server
if __name__ == "__main__":
    logger.info("Starting FastAPI server for backend...") # Changed
    # Ensure manager initialized before starting server
    if manager is None:
        logger.error("Cannot start server, WorkflowManager failed to initialize.") # Changed
    else:
        # Uvicorn has its own logger, which can be configured separately if needed.
        # For now, our application logger will handle app-specific logs.
        uvicorn.run(app, host="0.0.0.0", port=8000)