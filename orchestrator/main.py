import os
from typing import List, TypedDict, Annotated
from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import re

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()

# Configuration: Get OpenAI API key (will be fetched within functions)


# --- LangGraph State Definition ---
class GraphState(TypedDict):
    """
    Represents the state of our graph for information gathering.

    Attributes:
        conversation_history: The list of messages accumulated so far.
        task_description: A brief description of the overall task (e.g., "Order a pizza").
        required_details: A list of strings representing information needed for the task.
        gathered_details: A dictionary storing the information gathered from the user.
        missing_details: A list of strings representing information still needed.
    """

    conversation_history: Annotated[List[BaseMessage], add_messages]
    task_description: str | None = None  # Optional, can be inferred or set initially
    required_details: List[str] = (
        []
    )  # Example: ["pizza_size", "toppings", "delivery_address"]
    gathered_details: dict = {}
    missing_details: List[str] = []
    task_confirmed: bool = False  # Flag to indicate user confirmed the details


# --- Helper Function for LLM Calls ---
def _get_llm():
    """Helper to initialize the LLM, ensuring API key is checked."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # This should ideally be caught before node execution, but serves as a fallback.
        raise ValueError("OpenAI API key not found in environment variables.")
    # Using a cost-effective model for orchestration logic
    return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)


# --- Helper Function for JSON Parsing ---
def _parse_llm_json_response(response: BaseMessage) -> dict | None:
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


# --- LangGraph Nodes ---


def analyze_task(state: GraphState):
    """
    Analyzes the conversation history using LLM calls to:
    1. Identify the task and required details.
    2. Extract gathered details from the latest user message.
    Updates the state accordingly.
    """
    print("--- Running Node: analyze_task ---")
    llm = _get_llm()
    history = state["conversation_history"]
    gathered_details = state.get(
        "gathered_details", {}
    ).copy()  # Use a copy to avoid modifying original during processing
    task_description = state.get("task_description")
    required_details = state.get("required_details", [])

    # LLM Call 1: Identify Task and Required Details (if not already set)
    if not task_description or not required_details:
        print("  LLM Call 1: Identifying task and required details...")
        prompt1 = f"""Analyze the following conversation history: {history}

    Based *only* on the conversation history, identify the primary task the user wants to accomplish and the essential pieces of information (required details) needed to fulfill it.
    Return your answer as a JSON object with keys "task_description" (string) and "required_details" (list of strings).
    Example: {{"task_description": "Order a pizza", "required_details": ["pizza_size", "toppings", "delivery_address"]}}
    If no clear task is identifiable, return {{"task_description": null, "required_details": []}}.

    JSON Response:"""
    try:
        response1 = llm.invoke(prompt1)
        parsed_response1 = _parse_llm_json_response(response1)
        if parsed_response1:
            task_description = (
                parsed_response1.get("task_description") or task_description
            )  # Keep existing if LLM returns null
            required_details = (
                parsed_response1.get("required_details") or required_details
            )  # Keep existing if LLM returns null
            print(
                f"  LLM Call 1 Result: Task='{task_description}', Required={required_details}"
            )
        else:
            print(
                "  LLM Call 1: Failed to parse JSON response for task identification."
            )
            # Decide how to handle failure - maybe keep existing state or raise error? For now, keep existing.
    except Exception as e:
        print(f"  LLM Call 1 Error: {e}")
        # Handle error appropriately, maybe keep existing state

    # LLM Call 2: Extract Details from Latest User Message
    if history and isinstance(history[-1], HumanMessage) and required_details:
        print("  LLM Call 2: Extracting details from the latest message...")
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
        parsed_response2 = _parse_llm_json_response(response2)
        if parsed_response2:
            print(f"  LLM Call 2 Result (Newly Gathered): {parsed_response2}")
            # Update gathered_details safely, only adding keys that are in required_details
            for key, value in parsed_response2.items():
                if key in required_details:
                    gathered_details[key] = value
                else:
                    print(
                        f"  Warning: LLM returned unexpected detail '{key}', ignoring."
                    )
        else:
            print(
                "  LLM Call 2: Failed to parse JSON response for detail extraction."
            )
    except Exception as e:
        print(f"  LLM Call 2 Error: {e}")
        # Handle error appropriately

    # Recalculate missing details based on potentially updated gathered_details
    missing_details = [
        detail for detail in required_details if detail not in gathered_details
    ]

    print(f"  Task Desc: {task_description}")
    print(f"  Required : {required_details}")
    print(f"  Gathered : {gathered_details}")
    print(f"  Missing  : {missing_details}")

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
                print("  Task confirmed by user.")

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
    print("--- Running Node: ask_for_details ---")
    missing = state.get("missing_details", [])
    if not missing:
        # Should not happen if routing is correct, but handle defensively
        ai_message = AIMessage(content="It seems I have all the details needed!")
        print("  No missing details found (unexpected).")
    else:
        llm = _get_llm()
        next_detail_needed = missing[0]
        task_desc = state.get("task_description", "the current task")
        gathered = state.get("gathered_details", {})
        history = state.get("conversation_history", [])

        print(f"  LLM Call: Generating question for '{next_detail_needed}'...")
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
            print(f"  LLM Generated Question: {question}")
        except Exception as e:
            print(f"  LLM Call Error generating question: {e}")
            # Fallback question
            question = f"Okay, I still need the {next_detail_needed.replace('_', ' ')}. Can you provide that?"
            ai_message = AIMessage(content=question)
            print(f"  Using Fallback Question: {question}")

    # Add the AI's question to the history
    return {"conversation_history": [ai_message]}


def confirm_task(state: GraphState):
    """
    Generates a confirmation message summarizing the gathered details using an LLM.
    """
    print("--- Running Node: confirm_task ---")
    gathered = state.get("gathered_details", {})
    task_desc = state.get("task_description", "your request")
    history = state.get("conversation_history", [])

    if not gathered:
        # Should not happen if routing leads here, but handle defensively
        confirmation_message = "It seems I don't have any details to confirm yet. Could you please describe what you need?"
        print("  No details gathered to confirm (unexpected).")
    else:
        llm = _get_llm()
        print("  LLM Call: Generating confirmation message...")
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
            print(f"  LLM Generated Confirmation: {confirmation_message}")
        except Exception as e:
            print(f"  LLM Call Error generating confirmation: {e}")
            # Fallback confirmation
            summary_parts = [
                f"{key.replace('_', ' ')}: {value}" for key, value in gathered.items()
            ]
            summary = ", ".join(summary_parts)
            confirmation_message = (
                f"Okay, just to confirm {task_desc}: {summary}. Is that correct?"
            )
            print(f"  Using Fallback Confirmation: {confirmation_message}")

    ai_message = AIMessage(content=confirmation_message)

    # Add the AI's confirmation message to the history
    return {"conversation_history": [ai_message]}


def task_complete(state: GraphState):
    """
    Placeholder node for when the task is confirmed and finished.
    Just prints a message and returns the final state.
    """
    print("--- Running Node: task_complete ---")
    print("  Task confirmed and graph finished.")
    # Add a final message to the history before ending
    final_message = AIMessage(content="Okay, task confirmed and completed!")
    # Use add_messages logic if available, otherwise append directly
    # Assuming add_messages handles history correctly if needed elsewhere,
    # but for a simple append here:
    current_history = state.get("conversation_history", [])
    updated_history = current_history + [final_message]
    return {"conversation_history": updated_history}  # Return only the updated history


# --- Conditional Routing Logic ---
def route_after_analysis(state: GraphState):
    """
    Determines the next step based on whether details are missing.
    """
    print("--- Running Router: route_after_analysis ---")
    if state.get("task_confirmed"):
        print("  Routing to: task_complete (Task Confirmed)")
        return "task_complete"  # Route to the new terminal node
    elif state.get("missing_details"):
        print("  Routing to: ask_for_details")
        return "ask_for_details"
    else:
        print("  Routing to: confirm_task")
        return "confirm_task"


# --- LangGraph Graph Definition ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("analyze_task", analyze_task)
workflow.add_node("ask_for_details", ask_for_details)
workflow.add_node("confirm_task", confirm_task)
workflow.add_node("task_complete", task_complete)  # Add the new node

# Set the entry point
workflow.set_entry_point("analyze_task")

# Add conditional edges
workflow.add_conditional_edges(
    "analyze_task",
    route_after_analysis,
    {
        "ask_for_details": "ask_for_details",
        "confirm_task": "confirm_task",
        "task_complete": "task_complete", # Add route for task_complete outcome
    },
)

# Define endpoints for the information gathering loop
# After asking a question or confirming (but not confirmed yet), the graph should wait for the next user input
workflow.add_edge("ask_for_details", END)
workflow.add_edge("confirm_task", END)
# Add the final edge from our new terminal node to the actual END
workflow.add_edge("task_complete", END)

# Compile the graph
app_graph = workflow.compile()

# --- FastAPI Application ---


# Define the request body model, including optional history
class ChatMessage(BaseModel):
    message: str
    # History format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history: List[dict] = []
    # Allow passing initial state (optional, for more complex session management later)
    # For now, we primarily rely on history and let the graph derive the rest
    initial_state: dict | None = None


# Initialize the FastAPI app
app = FastAPI()


# Root endpoint
@app.get("/")
async def read_root():
    return {"status": "running"}


# Chat endpoint using LangGraph
@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """
    Handles chat requests using the information-gathering LangGraph workflow.
    """
    print(
        f"DEBUG: Received chat_message object: {chat_message.model_dump_json(indent=2)}"
    )  # <-- ADDED DEBUG LOG

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    # 1. Prepare conversation history for LangGraph state
    # Use history from initial_state if provided, otherwise from chat_message.history
    loaded_history = (
        chat_message.initial_state.get("conversation_history", [])
        if chat_message.initial_state
        else chat_message.history
    )
    conversation_history: List[BaseMessage] = []
    for msg in loaded_history:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        if role == "user":
            conversation_history.append(HumanMessage(content=content))
        elif role in ["assistant", "ai"]:
            conversation_history.append(AIMessage(content=content))

    # Add the new user message if it's not already the last one in history
    # (Prevents duplication if UI sends full history including the latest message)
    if (
        not conversation_history
        or conversation_history[-1].content != chat_message.message
    ):
        conversation_history.append(HumanMessage(content=chat_message.message))

    # 2. Define the input for the graph
    # Initialize state, prioritizing values from initial_state if provided
    initial_graph_state = {
        "conversation_history": conversation_history,
        "task_description": (
            chat_message.initial_state.get("task_description")
            if chat_message.initial_state
            else None
        ),
        "required_details": (
            chat_message.initial_state.get("required_details", [])
            if chat_message.initial_state
            else []
        ),
        "gathered_details": (
            chat_message.initial_state.get("gathered_details", {})
            if chat_message.initial_state
            else {}
        ),
        "missing_details": (
            chat_message.initial_state.get("missing_details", [])
            if chat_message.initial_state
            else []
        ),
    }
    # Ensure required_details are populated if empty (for first turn)
    if (
        not initial_graph_state["required_details"]
        and not initial_graph_state["task_description"]
    ):
        # Let analyze_task handle default initialization if state is completely empty
        pass

    print(f"\n--- Invoking Graph ---")
    print(
        f"Initial State (Partial): {{'conversation_history': [msg.type for msg in conversation_history], 'gathered_details': {initial_graph_state.get('gathered_details')}}}"
    )
    # print(f"DEBUG: Full initial_graph_state before invoke: {initial_graph_state}") # Keep for debugging if needed

    # 3. Invoke the LangGraph graph
    try:
        final_state = app_graph.invoke(initial_graph_state)
    except ValueError as e:  # Catch API key error from _get_llm helper
        print(f"Graph Invocation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Unexpected Graph Invocation Error: {e}")
        raise HTTPException(
            status_code=500, detail="An internal error occurred during graph execution."
        )

    print(
        f"Final State (Partial): { {k: v for k, v in final_state.items() if k != 'conversation_history'} }"
    )
    print(f"--- Graph Invocation Complete ---\n")

    # 4. Prepare serializable history from the final state
    serializable_history = []
    if final_state and final_state.get("conversation_history"):
        for msg in final_state["conversation_history"]:
            if isinstance(msg, HumanMessage):
                serializable_history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serializable_history.append(
                    {"role": "assistant", "content": msg.content}
                )

    # 5. Determine the response content
    response_content = "Error: Could not determine response."  # Default error
    if final_state:
        if final_state.get("task_confirmed"):
            # Task was confirmed and graph ended via task_complete node
            response_content = "Okay, task confirmed and completed!"  # Or potentially trigger next step
            # Add a final confirmation message to the history for display
            if (
                not serializable_history
                or serializable_history[-1].get("content") != response_content
            ):
                serializable_history.append(
                    {"role": "assistant", "content": response_content}
                )
        elif final_state.get("conversation_history"):
            # Graph ended via ask_for_details or confirm_task, extract last AI message
            # Check if the last message is indeed an AIMessage before accessing content
            last_message = final_state["conversation_history"][-1]
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            else:
                # This case might happen if the graph ends unexpectedly after a user message
                print(
                    f"Warning: Graph ended, but last message was not from AI. History: {serializable_history}"
                )
                # Decide on appropriate response, maybe echo confirmation or an error
                response_content = "Processing complete."  # Generic completion message
        else:
            # This case should ideally not happen if the graph runs
            print(
                f"Error: Final state lacks conversation history. Final state: {final_state}"
            )

    # 6. Return the response AND the updated state
    return {
        "response": response_content,
        "state": {
            "conversation_history": serializable_history,
            "task_description": final_state.get("task_description"),
            "required_details": final_state.get("required_details", []),
            "gathered_details": final_state.get("gathered_details", {}),
            "missing_details": final_state.get("missing_details", []),
            "task_confirmed": final_state.get("task_confirmed", False),
        },
    }


# Main execution block to run the server
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
