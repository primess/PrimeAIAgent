# Subtask 4: Implement Task Confirmation Logic

**Source PRD Requirement:** FR-3, NFR (Maintainability)

**Goal:** Implement the logic within the `/chat` endpoint to summarize the understood task and parameters, ask the user for explicit confirmation, and handle the response, along with corresponding automated tests.

**Functional Tasks:**
1.  Develop logic (likely within the `/chat` handler or a dedicated state machine/workflow manager) to determine when enough information has been gathered to propose a task (e.g., placing a call requires `instructions` and `phone_number` in context).
2.  Extract key parameters for the task (e.g., `instructions`, `phone_number`) from the context store (Subtask 3).
3.  Format a summary message for the user, clearly stating the intended action and its parameters (e.g., "Okay, I understand you want me to call [phone_number] with the instruction: '[instructions]'. Is this correct? Please reply with 'Confirm' or 'Cancel'.").
4.  Return this summary and confirmation request as the response from `/chat` when the system determines it's ready for confirmation.
5.  Implement logic to handle the user's subsequent `/chat` response containing "Confirm" or "Cancel".
    *   If "Confirm": Update internal state to indicate readiness for execution (Subtask 5). Return an acknowledgement (e.g., "Okay, proceeding with the call.").
    *   If "Cancel": Update internal state, clear relevant task parameters from context, and return an appropriate message (e.g., "Okay, cancelling the request. What would you like to do instead?").

**Testing Tasks:**
1.  **Test Confirmation Trigger:** Write a test using `TestClient` that simulates a conversation leading up to confirmation.
    *   Send initial messages to populate context (e.g., provide instructions, then phone number).
    *   Assert that the final message triggers the confirmation response.
    *   Assert the confirmation message content includes the correct parameters extracted from the (mocked or controlled) context.
2.  **Test "Confirm" Response:** Following the confirmation trigger test (or in a separate test simulating the "awaiting confirmation" state), send a `/chat` request with "Confirm".
    *   Assert the response acknowledges the confirmation.
    *   Assert the internal state (if inspectable) reflects readiness for execution.
3.  **Test "Cancel" Response:** Following the confirmation trigger test (or in a separate test simulating the "awaiting confirmation" state), send a `/chat` request with "Cancel".
    *   Assert the response acknowledges the cancellation.
    *   Assert the internal state reflects cancellation.
    *   Optionally, verify that task parameters were cleared from the context by sending another message and checking that confirmation isn't immediately re-triggered.

**Acceptance Criteria:**
*   When sufficient details for a task are present in the context, the `/chat` response includes an accurate summary and asks for confirmation.
*   The system correctly interprets "Confirm" and "Cancel" responses in subsequent `/chat` calls, updating its internal state and context appropriately.
*   The system does not proceed to task execution (Subtask 5 logic) without explicit confirmation.
*   All automated tests for this subtask pass successfully.