# Task 2: Simple Chat UI

**Phase:** 1 - Basic Engine & UI Communication

**Goal:** Develop a minimal web-based user interface using Streamlit that allows a user to send messages to the Orchestration Engine and view the responses. This provides the initial user interaction point.

**Requirements:**

1.  **Framework:** Use Streamlit to build the UI.
2.  **File Structure:** Create a new Python file (e.g., `ui.py`) in the project root (`d:/Development/RooCode/Pizza Agent/`).
3.  **Input:** Provide a text input field for the user to type their messages.
4.  **Display:** Display the conversation history, showing both user messages and the corresponding responses received from the Orchestration Engine. Use appropriate Streamlit elements (e.g., `st.chat_message`, `st.write`).
5.  **Communication:**
    *   When the user submits a message via the input field:
        *   The UI must send the message content in the expected JSON format (defined in Task 1) via an HTTP POST request to the Orchestration Engine's `/chat` endpoint (running on its configured host and port, e.g., `http://localhost:8000/chat`). Use a library like `requests` for this.
    *   The UI must display the `response` field from the JSON received back from the Orchestration Engine.
6.  **Dependencies:** Ensure necessary libraries (`streamlit`, `requests`) are installed.

**Testable Outcome:**

*   The Streamlit UI application can be started successfully (e.g., `streamlit run ui.py`).
*   With the Orchestration Engine (from Task 1) running concurrently:
    *   Typing a message into the UI's input field and submitting it results in the message appearing in the UI's chat display.
    *   The placeholder response from the Orchestration Engine (e.g., "message acknowledged") also appears in the UI's chat display associated with the user's message.
    *   The Orchestration Engine's console log shows the message being received from the UI.