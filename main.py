from starlette.websockets import WebSocketDisconnect
import os
import json
import base64
import asyncio
import websockets
import logging
import re # Added for input validation
from websockets.connection import State
import websockets.protocol # Added for explicit state checking
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK # Added specific exceptions
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.websockets import WebSocketDisconnect, WebSocketState # Added WebSocketState
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream, Parameter # Added Parameter
from twilio.rest import Client as TwilioClient # Added Twilio Client
from twilio.base.exceptions import TwilioRestException # Added specific Twilio exception
from dotenv import load_dotenv
from typing import Optional # Added Optional

load_dotenv()

# --- Configuration ---
PORT = int(os.getenv('PORT', 5002))
# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', "gpt-4o-realtime-preview-2024-10-01") # Specify model
OPENAI_WS_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s ▶ %(message)s")

# Validate essential configuration
if not OPENAI_API_KEY:
    raise ValueError('Missing OPENAI_API_KEY. Please set it in the .env file.')
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    raise ValueError('Missing Twilio credentials (SID, Auth Token, Phone Number). Please set them in the .env file.')

# Initialize Twilio Client
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- Helper Functions ---
def get_websocket_url(request: Request) -> str:
    """Determines the WebSocket URL (wss://) based on the request."""
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
    return {"message": "Pizza Ordering AI Agent is running!"}

@app.get("/order", response_class=JSONResponse)
async def handle_order(request: Request, instructions: str, phone_number: str):
    """Initiates an outbound call with the provided instructions."""
    logging.info(f"Received phone_number parameter: '{phone_number}'") # Log raw phone number
    logging.info(f"Received order request: Instructions='{instructions[:100]}...', Phone='{phone_number}'") # Log truncated instructions

    # --- Input Validation ---
    if not instructions:
        logging.error("Validation failed: instructions parameter is empty.")
        raise HTTPException(status_code=400, detail="instructions parameter cannot be empty.")

    # Phone number validation: full international or local number
    twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER', '')
    country_code = re.match(r"^\+(\d{1,3})", twilio_phone_number)
    if country_code:
        country_code = country_code.group(1)
        regex = r"^(?:\+" + country_code + r"[0-9]{3,14}|[0-9]{7,14})$"
    else:
        regex = r"^(?:\+[0-9]{1,3}[0-9]{3,14}|[0-9]{7,14})$"

    if not re.match(regex, phone_number):
        logging.error(f"Validation failed: Invalid phone_number format: {phone_number}")
        raise HTTPException(status_code=400, detail="Invalid phone_number format. Must be a valid international or local number.")

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
        stream.parameter(name="instructions", value=instructions) # Pass instructions parameter
        connect.append(stream)
        response.append(connect)
        logging.info("Appended <Connect><Stream> with instructions parameter to VoiceResponse.")
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
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml_content
        )
        logging.info(f"Initiated call to {phone_number}, Call SID: {call.sid}")
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
            logging.info(f"OPENAI_CONNECT_ATTEMPT: Attempting connection to OpenAI at {OPENAI_WS_URL}") # Added diagnostic log (replaces previous)
            async with websockets.connect(
                OPENAI_WS_URL,
                additional_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                },
                open_timeout=10 # Add a timeout
            ) as oai_ws:
                openai_ws = oai_ws # Assign the connected WebSocket
                logging.info(f"OPENAI_CONNECT_SUCCESS: Successfully connected to OpenAI. State: {openai_ws.state}") # Added diagnostic log (replaces previous)
                stream_sid: Optional[str] = None
                instructions_for_call: Optional[str] = None # Store instructions for this specific call

                async def receive_from_twilio():
                    nonlocal stream_sid, instructions_for_call # Allow modification
                    logging.info(f"Entered receive_from_twilio task (SID={stream_sid})") # Added task entry log
                    """Receive messages from Twilio, handle events, forward audio."""
                    try:
                        while True: # Keep listening until disconnect
                            logging.info(f"Attempting to receive from Twilio WebSocket (SID={stream_sid}). State: {ws.client_state}") # Added state log
                            # Check connection state before attempting to receive
                            if ws.client_state != WebSocketState.CONNECTED:
                                logging.warning(f"Twilio WebSocket no longer connected (State: {ws.client_state}). Exiting receive loop.")
                                break
                            try: # Added try block for disconnect handling
                                message = await ws.receive_text()
                                data = json.loads(message)

                                if data['event'] == 'start':
                                    stream_sid = data['start']['streamSid']
                                    # Extract pizza_type from parameters passed in TwiML
                                    # Extract instructions from parameters passed in TwiML via WebSocket URI query params
                                    logging.info(f"DEBUG: Full start event data: {data['start']}")
                                    # Extract instructions from custom parameters passed in TwiML
                                    instructions_for_call = data['start']['customParameters'].get('instructions', 'Please describe your task.') # Default if not found
                                    # Log expected audio format based on Twilio start event if available
                                    media_format = data['start'].get('mediaFormat', {})
                                    encoding = media_format.get('encoding', 'N/A')
                                    sample_rate = media_format.get('sampleRate', 'N/A')
                                    channels = media_format.get('channels', 'N/A')
                                    logging.info(f"Twilio stream started: SID={stream_sid}, Instructions='{instructions_for_call[:50]}...', MediaFormat: encoding={encoding}, sampleRate={sample_rate}, channels={channels}") # Log truncated instructions
                                    logging.info(f"TWILIO_START_RECEIVED: Received start event. Data: {json.dumps(data['start'])}") # Added diagnostic log
                                    logging.info(f"OpenAI session configured for input: g711_ulaw, output: g711_ulaw")
                                    # Now that we have the instructions, configure the OpenAI session
                                    await send_session_update(openai_ws, instructions_for_call)

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
                            logging.info(f"Attempting to receive from OpenAI WebSocket (SID={stream_sid}). State: {openai_ws.state}")
                            # --- End Added Logging ---
                            logging.debug(f"Raw message received from OpenAI: {openai_message}") # Added Debug Log
                            response = json.loads(openai_message)
                            logging.info(f"Received event type from OpenAI: {response.get('type')}") # Added Info Log
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
                                reason = response.get('response', {}).get('status_details', {}).get('reason', 'unknown')
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

async def send_session_update(openai_ws, instructions: str):
    """Send session update to OpenAI WebSocket with provided instructions."""
    # Instructions are now passed directly as an argument

    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",       # Format received from Twilio
            "output_audio_format": "g711_ulaw",     # Request mu-law from OpenAI
            "voice": VOICE,                         # Defined OpenAI voice
            "instructions": instructions,           # Dynamic instructions
            "modalities": ["audio", "text"],        # Supported combination
            "temperature": 0.7,                     # Adjust creativity/randomness
        }
    }
    logging.info(f"Sending session update to OpenAI: {json.dumps(session_update)}")
    await openai_ws.send(json.dumps(session_update))


if __name__ == "__main__":
    import uvicorn
    # Use reload=True for development convenience
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
