import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, AzureChatOpenAI

# Load environment variables from .env file
load_dotenv(override=True)

def get_llm():
    """
    Helper to initialize the LLM.
    Supports OpenAI direct, Azure OpenAI, and other OpenAI-compatible APIs.
    Configuration is driven by environment variables:
    - CHAT_MODEL_API_KEY: The API key.
    - CHAT_MODEL_URL: The base URL of the LLM API (Azure endpoint for Azure).
    - CHAT_MODEL_NAME: The model name (e.g., "gpt-4o-mini") or Azure deployment name.
    - CHAT_MODEL_API_VERSION (optional): For Azure, e.g., "2024-02-15-preview".
    - CHAT_MODEL_TEMPERATURE (optional): Defaults to 0.0.
    """
    api_key_env = os.getenv("CHAT_MODEL_API_KEY")
    model_url_env = os.getenv("CHAT_MODEL_URL") # This is the azure_endpoint for Azure
    model_name_env = os.getenv("CHAT_MODEL_NAME") # This is the azure_deployment for Azure
    api_version_env = os.getenv("CHAT_MODEL_API_VERSION")  # Can be None
    
    try:
        temperature_env = float(os.getenv("CHAT_MODEL_TEMPERATURE", "0.0"))
    except ValueError:
        raise ValueError("CHAT_MODEL_TEMPERATURE must be a valid float if set.")

    if not all([api_key_env, model_url_env, model_name_env]):
        missing_vars = []
        if not api_key_env: missing_vars.append("CHAT_MODEL_API_KEY")
        if not model_url_env: missing_vars.append("CHAT_MODEL_URL")
        if not model_name_env: missing_vars.append("CHAT_MODEL_NAME")
        raise ValueError(f"Required chat model environment variable(s) not found: {', '.join(missing_vars)}")

    if "azure.com" in model_url_env.lower():
        # Azure OpenAI
        # Azure OpenAI: Pass parameters directly to ChatOpenAI
        chat_openai_params = {
            "model": model_name_env,
            "azure_endpoint": model_url_env,
            "api_key": api_key_env,
            "azure_deployment": model_name_env,
            # "temperature": temperature_env, # Keep commented as per original
        }
        if api_version_env:
            chat_openai_params["openai_api_version"] = api_version_env
        
        return AzureChatOpenAI(**chat_openai_params)
    else:
        # Standard OpenAI or compatible
        return ChatOpenAI(
            model=model_name_env,
            api_key=api_key_env,
            base_url=model_url_env,
            # temperature=temperature_env
        )