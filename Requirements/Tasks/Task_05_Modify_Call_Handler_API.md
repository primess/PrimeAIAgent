# Task 5: Modify Call Handler API (`main.py`)

**Phase:** 3 - Connecting to the Call Handler

**Goal:** Update the API endpoint of the existing Realtime Call Handler (`Pizza Agent/main.py`) to accept a structured set of parameters required for initiating the call, as determined by the Orchestration Engine.

**Requirements:**

1.  **Endpoint Signature:** Modify the `/order` POST endpoint in `Pizza Agent/main.py`.
    *   Change the function signature (`handle_order`) to accept parameters beyond just `instructions` and `phone_number`. It should accept all details gathered by the Orchestration Engine that are necessary for the call context or TwiML generation (e.g., `target_phone_number`, `final_instructions`, potentially `user_address`, `user_name`, etc., depending on typical task needs).
    *   Use Pydantic models to define the expected structure of the incoming JSON request body for clarity and validation.
2.  **Parameter Usage:** Update the logic within the `handle_order` function:
    *   Ensure the `target_phone_number` is used in the `twilio_client.calls.create` function's `to` parameter.
    *   Ensure the `final_instructions` (which now includes the base prompt + task details) are passed as the value for the `<Parameter name="instructions">` tag within the generated TwiML `Stream` element.
    *   Utilize any other received parameters as needed (e.g., potentially logging them or passing them as additional TwiML parameters if the voice agent needs direct access to specific details like an address).
3.  **Configuration:** No changes to the core configuration (API keys, etc.) are expected for this task, but ensure the server still runs correctly.

**Testable Outcome:**

*   The Realtime Call Handler (`Pizza Agent/main.py`) server can be started successfully.
*   Sending a POST request to its `/order` endpoint using `curl` or Postman with a JSON payload matching the *new* Pydantic model structure is successful (returns a 2xx status code, e.g., `{"status": "Call initiated", "call_sid": "..."}`).
*   Sending a POST request with a payload *not* matching the new structure results in a FastAPI validation error (422).
*   Reviewing the logs of the Call Handler shows that the TwiML generated includes the `final_instructions` passed in the request payload within the `<Parameter name="instructions">` tag.
*   The logs should also show that the call is being initiated to the `target_phone_number` provided in the request payload.