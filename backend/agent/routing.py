import logging # Added

# Internal import for type hints
from .state import GraphState

logger = logging.getLogger(__name__) # Added

# --- Conditional Routing Logic ---
def route_after_analysis(state: GraphState):
    """
    Determines the next step based on whether details are missing or task is confirmed.
    """
    logger.info("--- Running Router: route_after_analysis ---") # Changed
    if state.get("task_confirmed"):
        logger.info("  Routing to: task_complete (Task Confirmed)") # Changed
        return "task_complete"  # Route to the terminal node
    elif state.get("missing_details"):
        logger.info("  Routing to: ask_for_details") # Changed
        return "ask_for_details"
    else:
        # No missing details and not yet confirmed -> ask for confirmation
        logger.info("  Routing to: confirm_task") # Changed
        return "confirm_task"