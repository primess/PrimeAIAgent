import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Assuming your FastAPI app instance is named 'app' in orchestrator.main
# If it's named differently, adjust the import accordingly.
# We need to import the app instance to test it.
# A common pattern is to have a create_app function or similar,
# but for now, let's assume direct import is possible.
# If main.py runs the server directly (uvicorn.run(app...)),
# we might need to refactor main.py slightly to expose the app instance
# without running the server when imported.
# For now, let's assume 'app' is importable.
# If the import fails now, the test run will show the actual ImportError.
from orchestrator.main import app

# Create a single TestClient instance using the imported app
client = TestClient(app)

# Tests are now synchronous
def test_read_root():
    """Test the GET / endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

def test_chat_valid():
    """Test the POST /chat endpoint with valid data."""
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json() == {"response": "message acknowledged"}

def test_chat_invalid_missing_message():
    """Test the POST /chat endpoint with invalid data (missing message)."""
    response = client.post("/chat", json={"other_field": "value"})
    # FastAPI should return 422 for validation errors
    assert response.status_code == 422