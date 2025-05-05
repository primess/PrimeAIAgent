import json
import re
from langchain_core.messages import BaseMessage

# --- Helper Function for JSON Parsing ---
def parse_llm_json_response(response: BaseMessage) -> dict | None:
    """
    Parses a JSON object from an LLM response string.
    Handles potential markdown code blocks and JSON decoding errors.
    """
    content = response.content
    try:
        # Check if response is wrapped in markdown code block
        match = re.search(
            r"```(json)?\s*(\{.*?\})\s*```", content, re.DOTALL | re.IGNORECASE
        )
        if match:
            json_str = match.group(2)
        else:
            # Assume the content is the JSON string itself
            json_str = content

        # Clean potential leading/trailing whitespace or quotes sometimes added by LLMs
        json_str = json_str.strip().strip('"')

        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from LLM response. Error: {e}")
        print(f"  LLM Response Content: {content}")
        return None
    except Exception as e:  # Catch other potential errors
        print(f"Error: Unexpected error during JSON parsing. Error: {e}")
        print(f"  LLM Response Content: {content}")
        return None