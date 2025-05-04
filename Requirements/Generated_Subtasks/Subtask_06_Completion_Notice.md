# Subtask 6: Implement Completion Notice

**Source PRD Requirement:** FR-5, NFR (Maintainability)

**Goal:** Notify the user via the `/chat` interface once an initiated task is considered complete (success/fail), based on a simulated or placeholder status update mechanism for MVP, along with corresponding automated tests.

**Functional Tasks:**
1.  **Define Task Status Tracking:**
    *   Add fields to the context store (or a dedicated task tracking structure) to hold the status of an initiated call (e.g., `task_id`, `call_sid`, `status: 'initiated' | 'completed_success' | 'completed_failure'`).
    *   When a call is successfully initiated (Subtask 5), store the `call_sid` and set the initial status to `'initiated'`.
2.  **Simulate Completion (MVP Approach):** Since no callback exists, implement a *temporary/placeholder* mechanism for marking a task as complete for testing and basic flow. Options:
    *   **Option A (Simple):** Immediately after successful initiation in Subtask 5, add logic to *also* update the status to `'completed_success'` (or `'completed_failure'` based on `/order` response) in the context. The completion notice will then be delivered on the *next* `/chat` call after initiation.
    *   **Option B (Slightly More Realistic Simulation):** Create a *hidden/test-only* endpoint (e.g., `POST /test/complete_task/{call_sid}`) that allows manually setting the task status in the context store to `'completed_success'` or `'completed_failure'`. This allows testing the notice delivery independently of initiation.
    *   *(Choose one approach for MVP implementation)*
3.  **Check Status and Notify:** Modify the `/chat` endpoint:
    *   At the beginning of handling a request, check if there's a task associated with the session/user marked as `'completed_success'` or `'completed_failure'`.
    *   If found, format the appropriate completion message (e.g., "Task Update: Call [call_sid] completed successfully." or "Task Update: Call [call_sid] failed.").
    *   Return this message as the response.
    *   Update the task status in context to `'notified'` or remove it to prevent sending the notice repeatedly.
    *   If no completed task is found, proceed with normal chat handling.

**Testing Tasks:**
1.  **Test Success Notification:**
    *   Simulate the state where a task has been initiated (context contains `call_sid` and status `'initiated'`).
    *   Manually update the task status in the context to `'completed_success'` (either directly in the test or via the Option B test endpoint if implemented).
    *   Send a new `/chat` request (e.g., user says "hello again").
    *   Assert that the response received is the correctly formatted success notification message, including the `call_sid`.
    *   Assert that the task status in context is updated to `'notified'` (or removed).
2.  **Test Failure Notification:**
    *   Simulate the initiated state.
    *   Manually update the task status in context to `'completed_failure'`.
    *   Send a new `/chat` request.
    *   Assert that the response received is the correctly formatted failure notification message.
    *   Assert the context status is updated appropriately.
3.  **Test No Notification:**
    *   Simulate the initiated state (`status: 'initiated'`).
    *   Send a new `/chat` request.
    *   Assert that the response is *not* a completion notification, but the normal chat response.
4.  **Test Repeated Notification Prevention:**
    *   Perform the success notification test (steps 1.1-1.4).
    *   Send *another* `/chat` request immediately after receiving the notification.
    *   Assert that the second response is *not* the completion notification again, but a normal chat response (because the status should have been updated to prevent repeats).

**Acceptance Criteria:**
*   After a task's status is marked as completed (success/failure) in the context, the *next* `/chat` interaction delivers the appropriate notification message.
*   The notification message correctly reflects success or failure and includes relevant identifiers like `call_sid`.
*   The context store is updated to prevent repeated notifications for the same completed task.
*   The chosen mechanism for simulating task completion (Option A or B) is implemented.
*   All automated tests for this subtask pass successfully.