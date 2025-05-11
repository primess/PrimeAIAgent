# AI Personal Assistant Agent Project

This project integrates a chat-based AI assistant with a voice communication service to automate tasks like placing orders over the phone. It consists of three primary components:

1.  **Orchestrator Agent (Backend):** Located in the `backend/` directory, this component uses FastAPI and LangGraph. It processes user requests from the chat interface, gathers necessary details, and can trigger outbound phone calls via the Call Handler service.
2.  **Frontend UI:** Located in `frontend/ui.py`, this is a Streamlit web application providing the chat interface for users to interact with the Orchestrator Agent.
3.  **Call Handler Service (Communications):** Located in `main.py`, this FastAPI application manages real-time voice communication. It receives call initiation requests from the Orchestrator Agent, makes outbound calls using Twilio, and handles the media stream with OpenAI's Realtime API for voice interaction.

This guide covers the setup and operation of all components for an end-to-end flow.

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

        # Twilio Credentials (Used by Call Handler Service in main.py)
        TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        TWILIO_AUTH_TOKEN=your_twilio_auth_token
        TWILIO_PHONE_NUMBER=+1xxxxxxxxxx # Your Twilio phone number

        # OpenAI Credentials (Used by Orchestrator Agent and Call Handler Service)
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # Optional: Specify a particular OpenAI model for the Call Handler's real-time voice interaction
        # OPENAI_MODEL="gpt-4o-realtime-preview-2024-10-01"
        
        # Ngrok Configuration (Used by Call Handler Service in main.py)
        # NGROK_AUTHTOKEN is for configuring the ngrok client itself (run `ngrok config add-authtoken YOUR_TOKEN` once)
        # NGROK_URL is the public hostname ngrok provides (e.g., your-random-string.ngrok-free.app), WITHOUT http/https or port.
        # The Call Handler (main.py) will prepend wss:// and append /media-stream to this.
        NGROK_URL=your-ngrok-hostname.ngrok-free.app
        # NGROK_PORT (Optional, if your ngrok setup requires specifying it for the URL construction, though typically not needed for the public URL)
        # NGROK_PORT=5002

        # Note: These variables are used by the Orchestrator Agent Backend and the Call Handler Service.
        ```
    *   **Important:** Add `.env` to your `.gitignore` file to prevent accidentally committing your secrets.

2.  **Twilio Setup (for Call Handler Service):**
    *   Log in to your [Twilio Console](https://www.twilio.com/console).
    *   Find your **Account SID** and **Auth Token** on the main dashboard. Add these to your `.env` file.
    *   Navigate to **Phone Numbers** > **Manage** > **Active Numbers**. Either purchase a new number or use an existing one. Add this number (in E.164 format, e.g., `+1234567890`) to your `.env` file as `TWILIO_PHONE_NUMBER`.
    *   **Webhook Configuration (for Call Handler Service):** For Twilio to stream call audio to your Call Handler Service (`main.py`), it needs a publicly accessible WebSocket URL. This is achieved using ngrok. The Call Handler constructs this URL (e.g., `wss://<your-ngrok-url>/media-stream`) and embeds it in the TwiML it serves to Twilio when initiating an outbound call via its `/order` endpoint. No separate webhook configuration is typically needed in the Twilio console for *this specific outbound streaming flow*, as the TwiML dictates the stream connection. If you were handling *incoming* calls to your Twilio number, then you would configure a voice webhook in the Twilio console.

3.  **OpenAI Setup:**
    *   Log in to the [OpenAI Platform](https://platform.openai.com/).
    *   Navigate to the **API Keys** section.
    *   Create a new secret key. Copy it immediately (you won't be able to see it again) and add it to your `.env` file as `OPENAI_API_KEY`.

4.  **ngrok Setup (for Call Handler Service):**
    *   Ensure ngrok is installed (refer to [ngrok installation docs](https://ngrok.com/docs/getting-started/)).
    *   Authenticate your ngrok agent with your authtoken (found in your ngrok dashboard). Run the following command once in your terminal:
        ```bash
        ngrok config add-authtoken <your_ngrok_authtoken>
        ```
        *(Replace `<your_ngrok_authtoken>` with your actual token)*.
    *   When you run the Call Handler Service (see below), you will also run ngrok to expose its port (e.g., 5002). Note the public HTTPS URL ngrok provides (e.g., `https://your-random-string.ngrok-free.app`). You need to set the **hostname** part of this URL (e.g., `your-random-string.ngrok-free.app`) as `NGROK_URL` in your `.env` file. The Call Handler application uses this to construct the correct `wss://` URL for Twilio media streaming.

## Running the Orchestrator Agent (Backend) and Frontend UI

The Orchestrator Agent (backend) and the Frontend UI work together to provide the chat interface.

**Using VS Code Launch Configurations (Recommended):**

1.  Open the "Run and Debug" panel in VS Code (Ctrl+Shift+D).
2.  Select the **"Run Backend and Frontend"** compound configuration from the dropdown menu (this typically runs `backend.web.app` and `frontend.ui`).
3.  Click the green "Start Debugging" arrow (F5).
    *   This will start the Orchestrator backend Uvicorn server (listening on port 8000 by default, as per `.vscode/launch.json`).
    *   This will start the Frontend Streamlit application (usually opens automatically in your browser, or provides a URL like `http://localhost:8501`).

**Running Manually:**

1.  **Start the Orchestrator Agent (Backend):**
    *   Ensure your virtual environment is activated.
    *   Run the Uvicorn server from the project root directory:
        ```bash
        uvicorn backend.web.app:app --host 0.0.0.0 --port 8000 --reload
        ```
    *   Keep this terminal open. The Orchestrator API is now running on `http://localhost:8000`.

2.  **Start the Frontend UI:**
    *   Open a **new** terminal window.
    *   Ensure your virtual environment is activated.
    *   Run the Streamlit application from the project root directory:
        ```bash
        streamlit run frontend/ui.py
        ```
    *   Streamlit will provide a URL (usually `http://localhost:8501`) to access the chat UI in your browser.

## Running the Call Handler Service (Communications - `main.py`)

The Call Handler Service (`main.py`) handles the actual voice call and media streaming. It needs to be publicly accessible via ngrok for Twilio to connect to its WebSocket endpoint.

1.  **Start the Call Handler Server:**
    *   Ensure your virtual environment is activated.
    *   Run the `main.py` script using Uvicorn:
        ```bash
        python -m uvicorn main:app --host 0.0.0.0 --port 5002 --reload
        ```
        *(Note: Using port 5002 as defined in `main.py` and expected by the Orchestrator Agent)*
    *   Keep this terminal open.

2.  **Start ngrok for the Call Handler:**
    *   Open a **new** terminal window.
    *   Ensure your virtual environment is activated.
    *   Start ngrok to expose the Call Handler's port (5002):
        ```bash
        ngrok http 5002
        ```
    *   ngrok will display a **Forwarding** URL (e.g., `https://<random-string>.ngrok-free.app`).
    *   **Crucial:** Copy the **hostname** part of this URL (e.g., `<random-string>.ngrok-free.app`) and set it as the value for `NGROK_URL` in your `.env` file. The Call Handler uses this to construct the `wss://` URL for Twilio. Restart the Call Handler server if you update `.env` while it's running to pick up the new `NGROK_URL`.

## Running the Full Application (Integrated Flow)

To run the entire system for end-to-end testing (chat leading to a phone call), follow these steps:

1.  **Environment Setup:**
    *   Ensure your `.env` file is correctly configured with all API keys (Twilio, OpenAI) and importantly, the `NGROK_URL` (hostname only, e.g., `your-id.ngrok-free.app`).

2.  **Start ngrok for the Call Handler:**
    *   Open a terminal window.
    *   Ensure your virtual environment is activated (if ngrok is installed there or for path consistency).
    *   Start ngrok to expose the Call Handler's port (5002):
        ```bash
        ngrok http 5002
        ```
    *   Note the public **hostname** ngrok provides (e.g., `your-id.ngrok-free.app`) and ensure it's set as `NGROK_URL` in your `.env` file. *The Call Handler and Orchestrator services will need to be (re)started after this `.env` value is set or updated.*
    *   Keep this ngrok terminal running.

3.  **Start All Application Services:**

    **Using VS Code Launch Configuration (Recommended for all components):**
    *   Open the "Run and Debug" panel in VS Code (Ctrl+Shift+D).
    *   Select the **"Run All (BE, FE, Communications)"** compound configuration from the dropdown menu. This configuration is defined in `.vscode/launch.json` and will start:
        *   Orchestrator Agent (Backend - `backend.web.app` on port 8000)
        *   Frontend UI (Streamlit app - `frontend/ui.py` on port 8501)
        *   Call Handler Service (Communications - `main:app` on port 5002)
    *   Click the green "Start Debugging" arrow (or press F5).
    *   VS Code will open integrated terminals for each service.

    **Running Manually (if not using VS Code or the above launch configuration):**
    *   **Terminal 1 (or Tab): Call Handler Service (`main:app`)**
        ```bash
        # Activate venv
        python -m uvicorn main:app --host 0.0.0.0 --port 5002 --reload
        ```
    *   **Terminal 2 (or Tab): Orchestrator Agent (Backend - `backend.web.app`)**
        ```bash
        # Activate venv
        uvicorn backend.web.app:app --host 0.0.0.0 --port 8000 --reload
        ```
    *   **Terminal 3 (or Tab): Frontend UI (`frontend/ui.py`)**
        ```bash
        # Activate venv
        streamlit run frontend/ui.py
        ```

4.  **Test the Flow:**
    *   Open the Streamlit UI (usually `http://localhost:8501`).
    *   Interact with the chat agent to provide details for a task that involves a phone call (e.g., "Order a pizza").
    *   Provide all necessary details, including the target phone number when prompted.
    *   Confirm the task. The Orchestrator Agent (running on port 8000) should then make an HTTP POST request to the Call Handler Service (running on port 5002) at its `/order` endpoint.
    *   The Call Handler Service will use Twilio to initiate the outbound call, and Twilio will attempt to connect to the WebSocket media stream using the `wss://<NGROK_URL>/media-stream` URL.

4.  **Monitor Logs:**
    *   Check logs in all four terminals for activity and errors.
    *   The Orchestrator logs will show the `trigger_call` node activity.
    *   The Call Handler logs (from `main.py`) will show the `/order` request, TwiML generation (including the Stream URL), Twilio API calls, and WebSocket connection attempts to `/media-stream`.
    *   The ngrok terminal shows HTTP/WebSocket requests forwarded to your local Call Handler.
    *   Check Twilio Console logs for call status and errors.

## Troubleshooting (Optional)

*   **API Key Errors:** Double-check credentials in your `.env` file. Ensure it's loaded correctly.
*   **`NGROK_URL` Configuration:** Ensure `NGROK_URL` in `.env` is set to *only the hostname* provided by ngrok (e.g., `your-id.ngrok-free.app`), not the full `https://...` URL and no port. The Call Handler (`main.py`) prepends `wss://`.
*   **ngrok Tunnel:** Verify the ngrok tunnel for the Call Handler (port 5002) is active. Check `http://127.0.0.1:4040` (ngrok status page).
*   **Twilio Media Stream Issues:** If the call connects but audio doesn't stream or you hear the fallback, check Twilio Debugger logs for errors related to the WebSocket connection to `wss://<NGROK_URL>/media-stream`. Ensure the Call Handler's `/media-stream` endpoint is functioning.
*   **Port Conflicts:** Orchestrator Backend (default 8000), Frontend UI (default 8501), Call Handler (default 5002). Ensure these are free.
*   **Firewall Issues:** Firewalls might block ngrok or inter-process communication.
*   **Virtual Environment:** Always ensure your `(venv)` is activated.
*   **Orchestrator-UI Connection:** If UI can't connect to Orchestrator Backend, ensure it's running on `http://localhost:8000`.
*   **Orchestrator-Call Handler Connection:** If the Orchestrator can't trigger a call, ensure the Call Handler is running on `http://localhost:5002` and accessible from the Orchestrator.
