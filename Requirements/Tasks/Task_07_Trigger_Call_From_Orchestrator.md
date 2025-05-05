# Task 6: Trigger Call from Orchestrator

**Phase:** 3 - Connecting to the Call Handler

**Goal:** Enable the Orchestration Engine to initiate a phone call via the Realtime Call Handler once the user has confirmed the task and all necessary details have been gathered.

**Requirements:**

1.  **Graph Node:** Add a new node to the Orchestration Engine's LangGraph graph (e.g., "trigger_call").
2.  **Trigger Logic:** This node should be executed after the user confirms the task details (following the "confirm_task" node from Task 4).
3.  **Data Preparation:** The "trigger_call" node must extract the necessary information from the LangGraph state (`gathered_details`, `final_instructions`, `target_phone_number`, etc.).
4.  **API Call:** The node must make an asynchronous HTTP POST request to the Realtime Call Handler's updated `/order` endpoint (Task 5).
    *   Use an appropriate async HTTP client library (e.g., `httpx`).
    *   Format the request body according to the Pydantic model defined in the Call Handler (Task 5).
    *   Handle potential exceptions during the API call (e.g., connection errors, non-2xx responses from the Call Handler).
5.  **State Update (Optional):** Optionally, update the LangGraph state to indicate that the call has been initiated (e.g., adding a `call_sid` if returned by the Call Handler, setting a status flag).

**Testable Outcome:**

*   Using the UI (Task 2) connected to the Engine (Task 4):
    *   Complete the information gathering process for a task.
    *   When the agent asks for confirmation and the user confirms (e.g., types "yes"), the Orchestrator should proceed to trigger the call.
*   Observe the Orchestration Engine's logs:
    *   Confirm that the "trigger_call" node is executed.
    *   Verify that an HTTP POST request is logged, showing the correct URL for the Call Handler's `/order` endpoint and the expected JSON payload containing the gathered details.
*   Observe the Realtime Call Handler's (`Pizza Agent/main.py`) logs:
    *   Confirm that a request is received on the `/order` endpoint matching the one sent by the Orchestrator.
    *   Verify that the Call Handler proceeds to initiate the Twilio call based on the received data.
*   A phone call should actually be initiated by Twilio to the target number.