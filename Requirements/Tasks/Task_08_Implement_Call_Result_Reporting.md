# Task 7: Implement Call Result Reporting

**Phase:** 4 - Closing the Loop

**Goal:** Establish a mechanism for the Realtime Call Handler (`Pizza Agent/main.py`) to communicate the outcome or status of the completed phone call back to the Orchestration Engine.

**Requirements:**

1.  **Reporting Mechanism Selection:** Choose and implement a method for the Call Handler to send data back to the Orchestrator. Common options include:
    *   **Orchestrator API Endpoint:** Define a new POST endpoint (e.g., `/call_result`) on the Orchestration Engine (FastAPI) specifically designed to receive call outcome data.
    *   **Twilio Status Callbacks:** Configure Twilio to send call status updates directly to an endpoint on the Orchestration Engine.
    *   **(Other methods like shared DB/queue are possible but likely more complex initially).**
    *   *Decision needed: Let's assume the **Orchestrator API Endpoint** method for now unless specified otherwise.*
2.  **Orchestrator Endpoint (`/call_result`):**
    *   Implement the chosen endpoint (e.g., `/call_result`) in `orchestrator/main.py`.
    *   Define a Pydantic model for the expected call result data (e.g., `call_sid`, `status`, `duration`, `summary/transcript snippet`, `error_message`).
    *   The endpoint logic should receive the data and update the relevant conversation/task state within the Orchestrator (details of state update handled in Task 8). For now, logging receipt is sufficient.
3.  **Call Handler Reporting Logic (`Pizza Agent/main.py`):**
    *   Modify the WebSocket handler (`handle_media_stream`) or related logic in `Pizza Agent/main.py`.
    *   Identify the point where a call is considered complete or has terminated (e.g., in `finally` blocks of `asyncio.gather`, upon receiving specific Twilio 'stop' events, or handling WebSocket closures).
    *   Gather relevant outcome information (e.g., success/failure indication, duration, potentially snippets of conversation if captured).
    *   Make an asynchronous HTTP POST request (using `httpx`) from the Call Handler to the Orchestrator's `/call_result` endpoint, sending the gathered outcome data.
    *   Handle potential errors during this reporting request.

**Testable Outcome:**

*   Initiate a call through the full UI -> Orchestrator -> Call Handler flow (Tasks 1-6).
*   Allow the call to connect and then terminate (either naturally or by hanging up).
*   Observe the Realtime Call Handler (`Pizza Agent/main.py`) logs:
    *   Verify that the call completion/termination is detected.
    *   Confirm that an HTTP POST request is logged, targeting the Orchestrator's `/call_result` endpoint with some outcome data.
*   Observe the Orchestration Engine (`orchestrator/main.py`) logs:
    *   Confirm that a request is received on the `/call_result` endpoint.
    *   Verify that the received payload contains the expected outcome data sent by the Call Handler.