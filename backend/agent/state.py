from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

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
        task_confirmed: A flag indicating if the user has confirmed the gathered details.
        final_instructions: A string summarizing the confirmed task and details for execution.
        target_phone_number: The phone number to be called for the task, if applicable.
        call_sid: The SID of the call after it has been initiated.
        error: Any error message encountered during node execution.
    """

    conversation_history: Annotated[List[BaseMessage], add_messages]
    task_description: str | None = None  # Optional, can be inferred or set initially
    required_details: List[str] = (
        []
    )  # Example: ["pizza_size", "toppings", "delivery_address", "contact_number"]
    gathered_details: dict = {}
    missing_details: List[str] = []
    task_confirmed: bool = False  # Flag to indicate user confirmed the details
    final_instructions: str | None = None
    target_phone_number: str | None = None
    call_sid: str | None = None # For storing call SID from trigger_call
    error: str | None = None # For storing error messages from nodes