# Task 1: Basic Orchestration Engine Setup

**Phase:** 1 - Basic Engine & UI Communication

**Goal:** Establish the foundational API server for the Orchestration Engine using FastAPI. This server will act as the central hub for managing user interactions and coordinating tasks.

**Requirements:**

1.  **Project Structure:** Create a dedicated directory named `orchestrator/` within the project root (`d:/Development/RooCode/Pizza Agent/`) to house the engine's code.
2.  **Framework:** Initialize a FastAPI application within the `orchestrator/` directory.
3.  **Root Endpoint:** Implement a GET endpoint at the root path (`/`) that returns a simple JSON response indicating the server is operational (e.g., `{"status": "running"}`).
4.  **Chat Endpoint:** Implement a POST endpoint at `/chat`.
    *   It must accept a JSON payload containing a user message (e.g., `{"message": "user's input text"}`). Define a Pydantic model for this input.
    *   Initially, this endpoint should return a placeholder JSON response confirming receipt (e.g., `{"response": "message acknowledged"}`). The actual chat logic will be added in a later task.
5.  **Server Configuration:** Configure the FastAPI application to run on a distinct port (e.g., 8000) to avoid conflicts with the Realtime Call Handler (which uses port 5002 by default).

**Testable Outcome:**

*   The Orchestration Engine server can be started successfully using `uvicorn` within the `orchestrator` directory.
*   Navigating to the root URL (e.g., `http://localhost:8000/`) in a browser or using `curl` returns the operational status JSON.
*   Sending a POST request with the correct JSON structure to the `/chat` endpoint (e.g., `http://localhost:8000/chat`) returns the placeholder acknowledgment JSON response.
*   Sending a POST request with an incorrect JSON structure to `/chat` results in a FastAPI validation error (422).