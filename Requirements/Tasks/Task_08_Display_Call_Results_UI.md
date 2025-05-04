# Task 8: Display Call Results in UI

**Phase:** 4 - Closing the Loop

**Goal:** Present the final outcome of the initiated phone call back to the user within the chat interface, completing the interaction loop.

**Requirements:**

1.  **Orchestrator State Handling:**
    *   Modify the Orchestration Engine's LangGraph state to accommodate the call result data received via the `/call_result` endpoint (Task 7). Include fields like `call_outcome_status`, `call_outcome_details`, etc.
    *   Update the `/call_result` endpoint logic in `orchestrator/main.py` to properly store the received outcome data into the correct task's state. (Requires a mechanism to correlate the incoming result to the ongoing task/conversation state).
2.  **Graph Flow Update:**
    *   Adjust the LangGraph flow in the Orchestrator. After the "trigger_call" node (Task 6), the graph should likely enter a waiting state or transition based on the expectation of receiving a result.
    *   Add a new node (e.g., "report_result").
    *   Implement logic (e.g., polling the state, or triggered by the `/call_result` endpoint) to transition the graph to the "report_result" node once the call outcome is available in the state.
3.  **Result Generation Node ("report_result"):**
    *   This node should access the call outcome information stored in the LangGraph state.
    *   It should use the LLM (or simple formatting logic) to generate a user-friendly message summarizing the outcome (e.g., success, failure, key details, error messages).
4.  **UI Update (`ui.py`):**
    *   Modify the Streamlit UI to handle the display of this final result message.
    *   The UI needs to fetch or receive this final update from the Orchestrator after the call process is complete. This might involve the UI polling the engine or the engine pushing an update if using WebSockets between UI and Engine (more advanced). Initially, displaying the result upon the *next* user interaction after the call might be sufficient for testing.

**Testable Outcome:**

*   Complete the entire end-to-end flow (Tasks 1-7).
*   Initiate a task, provide details, confirm, and let the call be triggered.
*   Wait for the call to complete and the result to be reported back to the Orchestrator.
*   Verify that the Streamlit UI updates to display a final message to the user reflecting the outcome of the phone call (e.g., "Task completed: [Summary]" or "Task failed: [Reason]").
*   The message displayed should correspond to the outcome data logged as received by the Orchestrator's `/call_result` endpoint in Task 7.