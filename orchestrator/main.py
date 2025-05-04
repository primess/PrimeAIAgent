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
    Represents the state of our graph.

    Attributes:
        messages: The list of messages accumulated so far.
    """
    messages: Annotated[List[BaseMessage], add_messages]

# --- LangGraph Node ---
def call_model(state: GraphState):
    """
    Invokes the LLM to get a response based on the current conversation history.

    Args:
        state: The current graph state.

    Returns:
        A dictionary containing the updated messages list.
    """
    messages = state['messages']
    api_key = os.getenv("OPENAI_API_KEY") # Fetch key inside the node

    # Ensure API key is available before trying to use it
    if not api_key:
         # If key is missing, return an error message within the graph state.
         # Note: The endpoint check should ideally prevent this node from running without a key.
         ai_response = AIMessage(content="Error: OpenAI API key not configured within graph node.")
         return {"messages": [ai_response]} # Return *only* the new error message

    try:
        # Use a default model if needed, gpt-4o-mini is cost-effective
        model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key) # Use fetched key
        response = model.invoke(messages)
        # Return the new AI response message
        return {"messages": [response]}
    except Exception as e:
        # Handle potential errors during model invocation (e.g., invalid key)
        error_message = f"Error calling OpenAI model: {e}"
        print(error_message) # Log the error server-side
        ai_response = AIMessage(content="Error: Could not communicate with AI model.")
        return {"messages": [ai_response]} # Return *only* the new error message

# --- LangGraph Graph Definition ---
# Define the workflow
workflow = StateGraph(GraphState)

# Define the single node in the graph: the LLM call
workflow.add_node("llm", call_model)

# Set the entry point
workflow.set_entry_point("llm")

# Set the finish point - after the LLM call, the graph ends
workflow.add_edge("llm", END)

# Compile the graph
app_graph = workflow.compile()

# --- FastAPI Application ---

# Define the request body model, including optional history
class ChatMessage(BaseModel):
    message: str
    # History format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history: List[dict] = []

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
    Handles chat requests using the LangGraph conversational agent.
    """
    api_key = os.getenv("OPENAI_API_KEY") # Fetch key inside the endpoint
    if not api_key:
        # Raise HTTP exception if key is missing for this endpoint
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    # 1. Prepare messages for LangGraph state
    input_messages: List[BaseMessage] = []
    for msg in chat_message.history:
        if msg.get("role") == "user":
            input_messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant" or msg.get("role") == "ai": # Accept 'assistant' or 'ai'
            input_messages.append(AIMessage(content=msg.get("content", "")))
        # Silently ignore other roles for now

    # Add the new user message
    input_messages.append(HumanMessage(content=chat_message.message))

    # 2. Define the input for the graph
    graph_input = {"messages": input_messages}

    # 3. Invoke the LangGraph graph
    # Use stream_mode="values" to get the final state directly
    final_state = app_graph.invoke(graph_input)

    # 4. Extract the latest AI response
    # The final state contains all messages, the last one should be the AI's response
    ai_response_message = final_state['messages'][-1] if final_state['messages'] else None

    if isinstance(ai_response_message, AIMessage):
        response_content = ai_response_message.content
    else:
        # Handle cases where the last message isn't from the AI (e.g., error during call_model)
        response_content = "Error: Could not retrieve AI response."
        # Check if the error message from call_model is the last one
        if isinstance(ai_response_message, BaseMessage) and "Error:" in ai_response_message.content:
             response_content = ai_response_message.content


    # 5. Return the response
    return {"response": response_content}

# Main execution block to run the server
if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)