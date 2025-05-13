---
created: 2025-05-13
---
 
# AI Coding Agent Execution Checklist: Alfred v2.0 MVP

## User Account & Onboarding (F-IN-01 related)

- [ ] **US001:** As a backend system, I want to store a new user's email and a securely hashed password in the UserDB, so their basic account can be created.
    - [ ] Task 1.1: Define the `users` table schema in a SQL dialect (e.g., PostgreSQL). Columns: `user_id` (UUID, Primary Key), `email` (VARCHAR(255), Unique, Not Null), `hashed_password` (VARCHAR(255), Not Null), `created_at` (TIMESTAMP WITH TIME ZONE, Default NOW()), `updated_at` (TIMESTAMP WITH TIME ZONE, Default NOW()).
    - [ ] Task 1.2: Create a database migration file (e.g., using Flyway, Alembic) with the `CREATE TABLE users` statement.
    - [ ] Task 1.3: Apply the migration to the development database to create the `users` table.
    - [ ] Task 1.4: In the backend application (e.g., Python/FastAPI, Node.js/Express), define a `User` data model/entity that maps to the `users` table structure. Include fields for `user_id`, `email`, `hashed_password`, `created_at`, `updated_at`.
    - [ ] Task 1.5: In the User/Auth service module, create a function `create_user_account(email, plain_password)`.
    - [ ] Task 1.6: Implement password hashing logic within `create_user_account` using a strong hashing algorithm (e.g., bcrypt or Argon2). Ensure a salt is generated and used per password.
    - [ ] Task 1.7: Implement database insertion logic within `create_user_account` to store the `email` and `hashed_password` into the `users` table. Handle potential unique constraint violations for email.
    - [ ] Task 1.8: Write a unit test for the password hashing function to verify correct hashing and salt generation.
    - [ ] Task 1.9: Write an integration test for `create_user_account` function that verifies:
        - [ ] Successful user creation and storage in the DB.
        - [ ] Correct password hashing.
        - [ ] Error handling for duplicate email addresses.
    - [ ] Task 1.10: Configure appropriate database connection pooling for the backend application.

- [ ] **US002:** As a backend system, I want to provide an API endpoint that validates a user's email and password against stored credentials, so users can authenticate.
    - [ ] Task 2.1: In the backend API router (e.g., FastAPI, Express), define a new POST endpoint, e.g., `/auth/login` or `/auth/token`.
    - [ ] Task 2.2: Define the request body model for this endpoint, expecting `email` (string) and `password` (string).
    - [ ] Task 2.3: Define the success response body model, which should include an access token (e.g., JWT).
    - [ ] Task 2.4: Define error response models for scenarios like "user not found" or "invalid credentials".
    - [ ] Task 2.5: In the User/Auth service module, create a function `authenticate_user(email, plain_password)`.
    - [ ] Task 2.6: Implement logic in `authenticate_user` to retrieve a user record from the `users` table by email. If not found, return an authentication failure.
    - [ ] Task 2.7: Implement logic in `authenticate_user` to verify the provided `plain_password` against the stored `hashed_password` using the same hashing algorithm and salt (e.g., bcrypt.checkpw). If verification fails, return an authentication failure.
    - [ ] Task 2.8: If authentication is successful, generate a JSON Web Token (JWT) containing `user_id` and an expiry time. Use a secure secret key for JWT signing.
    - [ ] Task 2.9: Implement the `/auth/login` endpoint handler to call `authenticate_user`. On success, return the JWT. On failure, return an appropriate HTTP error (e.g., 401 Unauthorized).
    - [ ] Task 2.10: Write integration tests for the `/auth/login` endpoint:
        - [ ] Test successful login with valid credentials, verifying JWT issuance.
        - [ ] Test login with an invalid email.
        - [ ] Test login with a valid email but an incorrect password.
    - [ ] Task 2.11: Ensure the JWT secret key is stored securely (e.g., environment variable) and not hardcoded.

- [ ] **US003:** As a new user, I want to see a basic login form (email input, password input, submit button) on the web interface, so I can attempt to log in.
    - [ ] Task 3.1: In the frontend application (e.g., React, Vue, Angular), create a new component `LoginForm.js` (or equivalent).
    - [ ] Task 3.2: Within `LoginForm`, add an HTML `<form>` element.
    - [ ] Task 3.3: Add an `<input type="email">` field for the email, with a corresponding `<label>`. Include `name="email"` attribute.
    - [ ] Task 3.4: Add an `<input type="password">` field for the password, with a corresponding `<label>`. Include `name="password"` attribute.
    - [ ] Task 3.5: Add an `<button type="submit">` with text like "Login".
    - [ ] Task 3.6: Implement basic frontend state management within `LoginForm` to hold the values of the email and password fields.
    - [ ] Task 3.7: Implement an `onSubmit` handler for the form. This handler should, for now, prevent default form submission and log the email/password to the console (actual API call will be a separate story/task).
    - [ ] Task 3.8: Add basic styling to the `LoginForm` to ensure fields are aligned and usable.
    - [ ] Task 3.9: Create a route (e.g., `/login`) in the frontend routing configuration that renders the `LoginForm` component.
    - [ ] Task 3.10: Write a UI component test for `LoginForm` verifying:
        - [ ] Presence of email field, password field, and submit button.
        - [ ] State updates correctly on input change.

- [ ] **US004:** As the User & Auth Service, when a new user account is successfully created, I want to assign a unique Alfred phone number from a pre-defined pool to that user and store it in UserDB, so the user has a number for Alfred.
    - [ ] Task 4.1: Define a new table `available_phone_numbers` in the database. Columns: `phone_number` (VARCHAR(20), Primary Key), `is_assigned` (BOOLEAN, Default FALSE), `assigned_to_user_id` (UUID, Foreign Key references `users.user_id`, Nullable), `provider_details` (JSONB, Nullable).
    - [ ] Task 4.2: Create a database migration for the `available_phone_numbers` table.
    - [ ] Task 4.3: Populate the `available_phone_numbers` table with a small pool of test phone numbers, initially marked as `is_assigned = FALSE`.
    - [ ] Task 4.4: Modify the `users` table schema to add a new column: `alfred_phone_number` (VARCHAR(20), Nullable, Unique). Update the migration.
    - [ ] Task 4.5: In the User/Auth service, create a function `assign_phone_number_to_user(user_id)`.
    - [ ] Task 4.6: Implement logic in `assign_phone_number_to_user` to find an unassigned phone number from `available_phone_numbers`, mark it as assigned (set `is_assigned = TRUE`, `assigned_to_user_id = user_id`), and update the `alfred_phone_number` column in the `users` table for the given `user_id`. This must be an atomic operation (transaction).
    - [ ] Task 4.7: Modify the `create_user_account` function (from US001) to call `assign_phone_number_to_user` after successful user record insertion.
    - [ ] Task 4.8: Write unit tests for `assign_phone_number_to_user` covering:
        - [ ] Successful assignment.
        - [ ] Scenario where no phone numbers are available.
    - [ ] Task 4.9: Update integration tests for `create_user_account` to verify `alfred_phone_number` is populated.
    - [ ] Task 4.10: (Future consideration, not for this 1pt task: actual provisioning via Telephony Provider API) For MVP, this assumes manual pre-population of numbers usable by Alfred.

- [ ] **US005:** As a logged-in user, I want to view my assigned Alfred phone number clearly displayed on a basic account overview page, so I know what it is.
    - [ ] Task 5.1: In the backend, create a new authenticated GET API endpoint, e.g., `/users/me/profile`.
    - [ ] Task 5.2: The `/users/me/profile` endpoint handler should retrieve the authenticated user's `email` and `alfred_phone_number` from the `users` table.
    - [ ] Task 5.3: Define the response model for `/users/me/profile` to include `email` and `alfred_phone_number`.
    - [ ] Task 5.4: In the frontend, create a new component `UserProfilePage.js` (or equivalent).
    - [ ] Task 5.5: Implement logic in `UserProfilePage` to fetch data from the `/users/me/profile` endpoint when the component mounts (assuming user is logged in and JWT is available for auth headers).
    - [ ] Task 5.6: Display the fetched `email` and `alfred_phone_number` in the `UserProfilePage` component. E.g., "Your Email: [email]", "Your Alfred Number: [alfred_phone_number]".
    - [ ] Task 5.7: Add a route (e.g., `/profile`) in the frontend routing configuration that renders `UserProfilePage`, ensuring it's a protected route (requires authentication).
    - [ ] Task 5.8: Write an integration test for the `/users/me/profile` backend endpoint.
    - [ ] Task 5.9: Write a UI component test for `UserProfilePage` to verify it displays the fetched data correctly (using mock API calls).
    - [ ] Task 5.10: Implement frontend logic to make authenticated API calls by including the JWT in the Authorization header (e.g., `Bearer <token>`).

## Text-based Chat Interface (F-CP-01 - Core Interaction)

- [ ] **US006:** As a user, I want a persistent text input field visible within the chat interface, so I can type commands or messages to Alfred.
    - [ ] Task 6.1: Create a new frontend component `ChatInput.js`.
    - [ ] Task 6.2: Inside `ChatInput.js`, add an HTML `<input type="text">` element.
    - [ ] Task 6.3: Style the input field to be an appropriate width (e.g., 100% of its container) and height.
    - [ ] Task 6.4: Add a placeholder text to the input field, e.g., "Type your message to Alfred...".
    - [ ] Task 6.5: Ensure the `ChatInput.js` component is rendered as part of a main `ChatInterface.js` component, typically fixed at the bottom of the chat window.
    - [ ] Task 6.6: Write a UI component test for `ChatInput.js` to verify the input field renders with the correct placeholder.

- [ ] **US007:** As a user, after typing a message in the chat input field, I want to click a 'Send' button (or press Enter) to submit my message to Alfred.
    - [ ] Task 7.1: In `ChatInput.js`, add an HTML `<button>` element next to the text input, with text "Send".
    - [ ] Task 7.2: Style the "Send" button appropriately.
    - [ ] Task 7.3: Implement state in `ChatInput.js` to store the current text of the input field (`currentMessage`). Update this state `onChange` of the input field.
    - [ ] Task 7.4: Create a `handleSendMessage` function in `ChatInput.js`.
    - [ ] Task 7.5: Attach `handleSendMessage` to the `onClick` event of the "Send" button.
    - [ ] Task 7.6: Attach `handleSendMessage` to be triggered when the "Enter" key is pressed while the input field is focused (if `currentMessage` is not empty).
    - [ ] Task 7.7: Inside `handleSendMessage`, for now, log `currentMessage` to the console and then clear `currentMessage` (reset the input field).
    - [ ] Task 7.8: The `ChatInput.js` component should accept a prop `onSendMessage(message)` which `handleSendMessage` will call.
    - [ ] Task 7.9: Write a UI component test for `ChatInput.js` verifying the `onSendMessage` prop is called with the input text when the send button is clicked or Enter is pressed, and the input field is cleared.

- [ ] **US008:** As a user, I want my submitted chat messages to be immediately displayed within the chat message history area, so I have a visual record of what I sent.
    - [ ] Task 8.1: Create a new frontend component `ChatMessageList.js`.
    - [ ] Task 8.2: `ChatMessageList.js` should accept a prop `messages` (an array of message objects). A message object should have at least `id`, `text`, `sender` ('user' or 'alfred'), `timestamp`.
    - [ ] Task 8.3: Create a `ChatMessageItem.js` component that takes a single `message` object as a prop and renders its `text` and `sender`. Style user messages differently from Alfred messages (e.g., alignment, background color).
    - [ ] Task 8.4: `ChatMessageList.js` should map over the `messages` prop and render a `ChatMessageItem.js` for each message.
    - [ ] Task 8.5: In the parent `ChatInterface.js` component, maintain a state variable `messageHistory` (array).
    - [ ] Task 8.6: When the `onSendMessage` function (from `ChatInput.js`) is called in `ChatInterface.js`, add a new message object (`{id: uuid(), text: message, sender: 'user', timestamp: new Date()}`) to the `messageHistory` state.
    - [ ] Task 8.7: Pass the `messageHistory` state to the `ChatMessageList.js` component.
    - [ ] Task 8.8: Ensure the `ChatMessageList.js` automatically scrolls to the bottom when a new message is added.
    - [ ] Task 8.9: Write UI component tests for `ChatMessageItem.js` and `ChatMessageList.js`.
    - [ ] Task 8.10: Write a UI integration test for `ChatInterface.js` verifying that sending a message updates the message list.

- [ ] **US009:** As a system, when a user opens the chat interface for the first time in a session, I want to display a hardcoded welcome message from "Alfred" (e.g., "Hello! I'm Alfred. How can I help you?"), so the user sees an initial engagement.
    - [ ] Task 9.1: In `ChatInterface.js`, modify the initial state of `messageHistory`.
    - [ ] Task 9.2: Add a default message object to `messageHistory` upon component initialization: `{id: 'welcome-msg', text: "Hello! I'm Alfred. How can I help you?", sender: 'alfred', timestamp: new Date()}`.
    - [ ] Task 9.3: Ensure this welcome message is only added once per session or on initial load (e.g., using `useEffect` with an empty dependency array).
    - [ ] Task 9.4: Verify the welcome message appears correctly styled as an 'alfred' message in the `ChatMessageList.js`.
    - [ ] Task 9.5: Write a UI test for `ChatInterface.js` to confirm the welcome message is present on initial render.

- [ ] **US010:** As a user, I want to see responses from Alfred displayed as distinct messages within the chat message history area, so I can read Alfred's replies.
    - [ ] Task 10.1: (This is largely covered by US008's `ChatMessageItem.js` styling for `sender: 'alfred'`).
    - [ ] Task 10.2: For now, simulate an Alfred response. After a user sends a message in `ChatInterface.js`, add a timeout (e.g., 1 second).
    - [ ] Task 10.3: After the timeout, add a hardcoded Alfred response to the `messageHistory` state. For example: `{id: uuid(), text: "I received: " + userMessage.text, sender: 'alfred', timestamp: new Date()}`.
    - [ ] Task 10.4: Ensure this simulated Alfred response is styled correctly and appears after the user's message in the `ChatMessageList.js`.
    - [ ] Task 10.5: Write a UI test for `ChatInterface.js` to verify that after sending a message, a simulated Alfred response appears.

## Custom Instruction Management (F-CFG-01 - MVP Basics)

- [ ] **US011:** As a user, I want a dedicated page or section within the Configuration Portal labeled "Custom Instructions", so I can find where to manage my call handling rules. (UI Shell)
    - [ ] Task 11.1: Create a new frontend component `CustomInstructionsPage.js`.
    - [ ] Task 11.2: Add a top-level heading to this page, e.g., `<h1>Custom Instructions</h1>`.
    - [ ] Task 11.3: Add this page to the frontend routing system, e.g., at `/portal/instructions`.
    - [ ] Task 11.4: Ensure navigation to this page is possible from a main Configuration Portal navigation menu (assuming a portal shell exists or will be created).
    - [ ] Task 11.5: The page should, for now, contain placeholder text like "Manage your custom call handling instructions here."
    - [ ] Task 11.6: Write a UI component test to verify the page renders with its heading.

- [ ] **US012:** As a user, within the Configuration Portal, I want a text input field to define a custom greeting message (e.g., "You've reached Alfred for [My Name]"), so this greeting is used for my inbound calls.
    - [ ] Task 12.1: In `CustomInstructionsPage.js` (or a sub-component `GreetingSetting.js`), add a `<label>`: "Custom Greeting Message:".
    - [ ] Task 12.2: Add a `<textarea>` or `<input type="text">` next to the label for the user to input their greeting.
    - [ ] Task 12.3: Add a "Save Greeting" `<button>`.
    - [ ] Task 12.4: Implement state within the component to hold the current value of the greeting message input.
    - [ ] Task 12.5: Implement an `onSaveGreeting` handler that currently logs the greeting message to the console. (API call in next story).
    - [ ] Task 12.6: (Future task: fetch and display current greeting if already set).
    - [ ] Task 12.7: Write a UI component test for this section, verifying input and button presence.

- [ ] **US013:** As the Configuration Service, I want to save a user's custom greeting text to the UserDB, ensuring it's associated with their account, so it can be retrieved by the call handling logic.
    - [ ] Task 13.1: Modify the `users` table schema: add a column `custom_greeting_message` (TEXT, Nullable). Update migration.
    - [ ] Task 13.2: In the backend, create a new authenticated PUT or POST API endpoint, e.g., `/config/greeting`.
    - [ ] Task 13.3: Request body for `/config/greeting` should expect `{ "greeting_message": "string" }`.
    - [ ] Task 13.4: Endpoint handler should take the `greeting_message` and update the `custom_greeting_message` column in the `users` table for the authenticated user.
    - [ ] Task 13.5: In the frontend `CustomInstructionsPage.js` (or `GreetingSetting.js`), modify `onSaveGreeting` handler to make an API call to `/config/greeting` with the current greeting text.
    - [ ] Task 13.6: Provide user feedback on save (e.g., "Greeting saved successfully" or error message).
    - [ ] Task 13.7: In the backend, create a GET API endpoint e.g. `/config/greeting` to fetch the current greeting for the authenticated user.
    - [ ] Task 13.8: In the frontend, when `CustomInstructionsPage.js` loads, fetch the current greeting using the GET endpoint and populate the input field.
    - [ ] Task 13.9: Write integration tests for both backend `/config/greeting` (PUT and GET) endpoints.
    - [ ] Task 13.10: Write UI integration test to verify saving and loading of the greeting message.

- [ ] **US014:** As a user, within the Configuration Portal, I want a text input field to specify a single phone number as my "Default Call Transfer Number", so Alfred knows where to forward certain calls.
    - [ ] Task 14.1: In `CustomInstructionsPage.js` (or a sub-component `TransferSetting.js`), add a `<label>`: "Default Call Transfer Number:".
    - [ ] Task 14.2: Add an `<input type="tel">` next to the label for the user to input the phone number. Add basic validation for phone number format if possible on frontend.
    - [ ] Task 14.3: Add a "Save Transfer Number" `<button>`.
    - [ ] Task 14.4: Implement state within the component for the transfer number input.
    - [ ] Task 14.5: Implement an `onSaveTransferNumber` handler that currently logs the number to the console.
    - [ ] Task 14.6: Write a UI component test for this section.

- [ ] **US015:** As the Configuration Service, I want to save a user's "Default Call Transfer Number" to the UserDB, so it's available for call transfer actions.
    - [ ] Task 15.1: Modify `users` table schema: add `default_transfer_number` (VARCHAR(20), Nullable). Update migration.
    - [ ] Task 15.2: Backend: Create new authenticated PUT/POST API endpoint, e.g., `/config/transfer-number`.
    - [ ] Task 15.3: Request body: `{ "transfer_number": "string" }`.
    - [ ] Task 15.4: Endpoint handler: Update `default_transfer_number` in `users` table for authenticated user. Add backend validation for phone number format.
    - [ ] Task 15.5: Frontend: Modify `onSaveTransferNumber` to call `/config/transfer-number` API.
    - [ ] Task 15.6: Provide user feedback on save.
    - [ ] Task 15.7: Backend: Create GET API endpoint `/config/transfer-number` to fetch current number.
    - [ ] Task 15.8: Frontend: On load, fetch and populate transfer number input.
    - [ ] Task 15.9: Write integration tests for backend `/config/transfer-number` (PUT and GET) endpoints.
    - [ ] Task 15.10: Write UI integration test for saving and loading transfer number.

- [ ] **US016:** As a user, in the Configuration Portal, I want to create one simple call rule: "IF an incoming call is from [specific phone number] THEN transfer the call to my Default Call Transfer Number", by inputting that specific phone number. (Storing this specific rule structure).
    - [ ] Task 16.1: In `CustomInstructionsPage.js` (or sub-component `VipTransferRule.js`), add UI elements for this rule:
        - [ ] Label: "VIP Transfer Rule: If call from:"
        - [ ] Input field `<input type="tel">` for "[specific phone number]".
        - [ ] Text display: "THEN transfer to Default Transfer Number (set above)".
        - [ ] Button: "Save VIP Rule".
    - [ ] Task 16.2: Implement component state for the VIP caller number input.
    - [ ] Task 16.3: `onSaveVipRule` handler initially logs the VIP number.
    - [ ] Task 16.4: Write a UI component test for this rule section.

- [ ] **US017:** As the Configuration Service, I want to store the user-defined "VIP caller number" and the associated "transfer to default" action in the UserDB, so the Call Logic service can access it.
    - [ ] Task 17.1: This MVP assumes only ONE such VIP rule. Modify `users` table schema: add `vip_caller_number_for_transfer` (VARCHAR(20), Nullable). Update migration. (A more robust solution would be a separate rules table, but this is for a 1pt story on MVP).
    - [ ] Task 17.2: Backend: Create PUT/POST API endpoint, e.g., `/config/vip-rule`. Request: `{ "vip_caller_number": "string" }`.
    - [ ] Task 17.3: Endpoint handler: Update `vip_caller_number_for_transfer` in `users` table for auth'd user.
    - [ ] Task 17.4: Frontend: Modify `onSaveVipRule` to call `/config/vip-rule` API. Provide feedback.
    - [ ] Task 17.5: Backend: Create GET API endpoint `/config/vip-rule` to fetch current VIP number.
    - [ ] Task 17.6: Frontend: On load, fetch and populate VIP number input.
    - [ ] Task 17.7: Write integration tests for backend `/config/vip-rule` (PUT and GET) endpoints.
    - [ ] Task 17.8: Write UI integration test for saving/loading VIP rule.

## Custom RAG Knowledge Base Management (F-CFG-02, F-AI-02 - MVP .txt Upload & Basic Processing)

- [ ] **US018:** As a user, I want an "Upload .txt File" button within the "Knowledge Base" section of the Configuration Portal, so I can initiate the process of adding a document for RAG.
    - [ ] Task 18.1: Create frontend component `RagManagementPage.js`. Add route e.g. `/portal/knowledge`.
    - [ ] Task 18.2: Add heading `<h1>Knowledge Base</h1>`.
    - [ ] Task 18.3: Add a button with text "Upload .txt File".
    - [ ] Task 18.4: Write UI component test for `RagManagementPage.js` verifying button presence.

- [ ] **US019:** As a system, upon user clicking "Upload .txt File", I want to present a standard OS file selection dialog filtered for .txt files, so the user can choose a document from their local system.
    - [ ] Task 19.1: In `RagManagementPage.js`, create a hidden `<input type="file" accept=".txt">` element.
    - [ ] Task 19.2: When "Upload .txt File" button is clicked, programmatically click the hidden file input element.
    - [ ] Task 19.3: Attach an `onChange` event handler to the file input.
    - [ ] Task 19.4: Test this behavior manually in a browser.

- [ ] **US020:** As the RAG Service (backend), I want to receive an uploaded .txt file from a user and store this raw file temporarily, linking it to the user's account, so it’s ready for processing.
    - [ ] Task 20.1: Backend: Create a new authenticated POST API endpoint, e.g., `/rag/upload-txt`. This endpoint must handle `multipart/form-data`.
    - [ ] Task 20.2: Endpoint handler:
        - [ ] Receive the uploaded file.
        - [ ] Generate a unique ID for the document.
        - [ ] Store the raw .txt file content in a designated temporary storage location (e.g., local filesystem path configured per environment, or a cloud storage bucket like S3 if available). The path should incorporate the user ID and document ID to ensure isolation and retrievability.
        - [ ] For MVP, we might store file metadata directly in a new `rag_documents` table.
    - [ ] Task 20.3: Define `rag_documents` table: `document_id` (UUID, PK), `user_id` (UUID, FK to users), `file_name` (VARCHAR), `storage_path` (VARCHAR), `status` (VARCHAR - e.g., 'uploaded', 'processing', 'active', 'error'), `uploaded_at` (TIMESTAMP). Create migration.
    - [ ] Task 20.4: After saving the file, create a record in `rag_documents` with `user_id`, original `file_name`, `storage_path`, and `status='uploaded'`.
    - [ ] Task 20.5: Frontend: In the file input's `onChange` handler (from US019), get the selected file. Create a `FormData` object, append the file, and POST it to `/rag/upload-txt`.
    - [ ] Task 20.6: Write integration test for `/rag/upload-txt` endpoint.

- [ ] **US021:** As a user, after selecting a .txt file for upload, I want to see its filename and an initial status (e.g., "Uploaded, Pending Processing") displayed in a list within the RAG management section, so I get confirmation.
    - [ ] Task 21.1: Backend: The `/rag/upload-txt` endpoint should return the newly created `rag_documents` record metadata (ID, filename, status) on successful upload.
    - [ ] Task 21.2: Frontend `RagManagementPage.js`:
        - [ ] Maintain a state variable `uploadedFilesList` (array).
        - [ ] After successful API response from `/rag/upload-txt`, add the returned document metadata to this list.
        - [ ] Render `uploadedFilesList` as a table or list, showing `file_name` and `status`.
    - [ ] Task 21.3: Backend: Create a GET endpoint `/rag/documents` to list all RAG documents for the authenticated user.
    - [ ] Task 21.4: Frontend: On `RagManagementPage.js` load, call `/rag/documents` and populate `uploadedFilesList`.
    - [ ] Task 21.5: Write UI integration test for file list display after upload and on page load.

- [ ] **US022:** As the RAG Service (backend), for one uploaded .txt file, I want to read its content from storage, split it into text chunks of a predefined maximum character length (e.g. 500 chars), and store these chunks. (Basic chunking for .txt).
    - [ ] Task 22.1: Create a new table `rag_document_chunks`: `chunk_id` (UUID, PK), `document_id` (UUID, FK to rag_documents), `user_id` (UUID, FK to users), `chunk_text` (TEXT), `chunk_order` (INTEGER), `created_at` (TIMESTAMP). Create migration.
    - [ ] Task 22.2: Backend (RAG Service module, potentially an async worker): Create a function `process_document_chunking(document_id)`.
    - [ ] Task 22.3: `process_document_chunking` should:
        - [ ] Fetch the `rag_documents` record by `document_id`. Update its status to 'processing_chunking'.
        - [ ] Read the raw .txt file content from `storage_path`.
        - [ ] Implement text splitting logic (e.g., by paragraphs, sentences, or fixed character count with overlap). For MVP, simple fixed character count (e.g. 500 chars) is fine.
        - [ ] For each chunk, create a record in `rag_document_chunks` table, including `document_id`, `user_id`, `chunk_text`, and `chunk_order`.
        - [ ] After all chunks are stored, update `rag_documents.status` to 'chunked' or 'pending_embedding'.
    - [ ] Task 22.4: Trigger `process_document_chunking` after a new document is uploaded (e.g., via a message queue, or synchronously for MVP if processing is fast for small files, though async is better). For now, it could be an internal call after successful upload and DB record creation in US020, but this will make the upload request longer. (Consider a dummy async trigger for now).
    - [ ] Task 22.5: Write unit tests for the text splitting logic.
    - [ ] Task 22.6: Write integration test for `process_document_chunking` (mocking file read, verify DB writes).

- [ ] **US023:** As the RAG Service (backend), for the text chunks of one processed .txt file, I want to generate vector embeddings using a pre-configured embedding model (e.g. Sentence Transformers `all-MiniLM-L6-v2`) and store these embeddings in the designated vector database (e.g., FAISS index file, or a simple table for MVP if vector DB is too much for 1pt).
    - [ ] Task 23.1: (Decision: For strict 1pt and MVP simplicity without external Vector DB setup, embeddings can be stored in a new column in `rag_document_chunks` if the vector size is manageable and search is simple, or a separate related table. Actual Vector DB is preferred but more setup). Let's assume a simplified storage for this 1pt: add `embedding_vector` (BYTEA or JSONB representation of float array) column to `rag_document_chunks`. Update migration.
    - [ ] Task 23.2: Backend (RAG Service): Create function `generate_embeddings_for_document(document_id)`.
    - [ ] Task 23.3: `generate_embeddings_for_document` should:
        - [ ] Fetch `rag_documents` record. Update status to 'processing_embeddings'.
        - [ ] Fetch all `rag_document_chunks` for that `document_id` where `embedding_vector` is NULL.
        - [ ] For each chunk's `chunk_text`, generate its embedding using a chosen sentence-transformer model (e.g., load `sentence-transformers/all-MiniLM-L6-v2` locally).
        - [ ] Store the resulting float vector (serialized to bytes or JSON) in the `embedding_vector` column for that chunk.
        - [ ] After all chunks are embedded, update `rag_documents.status` to 'active'.
    - [ ] Task 23.4: Trigger `generate_embeddings_for_document` after `process_document_chunking` is complete (e.g., another step in the dummy async flow).
    - [ ] Task 23.5: Write unit tests for generating an embedding for a sample text.
    - [ ] Task 23.6: Write integration test for `generate_embeddings_for_document` (mock model, verify DB writes).
    - [ ] Task 23.7: Ensure the sentence-transformer model is downloaded/available to the backend service.

- [ ] **US024:** As a user, I want the status of my uploaded .txt file to change from "Processing" to "Active" in the RAG management section once chunking and embedding are successfully completed, so I know it's ready for use by Alfred.
    - [ ] Task 24.1: This is a frontend task relying on the backend status updates from US022 and US023.
    - [ ] Task 24.2: The `RagManagementPage.js` already fetches documents and their statuses (from US021). Ensure it correctly displays 'processing_chunking', 'processing_embeddings', and 'active' statuses.
    - [ ] Task 24.3: Consider adding a manual "Refresh Status" button on the `RagManagementPage.js` for MVP, or implement basic polling if full real-time updates (WebSockets) are out of scope for 1pt. For now, assume user refreshes page or re-navigates.
    - [ ] Task 24.4: Write UI test verifying different statuses are displayed correctly based on mocked API responses.

## RAG-Informed Responses (F-AI-03 - MVP Simple Chat Retrieval)

- [ ] **US025:** As Alfred (Chat Backend), when a user sends a message, I want to pass this message as a query to the RAG Service, specifying the user's ID, to find relevant information from their active .txt documents.
    - [ ] Task 25.1: Backend: Create a new authenticated POST API endpoint, e.g., `/chat/send-message`. Request: `{ "message_text": "string" }`.
    - [ ] Task 25.2: In the handler for `/chat/send-message`:
        - [ ] Get the authenticated `user_id`.
        - [ ] Call a new RAG service function, e.g., `find_relevant_chunk(user_id, query_text=message_text)`.
        - [ ] (Logic for what to do with the chunk is in US027).
    - [ ] Task 25.3: Frontend `ChatInterface.js`: Modify the `onSendMessage` prop function (called by `ChatInput.js`) to make an API call to `/chat/send-message` with the user's typed message.
    - [ ] Task 25.4: The response from `/chat/send-message` should be Alfred's reply (which will incorporate RAG results).
    - [ ] Task 25.5: Update `ChatInterface.js` to add Alfred's response from the API to the `messageHistory`.
    - [ ] Task 25.6: Remove the hardcoded Alfred response simulation from US010.

- [ ] **US026:** As the RAG Service, given a user query and user ID, I want to perform a similarity search in the vector database (or simplified storage) against that user's .txt document embeddings and retrieve the single highest-scoring text chunk.
    - [ ] Task 26.1: Backend (RAG Service): Implement the `find_relevant_chunk(user_id, query_text)` function.
    - [ ] Task 26.2: Inside `find_relevant_chunk`:
        - [ ] Generate an embedding for the `query_text` using the same sentence-transformer model as in US023.
        - [ ] Fetch all `rag_document_chunks` (and their `embedding_vector`) for the given `user_id` where the parent document `status` is 'active'.
        - [ ] For each fetched chunk embedding, calculate cosine similarity between the query embedding and the chunk embedding. (Deserialize stored embedding first).
        - [ ] Identify the chunk with the highest similarity score.
        - [ ] If highest score is above a certain threshold (e.g., 0.7), return its `chunk_text`. Otherwise, return `None` or an indicator of no good match.
    - [ ] Task 26.3: Write unit tests for cosine similarity calculation.
    - [ ] Task 26.4: Write integration test for `find_relevant_chunk` with sample data in DB to verify retrieval of the correct chunk.

- [ ] **US027:** As Alfred (Chat Backend), if the RAG service returns a relevant text chunk (from .txt), I want to formulate a simple response like "From your document: '[retrieved text chunk]'" and display it to the user. (No LLM synthesis for this 1-pointer).
    - [ ] Task 27.1: Backend (`/chat/send-message` handler):
        - [ ] After calling `find_relevant_chunk(user_id, message_text)`.
        - [ ] If a `chunk_text` is returned: Alfred's response is `f"From your document: {chunk_text}"`.
        - [ ] (If no chunk is returned, handle in US028).
        - [ ] Return this Alfred response in the API call result.
    - [ ] Task 27.2: Ensure the frontend (US025) correctly displays this response.
    - [ ] Task 27.3: Update integration tests for `/chat/send-message` to cover scenario where RAG finds a chunk.

- [ ] **US028:** As Alfred (Chat Backend), if RAG returns no relevant chunks for a query from .txt, I want to display "I couldn't find information on that in your uploaded document." to the user.
    - [ ] Task 28.1: Backend (`/chat/send-message` handler):
        - [ ] After calling `find_relevant_chunk(user_id, message_text)`.
        - [ ] If `find_relevant_chunk` returns `None` (or no good match): Alfred's response is `"I couldn't find information on that in your uploaded document."`.
        - [ ] Return this Alfred response in the API call result.
    - [ ] Task 28.2: Ensure the frontend (US025) correctly displays this response.
    - [ ] Task 28.3: Update integration tests for `/chat/send-message` to cover scenario where RAG finds no chunk.

## Inbound Call Handling (MVP Core)
*(These tasks will assume a Telephony Provider like Twilio is chosen and an SDK or basic API interaction layer exists. Setting up the entire Telephony Gateway service from scratch is too large for 1pt stories; these focus on specific event handling and logic within that assumed context.)*

- [ ] **US029:** As the Telephony Gateway Service, I want to successfully receive an incoming call event notification (including caller ID and called Alfred number) from the integrated Telephony Provider (e.g., via a webhook).
    - [ ] Task 29.1: Backend (Telephony Gateway module): Define a new public webhook endpoint, e.g., `/telephony/webhook/incoming-call`.
    - [ ] Task 29.2: Configure this webhook URL with the Telephony Provider for when a call comes to an Alfred-assigned number.
    - [ ] Task 29.3: Implement the endpoint handler to parse the request from the Telephony Provider (e.g., Twilio's TwiML request format or Vonage's VXML). Extract `CallerID` (From number) and `CalledID` (To number - the Alfred number).
    - [ ] Task 29.4: For now, log the extracted `CallerID` and `CalledID`.
    - [ ] Task 29.5: The endpoint must respond in the format expected by the Telephony Provider (e.g., TwiML to say something or gather input). For this story, a minimal valid response to acknowledge the call.
    - [ ] Task 29.6: Write a unit test for parsing a sample Telephony Provider webhook payload.

- [ ] **US030:** As the Telephony Gateway Service, upon receiving an incoming call event, I want to send an "answer call" command to the Telephony Provider, so the call connection is established.
    - [ ] Task 30.1: This is usually part of the response to the incoming call webhook.
    - [ ] Task 30.2: Modify the `/telephony/webhook/incoming-call` handler (from US029).
    - [ ] Task 30.3: Instead of just logging, the handler should construct a response that tells the Telephony Provider to "answer" and then proceed (e.g., play a greeting). For Twilio, this would be a TwiML response like `<Response><Say>...</Say></Response>` or `<Response><Play>...</Play></Response>`. The act of responding with such TwiML effectively "answers" the call and dictates next actions.
    - [ ] Task 30.4: (This story just establishes answering. Playing greeting is US031). For now, respond with TwiML that just says a very simple "Connecting".
    - [ ] Task 30.5: Test this by calling an Alfred number and verifying it connects and plays the "Connecting" message.

- [ ] **US031:** As the Call Logic Service, immediately after a call is answered, I want to retrieve the user's configured custom greeting message (from US013) and use a TTS service to play this greeting to the caller. (Assumes basic TTS integration exists).
    - [ ] Task 31.1: Backend (Telephony Webhook Handler / Call Logic Service):
        - [ ] When an incoming call is received (US029/US030), identify the `user_id` associated with the `CalledID` (Alfred number). Query `users` table by `alfred_phone_number`.
        - [ ] Retrieve the user's `custom_greeting_message` from their `users` record. If null, use a default system greeting (e.g., "Hello, you've reached Alfred.").
        - [ ] Modify the TwiML (or equivalent) response to use the `<Say>` verb with the retrieved (or default) greeting message. The TTS is handled by the Telephony Provider based on `<Say>`.
    - [ ] Task 31.2: Write unit test for fetching user and their greeting by phone number.
    - [ ] Task 31.3: Test by calling an Alfred number for a user with a custom greeting set, and one without, to verify correct greeting is played.

- [ ] **US032:** As the Voice AI Service, for an active call, I want to capture the first 5-7 seconds of caller audio after the greeting finishes and send this audio to an STT service to get a text transcription. (Basic STT for initial caller utterance).
    - [ ] Task 32.1: Backend (Telephony Webhook Handler / Call Logic):
        - [ ] After the `<Say>` verb for the greeting, the TwiML response needs to use a verb like `<Gather input="speech" timeout="7" action="/telephony/webhook/handle-speech-input">` (Twilio example). This tells the provider to listen for speech.
        - [ ] Define a new webhook endpoint `/telephony/webhook/handle-speech-input`.
        - [ ] The Telephony Provider will call this new endpoint with the transcribed speech (or if speech was not detected).
        - [ ] In `/telephony/webhook/handle-speech-input` handler, extract the `SpeechResult` (transcribed text) from the payload.
        - [ ] For now, log the `SpeechResult`.
    - [ ] Task 32.2: This assumes STT is provided by the Telephony Provider. If a 3rd party STT is used, TwiML would use `<Record>` and then on recording completion, we'd fetch audio and send to STT API. For 1pt MVP, assume provider's STT via `<Gather>`.
    - [ ] Task 32.3: Test by calling, speaking after greeting, and checking logs for transcription.

- [ ] **US033:** As the NLU Service, for a given short transcribed text from the caller (e.g., "What are your opening hours?"), I want to identify if it contains the keyword "hours" to flag a basic 'query_hours' intent. (Simplest keyword-based NLU).
    - [ ] Task 33.1: Backend (NLU Service module, or within Call Logic): Create a function `get_simple_intent(transcribed_text)`.
    - [ ] Task 33.2: Implement logic in `get_simple_intent`: if `transcribed_text.lower().contains("hours")`, return intent `'query_hours'`. Add another simple keyword, e.g., if "spam" or "stop calling" in text, return `'report_spam'`. Else return `None` or `'unknown_intent'`.
    - [ ] Task 33.3: In `/telephony/webhook/handle-speech-input` handler (from US032), after getting `SpeechResult`, call `get_simple_intent(SpeechResult)`.
    - [ ] Task 33.4: Log the identified intent.
    - [ ] Task 33.5: Write unit tests for `get_simple_intent` with various sample texts.

- [ ] **US034:** As an administrator, I want a basic internal tool or script to add a phone number to a global "SpamNumbers" blocklist table in the database.
    - [ ] Task 34.1: Create `spam_numbers` table: `phone_number` (VARCHAR(20), PK), `added_at` (TIMESTAMP). Create migration.
    - [ ] Task 34.2: Write a simple command-line script (e.g., Python click/argparse) that takes a phone number as an argument and inserts it into `spam_numbers` table.
    - [ ] Task 34.3: Add basic error handling (e.g., number already exists).
    - [ ] Task 34.4: Document how to run this script. (No UI for this 1pt task).

- [ ] **US035:** As the Call Logic Service, upon receiving an incoming call's caller ID, I want to query the "SpamNumbers" blocklist.
    - [ ] Task 35.1: Backend (Telephony Webhook Handler for `/telephony/webhook/incoming-call`):
        - [ ] Before answering or playing greeting, get the `CallerID`.
        - [ ] Create a function `is_spam_number(caller_id)` that queries `spam_numbers` table. Returns true if found, false otherwise.
        - [ ] Call `is_spam_number(CallerID)`.
    - [ ] Task 35.2: Write unit test for `is_spam_number`.

- [ ] **US036:** As the Call Logic Service, if an incoming caller's ID is found on the "SpamNumbers" blocklist and the user has spam blocking enabled (default MVP behavior), I want to instruct the Telephony Gateway to immediately terminate the call (hangup/reject).
    - [ ] Task 36.1: Backend (Telephony Webhook Handler for `/telephony/webhook/incoming-call`):
        - [ ] If `is_spam_number(CallerID)` returns true:
        - [ ] Respond with TwiML (or equivalent) to `<Reject reason="busy"/>` or just `<Hangup/>`. This prevents the call from proceeding to the user's configured greeting.
    - [ ] Task 36.2: If not spam, proceed with normal flow (US031).
    - [ ] Task 36.3: Add a number to spam list using script from US034. Test by calling from that number; verify it's rejected/hung up immediately.

- [ ] **US037:** As the Call Logic Service, if the identified NLU intent (from US033) is 'query_hours' and the user has an active RAG document, I want to submit "What are the business hours?" to the RAG service for that user.
    - [ ] Task 37.1: Backend (`/telephony/webhook/handle-speech-input` handler):
        - [ ] After identifying intent as `'query_hours'`:
        - [ ] Get `user_id` associated with the current call (needs to be passed through webhook states or looked up again by Alfred number).
        - [ ] Call RAG service function `find_relevant_chunk(user_id, "What are the business hours?")` (from US026).
        - [ ] (Response handling in US038). For now, log the result from `find_relevant_chunk`.

- [ ] **US038:** As the Call Logic Service, upon receiving a single relevant text chunk from the RAG service (in response to a 'query_hours' request), I want to use TTS to speak this text chunk to the caller and then terminate the call. (Simple RAG answer delivery).
    - [ ] Task 38.1: Backend (`/telephony/webhook/handle-speech-input` handler):
        - [ ] If `find_relevant_chunk` returns a `chunk_text`:
        - [ ] Respond with TwiML `<Response><Say>{chunk_text}</Say><Hangup/></Response>`.
        - [ ] If no chunk text (or intent was not 'query_hours'), for now, respond with TwiML `<Response><Say>Sorry, I can't help with that right now.</Say><Hangup/></Response>`. (More advanced fallback in later stories).
    - [ ] Task 38.2: Test by calling, asking about hours (ensure RAG doc has hours info), verify Alfred speaks RAG content and hangs up.

- [ ] **US039:** As the Call Logic Service, if a user's custom rule "IF caller is [VIP number] THEN transfer" (from US017) is matched for an incoming call, I want to retrieve the user's "Default Call Transfer Number" (from US015).
    - [ ] Task 39.1: Backend (Telephony Webhook Handler for `/telephony/webhook/incoming-call`):
        - [ ] After identifying `user_id` from `CalledID` (Alfred number).
        - [ ] Fetch `vip_caller_number_for_transfer` and `default_transfer_number` from the user's record.
        - [ ] Compare `CallerID` with `vip_caller_number_for_transfer`.
        - [ ] If they match AND `default_transfer_number` is set, then this rule is active.
    - [ ] Task 39.2: This check should happen before spam check or standard greeting for VIPs.

- [ ] **US040:** As the Call Logic Service, upon matching a transfer rule and retrieving the destination number, I want to instruct the Telephony Gateway to initiate a call transfer to that destination number.
    - [ ] Task 40.1: Backend (`/telephony/webhook/incoming-call` handler):
        - [ ] If VIP rule is active (from US039):
        - [ ] Respond with TwiML `<Response><Dial>{default_transfer_number}</Dial></Response>`. This instructs Telephony Provider to transfer the call.
    - [ ] Task 40.2: Test by setting a VIP number and transfer number for a user. Call from VIP number, verify call is transferred.

- [ ] **US041:** As a user, in the Configuration Portal, I want to create a simple call rule: "IF an incoming call is from an UNKNOWN number (no Caller ID / withheld) THEN take a message".
    - [ ] Task 41.1: Modify `users` table schema: add `take_message_for_unknown_caller` (BOOLEAN, Default TRUE). Update migration.
    - [ ] Task 41.2: Frontend (`CustomInstructionsPage.js`): Add a checkbox "Take message if caller ID is Unknown/Withheld".
    - [ ] Task 41.3: State manage this checkbox. On save, call a new backend API endpoint.
    - [ ] Task 41.4: Backend: Create PUT/GET API endpoint `/config/rule-unknown-caller-message` to set/get this boolean flag for the user.
    - [ ] Task 41.5: Write tests for API and UI interaction.

- [ ] **US042:** As the Call Logic Service, if the "take message for UNKNOWN caller" rule is matched, I want to use TTS to play the prompt "Your call is important. Please leave your name, number, and a short message after the tone."
    - [ ] Task 42.1: Backend (`/telephony/webhook/incoming-call` handler):
        - [ ] Check if `CallerID` is empty/null/withheld.
        - [ ] If so, and user's `take_message_for_unknown_caller` is true:
        - [ ] The TwiML response should be `<Response><Say>Your call is important. Please leave your name, number, and a short message after the tone.</Say>{Further_Record_Action}</Response>`. (Recording in next story).
    - [ ] Task 42.2: This logic path should be chosen if no VIP rule matched.

- [ ] **US043:** As the Telephony Gateway, after the "leave message" prompt is played, I want to start recording the call's audio stream from the caller.
    - [ ] Task 43.1: Backend (`/telephony/webhook/incoming-call` handler, continuing from US042):
        - [ ] Append TwiML `<Record action="/telephony/webhook/handle-voicemail-recording" transcribe="true" transcribeCallback="/telephony/webhook/handle-transcription" maxLength="60" />` after the `<Say>` prompt.
        - [ ] The `action` URL is where the provider will POST after recording finishes. `transcribe` and `transcribeCallback` are for provider-based transcription (MVP bonus).
    - [ ] Task 43.2: Define new webhook endpoint `/telephony/webhook/handle-voicemail-recording`. For now, it logs the payload which includes `RecordingUrl`.
    - [ ] Task 43.3: Define new webhook endpoint `/telephony/webhook/handle-transcription`. For now, it logs the payload which includes `TranscriptionText`.

- [ ] **US044:** As the Telephony Gateway, I want to automatically stop the audio recording if 60 seconds of continuous recording is reached, or if the caller hangs up.
    - [ ] Task 44.1: This is handled by the `maxLength="60"` attribute in `<Record>` TwiML (US043).
    - [ ] Task 44.2: If caller hangs up during recording, Telephony Provider usually still calls the `action` URL. Verify this behavior.

- [ ] **US045:** As the Call Logic Service, I want to ensure the saved audio recording (voicemail) file is stored (or its URL from provider) and linked to the corresponding call's log entry ID.
    - [ ] Task 45.1: Create `voicemails` table: `voicemail_id` (UUID, PK), `call_log_id` (UUID, FK - tbd by call logging story), `user_id` (UUID, FK), `recording_url` (TEXT), `duration_seconds` (INTEGER), `transcription_text` (TEXT, Nullable), `received_at` (TIMESTAMP). Migration.
    - [ ] Task 45.2: Backend (`/telephony/webhook/handle-voicemail-recording` handler):
        - [ ] Extract `RecordingUrl`, `RecordingDuration` from payload.
        - [ ] Get `user_id` (passed via session or lookup).
        - [ ] Create an entry in `voicemails` table. (Need `call_log_id` - this implies call logging story US051 needs some pre-work or this story needs to also create a basic call log entry if none exists for this call SID). Assume call SID is available.
    - [ ] Task 45.3: Backend (`/telephony/webhook/handle-transcription` handler):
        - [ ] Extract `TranscriptionText` and `RecordingSid` (to find the voicemail record).
        - [ ] Update the corresponding `voicemails` record with the transcription.

- [ ] **US046:** As Alfred's Notification Service, after a voicemail is successfully recorded and saved, I want to send a simple text notification "New voicemail received" to the user's primary chat interface.
    - [ ] Task 46.1: This requires a way for the backend (after saving voicemail in US045) to push a message to the user's chat. If WebSockets are not yet in place for chat, this could be:
        - [ ] An internal "system message" stored in the chat message DB, that the chat interface polls for or loads on next view.
        - [ ] Or, for true 1pt, this might be simplified to an email notification if chat push is too complex. PRD implies chat.
    - [ ] Task 46.2: (Assuming chat storage, not real-time push for this 1pt) In backend, after `voicemails` record is created:
        - [ ] Create a new `chat_messages` record: `sender='alfred_system'`, `recipient_user_id=user_id`, `message_text='New voicemail received. Check your call log.'`, `timestamp=NOW()`. (Chat message table needs to exist).
    - [ ] Task 46.3: The main chat interface (US008) needs to be able to fetch and display these system messages too.

## Outbound Call Handling (MVP Basics)

- [ ] **US047:** As a user, I want to type the command "Alfred, call [phone_number]" (e.g., "Alfred, call 123-456-7890") into the chat interface, so I can instruct Alfred to make an outbound call.
    - [ ] Task 47.1: Frontend `ChatInput.js`: In `handleSendMessage`, parse the message text.
    - [ ] Task 47.2: If message matches regex `^Alfred, call (\+?[0-9\s\-]+)$`, extract phone number.
    - [ ] Task 47.3: Instead of sending to `/chat/send-message`, call a new API endpoint for this command.
    - [ ] Task 47.4: Backend: Create POST API endpoint `/actions/outbound-call`. Request: `{ "phone_number": "string" }`.
    - [ ] Task 47.5: (Actual call placement in US048). For now, this endpoint logs "Attempting to call [phone_number]" and returns success.
    - [ ] Task 47.6: Frontend: Display "Alfred is attempting to call [phone_number]..." in chat.

- [ ] **US048:** As the Orchestrator service, upon parsing a valid "Alfred, call [phone_number]" command from a user, I want to instruct the Telephony Gateway to initiate an outbound PSTN call from the user's Alfred number to the target number.
    - [ ] Task 48.1: Backend (`/actions/outbound-call` handler):
        - [ ] Get authenticated `user_id`. Fetch user's `alfred_phone_number`.
        - [ ] Use Telephony Provider's API to initiate an outbound call: `From = user.alfred_phone_number`, `To = target_phone_number`.
        - [ ] Specify a webhook URL (e.g., `/telephony/webhook/outbound-call-status`) for call progress events.
    - [ ] Task 48.2: Define `/telephony/webhook/outbound-call-status` to log events (e.g., ringing, answered, completed).
    - [ ] Task 48.3: Test by using the chat command, verify call is placed.

- [ ] **US049:** As a user, I want to be able to type "Alfred, call [phone_number] and say: [short message]" in the chat, so Alfred delivers that short message when the call is answered. (Extending command).
    - [ ] Task 49.1: Frontend `ChatInput.js`: Update regex to `^Alfred, call (\+?[0-9\s\-]+) and say: (.*?)$`. Extract phone number and message.
    - [ ] Task 49.2: Backend (`/actions/outbound-call`): Update request model to optionally include `{ "message_to_say": "string" }`.
    - [ ] Task 49.3: Store `message_to_say` (e.g., in a temporary call context DB or pass through provider's custom parameters) associated with the Call SID.

- [ ] **US050:** As the Call Logic Service, for an outbound call initiated with a "say: [short message]", once the Telephony Provider indicates the call is answered by the remote party, I want to use TTS to play the [short message] and then instruct the Telephony Gateway to hang up the call.
    - [ ] Task 50.1: Backend (`/telephony/webhook/outbound-call-status` handler):
        - [ ] When call status is 'answered':
        - [ ] Retrieve the `message_to_say` associated with this Call SID (from US049).
        - [ ] If message exists, respond to the webhook with TwiML: `<Response><Say>{message_to_say}</Say><Hangup/></Response>`.
        - [ ] If no message, just `<Response><Hangup/></Response>` (or allow conversation - but MVP says simple message).
    - [ ] Task 50.2: Test by using chat command with "and say:", verify message is spoken on answer.

## General Platform Features (MVP Logging & Basic Outcomes)

- [ ] **US051:** As the system (Call Logic Service), for every answered inbound call, I want to create a basic call log entry in the CallLogDB containing: timestamp, caller ID, called Alfred number, call direction (inbound), and call duration (once ended).
    - [ ] Task 51.1: Create `call_logs` table: `call_log_id` (UUID, PK), `user_id` (UUID, FK), `call_sid` (VARCHAR, Index - from Telephony Provider), `direction` ('inbound'/'outbound'), `caller_number` (VARCHAR), `alfred_number` (VARCHAR), `destination_number` (VARCHAR, for outbound), `start_time` (TIMESTAMP), `end_time` (TIMESTAMP, Nullable), `duration_seconds` (INTEGER, Nullable), `status` (VARCHAR - e.g. 'answered', 'completed', 'failed', 'busy', 'no-answer', 'spam-rejected'), `voicemail_id` (UUID, FK, Nullable). Migration.
    - [ ] Task 51.2: Backend (`/telephony/webhook/incoming-call`): When call starts, create a `call_logs` entry with `direction='inbound'`, `caller_number`, `alfred_number`, `start_time`, `status='initiated'`, `call_sid`.
    - [ ] Task 51.3: Backend (Telephony webhook for call completion/status): Update the `call_logs` entry (found by `call_sid`) with `end_time`, `duration_seconds`, and final `status`.

- [ ] **US052:** As the system (Orchestrator/Call Logic), for every user-initiated outbound call, I want to create a basic call log entry in CallLogDB containing: timestamp, number called, user's Alfred number, call direction (outbound), initial status ('initiated'), and final duration/status (once ended).
    - [ ] Task 52.1: Backend (`/actions/outbound-call` handler from US048): When initiating call, create `call_logs` entry with `direction='outbound'`, `alfred_number` (from), `destination_number` (to), `start_time`, `status='initiated'`, `call_sid`.
    - [ ] Task 52.2: Backend (`/telephony/webhook/outbound-call-status` handler): Update this `call_logs` entry with `end_time`, `duration_seconds`, final `status` on call completion.

- [ ] **US053:** As Alfred's chat interface, when an outbound call is initiated by the user's command, I want to display an immediate status update like "Calling [phone_number]..." in the user's chat.
    - [ ] Task 53.1: Frontend `ChatInput.js` / `ChatInterface.js`: When the outbound call command is parsed and API is called (US047), add a local message to `messageHistory`: `{ sender: 'alfred_status', text: "Calling [phone_number]..."}`.
    - [ ] Task 53.2: This is a client-side immediate feedback; actual call status might come later if we implement real-time updates.

- [ ] **US054:** As Alfred's chat interface, after an inbound call where a voicemail was successfully taken, I want to display a summary message like "Voicemail received from [CallerID if available, else 'Unknown Caller']" in the chat.
    - [ ] Task 54.1: This is covered by the notification system message in US046. "New voicemail received" is sufficient for 1pt. Adding CallerID here makes that system message creation slightly more complex but doable.
    - [ ] Task 54.2: Modify US046: when creating system chat message for voicemail, include callerID if available: `message_text = f"New voicemail received from {caller_id_or_unknown}. Check your call log."`.

- [ ] **US055:** As a user, I want a "Call History" section in the web interface (portal or chat) that displays a chronological list of my last 5 call log entries, showing at least: date/time, other party's number, and direction (in/out).
    - [ ] Task 55.1: Frontend: Create `CallHistoryPage.js` component. Route e.g. `/portal/call-history`.
    - [ ] Task 55.2: Backend: Create GET API endpoint `/call-logs?limit=5&offset=0` to fetch authenticated user's call logs, ordered by `start_time` DESC.
    - [ ] Task 55.3: `CallHistoryPage.js`: Fetch data from `/call-logs` on mount.
    - [ ] Task 55.4: Display data in a table/list: `Date/Time` (formatted `start_time`), `Direction` ('To:' or 'From:'), `Other Party Number` (`destination_number` for outbound, `caller_number` for inbound).
    - [ ] Task 55.5: Write UI tests.

- [ ] **US056:** As a user, in my "Call History", if a call log entry corresponds to a taken voicemail (i.e., `voicemail_id` is not NULL), I want to see a clear visual indicator (e.g., a voicemail icon).
    - [ ] Task 56.1: Backend (`/call-logs` endpoint): Ensure `voicemail_id` is returned in the call log data if present.
    - [ ] Task 56.2: Frontend (`CallHistoryPage.js`): When rendering each call log item, if `voicemail_id` is present, display an icon (e.g., a simple Unicode character 🎙️ or an SVG icon).
    - [ ] Task 56.3: Update UI tests.

- [ ] **US057:** As a user, when I click on a call log entry that has a voicemail indicator, I want a simple audio player to appear and allow me to play the recorded audio message for that call.
    - [ ] Task 57.1: Backend: Need an endpoint to get voicemail details, specifically `recording_url`, e.g., GET `/voicemails/{voicemail_id}`. (This might be part of `/call-logs/{call_log_id}/voicemail` as well). Assume for now that `recording_url` is directly available or fetchable if `voicemail_id` is known. If `recording_url` points to Telephony Provider, ensure it's accessible by the client. If self-hosted, need a streaming endpoint. For MVP, assume `recording_url` is directly playable by HTML5 audio.
    - [ ] Task 57.2: Frontend (`CallHistoryPage.js`):
        - [ ] Make the voicemail icon clickable.
        - [ ] On click, if there isn't already an audio player visible for this item, show one.
        - [ ] Use HTML5 `<audio controls>` element. Set its `src` to the `recording_url` associated with that voicemail. (Fetch this URL if not already part of call log data via the `voicemail_id`).
        - [ ] For simplicity, one audio player shown at a time, or inline with each item.
    - [ ] Task 57.3: Update UI tests for audio player display and `src` attribute setting.
