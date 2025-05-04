from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel

# Define the request body model
class ChatMessage(BaseModel):
    message: str

# Initialize the FastAPI app
app = FastAPI()

# Root endpoint
@app.get("/")
async def read_root():
    return {"status": "running"}

# Chat endpoint
@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    # In a real application, you would process the message here
    print(f"Received message: {chat_message.message}")
    return {"response": "message acknowledged"}

# Main execution block to run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)