import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()

def get_llm():
    """Helper to initialize the LLM, ensuring API key is checked."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # This should ideally be caught before node execution, but serves as a fallback.
        raise ValueError("OpenAI API key not found in environment variables.")
    # Using a cost-effective model for orchestration logic
    return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)