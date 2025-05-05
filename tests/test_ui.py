import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import json

# Add project root to sys.path to allow importing ui
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Mock streamlit functions before importing ui
# This prevents Streamlit from trying to run in a non-interactive environment
mock_st = MagicMock()
# Mock specific streamlit functions used in ui.py
mock_st.chat_message = MagicMock()
mock_st.markdown = MagicMock()
mock_st.error = MagicMock()
mock_st.session_state = MagicMock() # Will be configured in setUp
mock_st.title = MagicMock()
mock_st.chat_input = MagicMock() # Although not directly tested here, ui.py calls it

# Apply the mock to the sys.modules
sys.modules['streamlit'] = mock_st

# Now import the specific function and constants we need from the ui module
from ui import handle_input, API_URL, initialize_session_state
import ui # Keep this import for patching requests within the ui module context

class TestChatUI(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Reset mocks for each test
        mock_st.reset_mock()
        mock_st.chat_message.reset_mock()
        mock_st.markdown.reset_mock()
        mock_st.error.reset_mock()
        mock_st.session_state.reset_mock() # Reset the session_state mock itself

        # Define the initial state dictionary and store it
        self.initial_agent_state_dict = {
            "conversation_history": [],
            "task_description": None,
            "required_details": [],
            "gathered_details": {},
            "missing_details": [],
        }
        # Assign the dictionary to the mocked session_state.agent_state
        # Note: We assign the dictionary itself, not a mock, to allow direct comparison later
        mock_st.session_state.agent_state = self.initial_agent_state_dict.copy() # Use a copy to simulate real session state behavior

        # Also initialize the messages list for display consistency
        mock_st.session_state.messages = []

        # Directly assign a real list to the messages attribute of the session_state mock
        # This allows append to work directly on this list during the test.
        mock_st.session_state.messages = []


    @patch('ui.requests.post') # Patch requests.post within the ui module's namespace
    def test_handle_input_success(self, mock_post):
        """Test handle_input successfully sends message and processes response."""
        # Simulate user input FIRST
        user_input = "Hello there!"

        # Configure the mock response (now includes state and uses user_input)
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulate the backend returning the response and the updated state
        mock_response.json.return_value = {
            "response": "Hello from the assistant!",
            "state": { # Simulate the state returned by the backend
                 "conversation_history": [ # History now includes the assistant's response
                    {"role": "user", "content": user_input}, # Now user_input is defined
                    {"role": "assistant", "content": "Hello from the assistant!"}
                 ],
                 # Include other state keys if necessary for the test, otherwise keep simple
                 "task_description": None,
                 "required_details": [],
                 "gathered_details": {},
                 "missing_details": [],
            }
        }
        mock_post.return_value = mock_response

        # No need to capture state here anymore, we use the one from setUp

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages (updated based on backend state)
        # The handle_input function now updates messages based on the history in the returned state
        # So, we check the final state of messages after the call
        expected_history = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": "Hello from the assistant!"}
        ]
        # Access the messages list directly on the mock session state object
        self.assertEqual(mock_st.session_state.messages, expected_history)


        # 2. Check API call (now includes initial_state)
        # Assert the post call structure more flexibly
        mock_post.assert_called_once() # Check it was called once
        call_args, call_kwargs = mock_post.call_args

        # Check the URL argument
        self.assertEqual(call_args[0], API_URL)

        # Check the json payload in kwargs
        self.assertIn("json", call_kwargs)
        payload = call_kwargs["json"]
        self.assertEqual(payload.get("message"), user_input)
        # Assert that the initial_state passed in the payload matches the dictionary defined in setUp
        self.assertEqual(payload.get("initial_state"), self.initial_agent_state_dict)
        mock_response.raise_for_status.assert_called_once() # Keep this check

        # 3. Check Streamlit display calls (for user message only within this function's scope)
        # Verify chat_message was called with 'user'
        mock_st.chat_message.assert_any_call("user") # Check that the user message block was entered

        # Verify markdown was called with the user input
        mock_st.markdown.assert_any_call(user_input) # Check that the user message was displayed

        # Note: We don't assert assistant calls here as they happen after st.rerun() in a real app flow.

        # 4. Check no error was displayed
        mock_st.error.assert_not_called()


    @patch('ui.requests.post')
    def test_handle_input_connection_error(self, mock_post):
        """Test handle_input handles a connection error."""
        # Configure the mock to raise a RequestException
        error_msg = "Connection refused"
        mock_post.side_effect = ui.requests.exceptions.RequestException(error_msg)

        # Simulate user input
        user_input = "Test connection error"

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages
        self.assertEqual(len(mock_st.session_state.messages), 2) # User + Error Message
        self.assertEqual(mock_st.session_state.messages[0], {"role": "user", "content": user_input})
        self.assertEqual(mock_st.session_state.messages[1], {"role": "assistant", "content": f"Failed to get response: {error_msg}"})

        # 2. Check API call
        mock_post.assert_called_once_with(
            API_URL,
            json={
                "message": user_input,
                "initial_state": mock_st.session_state.agent_state # Check that state is sent
            }
        )

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with(f"Error connecting to the AI Assistant Agent engine: {error_msg}")


    @patch('ui.requests.post')
    def test_handle_input_bad_status(self, mock_post):
        """Test handle_input handles a bad HTTP status code (e.g., 500)."""
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = ui.requests.exceptions.HTTPError("Server Error")
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        # Simulate user input
        user_input = "Test server error"

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages
        self.assertEqual(len(mock_st.session_state.messages), 2) # User + Error Message
        self.assertEqual(mock_st.session_state.messages[0], {"role": "user", "content": user_input})
        self.assertEqual(mock_st.session_state.messages[1], {"role": "assistant", "content": f"Failed to get response: {http_error}"})

        # 2. Check API call
        mock_post.assert_called_once_with(
            API_URL,
            json={
                "message": user_input,
                "initial_state": mock_st.session_state.agent_state # Check that state is sent
            }
        )
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with(f"Error connecting to the AI Assistant Agent engine: {http_error}")


    @patch('ui.requests.post')
    def test_handle_input_non_json_response(self, mock_post):
        """Test handle_input handles a non-JSON response from the server."""
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "dummy doc", 0)
        mock_post.return_value = mock_response

        # Simulate user input
        user_input = "Test non-JSON response"

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages
        self.assertEqual(len(mock_st.session_state.messages), 2) # User + Error Message
        self.assertEqual(mock_st.session_state.messages[0], {"role": "user", "content": user_input})
        self.assertEqual(mock_st.session_state.messages[1], {"role": "assistant", "content": "Error: Received non-JSON response from server."})

        # 2. Check API call
        mock_post.assert_called_once_with(
            API_URL,
            json={
                "message": user_input,
                "initial_state": mock_st.session_state.agent_state # Check that state is sent
            }
        )
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with("Error: Could not decode JSON response from the server.")


    @patch('ui.requests.post')
    def test_handle_input_missing_response_key(self, mock_post):
        """Test handle_input handles a JSON response missing the 'response' key."""
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_key": "some data"} # Missing 'response'
        mock_post.return_value = mock_response

        # Simulate user input
        user_input = "Test missing key"

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages
        self.assertEqual(len(mock_st.session_state.messages), 2) # User + Error Message
        self.assertEqual(mock_st.session_state.messages[0], {"role": "user", "content": user_input})
        self.assertEqual(mock_st.session_state.messages[1], {"role": "assistant", "content": "Error: Invalid response format from server."})

        # 2. Check API call
        mock_post.assert_called_once_with(
            API_URL,
            json={
                "message": user_input,
                "initial_state": mock_st.session_state.agent_state # Check that state is sent
            }
        )
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        # Assert the correct error message, which now checks for 'state' too
        mock_st.error.assert_called_once_with("Error: 'response' or 'state' key not found in API response.")


if __name__ == '__main__':
    # Ensure the mocks are in place before running tests
    unittest.main()