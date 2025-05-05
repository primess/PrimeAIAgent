from pydantic import BaseModel
from typing import List, Dict, Any

# Define the request body model for the chat endpoint
class ChatMessage(BaseModel):
    message: str
    # History format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history: List[Dict[str, str]] = []
    # Allow passing initial state (optional, for more complex session management later)
    initial_state: Dict[str, Any] | None = None

# Potentially define response models here if needed for more structure,
# but for now the response is a simple dictionary defined in WorkflowManager.