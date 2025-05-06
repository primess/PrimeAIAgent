import logging # Added
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
    gathered_details = state.get(
        "gathered_details", {}
    ).copy()  # Use a copy to avoid modifying original during processing
    task_description = state.get("task_description")
    required_details = state.get("required_details", [])

    # LLM Call 1: Identify Task and Required Details (if not already set)
    if not task_description or not required_details:
        logger.info("  LLM Call 1: Identifying task and required details...") # Changed
        prompt1 = f"""Analyze the following conversation history: {history}

    Based *only* on the conversation history, identify the primary task the user wants to accomplish and the essential pieces of information (required details) needed to fulfill it.
    Return your answer as a JSON object with keys "task_description" (string) and "required_details" (list of strings).
    Example: {{"task_description": "Order a pizza", "required_details": ["pizza_size", "toppings", "delivery_address"]}}
    If no clear task is identifiable, return {{"task_description": null, "required_details": []}}.

    JSON Response:"""
        try:
            response1 = llm.invoke(prompt1)
            parsed_response1 = parse_llm_json_response(response1)
            if parsed_response1:
                task_description = (
                    parsed_response1.get("task_description") or task_description
                )  # Keep existing if LLM returns null
                required_details = (
                    parsed_response1.get("required_details") or required_details
                )  # Keep existing if LLM returns null
                logger.debug( # Changed
                    f"  LLM Call 1 Result: Task='{task_description}', Required={required_details}"
                )
            else:
                logger.warning( # Changed
                    "  LLM Call 1: Failed to parse JSON response for task identification."
                )
                # Decide how to handle failure - maybe keep existing state or raise error? For now, keep existing.
        except Exception as e:
            logger.error(f"  LLM Call 1 Error: {e}", exc_info=True) # Changed
            # Handle error appropriately, maybe keep existing state

    # LLM Call 2: Extract Details from Latest User Message
    if history and isinstance(history[-1], HumanMessage) and required_details:
        logger.info("  LLM Call 2: Extracting details from the latest message...") # Changed
        last_user_message = history[-1].content
        # Only consider details that are still missing
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
                    # Update gathered_details safely, only adding keys that are in required_details
                    for key, value in parsed_response2.items():
                        if key in required_details:
                            gathered_details[key] = value
                        else:
                            logger.warning( # Changed
                                f"  LLM returned unexpected detail '{key}', ignoring."
                            )
                else:
                    logger.warning( # Changed
                        "  LLM Call 2: Failed to parse JSON response for detail extraction."
                    )
            except Exception as e:
                logger.error(f"  LLM Call 2 Error: {e}", exc_info=True) # Changed
                # Handle error appropriately

    # Recalculate missing details based on potentially updated gathered_details
    missing_details = [
        detail for detail in required_details if detail not in gathered_details
    ]

    logger.debug(f"  Task Desc: {task_description}") # Changed
    logger.debug(f"  Required : {required_details}") # Changed
    logger.debug(f"  Gathered : {gathered_details}") # Changed
    logger.debug(f"  Missing  : {missing_details}") # Changed

    # Check for confirmation (Keep existing logic)
    confirmed = state.get("task_confirmed", False)  # Default to False
    if len(history) >= 2:
        last_ai_message = history[-2]
        last_user_message_obj = history[-1]
        # Check if the last AI message was a confirmation question
        if (
            isinstance(last_ai_message, AIMessage)
            and "Is that correct?" in last_ai_message.content
        ):
            # Check if the user's response is affirmative (simple check)
            if isinstance(last_user_message_obj, HumanMessage) and any(
                affirmative in last_user_message_obj.content.lower()
                for affirmative in [
                    "yes",
                    "correct",
                    "yep",
                    "sure",
                    "ok",
                    "confirm",
                    "affirmative",
                ]
            ):
                confirmed = True
                logger.info("  Task confirmed by user.") # Changed

    return {
        "task_description": task_description,
        "required_details": required_details,
        "gathered_details": gathered_details,
        "missing_details": missing_details,
        "task_confirmed": confirmed,
    }


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

    if not gathered:
        # Should not happen if routing leads here, but handle defensively
        confirmation_message = "It seems I don't have any details to confirm yet. Could you please describe what you need?"
        logger.warning("  No details gathered to confirm (unexpected).") # Changed
    else:
        llm = get_llm()
        logger.info("  LLM Call: Generating confirmation message...") # Changed
        prompt = f"""Conversation History:
{history}

Task Description: {task_desc}
Gathered Details: {gathered}

Generate a concise, natural-sounding confirmation message summarizing the task and all gathered details.
End the message *exactly* with the question "Is that correct?".
Do not add any extra preamble or closing remarks.

Example: If the task is 'Order a pizza' and details are {{"size": "large", "toppings": "pepperoni"}}, a good message is "Okay, I have you down for ordering a large pizza with pepperoni. Is that correct?".

Confirmation Message:"""
        try:
            response = llm.invoke(prompt)
            confirmation_message = response.content.strip()
            # Ensure it ends correctly
            if not confirmation_message.endswith("Is that correct?"):
                confirmation_message += " Is that correct?"
            logger.debug(f"  LLM Generated Confirmation: {confirmation_message}") # Changed
        except Exception as e:
            logger.error(f"  LLM Call Error generating confirmation: {e}", exc_info=True) # Changed
            # Fallback confirmation
            summary_parts = [
                f"{key.replace('_', ' ')}: {value}" for key, value in gathered.items()
            ]
            summary = ", ".join(summary_parts)
            confirmation_message = (
                f"Okay, just to confirm {task_desc}: {summary}. Is that correct?"
            )
            logger.warning(f"  Using Fallback Confirmation: {confirmation_message}") # Changed

    ai_message = AIMessage(content=confirmation_message)

    # Add the AI's confirmation message to the history
    return {"conversation_history": [ai_message]}


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