import os
from typing import List, TypedDict, Annotated
from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv

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
    task_description: str | None = None # Optional, can be inferred or set initially
    required_details: List[str] = [] # Example: ["pizza_size", "toppings", "delivery_address"]
    gathered_details: dict = {}
    missing_details: List[str] = []
    task_confirmed: bool = False # Flag to indicate user confirmed the details

# --- Helper Function for LLM Calls ---
def _get_llm():
    """Helper to initialize the LLM, ensuring API key is checked."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # This should ideally be caught before node execution, but serves as a fallback.
        raise ValueError("OpenAI API key not found in environment variables.")
    # Using a cost-effective model for orchestration logic
    return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)

# --- LangGraph Nodes ---

def analyze_task(state: GraphState):
    """
    Analyzes the latest user message to update gathered and missing details.
    (Placeholder: Uses LLM in a real scenario)
    """
    print("--- Running Node: analyze_task ---")
    # TODO: Implement LLM call to analyze state['conversation_history'][-1]
    #       and update gathered_details and missing_details based on required_details.

    # --- Placeholder Logic ---
    # For now, assume a pizza order task if not defined
    if not state.get('task_description'):
        state['task_description'] = "Order a pizza" # Example task
    if not state.get('required_details'):
        state['required_details'] = ["pizza_size", "toppings", "delivery_address", "phone_number"] # Example details

    # Simple check based on last message (very basic, LLM needed for robustness)
    last_message = state['conversation_history'][-1].content.lower()
    gathered = state.get('gathered_details', {})
    required = state.get('required_details', [])

    # Example: Check if message mentions size
    # More inclusive size check for placeholder
    if any(size in last_message for size in ["large", "medium", "small", "xl", "extra large"]):
        # In a real scenario, LLM would extract the specific size
        gathered["pizza_size"] = "mentioned" # Placeholder value
    if "pepperoni" in last_message or "mushrooms" in last_message:
        gathered["toppings"] = "mentioned" # Placeholder value
    if "address" in last_message: # Very naive check
         gathered["delivery_address"] = "mentioned"
    if "phone" in last_message or "number is" in last_message:
         gathered["phone_number"] = "mentioned"

    # Update missing details
    missing = [detail for detail in required if detail not in gathered]

    print(f"  Required: {required}")
    print(f"  Gathered: {gathered}")
    print(f"  Missing : {missing}")
    # --- End Placeholder Logic ---

    # Check for confirmation
    confirmed = state.get('task_confirmed', False) # Default to False
    if len(state['conversation_history']) >= 2:
        last_ai_message = state['conversation_history'][-2]
        last_user_message = state['conversation_history'][-1]
        # Check if the last AI message was a confirmation question
        if isinstance(last_ai_message, AIMessage) and "Is that correct?" in last_ai_message.content:
            # Check if the user's response is affirmative (simple check)
            if isinstance(last_user_message, HumanMessage) and any(affirmative in last_user_message.content.lower() for affirmative in ["yes", "correct", "yep", "sure", "ok"]):
                confirmed = True
                print("  Task confirmed by user.")

    return {
        "task_description": state['task_description'], # Persist task description
        "required_details": state['required_details'], # Persist required details
        "gathered_details": gathered,
        "missing_details": missing,
        "task_confirmed": confirmed # Return the updated confirmation status
    }

def ask_for_details(state: GraphState):
    """
    Generates a question asking for the next missing piece of information.
    (Placeholder: Uses LLM in a real scenario)
    """
    print("--- Running Node: ask_for_details ---")
    missing = state.get('missing_details', [])
    if not missing:
        # Should not happen if routing is correct, but handle defensively
        ai_message = AIMessage(content="It seems I have all the details needed!")
    else:
        # TODO: Implement LLM call to generate a natural question for missing[0]
        # --- Placeholder Logic ---
        next_detail_needed = missing[0]
        question = f"Okay, got it. What about the {next_detail_needed.replace('_', ' ')}?"
        ai_message = AIMessage(content=question)
        print(f"  Asking for: {next_detail_needed}")
        # --- End Placeholder Logic ---

    # Add the AI's question to the history
    return {"conversation_history": [ai_message]}

def confirm_task(state: GraphState):
    """
    Generates a confirmation message summarizing the gathered details.
    (Placeholder: Uses LLM in a real scenario)
    """
    print("--- Running Node: confirm_task ---")
    gathered = state.get('gathered_details', {})
    task_desc = state.get('task_description', 'your request')

    # TODO: Implement LLM call to generate a confirmation summary
    # --- Placeholder Logic ---
    summary_parts = [f"{key.replace('_', ' ')}: {value}" for key, value in gathered.items()]
    summary = ", ".join(summary_parts)
    confirmation_message = f"Great! Just to confirm {task_desc}: {summary}. Is that correct?"
    ai_message = AIMessage(content=confirmation_message)
    print(f"  Confirmation: {confirmation_message}")
    # --- End Placeholder Logic ---

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
    return {"conversation_history": updated_history} # Return only the updated history

# --- Conditional Routing Logic ---
def route_after_analysis(state: GraphState):
    """
    Determines the next step based on whether details are missing.
    """
    print("--- Running Router: route_after_analysis ---")
    if state.get('task_confirmed'):
        print("  Routing to: task_complete (Task Confirmed)")
        return "task_complete" # Route to the new terminal node
    elif state.get('missing_details'):
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
workflow.add_node("task_complete", task_complete) # Add the new node

# Set the entry point
workflow.set_entry_point("analyze_task")

# Add conditional edges
workflow.add_conditional_edges(
    "analyze_task",
    route_after_analysis,
    {
        "ask_for_details": "ask_for_details",
        "confirm_task": "confirm_task",
    }
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
    print(f"DEBUG: Received chat_message object: {chat_message.model_dump_json(indent=2)}") # <-- ADDED DEBUG LOG

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    # 1. Prepare conversation history for LangGraph state
    # Use history from initial_state if provided, otherwise from chat_message.history
    loaded_history = chat_message.initial_state.get("conversation_history", []) if chat_message.initial_state else chat_message.history
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
    if not conversation_history or conversation_history[-1].content != chat_message.message:
         conversation_history.append(HumanMessage(content=chat_message.message))

    # 2. Define the input for the graph
    # Initialize state, prioritizing values from initial_state if provided
    initial_graph_state = {
        "conversation_history": conversation_history,
        "task_description": chat_message.initial_state.get("task_description") if chat_message.initial_state else None,
        "required_details": chat_message.initial_state.get("required_details", []) if chat_message.initial_state else [],
        "gathered_details": chat_message.initial_state.get("gathered_details", {}) if chat_message.initial_state else {},
        "missing_details": chat_message.initial_state.get("missing_details", []) if chat_message.initial_state else [],
    }
    # Ensure required_details are populated if empty (for first turn)
    if not initial_graph_state["required_details"] and not initial_graph_state["task_description"]:
         # Let analyze_task handle default initialization if state is completely empty
         pass


    print(f"\n--- Invoking Graph ---")
    print(f"Initial State (Partial): {{'conversation_history': [msg.type for msg in conversation_history], 'gathered_details': {initial_graph_state.get('gathered_details')}}}")
    # print(f"DEBUG: Full initial_graph_state before invoke: {initial_graph_state}") # Keep for debugging if needed

    # 3. Invoke the LangGraph graph
    try:
        final_state = app_graph.invoke(initial_graph_state)
    except ValueError as e: # Catch API key error from _get_llm helper
         print(f"Graph Invocation Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Unexpected Graph Invocation Error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during graph execution.")


    print(f"Final State (Partial): { {k: v for k, v in final_state.items() if k != 'conversation_history'} }")
    print(f"--- Graph Invocation Complete ---\n")


    # 4. Prepare serializable history from the final state
    serializable_history = []
    if final_state and final_state.get('conversation_history'):
        for msg in final_state['conversation_history']:
            if isinstance(msg, HumanMessage):
                serializable_history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serializable_history.append({"role": "assistant", "content": msg.content})

    # 5. Determine the response content
    response_content = "Error: Could not determine response." # Default error
    if final_state:
        if final_state.get('task_confirmed'):
            # Task was confirmed and graph ended via task_complete node
            response_content = "Okay, task confirmed and completed!" # Or potentially trigger next step
            # Add a final confirmation message to the history for display
            if not serializable_history or serializable_history[-1].get("content") != response_content:
                 serializable_history.append({"role": "assistant", "content": response_content})
        elif final_state.get('conversation_history'):
            # Graph ended via ask_for_details or confirm_task, extract last AI message
            # Check if the last message is indeed an AIMessage before accessing content
            last_message = final_state['conversation_history'][-1]
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            else:
                 # This case might happen if the graph ends unexpectedly after a user message
                 print(f"Warning: Graph ended, but last message was not from AI. History: {serializable_history}")
                 # Decide on appropriate response, maybe echo confirmation or an error
                 response_content = "Processing complete." # Generic completion message
        else:
            # This case should ideally not happen if the graph runs
            print(f"Error: Final state lacks conversation history. Final state: {final_state}")


    # 6. Return the response AND the updated state
    return {
        "response": response_content,
        "state": {
            "conversation_history": serializable_history,
            "task_description": final_state.get("task_description"),
            "required_details": final_state.get("required_details", []),
            "gathered_details": final_state.get("gathered_details", {}),
            "missing_details": final_state.get("missing_details", []),
            "task_confirmed": final_state.get("task_confirmed", False)
        }
    }

# Main execution block to run the server
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)