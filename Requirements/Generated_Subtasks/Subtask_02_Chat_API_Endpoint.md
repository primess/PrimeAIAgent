# Subtask 2: Implement /chat API Endpoint

**Source PRD Requirement:** FR-1, NFR (Maintainability)

**Goal:** Create the main conversational endpoint `/chat` for the Orchestration Engine, along with corresponding automated tests.

**Functional Tasks:**
1.  Define Pydantic models for the request body (e.g., `UserInput` containing user text, potentially a session/user ID later) and the response body (e.g., `AssistantResponse` containing the assistant's reply text and potentially structured data).
2.  Implement the `POST /chat` endpoint in the FastAPI application.
3.  The initial implementation should:
    *   Accept user text from the request body according to the `UserInput` model.
    *   Perform minimal processing (e.g., echo back the input for now, or a placeholder response like "Received: [user text]").
    *   Return a structured JSON response using the `AssistantResponse` model.
4.  Ensure the endpoint is registered with the FastAPI app and is routable.

**Testing Tasks:**
1.  **Test Valid Input:** Write a test using `TestClient` that sends a valid POST request (matching `UserInput`) to `/chat`. Assert that the status code is 200 OK and the response body matches the `AssistantResponse` model structure.
2.  **Test Response Content:** Assert that the content of the response in the valid input test is as expected (e.g., contains the echoed input or the placeholder text).
3.  **Test Invalid Input:** Write a test that sends a POST request with data that *does not* conform to the `UserInput` model. Assert that FastAPI returns an appropriate validation error (e.g., 422 Unprocessable Entity).

**Acceptance Criteria:**
*   Sending a POST request to `/chat` with valid JSON (matching `UserInput`) returns a 200 OK status.
*   The response body for a valid request is valid JSON matching the `AssistantResponse` model and contains the expected content.
*   Sending invalid data to `/chat` results in a 422 status code.
*   The endpoint integrates with the basic FastAPI app structure from Subtask 1.
*   All automated tests for this subtask pass successfully.