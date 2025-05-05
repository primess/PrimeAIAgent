import streamlit as st
import requests
import json

# Define the API endpoint for the orchestration engine
API_URL = "http://localhost:8000/chat"

def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = [] # Stores messages for display {role: "user/assistant", content: "..."}
    if "agent_state" not in st.session_state:
        # Stores the state received from the backend (history, gathered_details, etc.)
        st.session_state.agent_state = {
            "conversation_history": [],
            "task_description": None,
            "required_details": [],
            "gathered_details": {},
            "missing_details": [],
        }

def display_history():
    """Displays the chat history stored in session state."""
    # Display messages based on the potentially updated history from agent_state
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_input(prompt):
    """Handles user input, sends it with state to the API, updates state, and displays the response."""
    if not prompt: # Ignore empty input
        return

    # Display user message immediately (optimistic update)
    # The full history will be updated based on the backend response later
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare the JSON payload for the API, including the current state
    payload = {
        "message": prompt,
        "initial_state": st.session_state.agent_state # Send the last known state
    }

    # Send message to the orchestration engine and display response
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        try:
            api_response_json = response.json()
            if "response" in api_response_json and "state" in api_response_json:
                assistant_response_content = api_response_json["response"]
                new_agent_state = api_response_json["state"]

                # Update the agent state in session state
                st.session_state.agent_state = new_agent_state

                # Update the display messages based on the history from the backend state
                st.session_state.messages = st.session_state.agent_state.get("conversation_history", [])

                # Rerun to refresh the display with the updated history
                st.rerun()

            else:
                error_msg = "Error: 'response' or 'state' key not found in API response."
                st.error(error_msg)
                # Add a simple error message to display history if state update fails
                st.session_state.messages.append({"role": "user", "content": prompt}) # Keep user msg
                st.session_state.messages.append({"role": "assistant", "content": "Error: Invalid response format from server."})


        except json.JSONDecodeError:
            error_msg = "Error: Could not decode JSON response from the server."
            st.error(error_msg)
            st.session_state.messages.append({"role": "user", "content": prompt}) # Keep user msg
            st.session_state.messages.append({"role": "assistant", "content": "Error: Received non-JSON response from server."})


    except requests.exceptions.RequestException as e:
        error_message = f"Error connecting to the AI Assistant Agent engine: {e}"
        st.error(error_message)
        st.session_state.messages.append({"role": "user", "content": prompt}) # Keep user msg
        st.session_state.messages.append({"role": "assistant", "content": f"Failed to get response: {e}"})


def main():
    """Main function to run the Streamlit app."""
    st.title("🤵 AI Assistant Agent Chat")

    initialize_session_state()
    display_history()

    # Accept user input using chat_input
    if prompt := st.chat_input("What would you like to order or ask?"):
        handle_input(prompt)

# Run the main function only when the script is executed directly
if __name__ == "__main__":
    main()