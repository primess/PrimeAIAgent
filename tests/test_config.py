import pytest
import os
from unittest.mock import patch, MagicMock

# Function to test
from backend.agent.config import get_llm

# Original classes for spec and isinstance checks
# These are the actual classes that ChatOpenAI and SdkAzureOpenAI from config.py refer to.
from langchain_openai import ChatOpenAI as OriginalChatOpenAI, AzureChatOpenAI as OriginalAzureChatOpenAI
from openai import AzureOpenAI as OriginalSdkAzureOpenAI


@patch('backend.agent.config.ChatOpenAI')
@patch('os.getenv')
def test_get_llm_openai_direct_success(mock_getenv, MockLangchainChatOpenAI):
    # 1. Configure Mocks for os.getenv
    def getenv_side_effect(key, default=None):
        env_vars = {
            "CHAT_MODEL_API_KEY": "test_api_key",
            "CHAT_MODEL_URL": "https://api.openai.com/v1",
            "CHAT_MODEL_NAME": "gpt-4o-mini",
            "CHAT_MODEL_TEMPERATURE": "0.1" # get_llm reads this, but doesn't pass to ChatOpenAI
        }
        return env_vars.get(key, default)
    mock_getenv.side_effect = getenv_side_effect

    # Configure mock for ChatOpenAI (from langchain_openai)
    mock_llm_instance = MagicMock(spec=OriginalChatOpenAI)
    mock_llm_instance.invoke.return_value = "Mocked OpenAI response"
    MockLangchainChatOpenAI.return_value = mock_llm_instance

    # 2. Call the function
    llm = get_llm()

    # 3. Assertions
    # Assert ChatOpenAI (from langchain_openai) was called with correct parameters
    MockLangchainChatOpenAI.assert_called_once_with(
        model="gpt-4o-mini",
        api_key="test_api_key",
        base_url="https://api.openai.com/v1"
        # temperature is not passed by the current get_llm implementation
    )
    assert llm is mock_llm_instance, "get_llm should return the mocked ChatOpenAI instance"
    assert isinstance(llm, OriginalChatOpenAI), "Returned object should be an instance of ChatOpenAI"

    # Assert the llm can "process" a prompt
    response = llm.invoke("Hello")
    assert response == "Mocked OpenAI response"
    mock_llm_instance.invoke.assert_called_once_with("Hello")


@patch('backend.agent.config.AzureChatOpenAI') # Patched to AzureChatOpenAI
@patch('os.getenv')
def test_get_llm_azure_openai_success(mock_getenv, MockLangchainAzureChatOpenAI): # Renamed mock
    # 1. Configure Mocks for os.getenv
    def getenv_side_effect(key, default=None):
        env_vars = {
            "CHAT_MODEL_API_KEY": "azure_test_api_key",
            "CHAT_MODEL_URL": "https://my-azure-resource.openai.azure.com",
            "CHAT_MODEL_NAME": "my-azure-deployment",
            "CHAT_MODEL_API_VERSION": "2024-02-15-preview",
            "CHAT_MODEL_TEMPERATURE": "0.2"
        }
        return env_vars.get(key, default)
    mock_getenv.side_effect = getenv_side_effect

    # Configure mock for AzureChatOpenAI
    mock_llm_instance = MagicMock(spec=OriginalAzureChatOpenAI) # Spec updated
    mock_llm_instance.invoke.return_value = "Mocked Azure response"
    MockLangchainAzureChatOpenAI.return_value = mock_llm_instance

    # 2. Call the function
    llm = get_llm()

    # 3. Assertions
    # Assert AzureChatOpenAI was called with correct parameters
    MockLangchainAzureChatOpenAI.assert_called_once_with(
        model="my-azure-deployment",
        api_key="azure_test_api_key",
        azure_endpoint="https://my-azure-resource.openai.azure.com",
        azure_deployment="my-azure-deployment",
        openai_api_version="2024-02-15-preview"
    )
    assert llm is mock_llm_instance, "get_llm should return the mocked AzureChatOpenAI instance"
    assert isinstance(llm, OriginalAzureChatOpenAI), "Returned object should be an instance of AzureChatOpenAI" # Type check updated


    # Assert the llm can "process" a prompt
    response = llm.invoke("Hello Azure")
    assert response == "Mocked Azure response"
    mock_llm_instance.invoke.assert_called_once_with("Hello Azure")


@patch('os.getenv')
def test_get_llm_missing_required_env_vars(mock_getenv):
    scenarios = [
        ({"CHAT_MODEL_URL": "some_url", "CHAT_MODEL_NAME": "some_name"}),
        ({"CHAT_MODEL_API_KEY": "some_key", "CHAT_MODEL_NAME": "some_name"}),
        ({"CHAT_MODEL_API_KEY": "some_key", "CHAT_MODEL_URL": "some_url"}),
        ({"CHAT_MODEL_NAME": "some_name"}),
        ({"CHAT_MODEL_URL": "some_url"}),
        ({"CHAT_MODEL_API_KEY": "some_key"}),
        ({}),
    ]

    for provided_vars in scenarios:
        # Configure mock_getenv for the current scenario
        def getenv_side_effect(key, default=None):
            if key == "CHAT_MODEL_TEMPERATURE": # ensure it has a default for float conversion
                return provided_vars.get(key, "0.0")
            return provided_vars.get(key, None) # Other keys return None if not in provided_vars
        
        mock_getenv.side_effect = getenv_side_effect

        with pytest.raises(ValueError) as excinfo:
            get_llm()
        
        # Determine the actual missing variables based on the logic in get_llm
        # The order in the error message is: API_KEY, URL, NAME
        actual_missing_in_message = []
        if not provided_vars.get("CHAT_MODEL_API_KEY"):
            actual_missing_in_message.append("CHAT_MODEL_API_KEY")
        if not provided_vars.get("CHAT_MODEL_URL"):
            actual_missing_in_message.append("CHAT_MODEL_URL")
        if not provided_vars.get("CHAT_MODEL_NAME"):
            actual_missing_in_message.append("CHAT_MODEL_NAME")

        expected_message = f"Required chat model environment variable(s) not found: {', '.join(actual_missing_in_message)}"
        assert str(excinfo.value) == expected_message, \
            f"Test failed for scenario: {provided_vars}. Expected: '{expected_message}', Got: '{str(excinfo.value)}'"


@patch('os.getenv')
def test_get_llm_invalid_temperature(mock_getenv):
    def getenv_side_effect(key, default=None):
        env_vars = {
            "CHAT_MODEL_API_KEY": "key",
            "CHAT_MODEL_URL": "url",
            "CHAT_MODEL_NAME": "name",
            "CHAT_MODEL_TEMPERATURE": "not-a-float"
        }
        return env_vars.get(key, default)
    mock_getenv.side_effect = getenv_side_effect

    with pytest.raises(ValueError) as excinfo:
        get_llm()
    assert str(excinfo.value) == "CHAT_MODEL_TEMPERATURE must be a valid float if set."


# Test for when temperature is not set, should default to 0.0 and not cause issues
# This also tests that the temperature_env is correctly calculated as 0.0
# and doesn't affect ChatOpenAI call if it's not passed (which it isn't in current get_llm)
@patch('backend.agent.config.ChatOpenAI')
@patch('os.getenv')
def test_get_llm_openai_direct_default_temperature_handling(mock_getenv, MockLangchainChatOpenAI):
    def getenv_side_effect(key, default=None):
        env_vars = {
            "CHAT_MODEL_API_KEY": "test_api_key",
            "CHAT_MODEL_URL": "https://api.openai.com/v1",
            "CHAT_MODEL_NAME": "gpt-4o-mini"
            # CHAT_MODEL_TEMPERATURE is not in env_vars, so os.getenv("CHAT_MODEL_TEMPERATURE", "0.0") -> "0.0"
        }
        # Simulate os.getenv behavior: if key is CHAT_MODEL_TEMPERATURE, it will use the default "0.0"
        # because it's not in env_vars.
        if key == "CHAT_MODEL_TEMPERATURE":
            return env_vars.get(key, "0.0") # This is how get_llm calls it
        return env_vars.get(key, default)

    mock_getenv.side_effect = getenv_side_effect

    mock_llm_instance = MagicMock(spec=OriginalChatOpenAI)
    MockLangchainChatOpenAI.return_value = mock_llm_instance

    # Call the function - no ValueError should be raised for temperature
    llm = get_llm() 
    assert llm is mock_llm_instance

    # Assert ChatOpenAI was called without temperature, as per get_llm's current code
    MockLangchainChatOpenAI.assert_called_once_with(
        model="gpt-4o-mini",
        api_key="test_api_key",
        base_url="https://api.openai.com/v1"
    )
    # The internal temperature_env would have been 0.0, but it's not used.
    
    # Verify getenv was called for temperature with the default
    found_temp_call = False
    for call_args_tuple in mock_getenv.call_args_list:
        args, _ = call_args_tuple # call_args_tuple can be call(arg1, arg2, ..., kwarg1=val1, ...) or (args_tuple, kwargs_dict)
        if args[0] == "CHAT_MODEL_TEMPERATURE" and len(args) > 1 and args[1] == "0.0":
            found_temp_call = True
            break
    assert found_temp_call, "os.getenv should have been called for CHAT_MODEL_TEMPERATURE with default '0.0'"

# Helper function to check OpenAI direct configuration at runtime for skipif
def _is_openai_direct_configured_for_real_call():
    from dotenv import load_dotenv
    load_dotenv(override=True)

    api_key = os.getenv("CHAT_MODEL_API_KEY")
    url = os.getenv("CHAT_MODEL_URL")
    model_name = os.getenv("CHAT_MODEL_NAME")

    return bool(
        api_key and
        url and "azure.com" not in url.lower() and # Key difference: not Azure
        model_name
    )

# Helper function to check Azure configuration at runtime for skipif
def _is_azure_configured_for_real_call():
    # Ensure dotenv is loaded if get_llm hasn't been called yet in this scope,
    # though get_llm itself calls load_dotenv.
    from dotenv import load_dotenv # Import here
    load_dotenv(override=True) # Explicitly load .env for the skipif check, overriding existing vars

    api_key = os.getenv("CHAT_MODEL_API_KEY")
    url = os.getenv("CHAT_MODEL_URL")
    model_name = os.getenv("CHAT_MODEL_NAME")
    api_version = os.getenv("CHAT_MODEL_API_VERSION")
    
    return bool(
        api_key and
        url and "azure.com" in url.lower() and
        model_name and
        api_version
    )

@pytest.mark.skipif(not _is_azure_configured_for_real_call(), reason="Azure OpenAI environment variables not fully configured for a real call test.")
def test_get_llm_azure_openai_real_call():
    """
    Tests a real call to Azure OpenAI using get_llm.
    This test requires the following environment variables to be set:
    - CHAT_MODEL_API_KEY
    - CHAT_MODEL_URL (must be an Azure endpoint)
    - CHAT_MODEL_NAME (Azure deployment name)
    - CHAT_MODEL_API_VERSION
    - CHAT_MODEL_TEMPERATURE (optional, defaults to 0.0)
    """
    # Read env vars inside the test to ensure freshness
    current_azure_url = os.getenv("CHAT_MODEL_URL")
    current_azure_model_name = os.getenv("CHAT_MODEL_NAME")
    current_azure_api_version = os.getenv("CHAT_MODEL_API_VERSION")

    print(f"Attempting real Azure call with: URL='{current_azure_url}', Model='{current_azure_model_name}', Version='{current_azure_api_version}'")
    
    llm = None
    try:
        # No mocks for os.getenv here, get_llm will use actual environment variables
        llm = get_llm()
    except ValueError as e:
        pytest.fail(f"get_llm() raised ValueError during setup for real Azure call: {e}")
    
    assert llm is not None, "get_llm() should return an LLM instance for Azure real call."
    assert isinstance(llm, OriginalAzureChatOpenAI), \
        f"LLM instance should be OriginalAzureChatOpenAI for Azure. Got {type(llm)}"

    try:
        # Attempt a simple invocation
        response = llm.invoke("This is a test prompt for Azure OpenAI.")
        assert response is not None, "Response from Azure OpenAI should not be None."
        
        # Depending on the model, response might be AIMessage or just content
        if hasattr(response, 'content'):
            assert response.content is not None and response.content.strip() != "", \
                "Response content from Azure OpenAI should not be empty."
            print(f"Received response content: {response.content[:100]}...")
        else: # Fallback for older versions or different response structures
            assert str(response).strip() != "", \
            "String representation of response from Azure OpenAI should not be empty."
            print(f"Received response (string): {str(response)[:100]}...")

    except Exception as e:
        pytest.fail(f"LLM invocation failed for real Azure call: {e}")


@pytest.mark.skipif(not _is_openai_direct_configured_for_real_call(), reason="OpenAI direct/compatible environment variables not fully configured for a real call test.")
def test_get_llm_openai_direct_real_call():
    """
    Tests a real call to an OpenAI direct or compatible endpoint using get_llm.
    This test requires the following environment variables to be set:
    - CHAT_MODEL_API_KEY
    - CHAT_MODEL_URL (must NOT be an Azure endpoint)
    - CHAT_MODEL_NAME
    - CHAT_MODEL_TEMPERATURE (optional, defaults to 0.0)
    """
    # Read env vars inside the test to ensure freshness
    current_openai_url = os.getenv("CHAT_MODEL_URL")
    current_openai_model_name = os.getenv("CHAT_MODEL_NAME")

    print(f"Attempting real OpenAI direct call with: URL='{current_openai_url}', Model='{current_openai_model_name}'")
    
    llm = None
    try:
        # No mocks for os.getenv here, get_llm will use actual environment variables
        llm = get_llm()
    except ValueError as e:
        pytest.fail(f"get_llm() raised ValueError during setup for real OpenAI direct call: {e}")
    
    assert llm is not None, "get_llm() should return an LLM instance for OpenAI direct real call."
    assert isinstance(llm, OriginalChatOpenAI), \
        f"LLM instance should be OriginalChatOpenAI for OpenAI direct. Got {type(llm)}"

    try:
        # Attempt a simple invocation
        response = llm.invoke("This is a test prompt for OpenAI direct.")
        assert response is not None, "Response from OpenAI direct should not be None."
        
        # Depending on the model, response might be AIMessage or just content
        if hasattr(response, 'content'):
            assert response.content is not None and response.content.strip() != "", \
                "Response content from OpenAI direct should not be empty."
            print(f"Received response content: {response.content[:100]}...")
        else: # Fallback for older versions or different response structures
            assert str(response).strip() != "", \
            "String representation of response from OpenAI direct should not be empty."
            print(f"Received response (string): {str(response)[:100]}...")

    except Exception as e:
        pytest.fail(f"LLM invocation failed for real OpenAI direct call: {e}")