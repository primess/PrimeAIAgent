# Revised Plan: Task 6 - Modify Call Handler API (`main.py`)

**Approved:** May 6, 2025

**Goal:** Update the `/order` endpoint in `main.py` to accept a structured JSON payload via POST, using Pydantic for validation. Crucially, this payload will carry structured context gathered by the orchestrator, which will be passed to the LLM agent handling the live call.

**Value Proposition:**

*   **Scalability:** Handles complex, multi-field data better than GET query parameters.
*   **Clarity & Validation:** Pydantic models enforce structure and enable automatic validation.
*   **Convention:** Aligns with best practices for sending complex/sensitive data.

**Revised Plan Steps:**

1.  **Define Pydantic Request Model (`backend/web/api_models.py`):**
    *   Create `CallInitiationRequest` model:
        ```python
        from pydantic import BaseModel, Field
        from typing import Dict, Any

        class CallInitiationRequest(BaseModel):
            target_phone_number: str = Field(..., description="The phone number to call.")
            task_instruction: str = Field(..., description="Base instruction for the LLM agent's role and goal.")
            call_context: Dict[str, Any] = Field(default_factory=dict, description="Structured details gathered by the orchestrator (e.g., from GraphState.gathered_details).")
        ```

2.  **Modify `main.py` Endpoint:**
    *   Import `CallInitiationRequest` from `backend.web.api_models`.
    *   Change decorator to `@app.post("/order", response_class=JSONResponse)`.
    *   Change function signature to `async def handle_order(request: Request, call_details: CallInitiationRequest):`.
    *   Remove old `instructions` and `phone_number` parameters.

3.  **Update `handle_order` Function Logic (`main.py`):**
    *   Access data via `call_details.target_phone_number`, `call_details.task_instruction`, `call_details.call_context`.
    *   Adapt validation logic for `call_details.target_phone_number`.
    *   **TwiML Generation:**
        *   Pass `call_details.task_instruction` as the value for `<Parameter name="instructions">`.
        *   Serialize `call_details.call_context` to a JSON string.
        *   Pass the JSON string as the value for a *new* `<Parameter name="context">`.
        ```python
        import json # Add import

        # ... inside handle_order
        context_json = json.dumps(call_details.call_context)
        stream = Stream(url=ws_url)
        stream.parameter(name="instructions", value=call_details.task_instruction)
        stream.parameter(name="context", value=context_json) # Pass serialized context
        connect.append(stream)
        # ... rest of TwiML generation
        ```
    *   **Twilio Call:** Use `call_details.target_phone_number` for the `to` parameter.
    *   Update logging statements.

4.  **Update WebSocket Handler (`/media-stream` in `main.py`):**
    *   **Receive Context:** In the `start` event handler (inside `receive_from_twilio`), extract both `instructions` and the new `context` parameter from `data['start']['customParameters']`.
    *   **Deserialize Context:** Parse the `context` JSON string back into a Python dictionary.
    *   **Construct Final Prompt:** In `send_session_update`, combine the `instructions` string with a formatted representation of the deserialized `context` dictionary to create the final, comprehensive prompt for the OpenAI API.
        ```python
        # Example within send_session_update or called from it
        def format_prompt(base_instruction: str, context_data: dict) -> str:
            prompt = base_instruction
            if context_data:
                prompt += "\n\nHere are the details gathered for this task:\n"
                for key, value in context_data.items():
                    # Simple formatting, can be enhanced
                    prompt += f"- {key.replace('_', ' ').title()}: {value}\n"
                prompt += "\nPlease proceed based on these details." # Or similar closing
            return prompt

        # When calling send_session_update:
        # instructions = data['start']['customParameters'].get('instructions', 'Default instructions')
        # context_str = data['start']['customParameters'].get('context', '{}')
        # try:
        #     context_data = json.loads(context_str)
        # except json.JSONDecodeError:
        #     context_data = {} # Handle potential errors
        # final_prompt = format_prompt(instructions, context_data)
        # await send_session_update(openai_ws, final_prompt) # Pass the combined prompt
        ```
    *   **Modify `send_session_update`:** Change the function signature to accept the final combined prompt string directly, rather than just the base instructions.

**Visual Plan (Mermaid Sequence Diagram):**

```mermaid
sequenceDiagram
    participant Client as API Client (Orchestrator)
    participant API as Call Handler API (main.py /order)
    participant Pydantic as FastAPI/Pydantic Validation
    participant TwilioAPI as Twilio REST API
    participant TwilioMedia as Twilio Media Streams
    participant WSHandler as WebSocket Handler (main.py /media-stream)
    participant OpenAI as OpenAI Realtime API

    Client->>+API: POST /order (JSON: CallInitiationRequest)
    API->>+Pydantic: Validate request body
    alt Invalid Payload
        Pydantic-->>-API: Validation Error (422)
        API-->>-Client: HTTP 422
    else Valid Payload
        Pydantic-->>-API: Validated call_details object
        API->>API: Serialize call_details.call_context to JSON string
        API->>API: Generate TwiML (<Parameter name="instructions" value=task_instruction>, <Parameter name="context" value=context_json>)
        API->>+TwilioAPI: calls.create(to=target_phone_number, twiml=...)
        TwilioAPI-->>-API: Call SID
        API->>-Client: HTTP 200 OK (JSON: {status, call_sid})

        TwilioAPI->>+TwilioMedia: Initiate Call Leg
        TwilioMedia->>+WSHandler: WebSocket Connect (/media-stream)
        WSHandler->>WSHandler: Accept Connection
        TwilioMedia->>WSHandler: Send 'start' event (with customParameters: instructions, context)
        WSHandler->>WSHandler: Extract instructions, Deserialize context JSON
        WSHandler->>WSHandler: Construct final prompt string
        WSHandler->>+OpenAI: Connect WebSocket
        OpenAI-->>-WSHandler: Connection Established
        WSHandler->>OpenAI: Send 'session.update' (with final combined prompt)

        loop Audio Streaming
            TwilioMedia->>WSHandler: Send 'media' event (audio chunk)
            WSHandler->>OpenAI: Forward audio chunk ('input_audio_buffer.append')
            OpenAI->>WSHandler: Send 'response.audio.delta' (AI audio chunk)
            WSHandler->>TwilioMedia: Forward audio chunk ('media' event)
        end

        TwilioMedia->>WSHandler: Send 'stop' event
        WSHandler->>OpenAI: Close WebSocket
        WSHandler->>WSHandler: Close Twilio WebSocket Connection
    end