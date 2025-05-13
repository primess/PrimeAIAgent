from starlette.websockets import WebSocketDisconnect
import os
import json # Already present, but ensure it is
import base64
import asyncio
import websockets
import logging
import re # Added for input validation
from websockets.protocol import State # Changed from websockets.connection
import websockets.protocol # Added for explicit state checking (this line is now redundant if only State is used from here, but harmless)
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK # Added specific exceptions
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.websockets import WebSocketDisconnect, WebSocketState # Added WebSocketState
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream, Parameter # Added Parameter
from twilio.rest import Client as TwilioClient # Added Twilio Client
from twilio.base.exceptions import TwilioRestException # Added specific Twilio exception
from dotenv import load_dotenv
from typing import Optional # Added Optional
from backend.web.call_handler_models import CallInitiationRequest # Added for Task 6
from logging_config import LOGGING_CONFIG_DICT, setup_logging # Import the dict and setup function

# Apply logging configuration immediately
setup_logging()

load_dotenv()

# --- Configuration ---
PORT = int(os.getenv('PORT', 5002))
# OpenAI
CHAT_MODEL_API_KEY = os.getenv('CHAT_MODEL_API_KEY')
REALTIME_VOICE_API_KEY = os.getenv('CHAT_MODEL_API_KEY')
REALTIME_VOICE_WS_URL = os.getenv('REALTIME_VOICE_WS_URL') # OpenAI Realtime Voice WebSocket URL

#for openai direct - comment out
#REALTIME_AI_MODEL = os.getenv('REALTIME_AI_MODEL', "gpt-4o-realtime-preview-2024-10-01") # Specify model
#OPENAI_WS_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
VOICE = os.getenv('VOICE', 'alloy') # OpenAI Voice
# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN') # Renamed from TWILIO_TOKEN for consistency
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# General
LOG_EVENT_TYPES = [ # For debugging OpenAI events
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

# --- Initialization ---
app = FastAPI()

# Logging configuration is now imported from logging_config.py
# The LOG_DIR creation and LOG_FILE definition are also in logging_config.py

# Validate essential configuration
if not CHAT_MODEL_API_KEY:
    raise ValueError('Missing CHAT_MODEL_API_KEY. Please set it in the .env file.')
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    raise ValueError('Missing Twilio credentials (SID, Auth Token, Phone Number). Please set them in the .env file.')

# Initialize Twilio Client
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- Helper Functions ---
def get_websocket_url(request: Request) -> str:
    """Determines the WebSocket URL (wss://) based on the request."""
    ngrok_url_env = os.getenv("NGROK_URL")
    # NGROK_PORT is not typically needed for the public Twilio Stream URL
    # as ngrok maps its public URL (usually on port 443 for wss) to your local port.
    if ngrok_url_env:
        # Assume ngrok provides an HTTPS endpoint, so use wss.
        # Do not append the local port to the public ngrok hostname for Twilio.
        # NGROK_URL should be just the hostname, e.g., "xxxx.ngrok-free.app"
        return f"wss://{ngrok_url_env}/media-stream"
    else:
        # Fallback for non-ngrok deployments (e.g., direct public IP or other proxy)
        scheme = "wss" if request.url.scheme in ["https", "wss"] else "ws"
        # Use X-Forwarded-Host if available (common with proxies like ngrok)
        host = request.headers.get("x-forwarded-host", request.url.hostname)
        port_str = f":{request.url.port}" if request.url.port else ""
        # Avoid adding default ports 80/443 explicitly
        if (scheme == "ws" and request.url.port == 80) or \
            (scheme == "wss" and request.url.port == 443):
            port_str = ""
        return f"{scheme}://{host}{port_str}/media-stream"


# --- FastAPI Endpoints ---
@app.get("/", response_class=JSONResponse)
async def index_page():
    """Basic status endpoint."""
    return {"message": "AI Assistant Agent is running!"}

@app.get("/", response_class=JSONResponse)
async def index_page():
    """Basic status endpoint."""
    return {"message": "AI Assistant Agent is running!"}

from backend.agent.workflow_manager import WorkflowManager

workflow_manager = WorkflowManager()

@app.post("/chat", response_class=JSONResponse)
async def chat_endpoint(request: Request):
    """Processes chat messages and returns the AI's response."""
    try:
        chat_message = await request.json()
        response = await workflow_manager.process_chat(chat_message)
        return response
    except Exception as e:
        logging.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/order", response_class=JSONResponse) # Changed from GET to POST
async def handle_order(request: Request, call_details: CallInitiationRequest): # Changed signature
    """Initiates an outbound call using details from the POST request body."""
    # --- Debugging Headers ---
    logging.info(f"Incoming Request Headers: {dict(request.headers)}")
    # --- End Debugging ---
    logging.info(f"Received order request: Target='{call_details.target_phone_number}', Instruction='{call_details.task_instruction[:100]}...', Context Keys='{list(call_details.call_context.keys())}'")

    # --- Input Validation ---
    # Validate instruction (from the new model field)
    if not call_details.task_instruction:
        logging.error("Validation failed: task_instruction parameter is empty.")
        raise HTTPException(status_code=400, detail="task_instruction parameter cannot be empty.")

    # Validate target_phone_number format (E.164 recommended for Twilio)
    # Simple regex for E.164: '+' followed by 1-15 digits, starting with 1-9.
    # Twilio performs more thorough validation, this is a basic sanity check.
    e164_regex = r"^\+[1-9]\d{1,14}$"
    if not re.match(e164_regex, call_details.target_phone_number):
        logging.error(f"Validation failed: Invalid target_phone_number format: {call_details.target_phone_number}. Expected E.164 format (e.g., +15551234567).")
        raise HTTPException(status_code=400, detail="Invalid target_phone_number format. Expected E.164 format (e.g., +15551234567).")

    logging.info("Input validation passed.")
    # --- End Input Validation ---

    try:
        ws_url = get_websocket_url(request) # Get dynamic WSS URL
        logging.info(f"Generated WebSocket URL for Twilio Stream: {ws_url}")
        logging.info(f"VERIFY_WS_URL: Embedding WebSocket URL in TwiML: {ws_url}") # Added diagnostic log

        # Generate TwiML for the outbound call
        response = VoiceResponse()
        logging.info("VoiceResponse object created.")
        connect = Connect()
        stream = Stream(url=ws_url)
        # Pass base instruction
        stream.parameter(name="instructions", value=call_details.task_instruction)
        # Serialize and pass the context dictionary
        context_json = json.dumps(call_details.call_context)
        stream.parameter(name="context", value=context_json)
        connect.append(stream)
        response.append(connect)
        logging.info("Appended <Connect><Stream> with 'instructions' and 'context' parameters to VoiceResponse.")
        # Add a fallback message if the stream fails
        response.say("Sorry, I couldn't connect to the ordering service.")
        logging.info("Appended fallback <Say> to VoiceResponse.")

        twiml_content = str(response)
        logging.info(f"Generated TwiML for outbound call:\n{twiml_content}")

        # Log TwiML fallback limitation
        logging.warning("Initiating call with <Stream>. Fallback <Say> may not execute if stream connection fails post-initiation.")
        logging.info(f"Generated TwiML: {str(response)}") # Added diagnostic log
        logging.info("Attempting to initiate Twilio call...") # Added diagnostic log

        # Create the outbound call
        call = twilio_client.calls.create(
            to=call_details.target_phone_number, # Use target_phone_number from request body
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml_content
        )
        logging.info(f"Initiated call to {call_details.target_phone_number}, Call SID: {call.sid}")
        return {"status": "Call initiated", "call_sid": call.sid}
    except TwilioRestException as e:
        logging.exception(f"Twilio API error initiating call: {e}") # Use logging.exception
        raise HTTPException(status_code=500, detail=f"Failed to initiate call via Twilio: {str(e)}")
    except Exception as e:
        logging.exception(f"Unexpected error initiating call: {e}") # Use logging.exception
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    logging.info(f"Twilio WebSocket client attempting connection from {websocket.client.host}:{websocket.client.port}")
    await websocket.accept()
    logging.info(f"Twilio WebSocket client connected. State: {websocket.client_state}")
    logging.info(f"MEDIA_STREAM_ENTRY: WebSocket connection accepted from {websocket.client.host}:{websocket.client.port}") # Added diagnostic log
    openai_ws: Optional[websockets.WebSocketClientProtocol] = None # Initialize openai_ws with type hint
    session_task = None # Task for handling the session

    async def session_handler(ws: WebSocket):
        nonlocal openai_ws # Allow modification of outer scope variable
        try:
            logging.info(f"OPENAI_CONNECT_ATTEMPT: Attempting connection to OpenAI at {REALTIME_VOICE_WS_URL}") # Added diagnostic log (replaces previous)
            async with websockets.connect(
                REALTIME_VOICE_WS_URL,
                additional_headers={
                    "api-key": REALTIME_VOICE_API_KEY,
                    # "OpenAI-Beta": "realtime=v1"
                },
                open_timeout=10 # Add a timeout
            ) as oai_ws:
                openai_ws = oai_ws # Assign the connected WebSocket
                logging.info(f"OPENAI_CONNECT_SUCCESS: Successfully connected to OpenAI. State: {openai_ws.state}") # Added diagnostic log (replaces previous)

                # --- Try sending an initial update immediately ---
                await send_session_update(openai_ws, "Initializing session...") # Send placeholder
                logging.info("Sent initial placeholder session update to OpenAI.")
                # --- End initial update ---

                stream_sid: Optional[str] = None
                # Removed instructions_for_call, will construct final prompt just before sending

                async def receive_from_twilio():
                    nonlocal stream_sid # Allow modification
                    logging.info(f"Entered receive_from_twilio task (SID={stream_sid})") # Added task entry log
                    """Receive messages from Twilio, handle events, forward audio."""
                    try:
                        while True: # Keep listening until disconnect
                            logging.debug(f"Attempting to receive from Twilio WebSocket (SID={stream_sid}). State: {ws.client_state}") # Added state log
                            # Check connection state before attempting to receive
                            if ws.client_state != WebSocketState.CONNECTED:
                                logging.warning(f"Twilio WebSocket no longer connected (State: {ws.client_state}). Exiting receive loop.")
                                break
                            try: # Added try block for disconnect handling
                                message = await ws.receive_text()
                                data = json.loads(message)

                                if data['event'] == 'start':
                                    stream_sid = data['start']['streamSid']
                                    # Extract instructions from parameters passed in TwiML via WebSocket URI query params
                                    logging.info(f"DEBUG: Full start event data: {data['start']}")
                                    # Extract base instructions and context from custom parameters
                                    custom_params = data['start'].get('customParameters', {}) # Get params safely
                                    logging.info(f"DEBUG: Received customParameters: {custom_params}") # Log received params
                                    base_instructions = custom_params.get('instructions', 'Please describe your task.') # Use custom_params
                                    context_str = custom_params.get('context', '{}') # Use custom_params
                                    try:
                                        context_data = json.loads(context_str)
                                    except json.JSONDecodeError:
                                        logging.error(f"Error decoding context JSON for SID={stream_sid}: {context_str}")
                                        context_data = {} # Use empty context on error

                                    # Construct the final prompt
                                    final_prompt = format_prompt(base_instructions, context_data)
                                    # --- Debugging: Log the final prompt before sending ---
                                    logging.info(f"DEBUG: Constructed final_prompt: {final_prompt}")
                                    # --- End Debugging ---

                                    # Log expected audio format based on Twilio start event if available
                                    media_format = data['start'].get('mediaFormat', {})
                                    encoding = media_format.get('encoding', 'N/A')
                                    sample_rate = media_format.get('sampleRate', 'N/A')
                                    channels = media_format.get('channels', 'N/A')
                                    # Log truncated base instructions and context keys
                                    logging.info(f"Twilio stream started: SID={stream_sid}, BaseInstructions='{base_instructions[:50]}...', ContextKeys='{list(context_data.keys())}', MediaFormat: encoding={encoding}, sampleRate={sample_rate}, channels={channels}")
                                    logging.info(f"TWILIO_START_RECEIVED: Received start event. Data: {json.dumps(data['start'])}") # Added diagnostic log
                                    logging.info(f"OpenAI session configured for input: g711_ulaw, output: g711_ulaw")
                                    # Now that we have the final prompt, configure the OpenAI session
                                    await send_session_update(openai_ws, final_prompt) # Pass the combined prompt

                                elif data['event'] == 'media':
                                    # Log received audio format (though Twilio usually only sends payload here)
                                    # logging.debug(f"Received media event. Payload size: {len(data['media']['payload'])}") # Debug level if needed
                                    # Ensure openai_ws exists and is open before sending
                                    if openai_ws and openai_ws.state == websockets.protocol.State.OPEN:
                                        # Forward audio payload to OpenAI
                                        audio_append = {
                                            "type": "input_audio_buffer.append",
                                            "audio": data['media']['payload'] # Already base64 encoded mu-law from Twilio
                                        }
                                        await openai_ws.send(json.dumps(audio_append))
                                    else:
                                        logging.warning(f"Received Twilio media for SID={stream_sid}, but OpenAI WebSocket is not open (State: {openai_ws.state if openai_ws else 'None'}). Discarding.")

                                elif data['event'] == 'stop':
                                    logging.info(f"Twilio stream stopped event received: SID={stream_sid}. Preparing to close OpenAI connection.")
                                    # NOTE: OpenAI Realtime API doesn't specify an explicit 'end of input' message.
                                    # Closing the WebSocket connection signals the end of the stream.
                                    # If an explicit signal were available, it would be sent here before closing.
                                    break # Exit loop on stop event

                                elif data['event'] == 'mark':
                                    logging.info(f"Twilio mark event: {data['mark']}")

                            except WebSocketDisconnect as e: # Catch specific disconnect
                                logging.info(f"Twilio WebSocket disconnected in receive loop (SID={stream_sid}). Code: {e.code}, Reason: {e.reason}")
                                break # Exit the loop on disconnect
                            except json.JSONDecodeError as e:
                                logging.error(f"Error decoding JSON from Twilio (SID={stream_sid}): {message}. Error: {e}")
                                # Decide whether to continue or break; maybe log and continue for minor issues
                                continue # Continue listening if it's just a bad message
                            except Exception as e: # Catch other potential errors during receive/processing
                                logging.error(f"Error processing message from Twilio (SID={stream_sid}): {e}", exc_info=True) # Log with traceback
                                # Decide if we should break or continue based on the error
                                # For now, let's break on any other processing error within the loop
                                break
                    finally:
                        logging.info(f"Exiting receive_from_twilio loop (SID={stream_sid}). Cleaning up OpenAI connection.")
                        # Ensure OpenAI connection is closed if Twilio disconnects or loop exits
                        if openai_ws and openai_ws.state == State.OPEN:
                            logging.info(f"Closing OpenAI WebSocket (SID={stream_sid}) from receive_from_twilio finally block.")
                            # NOTE: This is where an explicit OpenAI end-of-input signal would go if available.
                            try:
                                await openai_ws.close(code=1000, reason="Twilio stream ended")
                                logging.info(f"OpenAI WebSocket closed gracefully (SID={stream_sid}). State: {openai_ws.state}")
                            except Exception as close_err:
                                logging.error(f"Error closing OpenAI WebSocket (SID={stream_sid}): {close_err}", exc_info=True)
                        elif openai_ws:
                            logging.info(f"OpenAI WebSocket already closed or not open (State: {openai_ws.state}) in receive_from_twilio finally block.")
                        else:
                            logging.info("OpenAI WebSocket was not established in receive_from_twilio finally block.")

                async def send_to_twilio():
                    nonlocal stream_sid
                    logging.info(f"Entered send_to_twilio task (SID={stream_sid})") # Added task entry log
                    """Receive messages from OpenAI, handle events, forward audio."""
                    try:
                        async for openai_message in openai_ws:
                            # --- Added Logging ---
                            logging.debug(f"Attempting to receive from OpenAI WebSocket (SID={stream_sid}). State: {openai_ws.state}")
                            # --- End Added Logging ---
                            logging.debug(f"Raw message received from OpenAI: {openai_message}") # Added Debug Log
                            response = json.loads(openai_message)
                            logging.debug(f"Received event type from OpenAI: {response.get('type')}") # Added Info Log
                            # --- End Added Logging ---

                            # Log specific event types for debugging
                            if response['type'] in LOG_EVENT_TYPES:
                                logging.info(f"[OpenAI Event] Type: {response['type']}, SID: {stream_sid}, Details: {response}")

                            # Handle audio delta from OpenAI
                            if response['type'] == 'response.audio.delta' and response.get('delta'):
                                pcm_audio_b64 = response['delta'] # Base64 encoded PCM data from OpenAI
                                # logging.debug(f"Received PCM audio delta from OpenAI. Base64 size: {len(pcm_audio_b64)}") # Debug if needed

                                if not stream_sid:
                                    logging.warning(f"Received audio delta from OpenAI before stream_sid was set (Payload size: {len(pcm_audio_b64)}). Ignoring.")
                                    continue
                                if ws.client_state != WebSocketState.CONNECTED:
                                    logging.warning(f"Received audio delta from OpenAI for SID={stream_sid}, but Twilio WebSocket is not connected (State: {ws.client_state}). Discarding.")
                                    continue

                                try:
                                    # Forward the base64 audio delta directly from OpenAI
                                    # logging.debug(f"Forwarding original audio delta. Base64 size: {len(pcm_audio_b64)}") # Debug if needed

                                    audio_delta_msg = {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {
                                            "payload": pcm_audio_b64 # Send original base64 data from OpenAI
                                        }
                                    }
                                    await ws.send_json(audio_delta_msg)
                                except WebSocketDisconnect:
                                    logging.warning(f"Twilio WebSocket disconnected while trying to send audio delta (SID={stream_sid}).")
                                    break # Exit loop as we can't send anymore
                                except Exception as e:
                                    logging.error(f"Error sending audio delta to Twilio (SID={stream_sid}): {e}", exc_info=True)
                                    # Decide if we should break or continue based on the error
                                    if isinstance(e, (ConnectionClosedError, ConnectionClosedOK, WebSocketDisconnect)): # Check for disconnect too
                                        break

                            # Handle response.done event specifically
                            elif response['type'] == 'response.done':
                                status = response.get('response', {}).get('status', 'unknown')
                                # Debug log added here (correctly indented)
                                logging.debug(f"DEBUG: status_details value: {response.get('response', {}).get('status_details')}")
                                # Check if status_details is None before trying to access 'reason'
                                status_details = response.get('response', {}).get('status_details')
                                reason = status_details.get('reason', 'unknown') if isinstance(status_details, dict) else 'unknown' # Safely get reason
                                logging.info(f"[OpenAI Response Done] SID: {stream_sid}, Status: {status}, Reason: {reason}, Details: {json.dumps(response)}") # Log full details
                                if reason == 'turn_detected':
                                    logging.warning(f"OpenAI detected turn (SID={stream_sid}). AI response was cancelled. Continuing to listen.")
                                elif status == 'completed':
                                    logging.info(f"OpenAI response completed normally (SID={stream_sid}). Continuing to listen.")
                                else:
                                    logging.warning(f"OpenAI response done with unhandled status/reason (SID={stream_sid}): Status={status}, Reason={reason}")
                                # Continue listening in all 'response.done' cases for now

                            # Handle other OpenAI events if needed (e.g., text delta for logging)
                            elif response['type'] == 'response.text.delta':
                                logging.info(f"[OpenAI Transcript Delta] SID: {stream_sid}, Text: {response.get('text', '')}")

                            # --- Added Error Logging ---
                            elif response.get('type') == 'error':
                                logging.error(f"Received error event from OpenAI (SID={stream_sid}): {response}")
                                # Decide if we need to break or handle the error further.
                                # For now, just logging as requested.
                            # --- End Added Error Logging ---

                    # --- Modified Exception Logging ---
                    except websockets.exceptions.ConnectionClosedOK:
                        logging.info(f"OpenAI WebSocket closed normally (OK) (SID={stream_sid}). State: {openai_ws.state if openai_ws else 'None'}")
                    except websockets.exceptions.ConnectionClosedError as e:
                        logging.error(f"OpenAI WebSocket closed with error (SID={stream_sid}). State: {openai_ws.state if openai_ws else 'None'}. Code={e.code}, Reason='{e.reason}'")
                    except WebSocketDisconnect: # Keep this specific Twilio disconnect handler
                        # This shouldn't ideally happen here as we are reading from OpenAI, but handle defensively
                        logging.warning(f"Twilio WebSocket disconnected while send_to_twilio was active (SID={stream_sid}). State: {ws.client_state}") # Log Twilio state
                    except Exception as e:
                        # Log state for general exceptions too
                        logging.exception(f"Error processing message from OpenAI (SID={stream_sid}). State: {openai_ws.state if openai_ws else 'None'}")
                    # --- End Modified Exception Logging ---
                    finally:
                        logging.info(f"Exiting send_to_twilio loop (SID={stream_sid}). Cleaning up Twilio connection.")
                        # Ensure Twilio connection is closed if OpenAI disconnects or loop exits
                        if ws.client_state == WebSocketState.CONNECTED:
                            logging.info(f"Closing Twilio WebSocket (SID={stream_sid}) from send_to_twilio finally block.")
                            try:
                                await ws.close(code=1000, reason="OpenAI stream ended or error")
                                logging.info(f"Twilio WebSocket closed gracefully (SID={stream_sid}). State: {ws.client_state}")
                            except Exception as close_err:
                                logging.error(f"Error closing Twilio WebSocket (SID={stream_sid}): {close_err}", exc_info=True)
                        else:
                            logging.info(f"Twilio WebSocket already closed or not connected (State: {ws.client_state}) in send_to_twilio finally block.")


                logging.info(f"Starting concurrent tasks: receive_from_twilio and send_to_twilio (SID={stream_sid})") # Added gather log
                # Run the listeners concurrently
                await asyncio.gather(receive_from_twilio(), send_to_twilio())

        except ConnectionClosedError as e:
            logging.error(f"OPENAI_CONNECT_FAILURE: Initial connection to OpenAI WebSocket failed.") # Added diagnostic log
            logging.error(f"Failed to connect to OpenAI WebSocket: {e}", exc_info=True)
            # Close the Twilio connection if we couldn't connect to OpenAI initially
            if websocket.client_state == WebSocketState.CONNECTED:
                logging.info("Closing Twilio WebSocket because initial OpenAI connection failed.")
                await websocket.close(code=1011, reason="Failed to connect to backend AI service")
        except Exception as e:
            logging.error(f"Unhandled error in session_handler main try block: {e}", exc_info=True)
            # Ensure cleanup in case of unexpected errors before or during gather
            if openai_ws and openai_ws.state == State.OPEN:
                logging.info("Closing OpenAI WebSocket due to error in session_handler.")
                await openai_ws.close(code=1011, reason="Session handler error")
            if websocket.client_state == WebSocketState.CONNECTED:
                logging.info("Closing Twilio WebSocket due to error in session_handler.")
                await websocket.close(code=1011, reason="Internal server error in session handler")

    # Start the session handler task
    session_task = asyncio.create_task(session_handler(websocket))
    
    # Keep the endpoint alive until the task completes
    try:
        await session_task
    except asyncio.CancelledError:
        logging.info("WebSocket handler task cancelled.")
    finally:
        # Final log indicating the handler for this specific Twilio connection is ending
        logging.info(f"Session handler for Twilio client {websocket.client.host}:{websocket.client.port} finished.")

# --- Helper function to format prompt (Task 6) ---
def format_prompt(base_instruction: str, context_data: dict) -> str:
    """Combines base instruction with formatted context data."""
    prompt = base_instruction
    if context_data:
        prompt += "\n\nHere are the details gathered for this task:\n"
        for key, value in context_data.items():
            # Simple formatting, can be enhanced (e.g., handling nested dicts/lists)
            prompt += f"- {key.replace('_', ' ').title()}: {value}\n"
        prompt += "\nPlease proceed based on these details." # Or similar closing
    return prompt
# --- End Helper function ---

async def send_session_update(openai_ws, final_prompt: str): # Changed signature
    """Send session update to OpenAI WebSocket with the final combined prompt."""
    # The final prompt (base instructions + formatted context) is now passed directly

    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",       # Format received from Twilio
            "output_audio_format": "g711_ulaw",     # Reverted back from "mulaw"
            "voice": VOICE,                         # Defined OpenAI voice
            "instructions": final_prompt,           # Use the final combined prompt
            "modalities": ["audio", "text"],        # Supported combination
            "temperature": 0.7,                     # Adjust creativity/randomness
        }
    }
    logging.info(f"Sending session update to OpenAI: {json.dumps(session_update)}")
    # --- Debugging: Log the exact instructions being sent ---
    logging.info(f"DEBUG: OpenAI session.update instructions: {session_update['session']['instructions']}")
    # --- End Debugging ---
    await openai_ws.send(json.dumps(session_update))


if __name__ == "__main__":
    import uvicorn
    # Use reload=True for development convenience
    # Pass the custom logging configuration to Uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_config=LOGGING_CONFIG_DICT # Pass the dictionary
    )
