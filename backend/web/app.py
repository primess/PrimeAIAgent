import os
import uvicorn
import logging # Added
from fastapi import FastAPI, HTTPException

# Configure logging # Added
# logging.basicConfig( # Removed redundant basicConfig
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