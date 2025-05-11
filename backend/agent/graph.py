from langgraph.graph import StateGraph, END

# Internal imports for graph definition
from .state import GraphState
from .nodes import analyze_task, ask_for_details, confirm_task, task_complete, trigger_call
from .routing import route_after_analysis

# --- LangGraph Graph Definition ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("analyze_task", analyze_task)
workflow.add_node("ask_for_details", ask_for_details)
workflow.add_node("confirm_task", confirm_task)
workflow.add_node("trigger_call", trigger_call)
workflow.add_node("task_complete", task_complete)  # Terminal node

# Set the entry point
workflow.set_entry_point("analyze_task")

# Add conditional edges
workflow.add_conditional_edges(
    "analyze_task",
    route_after_analysis,
    {
        "ask_for_details": "ask_for_details",
        "confirm_task": "confirm_task",
        "task_complete": "task_complete", # Route for task_complete outcome
    },
)

# Define endpoints for the information gathering loop
# After asking a question or confirming (but not confirmed yet), the graph should wait for the next user input
workflow.add_edge("ask_for_details", END)
workflow.add_edge("confirm_task", "trigger_call")
# Add the final edge from our terminal node to the actual END
workflow.add_edge("trigger_call", "task_complete")
workflow.add_edge("task_complete", END)
# Compile the graph
app_graph = workflow.compile()