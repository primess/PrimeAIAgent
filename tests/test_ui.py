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
        mock_st.session_state.reset_mock()

        # Directly assign a real list to the messages attribute of the session_state mock
        # This allows append to work directly on this list during the test.
        mock_st.session_state.messages = []


    @patch('ui.requests.post') # Patch requests.post within the ui module's namespace
    def test_handle_input_success(self, mock_post):
        """Test handle_input successfully sends message and processes response."""
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Hello from the assistant!"}
        mock_post.return_value = mock_response

        # Simulate user input
        user_input = "Hello there!"

        # Call the function under test
        handle_input(user_input)

        # Assertions
        # 1. Check session state for messages (accessing the list directly on the mock)
        self.assertEqual(len(mock_st.session_state.messages), 2) # User + Assistant
        self.assertEqual(mock_st.session_state.messages[0], {"role": "user", "content": user_input})
        self.assertEqual(mock_st.session_state.messages[1], {"role": "assistant", "content": "Hello from the assistant!"})

        # 2. Check API call
        mock_post.assert_called_once_with(API_URL, json={"message": user_input})
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        # Verify chat_message was called with 'user' and 'assistant'
        chat_message_calls = [c.args[0] for c in mock_st.chat_message.call_args_list if c.args] # Extract first arg from calls
        self.assertIn("user", chat_message_calls)
        self.assertIn("assistant", chat_message_calls)
        self.assertEqual(len(chat_message_calls), 2) # Ensure it was called exactly twice with arguments

        # Verify markdown was called with the correct content in the expected order
        self.assertEqual(mock_st.markdown.call_count, 2)
        mock_st.markdown.assert_has_calls([call(user_input), call("Hello from the assistant!")], any_order=False)

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
        mock_post.assert_called_once_with(API_URL, json={"message": user_input})

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with(f"Error connecting to the Pizza Agent engine: {error_msg}")


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
        mock_post.assert_called_once_with(API_URL, json={"message": user_input})
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with(f"Error connecting to the Pizza Agent engine: {http_error}")


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
        mock_post.assert_called_once_with(API_URL, json={"message": user_input})
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
        mock_post.assert_called_once_with(API_URL, json={"message": user_input})
        mock_response.raise_for_status.assert_called_once()

        # 3. Check Streamlit display calls
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with(user_input)
        mock_st.error.assert_called_once_with("Error: 'response' key not found in API response.")


if __name__ == '__main__':
    # Ensure the mocks are in place before running tests
    unittest.main()