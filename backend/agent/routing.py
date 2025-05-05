# Internal import for type hints
from .state import GraphState

# --- Conditional Routing Logic ---
def route_after_analysis(state: GraphState):
    """
    Determines the next step based on whether details are missing or task is confirmed.
    """
    print("--- Running Router: route_after_analysis ---")
    if state.get("task_confirmed"):
        print("  Routing to: task_complete (Task Confirmed)")
        return "task_complete"  # Route to the terminal node
    elif state.get("missing_details"):
        print("  Routing to: ask_for_details")
        return "ask_for_details"
    else:
        # No missing details and not yet confirmed -> ask for confirmation
        print("  Routing to: confirm_task")
        return "confirm_task"