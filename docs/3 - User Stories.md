---
created: 2025-05-13
---
## One-Story-Point User Stories (MVP Focus)

### User Account & Onboarding (F-IN-01 related)
1.  **US001:** As a backend system, I want to store a new user's email and a securely hashed password in the UserDB, so their basic account can be created.
2.  **US002:** As a backend system, I want to provide an API endpoint that validates a user's email and password against stored credentials, so users can authenticate.
3.  **US003:** As a new user, I want to see a basic login form (email input, password input, submit button) on the web interface, so I can attempt to log in.
4.  **US004:** As the User & Auth Service, when a new user account is successfully created, I want to assign a unique Alfred phone number from a pre-defined pool to that user and store it in UserDB, so the user has a number for Alfred.
5.  **US005:** As a logged-in user, I want to view my assigned Alfred phone number clearly displayed on a basic account overview page, so I know which number to use/share.

### Text-based Chat Interface (F-CP-01 - Core Interaction)
6.  **US006:** As a user, I want a persistent text input field visible within the chat interface, so I can type commands or messages to Alfred.
7.  **US007:** As a user, after typing a message in the chat input field, I want to click a 'Send' button (or press Enter) to submit my message to Alfred.
8.  **US008:** As a user, I want my submitted chat messages to be immediately displayed within the chat message history area, so I have a visual record of what I sent.
9.  **US009:** As a system, when a user opens the chat interface for the first time in a session, I want to display a hardcoded welcome message from "Alfred" (e.g., "Hello! I'm Alfred. How can I help you?"), so the user sees an initial engagement.
10. **US010:** As a user, I want to see responses from Alfred displayed as distinct messages within the chat message history area, so I can read Alfred's replies.

### Custom Instruction Management (F-CFG-01 - MVP Basics)
11. **US011:** As a user, I want a dedicated page or section within the Configuration Portal labeled "Custom Instructions", so I can find where to manage my call handling rules. (UI Shell)
12. **US012:** As a user, within the Configuration Portal, I want a text input field to define a custom greeting message (e.g., "You've reached Alfred for `[My Name`]"), so this greeting is used for my inbound calls.
13. **US013:** As the Configuration Service, I want to save a user's custom greeting text to the UserDB, ensuring it's associated with their account, so it can be retrieved by the call handling logic.
14. **US014:** As a user, within the Configuration Portal, I want a text input field to specify a single phone number as my "Default Call Transfer Number", so Alfred knows where to forward certain calls.
15. **US015:** As the Configuration Service, I want to save a user's "Default Call Transfer Number" to the UserDB, so it's available for call transfer actions.
16. **US016:** As a user, in the Configuration Portal, I want to create one simple call rule: "IF an incoming call is from `[specific phone number`] THEN transfer the call to my Default Call Transfer Number", by inputting that specific phone number. (Storing this specific rule structure).
17. **US017:** As the Configuration Service, I want to store the user-defined "VIP caller number" and the associated "transfer to default" action in the UserDB, so the Call Logic service can access it.

### Custom RAG Knowledge Base Management (F-CFG-02, F-AI-02 - MVP .txt Upload & Basic Processing)
18. **US018:** As a user, I want an "Upload .txt File" button within the "Knowledge Base" section of the Configuration Portal, so I can initiate the process of adding a document for RAG.
19. **US019:** As a system, upon user clicking "Upload .txt File", I want to present a standard OS file selection dialog filtered for .txt files, so the user can choose a document from their local system.
20. **US020:** As the RAG Service (backend), I want to receive an uploaded .txt file from a user and store this raw file temporarily, linking it to the user's account, so it’s ready for processing.
21. **US021:** As a user, after selecting a .txt file for upload, I want to see its filename and an initial status (e.g., "Uploaded, Pending Processing") displayed in a list within the RAG management section, so I get confirmation.
22. **US022:** As the RAG Service (backend), for one uploaded .txt file, I want to read its content and split it into text chunks of a predefined maximum character length, storing these chunks associated with the original file ID. (Basic chunking for .txt).
23. **US023:** As the RAG Service (backend), for the text chunks of one processed .txt file, I want to generate vector embeddings using a pre-configured embedding model and store these embeddings in the designated vector database, linked to their respective chunks.
24. **US024:** As a user, I want the status of my uploaded .txt file to change from "Processing" to "Active" in the RAG management section once chunking and embedding are successfully completed, so I know it's ready for use by Alfred.

### RAG-Informed Responses (F-AI-03 - MVP Simple Chat Retrieval)
25. **US025:** As Alfred (Chat Backend), when a user sends a message, I want to pass this message as a query to the RAG Service, specifying the user's ID, to find relevant information from their active .txt documents.
26. **US026:** As the RAG Service, given a user query and user ID, I want to perform a similarity search in the vector database against that user's .txt document embeddings and retrieve the single highest-scoring text chunk.
27. **US027:** As Alfred (Chat Backend), if the RAG service returns a relevant text chunk (from .txt), I want to formulate a simple response like "From your document: '`[retrieved text chunk`]'" and send it to the user's chat interface. (No LLM synthesis for this 1-pointer).
28. **US028:** As Alfred (Chat Backend), if the RAG service indicates no relevant chunks were found for a user's query in their .txt documents, I want to send the message "I couldn't find information on that in your uploaded document." to the user's chat interface.

### Inbound Call Handling (MVP Core)
29. **US029:** As the Telephony Gateway Service, I want to successfully receive an incoming call event notification (including caller ID and called Alfred number) from the integrated Telephony Provider.
30. **US030:** As the Telephony Gateway Service, upon receiving an incoming call event, I want to send an "answer call" command to the Telephony Provider, so the call connection is established.
31. **US031:** As the Call Logic Service, immediately after a call is answered, I want to retrieve the user's configured custom greeting message (from US013) and use a TTS service to play this greeting to the caller. (Assumes basic TTS integration exists).
32. **US032:** As the Voice AI Service, for an active call, I want to capture the first 5-7 seconds of caller audio after the greeting finishes and send this audio to an STT service to get a text transcription. (Basic STT for initial caller utterance).
33. **US033:** As the NLU Service, for a given short transcribed text from the caller (e.g., "What are your opening hours?"), I want to identify if it contains the keyword "hours" to flag a basic 'query_hours' intent. (Simplest keyword-based NLU).
34. **US034:** As an administrator, I want a basic internal tool or script to add a phone number to a global "SpamNumbers" blocklist table in the database.
35. **US035:** As the Call Logic Service, upon receiving an incoming call's caller ID, I want to query the "SpamNumbers" blocklist.
36. **US036:** As the Call Logic Service, if an incoming caller's ID is found on the "SpamNumbers" blocklist and the user has spam blocking enabled (default MVP behavior), I want to instruct the Telephony Gateway to immediately terminate the call (hangup/reject).
37. **US037:** As the Call Logic Service, if the identified NLU intent (from US033) is 'query_hours' and the user has an active RAG document, I want to submit "What are the business hours?" to the RAG service for that user.
38. **US038:** As the Call Logic Service, upon receiving a single relevant text chunk from the RAG service (in response to a 'query_hours' request), I want to use TTS to speak this text chunk to the caller and then terminate the call. (Simple RAG answer delivery).
39. **US039:** As the Call Logic Service, if a user's custom rule "IF caller is `[VIP number`] THEN transfer" (from US017) is matched for an incoming call, I want to retrieve the user's "Default Call Transfer Number" (from US015).
40. **US040:** As the Call Logic Service, upon matching a transfer rule and retrieving the destination number, I want to instruct the Telephony Gateway to initiate a call transfer to that destination number.
41. **US041:** As a user, in the Configuration Portal, I want to create a simple call rule: "IF an incoming call is from an UNKNOWN number (no Caller ID / withheld) THEN take a message".
42. **US042:** As the Call Logic Service, if the "take message for UNKNOWN caller" rule is matched, I want to use TTS to play the prompt "Your call is important. Please leave your name, number, and a short message after the tone."
43. **US043:** As the Telephony Gateway, after the "leave message" prompt is played, I want to start recording the call's audio stream from the caller.
44. **US044:** As the Telephony Gateway, I want to automatically stop the audio recording if 60 seconds of continuous recording is reached, or if the caller hangs up.
45. **US045:** As the Call Logic Service, I want to ensure the saved audio recording (voicemail) file is stored and linked to the corresponding call's log entry ID.
46. **US046:** As Alfred's Notification Service, after a voicemail is successfully recorded and saved, I want to send a simple text notification "New voicemail received" to the user's primary chat interface.

### Outbound Call Handling (MVP Basics)
47. **US047:** As a user, I want to type the command "Alfred, call `[phone_number`]" (e.g., "Alfred, call 123-456-7890") into the chat interface, so I can instruct Alfred to make an outbound call.
48. **US048:** As the Orchestrator service, upon parsing a valid "Alfred, call `[phone_number`]" command from a user, I want to instruct the Telephony Gateway to initiate an outbound PSTN call from the user's Alfred number to the specified `[phone_number`].
49. **US049:** As a user, I want to be able to type "Alfred, call `[phone_number`] and say: `[short message`]" in the chat, so Alfred delivers that short message when the call is answered. (Extending command).
50. **US050:** As the Call Logic Service, for an outbound call initiated with a "say: `[short message`]", once the Telephony Provider indicates the call is answered by the remote party, I want to use TTS to play the `[short message`] and then instruct the Telephony Gateway to hang up the call.

### General Platform Features (MVP Logging & Basic Outcomes)
51. **US051:** As the system (Call Logic Service), for every answered inbound call, I want to create a basic call log entry in the CallLogDB containing: timestamp, caller ID, called Alfred number, call direction (inbound), and call duration (once ended).
52. **US052:** As the system (Orchestrator/Call Logic), for every user-initiated outbound call, I want to create a basic call log entry in CallLogDB containing: timestamp, destination number called, user's Alfred number, call direction (outbound), initial status ('initiated'), and final duration/status (once ended).
53. **US053:** As Alfred's chat interface, when an outbound call is initiated by the user's command, I want to display an immediate status update like "Calling `[phone_number`]..." in the chat.
54. **US054:** As Alfred's chat interface, after an inbound call where a voicemail was successfully taken, I want to display a summary message like "Voicemail received from `[CallerID if available, else 'Unknown Caller'`]" in the chat.
55. **US055:** As a user, I want a "Call History" section in the web interface (portal or chat) that displays a chronological list of my last 5 call log entries, showing at least: date/time, other party's number, and direction (in/out).
56. **US056:** As a user, in my "Call History", if a call log entry corresponds to a taken voicemail, I want to see a clear visual indicator (e.g., a voicemail icon).
57. **US057:** As a user, when I click on a call log entry that has a voicemail indicator, I want a simple audio player to appear and allow me to play the recorded audio message for that call.