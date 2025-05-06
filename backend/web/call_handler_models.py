from pydantic import BaseModel, Field
from typing import Dict, Any

# Define the request body model for the call initiation endpoint (/order)
class CallInitiationRequest(BaseModel):
    target_phone_number: str = Field(..., description="The phone number to call.")
    task_instruction: str = Field(..., description="Base instruction for the LLM agent's role and goal.")
    call_context: Dict[str, Any] = Field(default_factory=dict, description="Structured details gathered by the orchestrator (e.g., from GraphState.gathered_details).")