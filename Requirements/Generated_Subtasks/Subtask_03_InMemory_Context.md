# Subtask 3: Implement In-Memory Context Management

**Source PRD Requirement:** FR-2 (Phase 0/1: In-memory), NFR (Maintainability)

**Goal:** Implement a basic in-memory storage mechanism to hold minimal user context during a session, along with corresponding automated tests.

**Functional Tasks:**
1.  Define a simple data structure (e.g., a Python dictionary or a dedicated class instance) within the Orchestration Engine's scope to act as the context store. Make it accessible for modification within request handlers.
2.  Modify the `/chat` endpoint (or create helper functions/classes) to:
    *   Retrieve context relevant to the current user/session (initially, a single global context might suffice for MVP).
    *   Store relevant information extracted from the conversation (e.g., identified entities like phone numbers, task details) into the in-memory store based on simple logic (e.g., if the user mentions a phone number, store it).
    *   Use stored context in generating responses (e.g., if a phone number is stored, acknowledge it in the next response: "Okay, I have noted the number [phone_number]").
3.  Ensure the context store resets when the application restarts (inherent nature of in-memory).

**Testing Tasks:**
1.  **Test Context Storage:** Write a test using `TestClient` that sends a `/chat` request designed to trigger context storage (e.g., "My number is 12345"). Then, either:
    *   Inspect the internal state of the context store directly (if accessible during tests).
    *   *OR* Send a subsequent `/chat` request designed to retrieve or use that context, and assert the response reflects the stored data (e.g., response contains "Okay, I have noted the number 12345").
2.  **Test Context Persistence:** Within a single test function using the same `TestClient` instance, make multiple `/chat` calls. Verify that context stored in an earlier call is available and used correctly in a later call within that same test run.
3.  **Test Context Isolation (if applicable):** If implementing per-user context later, tests should verify that context from one simulated user doesn't leak to another. (For global MVP context, this might not be applicable yet).

**Acceptance Criteria:**
*   Information can be added to the in-memory context store via `/chat` interactions.
*   Stored information can be retrieved and influences subsequent `/chat` responses within the same application run.
*   The context is implicitly cleared upon application restart.
*   No file I/O is used for context storage in this subtask.
*   All automated tests for this subtask pass successfully.