import logging
import httpx
import json
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Internal imports for type hints and utilities
from .state import GraphState
from .config import get_llm
from .llm_utils import parse_llm_json_response


logger = logging.getLogger(__name__) # Added

# --- LangGraph Nodes ---

def analyze_task(state: GraphState):
    """
    Analyzes the conversation history using LLM calls to:
    1. Identify the task and required details.
    2. Extract gathered details from the latest user message.
    Updates the state accordingly.
    """
    logger.info("--- Running Node: analyze_task ---") # Changed
    llm = get_llm()
    history = state["conversation_history"]
    
    # Initialize from state, ensuring copies for modification
    gathered_details = state.get("gathered_details", {}).copy()
    task_description = state.get("task_description")
    required_details = state.get("required_details", [])
    # Initialize new state fields
    current_target_phone_number = state.get("target_phone_number")

    # LLM Call 1: Identify Task and Required Details (if not already set)
    if not task_description or not required_details:
        logger.info("  LLM Call 1: Identifying task and required details...") # Changed
        prompt1 = f"""Analyze the following conversation history: {history}

    Based *only* on the conversation history, identify the primary task the user wants to accomplish and the essential pieces of information (required details) needed to fulfill it.
    Return your answer as a JSON object with keys "task_description" (string) and "required_details" (list of strings).
    Example: {{"task_description": "Order a pizza", "required_details": ["pizza_size", "toppings", "delivery_address"]}}
    If no clear task is identifiable, return {{"task_description": null, "required_details": []}}.
    If the task requires making a call, ensure one of the following keys is included in "required_details": "target_phone_number", "contact_number", or "phone_number". Use "target_phone_number" if possible.

    JSON Response:"""
        try:
            response1 = llm.invoke(prompt1)
            parsed_response1 = parse_llm_json_response(response1)
            if parsed_response1:
                task_description = parsed_response1.get("task_description") or task_description
                required_details = parsed_response1.get("required_details") or required_details
                logger.debug(f"  LLM Call 1 Result: Task='{task_description}', Required={required_details}")
            else:
                logger.warning("  LLM Call 1: Failed to parse JSON response for task identification.")
        except Exception as e:
            logger.error(f"  LLM Call 1 Error: {e}", exc_info=True)

    # Define potential keys that represent a phone number
    phone_detail_keys = ["target_phone_number", "contact_number", "phone_number", "phone"]

    # LLM Call 2: Extract Details from Latest User Message
    if history and isinstance(history[-1], HumanMessage) and required_details:
        logger.info("  LLM Call 2: Extracting details from the latest message...") # Changed
        last_user_message = history[-1].content
        details_to_look_for = [
            detail for detail in required_details if detail not in gathered_details
        ]

        if details_to_look_for:
            prompt2 = f"""Given the conversation history: {history}

    The user's task is: {task_description}
    The details required for this task are: {required_details}
    The details already gathered are: {gathered_details}
    The details still needed are: {details_to_look_for}

    Analyze *only* the latest user message: "{last_user_message}"

    Extract the values for any of the *needed* details ({details_to_look_for}) mentioned in the latest user message.
    Return *only* the newly gathered key-value pairs as a JSON object.
    Do *not* include details that were already gathered ({gathered_details}).
    If a needed detail is mentioned but the specific value is ambiguous or missing in the last message, do not include it in the JSON.
    If no new details are found in the last message, return an empty JSON object {{}}.

    Example: If needed details are ["size", "topping"] and the last message is "I want a large pizza with pepperoni", return {{"size": "large", "topping": "pepperoni"}}.
    Example: If needed details are ["address"] and the last message is "What about the address?", return {{}}.

    JSON Response:"""
            try:
                response2 = llm.invoke(prompt2)
                parsed_response2 = parse_llm_json_response(response2)
                if parsed_response2:
                    logger.debug(f"  LLM Call 2 Result (Newly Gathered): {parsed_response2}") # Changed
                    for key, value in parsed_response2.items():
                        if key in required_details:
                            gathered_details[key] = value
                            # If this key is a known phone number key, update the dedicated state field
                            if key in phone_detail_keys and value:
                                current_target_phone_number = str(value) # Ensure it's a string
                                logger.info(f"  Extracted and set target_phone_number in state: {current_target_phone_number}")
                        else:
                            logger.warning(f"  LLM returned unexpected detail '{key}', ignoring.")
                else:
                    logger.warning("  LLM Call 2: Failed to parse JSON response for detail extraction.")
            except Exception as e:
                logger.error(f"  LLM Call 2 Error: {e}", exc_info=True)

    missing_details = [
        detail for detail in required_details if detail not in gathered_details
    ]
    # If a phone number was required but not found in gathered_details,
    # but IS in current_target_phone_number, remove it from missing.
    for phone_key in phone_detail_keys:
        if phone_key in missing_details and current_target_phone_number:
            missing_details.remove(phone_key)
            # Also ensure it's in gathered_details for consistency if it wasn't added by LLM2 under that specific key
            if phone_key not in gathered_details:
                 gathered_details[phone_key] = current_target_phone_number


    logger.debug(f"  Task Desc: {task_description}") # Changed
    logger.debug(f"  Required : {required_details}") # Changed
    logger.debug(f"  Gathered : {gathered_details}") # Changed
    logger.debug(f"  Missing  : {missing_details}") # Changed
    logger.debug(f"  Target Phone (state): {current_target_phone_number}")

    # Check for confirmation
    confirmed = state.get("task_confirmed", False)
    if not confirmed and len(history) >= 2: # Only check for confirmation if not already confirmed
        last_ai_message = history[-2]
        last_user_message_obj = history[-1]
        if (
            isinstance(last_ai_message, AIMessage)
            and "Is that correct?" in last_ai_message.content
            and isinstance(last_user_message_obj, HumanMessage)
            and any(
                affirmative in last_user_message_obj.content.lower()
                for affirmative in ["yes", "correct", "yep", "sure", "ok", "confirm", "affirmative"]
            )
        ):
            confirmed = True
            logger.info("  Task confirmed by user.") # Changed

    return_state = {
        "task_description": task_description,
        "required_details": required_details,
        "gathered_details": gathered_details,
        "missing_details": missing_details,
        "task_confirmed": confirmed,
        "target_phone_number": current_target_phone_number # Pass along the updated phone number
    }
    logger.info(f"analyze_task returning: {return_state}")
    return return_state

def ask_for_details(state: GraphState):
    """
    Generates a question asking for the next missing piece of information using an LLM.
    """
    logger.info("--- Running Node: ask_for_details ---") # Changed
    missing = state.get("missing_details", [])
    if not missing:
        # Should not happen if routing is correct, but handle defensively
        ai_message = AIMessage(content="It seems I have all the details needed!")
        logger.warning("  No missing details found (unexpected).") # Changed
    else:
        llm = get_llm()
        next_detail_needed = missing[0]
        task_desc = state.get("task_description", "the current task")
        gathered = state.get("gathered_details", {})
        history = state.get("conversation_history", [])

        logger.info(f"  LLM Call: Generating question for '{next_detail_needed}'...") # Changed
        prompt = f"""Conversation History:
{history}

Task: {task_desc}
Gathered Details: {gathered}
Next Detail Needed: {next_detail_needed}

Generate a concise, natural-sounding question to ask the user for the '{next_detail_needed}'.
Keep the question focused on gathering this specific piece of information. Avoid confirming already gathered details.
Do not add any preamble like "Okay, got it.". Just ask the question directly.

Example: If the task is 'Order a pizza' and the next detail is 'delivery_address', a good question is "What is the delivery address?".

Question:"""
        try:
            response = llm.invoke(prompt)
            question = response.content.strip()
            ai_message = AIMessage(content=question)
            logger.debug(f"  LLM Generated Question: {question}") # Changed
        except Exception as e:
            logger.error(f"  LLM Call Error generating question: {e}", exc_info=True) # Changed
            # Fallback question
            question = f"Okay, I still need the {next_detail_needed.replace('_', ' ')}. Can you provide that?"
            ai_message = AIMessage(content=question)
            logger.warning(f"  Using Fallback Question: {question}") # Changed

    # Add the AI's question to the history
    return {"conversation_history": [ai_message]}

def confirm_task(state: GraphState):
    """
    Generates a confirmation message summarizing the gathered details using an LLM.
    """
    logger.info("--- Running Node: confirm_task ---") # Changed
    gathered = state.get("gathered_details", {})
    task_desc = state.get("task_description", "your request")
    history = state.get("conversation_history", [])
    
    # Get the target_phone_number from the dedicated state field
    current_target_phone_number = state.get("target_phone_number")

    logger.info(f"  confirm_task - Incoming state 'gathered_details': {gathered}")
    logger.info(f"  confirm_task - Incoming state 'task_description': {task_desc}")
    logger.info(f"  confirm_task - Incoming state 'target_phone_number' (from state): {current_target_phone_number}")

    if not gathered and not current_target_phone_number: # Check if we have anything to confirm
        confirmation_message = "It seems I don't have any details to confirm yet. Could you please describe what you need?"
        logger.warning("  No details gathered and no target phone number to confirm (unexpected).")
        constructed_final_instructions = f"Task: {task_desc} - No details gathered."
    else:
        llm = get_llm()
        # Include phone number in confirmation if present
        confirm_details = gathered.copy()
        if current_target_phone_number and "target_phone_number" not in confirm_details and "contact_number" not in confirm_details and "phone_number" not in confirm_details:
             confirm_details["phone_number_to_call"] = current_target_phone_number

        logger.info(f"  LLM Call: Generating confirmation message with details: {confirm_details}...")
        prompt = f"""Conversation History:
{history}

Task Description: {task_desc}
Details to Confirm: {confirm_details}

Generate a concise, natural-sounding confirmation message summarizing the task and all details to confirm.
End the message *exactly* with the question "Is that correct?".
Do not add any extra preamble or closing remarks.

Example: If the task is 'Order a pizza' and details are {{"size": "large", "toppings": "pepperoni", "phone_number_to_call": "+15551234567"}}, a good message is "Okay, I have you down for ordering a large pizza with pepperoni, and I'll call +15551234567. Is that correct?".

Confirmation Message:"""
        try:
            response = llm.invoke(prompt)
            confirmation_message = response.content.strip()
            if not confirmation_message.endswith("Is that correct?"):
                confirmation_message += " Is that correct?"
            logger.debug(f"  LLM Generated Confirmation: {confirmation_message}")
        except Exception as e:
            logger.error(f"  LLM Call Error generating confirmation: {e}", exc_info=True)
            summary_parts = [f"{key.replace('_', ' ')}: {value}" for key, value in confirm_details.items()]
            summary = ", ".join(summary_parts)
            confirmation_message = f"Okay, just to confirm {task_desc}: {summary}. Is that correct?"
            logger.warning(f"  Using Fallback Confirmation: {confirmation_message}")
        
        # Construct final_instructions for the call
        details_summary = "; ".join([f"{k}: {v}" for k, v in gathered.items()]) # Use original gathered_details for instruction
        constructed_final_instructions = f"Please action the following task: {task_desc}. Details are: {details_summary}."
        if current_target_phone_number:
            constructed_final_instructions += f" Target phone number is {current_target_phone_number}."


    ai_message = AIMessage(content=confirmation_message)
    
    # These will be merged into the main graph state by LangGraph
    updates_for_state = {
        "conversation_history": [ai_message], # Add to history
        "final_instructions": constructed_final_instructions,
        "target_phone_number": current_target_phone_number # Ensure this is passed explicitly
    }
    logger.info(f"  confirm_task - Returning updates for state: {updates_for_state}")
    return updates_for_state

def task_complete(state: GraphState):
    """
    Placeholder node for when the task is confirmed and finished.
    Just prints a message and returns the final state.
    """
    logger.info("--- Running Node: task_complete ---") # Changed
    logger.info("  Task confirmed and graph finished.") # Changed
    # Add a final message to the history before ending
    final_message = AIMessage(content="Okay, task confirmed and completed!")
    # Use add_messages logic if available, otherwise append directly
    # Assuming add_messages handles history correctly if needed elsewhere,
    # but for a simple append here:
    current_history = state.get("conversation_history", [])
    updated_history = current_history + [final_message]
    return {"conversation_history": updated_history}  # Return only the updated history 

async def trigger_call(state: GraphState):
    """
    Triggers a call to the Call Handler with the details extracted from the graph state.
    """
    logger.info("--- Running Node: trigger_call ---")
    # Log the entire incoming state for comprehensive debugging
    logger.debug(f"  trigger_call - Full incoming state: {dict(state)}")

    gathered_details = state.get("gathered_details", {})
    # final_instructions and target_phone_number should now be directly in the state
    # as set by the modified confirm_task node (and potentially analyze_task for phone).
    final_instructions_from_state = state.get("final_instructions")
    target_phone_number_from_state = state.get("target_phone_number")

    logger.info(f"  trigger_call - Received final_instructions from state: {final_instructions_from_state}")
    logger.info(f"  trigger_call - Received target_phone_number from state: {target_phone_number_from_state}")
    logger.info(f"  trigger_call - Received gathered_details from state: {gathered_details}")

    # Validate essential inputs
    if not target_phone_number_from_state:
        error_message = "Cannot trigger call: Target phone number is missing in state."
        logger.error(f"  {error_message}")
        return {"error": error_message, "call_sid": None}

    # Use final_instructions_from_state if available, otherwise default to a generic instruction based on gathered_details
    if not final_instructions_from_state:
        logger.warning("  final_instructions missing in state for trigger_call. Constructing a generic one.")
        if gathered_details:
            details_summary = "; ".join([f"{k}: {v}" for k, v in gathered_details.items()])
            task_desc_for_instruction = state.get("task_description", "process the request")
            api_task_instruction = f"Please {task_desc_for_instruction}. Details: {details_summary}."
        else:
            api_task_instruction = "Please process the request." # Very generic fallback
    else:
        api_task_instruction = final_instructions_from_state

    # Construct the request body
    request_body = {
        "order_details": gathered_details,
        "task_instruction": api_task_instruction,
        "target_phone_number": target_phone_number_from_state,
    }
    logger.info(f"  trigger_call - Request body for Call Handler: {request_body}")
 
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:5002/order",  # Changed port to 5002
                json=request_body,
                timeout=10.0,
            )
            response.raise_for_status()
            response_data = response.json() # Removed await, httpx.Response.json() is sync
            call_sid = response_data.get("call_sid")
            logger.info(f"  Call initiated successfully. Call SID: {call_sid}")
            return {"call_sid": call_sid, "error": None}
 
        except httpx.TimeoutException as e:
            logger.error(f"  Timeout error during API call: {e}", exc_info=True)
            return {"error": "API call timed out.", "call_sid": None}
        except httpx.HTTPStatusError as e:
            logger.error(
                f"  HTTP error during API call: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            return {"error": f"API call failed with status code: {e.response.status_code}", "call_sid": None}
        except Exception as e:
            logger.error(f"  Unexpected error during API call: {e}", exc_info=True)
            return {"error": f"Unexpected error during API call: {str(e)}", "call_sid": None}