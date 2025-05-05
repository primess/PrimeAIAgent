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
    """

    conversation_history: Annotated[List[BaseMessage], add_messages]
    task_description: str | None = None  # Optional, can be inferred or set initially
    required_details: List[str] = (
        []
    )  # Example: ["pizza_size", "toppings", "delivery_address"]
    gathered_details: dict = {}
    missing_details: List[str] = []
    task_confirmed: bool = False  # Flag to indicate user confirmed the details