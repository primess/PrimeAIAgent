import os
import logging # Added
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__) # Added

# Assuming api_models will be in backend.web
# We need ChatMessage for type hinting, but avoid circular dependency for now
# from backend.web.api_models import ChatMessage # Use forward reference if needed or Any

# Internal imports
from .graph import app_graph
from .state import GraphState # For type hinting if needed, though state is dict

class WorkflowManager:
    """
    Manages the execution of the information-gathering LangGraph workflow.
    """
    def __init__(self):
        """Initializes the WorkflowManager, loading the compiled graph."""
        self.app_graph = app_graph
        # Potentially load other resources or configurations if needed

    def process_chat(self, chat_message: Any) -> Dict[str, Any]:
        """
        Processes a chat message using the LangGraph workflow.

        Args:
            chat_message: An object containing the user's message and conversation history
                          (expected structure similar to the original ChatMessage model).

        Returns:
            A dictionary containing the AI's response and the final workflow state.
        """
        logger.info("--- WorkflowManager: Processing Chat ---") # Changed
        # logger.debug(f"Received chat_message object: {chat_message}") # Changed print to logger.debug

        # --- Prepare Graph Input ---

        # 1. Prepare conversation history for LangGraph state
        loaded_history = []
        initial_state_data = getattr(chat_message, 'initial_state', None) or {}
        history_from_message = getattr(chat_message, 'history', [])

        # Prioritize history from initial_state if provided
        if initial_state_data.get("conversation_history"):
             loaded_history = initial_state_data["conversation_history"]
        elif history_from_message:
             loaded_history = history_from_message

        conversation_history: List[BaseMessage] = []
        for msg in loaded_history:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            if role == "user":
                conversation_history.append(HumanMessage(content=content))
            elif role in ["assistant", "ai"]:
                conversation_history.append(AIMessage(content=content))

        # Add the new user message if it's not already the last one in history
        current_message_content = getattr(chat_message, 'message', '')
        if current_message_content and (
            not conversation_history
            or not isinstance(conversation_history[-1], HumanMessage) # Ensure last isn't already the user msg
            or conversation_history[-1].content != current_message_content
        ):
            conversation_history.append(HumanMessage(content=current_message_content))

        # 2. Define the initial input state for the graph
        initial_graph_state = {
            "conversation_history": conversation_history,
            "task_description": initial_state_data.get("task_description"),
            "required_details": initial_state_data.get("required_details", []),
            "gathered_details": initial_state_data.get("gathered_details", {}),
            "missing_details": initial_state_data.get("missing_details", []),
            "task_confirmed": initial_state_data.get("task_confirmed", False), # Ensure task_confirmed is included
        }

        logger.info("--- Invoking Graph ---") # Changed
        logger.debug( # Changed
            f"Initial State (Partial): {{'conversation_history': [msg.type for msg in conversation_history], 'gathered_details': {initial_graph_state.get('gathered_details')}}}"
        )

        # --- Invoke Graph ---
        try:
            # Note: Error handling for API key should ideally happen within get_llm
            # or be caught here if get_llm raises an exception.
            final_state = self.app_graph.invoke(initial_graph_state)
        except ValueError as e: # Catch potential API key error from config.get_llm
             logger.error(f"Graph Invocation Error (ValueError): {e}") # Changed
             # Return an error structure instead of raising HTTPException
             return {
                 "response": f"Error: {str(e)}",
                 "state": initial_graph_state, # Return initial state on error
             }
        except Exception as e:
            logger.error(f"Unexpected Graph Invocation Error: {e}", exc_info=True) # Changed
            # Return an error structure
            return {
                 "response": "An internal error occurred during graph execution.",
                 "state": initial_graph_state, # Return initial state on error
             }

        logger.debug( # Changed
            f"Final State (Partial): { {k: v for k, v in final_state.items() if k != 'conversation_history'} }"
        )
        logger.info("--- Graph Invocation Complete ---") # Changed


        # --- Process Graph Output ---

        # 1. Prepare serializable history from the final state
        serializable_history = []
        final_conversation_history = final_state.get("conversation_history", [])
        if final_conversation_history:
            for msg in final_conversation_history:
                if isinstance(msg, HumanMessage):
                    serializable_history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    serializable_history.append(
                        {"role": "assistant", "content": msg.content}
                    )

        # 2. Determine the response content
        response_content = "Error: Could not determine response."  # Default error
        if final_state:
            # Check if the graph ended via task_complete node
            if final_state.get("task_confirmed"):
                 # Check the last message added by task_complete node
                 if serializable_history and serializable_history[-1]["role"] == "assistant":
                     response_content = serializable_history[-1]["content"]
                 else:
                     # Fallback if task_complete didn't add a message as expected
                     response_content = "Okay, task confirmed and completed!"
                     # Ensure this message is in the history for the client
                     if not serializable_history or serializable_history[-1].get("content") != response_content:
                          serializable_history.append({"role": "assistant", "content": response_content})

            # Check if graph ended after asking/confirming (last message is AI)
            elif final_conversation_history and isinstance(final_conversation_history[-1], AIMessage):
                response_content = final_conversation_history[-1].content
            else:
                # This case might happen if the graph ends unexpectedly or after user input without AI reply
                logger.warning( # Changed
                    f"Graph ended, but last message was not from AI or state unclear. History: {serializable_history}"
                )
                # Decide on appropriate response, maybe echo confirmation or an error
                response_content = "Processing complete." # Generic completion message

        # 3. Construct the final return dictionary
        return_state = {
            "conversation_history": serializable_history,
            "task_description": final_state.get("task_description"),
            "required_details": final_state.get("required_details", []),
            "gathered_details": final_state.get("gathered_details", {}),
            "missing_details": final_state.get("missing_details", []),
            "task_confirmed": final_state.get("task_confirmed", False),
        }

        return {
            "response": response_content,
            "state": return_state,
        }