import streamlit as st
import requests
import json

# Define the API endpoint for the orchestration engine
API_URL = "http://localhost:8000/chat"

def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

def display_history():
    """Displays the chat history stored in session state."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_input(prompt):
    """Handles user input, sends it to the API, and displays the response."""
    if not prompt: # Ignore empty input
        return

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare the JSON payload for the API
    payload = {"message": prompt}

    # Send message to the orchestration engine and display response
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        try:
            api_response_json = response.json()
            if "response" in api_response_json:
                assistant_response = api_response_json["response"]
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                # Display assistant response in chat message container
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
            else:
                error_msg = "Error: 'response' key not found in API response."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": "Error: Invalid response format from server."})

        except json.JSONDecodeError:
            error_msg = "Error: Could not decode JSON response from the server."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": "Error: Received non-JSON response from server."})

    except requests.exceptions.RequestException as e:
        error_message = f"Error connecting to the Pizza Agent engine: {e}"
        st.error(error_message)
        # Add error message to chat history to indicate failure
        st.session_state.messages.append({"role": "assistant", "content": f"Failed to get response: {e}"})

def main():
    """Main function to run the Streamlit app."""
    st.title("🍕 Pizza Agent Chat")

    initialize_session_state()
    display_history()

    # Accept user input using chat_input
    if prompt := st.chat_input("What would you like to order or ask?"):
        handle_input(prompt)

# Run the main function only when the script is executed directly
if __name__ == "__main__":
    main()