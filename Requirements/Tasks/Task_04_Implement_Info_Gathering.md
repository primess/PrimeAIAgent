# Task 4: Implement Information Gathering Logic (LangGraph)

**Phase:** 2 - Core Conversational Logic (Engine)

**Goal:** Enhance the Orchestration Engine's LangGraph graph to actively manage the conversation state, identify missing information required for a task, and proactively ask the user clarifying questions until all necessary details are gathered.

**Requirements:**

1.  **State Enhancement:** Expand the LangGraph state definition to include fields relevant to task execution, such as:
    *   `task_description`: The user's stated goal.
    *   `required_details`: A list or structure defining information needed for the task type (this might be dynamic based on the task).
    *   `gathered_details`: A structure (e.g., dictionary) storing information collected from the user.
    *   `missing_details`: A list of details still needed.
    *   `conversation_history`: The ongoing chat log.
2.  **Graph Logic Modification:** Refactor the LangGraph graph to implement a stateful information-gathering loop:
    *   **Analysis Node:** Add a node (e.g., "analyze_task") that uses the LLM (or potentially rule-based logic) to compare `gathered_details` against `required_details` based on the `task_description`, updating the `missing_details` field in the state.
    *   **Conditional Routing:** Implement conditional edges based on the `missing_details` field:
        *   If `missing_details` is not empty, route to a node responsible for asking the user for the needed information (e.g., "ask_for_details").
        *   If `missing_details` is empty, route to a node responsible for summarizing the gathered information and asking the user for confirmation (e.g., "confirm_task").
    *   **Question Generation Node ("ask_for_details"):** This node should use the LLM, prompted with the `missing_details` list, to generate a natural language question for the user.
    *   **Confirmation Node ("confirm_task"):** This node should use the LLM, prompted with the `gathered_details`, to generate a summary and ask the user to confirm before proceeding.
    *   **Looping:** Ensure the graph routes back appropriately after the user provides input in response to a question, allowing the analysis node to re-evaluate the state.
3.  **State Persistence:** Ensure the enhanced state is maintained correctly across user interactions within a session (building upon the basic state mechanism from Task 3).

**Testable Outcome:**

*   Using the UI (Task 2) connected to the updated Engine:
    *   Initiate a task requiring specific details (e.g., "Order a pepperoni pizza for delivery").
    *   The agent should respond by asking for the first piece of missing information (e.g., "Okay, I can help with that. What address should the pizza be delivered to?").
    *   Provide the requested detail. The agent should then ask for the next missing detail (e.g., "Got it. And what's a phone number for the order?").
    *   Continue providing details until all required information is gathered.
    *   The agent should then present a summary of the gathered details and ask for confirmation (e.g., "Alright, so I'll order one pepperoni pizza to be delivered to [Address] for [Phone Number]. Is that correct?").
*   Providing insufficient or ambiguous information should prompt the agent to ask clarifying questions.