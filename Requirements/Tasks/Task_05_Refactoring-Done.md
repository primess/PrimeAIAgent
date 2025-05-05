# Task 05: Refactor Backend Structure and Code Organization

## Objective

Refactor the existing `orchestrator/main.py` and project structure to improve modularity, maintainability, and adherence to SOLID principles, particularly the Single Responsibility Principle. Introduce a clear separation between backend and frontend components, and organize backend code into functional areas (web, agent, etc.).

## Pre-requisites

1.  Ensure all existing unit tests pass before starting the refactoring. Execute the test suite and confirm a successful run.

## Refactoring Steps

1.  **Rename `orchestrator/` to `backend/`**: Update the top-level directory containing the core application logic.
2.  **Create `frontend/` directory**: Create a new top-level directory for UI code.
3.  **Move `ui.py`**: Relocate the existing `ui.py` file to `frontend/ui.py`.
4.  **Create `backend/web/` directory**: For FastAPI and web-related components.
    *   Create `backend/web/__init__.py`.
    *   Create `backend/web/app.py`: Move FastAPI app initialization (`FastAPI()`), endpoint definitions (`/`, `/chat`), and Uvicorn server start logic (`if __name__ == "__main__":`) from the original `orchestrator/main.py` here.
    *   Create `backend/web/api_models.py`: Move Pydantic models (e.g., `ChatMessage`) from the original `orchestrator/main.py` here.
5.  **Create `backend/agent/` directory**: For LangGraph agent logic and components.
    *   Create `backend/agent/__init__.py`.
    *   Create `backend/agent/config.py`: Move configuration loading (`load_dotenv`) and LLM client initialization (`_get_llm`) here.
    *   Create `backend/agent/state.py`: Move the `GraphState` TypedDict definition here.
    *   Create `backend/agent/llm_utils.py`: Move LLM utility functions (`_parse_llm_json_response`) here.
    *   Create `backend/agent/nodes.py`: Move node functions (`analyze_task`, `ask_for_details`, `confirm_task`, `task_complete`) here.
    *   Create `backend/agent/routing.py`: Move routing logic (`route_after_analysis`) here.
    *   Create `backend/agent/graph.py`: Move LangGraph definition (`StateGraph(...)`) and compilation logic (`workflow.compile()`) here.
    *   Create `backend/agent/workflow_manager.py`: Implement a `WorkflowManager` class. This class should load the compiled graph and contain a method (e.g., `process_chat`) that encapsulates the logic for preparing input, invoking the graph, and processing the output, previously handled directly in the `/chat` endpoint.
6.  **Create `backend/twilio/` directory**: Placeholder for future Twilio integration.
    *   Create `backend/twilio/__init__.py`.
7.  **Create `backend/openai_realtime/` directory**: Placeholder for future OpenAI realtime features.
    *   Create `backend/openai_realtime/__init__.py`.
8.  **Create `backend/__init__.py`**: Root init file for the backend package.
9.  **Update Imports**: Carefully review all newly created/modified files and update all `import` statements to reflect the new directory structure (e.g., use `from backend.agent.state import GraphState`, `from backend.web.api_models import ChatMessage`, `from backend.agent.workflow_manager import WorkflowManager`). Ensure relative imports are correct where used.
10. **Refactor `backend/web/app.py`**:
    *   Import and instantiate the `WorkflowManager` from `backend.agent.workflow_manager`.
    *   Modify the `/chat` endpoint implementation to delegate the core processing logic by calling the appropriate method on the `WorkflowManager` instance (e.g., `result = manager.process_chat(chat_message)`).
11. **Review and Remove**:
    *   Delete the original `orchestrator/` directory and its contents (`main.py`, `__init__.py`) after verifying all code has been successfully moved and refactored.
    *   Review the `main.py` file currently in the project root. Determine if its functionality is still required or if it should be removed or modified, given that `backend/web/app.py` is now the primary entry point for the backend service.

## Verification

1.  Run the complete unit test suite again after all refactoring steps are complete.
2.  Confirm that all tests pass successfully, indicating that the refactoring did not break existing functionality.

## Proposed Structure Diagram

```mermaid
graph TD
    subgraph Root
        direction LR
        A[.env.example]
        B[.gitignore]
        C[README.md]
        D[requirements.txt]
        E[Requirements/]
        F[tests/]
        G[backend/]
        H[frontend/]
    end

    subgraph backend/
        direction LR
        I[__init__.py]
        J[web/]
        K[agent/]
        L[twilio/]
        M[openai_realtime/]
    end

    subgraph frontend/
        direction LR
        N[ui.py]
    end

    subgraph backend/web/
        direction LR
        O[__init__.py]
        P[app.py]
        Q[api_models.py]
    end

    subgraph backend/agent/
        direction LR
        R[__init__.py]
        S[config.py]
        T[state.py]
        U[llm_utils.py]
        V[nodes.py]
        W[routing.py]
        X[graph.py]
        Y[workflow_manager.py]
    end

    G --> I & J & K & L & M
    H --> N
    J --> O & P & Q
    K --> R & S & T & U & V & W & X & Y
