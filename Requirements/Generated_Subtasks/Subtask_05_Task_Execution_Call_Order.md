# Subtask 5: Implement Task Execution (Call /order)

**Source PRD Requirement:** FR-4, NFR (Maintainability, Reliability)

**Goal:** Implement the logic to trigger the actual task execution by calling the existing Call-Handler service's `/order` endpoint upon user confirmation, along with corresponding automated tests that mock the external call.

**Functional Tasks:**
1.  Identify the state where the user has confirmed the task (from Subtask 4).
2.  When in the confirmed state, extract the necessary parameters (`instructions`, `phone_number`) from the context store.
3.  Use an HTTP client library (e.g., `httpx` or `requests`) to *prepare* the `GET` request to the Call-Handler service's `/order` endpoint (address configured via environment variable or constant, e.g., `CALL_HANDLER_HOST`).
4.  Include the extracted `instructions` and `phone_number` as query parameters in the request details.
5.  Execute the HTTP request.
6.  Handle the response from `/order`:
    *   If successful (e.g., 200 OK): Parse the JSON response (expecting `{"status": "Call initiated", "call_sid": "..."}`). Store the `call_sid` in the context store, associated with the task. Log the success.
    *   If unsuccessful (e.g., connection error, timeout, non-2xx status): Log the error appropriately (FR-6/FR-7). Update task status in context to indicate failure.
7.  Return an appropriate message to the user via `/chat` indicating the call was initiated (e.g., "Okay, I've initiated the call. The call ID is [call_sid].") or that initiation failed.

**Testing Tasks:**
1.  **Mock HTTP Client:** Use a mocking library (e.g., `pytest-httpx` for `httpx`, `responses` for `requests`, or `unittest.mock.patch`) to intercept outgoing HTTP calls to the configured `CALL_HANDLER_HOST`. **Ensure no actual HTTP requests leave the test environment.**
2.  **Test Successful Call:**
    *   Simulate the conversation flow up to and including user confirmation ("Confirm").
    *   Configure the mock to respond successfully (e.g., status 200, JSON body `{"status": "Call initiated", "call_sid": "TEST_SID_123"}`) when the specific `/order` URL with correct query parameters is requested via GET.
    *   Assert that the HTTP call was made exactly once with the correct URL, method (GET), and query parameters.
    *   Assert that the `call_sid` ("TEST_SID_123") is stored correctly in the context.
    *   Assert the `/chat` response indicates successful initiation and includes the `call_sid`.
3.  **Test Failed Call (e.g., 500 Error):**
    *   Simulate the flow up to confirmation.
    *   Configure the mock to respond with an error (e.g., status 500) to the `/order` request.
    *   Assert that the HTTP call was attempted.
    *   Assert that the error is logged correctly.
    *   Assert that the task status in context reflects the failure.
    *   Assert the `/chat` response indicates failure.
4.  **Test Connection Error:** (If using `httpx`, `pytest-httpx` can simulate this; `unittest.mock` can raise exceptions).
    *   Simulate the flow up to confirmation.
    *   Configure the mock to raise a connection error when the call is attempted.
    *   Assert error logging and failure status/response similar to the 500 error test.

**Acceptance Criteria:**
*   Upon user confirmation via `/chat`, the Orchestrator attempts to send a correctly formatted `GET` request to the configured Call-Handler `/order` endpoint.
*   The `call_sid` from a successful (mocked) `/order` response is stored in the context.
*   Failures during the (mocked) HTTP request (non-200 status, connection errors) are handled gracefully, logged, and reflected in the task status/user response.
*   Appropriate logs are generated for the request attempt and its outcome.
*   All automated tests for this subtask, including HTTP mocking, pass successfully.
*   **Crucially: No actual HTTP requests are made to the Call-Handler during test execution.**