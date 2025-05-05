# AI Personal Assistant Agent Project

This project contains two main components:

1.  **Chat Agent:** A web-based chat interface allowing users to interact with an AI assistant that gathers information for tasks (e.g., ordering pizza). Uses FastAPI, LangGraph, and Streamlit. (Code located in `backend/` and `frontend/` directories).
2.  **Voice Agent:** (In `main.py`) An agent capable of making outbound phone calls using Twilio and OpenAI's Realtime API for voice interaction.

This guide covers setup for both components.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

*   **Python:** Version 3.8 or higher. You can download it from [python.org](https://www.python.org/).
*   **pip:** Python's package installer (usually comes with Python). Verify installation with `pip --version`.
*   **Git:** For cloning the repository. Download from [git-scm.com](https://git-scm.com/).
*   **ngrok Account:** A registered account with ngrok. Sign up at [ngrok.com](https://ngrok.com/). You'll need your authtoken. (Required primarily for the Voice Agent).
*   **Twilio Account:** A Twilio account with access to the console. Sign up at [twilio.com](https://www.twilio.com/). You'll need your Account SID, Auth Token, and a Twilio phone number. (Required primarily for the Voice Agent).
*   **OpenAI Account:** An OpenAI account with API access. Sign up at [openai.com](https://platform.openai.com/). You'll need an API key. (Required for both agents).

## Installation

Follow these steps to set up the project environment:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/primess/PrimeAIAgent.git
    cd PrimeAIAgent
    ```

2.  **Create and activate a virtual environment:** This isolates project dependencies.
    ```bash
    # Create the virtual environment
    python -m venv venv
    ```
    *   **Activate on Unix/macOS:**
        ```bash
        source venv/bin/activate
        ```
    *   **Activate on Windows (Command Prompt/PowerShell):**
        ```bash
        .\venv\Scripts\activate
        ```
    *(You should see `(venv)` preceding your command prompt)*

3.  **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Proper configuration is crucial for the application to connect to external services.

1.  **Environment Variables:**
    *   Create a file named `.env` in the root project directory. You can copy the provided `.env.example` file as a template:
        ```bash
        # On Unix/macOS
        cp .env.example .env

        # On Windows
        copy .env.example .env
        ```
    *   Edit the `.env` file and add your credentials. It should look like this:
        ```dotenv
        # .env.example - Copy this to .env and fill in your values

        # Twilio Credentials (Primarily for Voice Agent in main.py)
        TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        TWILIO_AUTH_TOKEN=your_twilio_auth_token
        TWILIO_PHONE_NUMBER=+1xxxxxxxxxx # Your Twilio phone number

        # OpenAI Credentials (Used by both Chat and Voice Agents)
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # Ngrok Authentication (Primarily for Voice Agent in main.py)
        NGROK_AUTHTOKEN=your_ngrok_authtoken

        # Note: These variables are used by both the Chat Agent Backend and the Voice Agent.
        ```
    *   **Important:** Add `.env` to your `.gitignore` file to prevent accidentally committing your secrets.

2.  **Twilio Setup (for Voice Agent):**
    *   Log in to your [Twilio Console](https://www.twilio.com/console).
    *   Find your **Account SID** and **Auth Token** on the main dashboard. Add these to your `.env` file.
    *   Navigate to **Phone Numbers** > **Manage** > **Active Numbers**. Either purchase a new number or use an existing one. Add this number (in E.164 format, e.g., `+1234567890`) to your `.env` file as `TWILIO_PHONE_NUMBER`.
    *   **Webhook Configuration (for Voice Agent):** The Voice Agent (`main.py`) requires webhook configuration for call events. You need to tell Twilio where to send call status updates or potentially receive incoming calls. This typically involves using ngrok (see "Running the Voice Agent" below) to expose the `/media-stream` endpoint defined in `main.py`. Go to your Twilio phone number settings and configure the Voice webhook URL accordingly (e.g., `https://<random-string>.ngrok-free.app/voice`). *Note: The current `/order` endpoint initiates outbound calls and doesn't require an incoming call webhook.*

3.  **OpenAI Setup:**
    *   Log in to the [OpenAI Platform](https://platform.openai.com/).
    *   Navigate to the **API Keys** section.
    *   Create a new secret key. Copy it immediately (you won't be able to see it again) and add it to your `.env` file as `OPENAI_API_KEY`.

4.  **ngrok Setup (for Voice Agent):**
    *   Ensure ngrok is installed (refer to [ngrok installation docs](https://ngrok.com/docs/getting-started/)).
    *   Authenticate your ngrok agent with your authtoken (found in your ngrok dashboard). Add the token to your `.env` file as `NGROK_AUTHTOKEN`. Then, run the following command once:
        ```bash
        ngrok config add-authtoken <your_ngrok_authtoken>
        ```
        *(Replace `<your_ngrok_authtoken>` with your actual token)*. Ngrok uses this token to associate the tunnel with your account.

## Running the Chat Agent

The Chat Agent consists of a backend API and a frontend UI.

**Using VS Code Launch Configurations (Recommended):**

1.  Open the "Run and Debug" panel in VS Code (Ctrl+Shift+D).
2.  Select the **"Run Backend and Frontend"** compound configuration from the dropdown menu.
3.  Click the green "Start Debugging" arrow (F5).
    *   This will start the backend Uvicorn server (listening on port 8000 by default).
    *   This will start the frontend Streamlit application (usually opens automatically in your browser, or provides a URL like `http://localhost:8501`).

**Running Manually:**

1.  **Start the Backend:**
    *   Ensure your virtual environment is activated.
    *   Run the Uvicorn server from the project root directory:
        ```bash
        uvicorn backend.web.app:app --host 0.0.0.0 --port 8000 --reload
        ```
    *   Keep this terminal open. The backend API is now running on `http://localhost:8000`.

2.  **Start the Frontend:**
    *   Open a **new** terminal window.
    *   Ensure your virtual environment is activated.
    *   Run the Streamlit application from the project root directory:
        ```bash
        streamlit run frontend/ui.py
        ```
    *   Streamlit will provide a URL (usually `http://localhost:8501`) to access the chat UI in your browser.

## Running the Voice Agent (from `main.py`)

The Voice Agent requires exposing its local server to the internet using ngrok for Twilio webhooks.

1.  **Start the Voice Agent Server:**
    *   Ensure your virtual environment is activated.
    *   Run the `main.py` script using Uvicorn (it defines a FastAPI app):
        ```bash
        uvicorn main:app --host 0.0.0.0 --port 5002 --reload
        ```
        *(Note: Using port 5002 as defined in `main.py`)*
    *   Keep this terminal open.

2.  **Start ngrok:**
    *   Open a **new** terminal window.
    *   Ensure your virtual environment is activated.
    *   Start ngrok to expose the Voice Agent's port (5002):
        ```bash
        ngrok http 5002
        ```
    *   ngrok will display a **Forwarding** URL (e.g., `https://<random-string>.ngrok-free.app`). **Copy the HTTPS URL.**

3.  **Update Twilio Webhook (if needed):**
    *   If your Twilio setup requires a webhook for call status or incoming calls directed to this agent, update the relevant webhook in the Twilio console to point to your ngrok HTTPS URL, appending the correct path (e.g., `/media-stream` might be relevant depending on Twilio configuration).

## Verification (Voice Agent)

1.  **Initiate an Outbound Call:** Use a tool like `curl` or Postman to hit the `/order` endpoint of the running Voice Agent (use the *local* URL, as the call originates from the server):
    ```bash
    curl -X GET "http://localhost:5002/order?instructions=Your%20call%20instructions%20here&phone_number=+1xxxxxxxxxx"
    ```
    *(Replace instructions and the phone number)*
2.  **Check Application Logs:** Observe the terminal where the Voice Agent (`uvicorn main:app...`) is running. You should see logs indicating the call initiation and potentially WebSocket activity if the call connects.
3.  **Check Twilio Logs:** Monitor the call logs in your Twilio console for status updates.
4.  **Check ngrok Logs:** The ngrok terminal (`ngrok http 5002`) will show traffic if Twilio sends webhook events to it.

## Troubleshooting (Optional)

*   **API Key Errors:** Double-check that `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `OPENAI_API_KEY` in your `.env` file are correct and have no extra spaces. Ensure the `.env` file is being loaded correctly by your application.
*   **ngrok Errors:** Ensure you've authenticated ngrok (`ngrok config add-authtoken ...`). Verify the ngrok tunnel is running and forwarding to the correct local port (5002 for Voice Agent). Check the ngrok status page (`http://127.0.0.1:4040` in your browser while ngrok is running).
*   **Twilio Webhook Issues (Voice Agent):** Confirm the webhook URL in the Twilio console exactly matches the HTTPS ngrok forwarding URL for the Voice Agent (port 5002), including any necessary path (e.g., `/media-stream`). Ensure the Voice Agent server (`uvicorn main:app...`) is running and accessible via the ngrok tunnel. Check Twilio's Debugger logs in the console for errors.
*   **Port Conflicts:** The Chat Agent Backend uses port 8000, the Frontend uses 8501 (by default), and the Voice Agent uses 5002. Ensure these ports are free or configure them differently (update `.vscode/launch.json` and the manual commands if changed).
*   **Firewall Issues:** Local firewalls might block incoming connections via ngrok or prevent local connections between frontend/backend. Ensure your firewall allows traffic on the necessary ports (8000, 8501, 5002).
*   **Virtual Environment Not Activated:** Many errors occur if dependencies aren't installed or found. Ensure `(venv)` is visible in your terminal prompt before running `pip install` or starting the servers.
*   **Chat Agent Connection Issues:** If the Streamlit UI can't connect to the backend, ensure the backend (`uvicorn backend.web.app...`) is running and accessible on `http://localhost:8000`. Check the terminal logs for both frontend and backend for errors.
