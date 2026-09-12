# Salesforce Bulk File Uploader
## Technical Documentation

**Version:** 1.0.0  
**Stack:** Python, FastAPI, JavaScript, HTML, CSS, Salesforce REST API  
**Deployment:** Render  
**Purpose:** Bulk upload files to Salesforce and optionally relate each file to a Salesforce record using filename-based matching.

---

## 1. Overview

The application is a standalone web application consisting of:

- A browser-based frontend built with HTML, CSS, and vanilla JavaScript.
- A Python FastAPI backend.
- Salesforce OAuth 2.0 authentication using the Client Credentials Flow.
- Salesforce REST API integration for `ContentVersion` and `ContentDocumentLink`.
- Filename-to-record matching using a configurable Salesforce object and field.
- Per-file success/failure reporting.

The application intentionally keeps the Salesforce access token on the backend. The browser receives only the authentication result and Salesforce instance URL, not the access token.

### High-Level Architecture

```text
Browser
  |
  | HTTP / JSON / multipart-form-data
  v
FastAPI Backend
  |
  +-- Authentication
  |      |
  |      +-- Salesforce OAuth
  |
  +-- Session
  |
  +-- File Processing
  |      |
  |      +-- Record Matching
  |      +-- ContentVersion creation
  |      +-- ContentDocumentLink creation
  |
  v
Salesforce REST API
```

---

# 2. Project Structure

```text
UploadInBulk/
│
├── Backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── login.py
│       ├── session.py
│       ├── bulk_upload.py
│       └── salesforce_files.py
│
├── FrontEnd/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── requirements.txt
└── README.md
```

## 2.1 Backend Responsibilities

| File | Responsibility |
|---|---|
| `main.py` | FastAPI application and HTTP endpoints |
| `login.py` | Salesforce OAuth authentication |
| `session.py` | In-memory Salesforce session storage |
| `bulk_upload.py` | File-processing orchestration |
| `salesforce_files.py` | Salesforce REST API operations |

## 2.2 Frontend Responsibilities

| File | Responsibility |
|---|---|
| `index.html` | Application structure and UI |
| `app.js` | State, events, API calls, uploads, result rendering |
| `style.css` | UI styling |

---

# 3. Technology Stack

## Backend

- Python 3.x
- FastAPI
- Uvicorn
- Requests
- Pydantic
- Python Multipart support

## Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Browser File API
- Browser Fetch API
- `FormData`

## External System

- Salesforce REST API
- Salesforce OAuth 2.0 Client Credentials Flow

---

# 4. Python Dependencies

`requirements.txt`:

```text
fastapi
uvicorn[standard]
requests
python-multipart
pydantic
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Python Standard Library Modules

The application also uses standard-library modules such as:

```python
pathlib
typing
base64
urllib.parse
```

These do not need to be added to `requirements.txt`.

---

# 5. Application Startup

The FastAPI application is defined in:

```text
Backend/app/main.py
```

The application object is:

```python
app = FastAPI(
    title="Salesforce Bulk File Uploader",
    version="1.0.0"
)
```

The application is started with Uvicorn.

## Local Development

From the repository root:

```bash
uvicorn Backend.app.main:app --reload
```

The application is then available at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Production

```bash
uvicorn Backend.app.main:app --host 0.0.0.0 --port $PORT
```

`$PORT` is supplied by the hosting platform.

---

# 6. FastAPI Application Structure

`main.py` exposes the HTTP API.

The main endpoints are:

```text
GET  /api/health
POST /api/auth/login
POST /api/files/upload
```

The frontend is served as static files after the API routes are registered.

```python
app.mount(
    "/",
    StaticFiles(
        directory=str(FRONTEND_DIR),
        html=True
    ),
    name="frontend"
)
```

## Important Routing Rule

The static frontend mount must be declared **after** API routes.

Correct:

```text
/api/health
/api/auth/login
/api/files/upload
/
```

If `/` is mounted before the API routes, the static application can intercept requests intended for the API. This can cause errors such as:

```text
405 Method Not Allowed
```

---

# 7. Frontend Serving

The backend determines the project root:

```python
BASE_DIR = Path(__file__).resolve().parents[2]
```

Then:

```python
FRONTEND_DIR = BASE_DIR / "FrontEnd"
```

This results in:

```text
UploadInBulk/
    FrontEnd/
```

being used as the static frontend directory.

The frontend contains:

```text
index.html
app.js
style.css
```

---

# 8. Authentication Architecture

Authentication uses the Salesforce OAuth 2.0 Client Credentials Flow.

The user supplies:

```text
Salesforce URL
Client ID
Client Secret
```

The browser sends those values to:

```http
POST /api/auth/login
```

The backend sends a request to:

```text
{salesforce_url}/services/oauth2/token
```

with:

```text
grant_type=client_credentials
client_id=<client id>
client_secret=<client secret>
```

Salesforce returns:

```json
{
  "access_token": "...",
  "instance_url": "https://example.my.salesforce.com"
}
```

The backend stores these values in the server-side session.

---

# 9. `login.py`

The authentication function is:

```python
def get_access_token_info(
    login_url: str,
    client_id: str,
    client_secret: str
):
```

The function:

1. Constructs the OAuth token URL.
2. Sends a POST request to Salesforce.
3. Validates the HTTP response.
4. Parses JSON.
5. Verifies that an access token exists.
6. Verifies that an instance URL exists.
7. Returns the token response.

Example:

```python
response = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    },
    timeout=30
)
```

The `requests` library is used for outbound HTTP communication.

---

# 10. Pydantic Request Models

The login API uses a Pydantic model:

```python
class SalesforceLoginRequest(BaseModel):
    salesforce_url: str
    client_id: str
    client_secret: str
```

This defines the expected JSON structure.

Example request:

```json
{
  "salesforce_url": "https://login.salesforce.com",
  "client_id": "CLIENT_ID",
  "client_secret": "CLIENT_SECRET"
}
```

FastAPI validates the incoming request before executing the endpoint.

---

# 11. In-Memory Session

`session.py` contains:

```python
salesforce_session = {
    "access_token": None,
    "instance_url": None
}
```

After successful authentication:

```python
set_salesforce_session(
    access_token=token_data["access_token"],
    instance_url=token_data["instance_url"]
)
```

Later, the upload endpoint retrieves the session:

```python
session = get_salesforce_session()
```

### Current Limitation

This session is process-local.

If the FastAPI process restarts:

```text
FastAPI restart
    ↓
Python process recreated
    ↓
salesforce_session recreated
    ↓
access token lost
```

This is acceptable for a simple single-user/internal utility.

For a multi-user production system, the session model should be replaced with per-user authentication/session storage.

---

# 12. Login Endpoint

The endpoint:

```python
@app.post("/api/auth/login")
def login(request: SalesforceLoginRequest):
```

performs:

```text
Browser
   |
   | Salesforce credentials
   v
FastAPI
   |
   | OAuth request
   v
Salesforce
   |
   | access token
   v
FastAPI session
```

Successful response:

```json
{
  "success": true,
  "message": "Successfully connected to Salesforce.",
  "instance_url": "https://example.my.salesforce.com"
}
```

The access token is intentionally not returned to the browser.

---

# 13. Frontend Wizard

The frontend is organized into three logical steps.

## Step 1 — Salesforce Connection

User provides:

- Salesforce URL
- Client ID
- Client Secret

After successful authentication, Step 2 is displayed.

## Step 2 — File Relationship

User can optionally configure:

- Salesforce object API name
- Matching field API name
- ContentDocumentLink visibility

Example:

```text
Object:
Product2

Matching Field:
ProductCode

Visibility:
AllUsers
```

If no object is provided, files are uploaded without a Salesforce record relationship.

## Step 3 — File Selection / Upload

The user selects files and submits them.

The frontend sends all selected files and relationship configuration to:

```text
POST /api/files/upload
```

---

# 14. JavaScript Application State

The frontend maintains state similar to:

```javascript
state = {
    files: [],
    relation: {
        object: null,
        matchingField: null,
        visibility: null
    }
};
```

The state represents the current wizard configuration.

Example:

```javascript
state.relation = {
    object: "Product2",
    matchingField: "ProductCode",
    visibility: "AllUsers"
};
```

---

# 15. JavaScript DOM Manipulation

JavaScript obtains HTML elements through the DOM.

Example:

```javascript
const uploadButton =
    document.getElementById("uploadButton");
```

The DOM represents the HTML document as objects that JavaScript can read and modify.

For example:

```javascript
resultUploaded.textContent = data.uploaded;
```

updates the displayed upload count.

---

# 16. JavaScript Event Handling

The upload button uses an event listener:

```javascript
uploadButton.addEventListener(
    "click",
    handleUpload
);
```

This creates an event-driven flow:

```text
User clicks button
       ↓
click event
       ↓
handleUpload()
```

Other common browser events include:

```text
click
change
input
submit
load
keydown
```

---

# 17. Browser File API

When files are selected, JavaScript receives browser `File` objects.

A file provides properties such as:

```javascript
file.name
file.size
file.type
```

Example:

```text
name = RES-101.pdf
type = application/pdf
size = 17825792
```

The browser does not automatically send the file to Salesforce. JavaScript explicitly constructs an HTTP request.

---

# 18. FormData

The application uses:

```javascript
const formData = new FormData();
```

Files are appended:

```javascript
state.files.forEach(file => {
    formData.append("files", file);
});
```

If relationship configuration is supplied:

```javascript
formData.append(
    "object_name",
    state.relation.object
);

formData.append(
    "field_name",
    state.relation.matchingField
);

formData.append(
    "visibility",
    state.relation.visibility
);
```

The resulting multipart request conceptually contains:

```text
files = RES-101.pdf
files = RES-102.pdf
files = RES-103.pdf
object_name = Product2
field_name = ProductCode
visibility = AllUsers
```

---

# 19. Fetch API

The browser sends the request using the native Fetch API:

```javascript
const response = await fetch(
    "/api/files/upload",
    {
        method: "POST",
        body: formData
    }
);
```

No additional HTTP library such as Axios is required.

The flow is:

```text
JavaScript
    |
    | fetch()
    v
HTTP POST
    |
    v
FastAPI
```

---

# 20. JavaScript Async/Await

The upload function is asynchronous:

```javascript
async function handleUpload() {
```

and uses:

```javascript
await fetch(...)
```

`fetch()` returns a Promise.

`await` allows the code to wait for the network operation before continuing.

The general pattern is:

```javascript
async function example() {
    const response = await fetch(url);
    const data = await response.json();
}
```

This is the standard pattern for browser API communication.

---

# 21. Upload API

The upload endpoint is:

```python
@app.post("/api/files/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    object_name: Optional[str] = Form(None),
    field_name: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
):
```

FastAPI automatically parses:

```text
multipart/form-data
```

into:

```text
files
object_name
field_name
visibility
```

---

# 22. Request Validation

The endpoint validates relationship configuration.

If an object is supplied but no matching field exists:

```text
object_name = Product2
field_name = null
```

the request fails.

If an object is supplied, visibility must be one of:

```text
AllUsers
InternalUsers
SharedUsers
```

If no object is supplied:

```text
object_name = null
```

the matching field and visibility are ignored.

---

# 23. Upload Processing Architecture

The upload endpoint delegates the business logic to:

```python
process_files(...)
```

from:

```text
bulk_upload.py
```

This separation keeps `main.py` focused on HTTP/API responsibilities.

The flow is:

```text
main.py
   ↓
process_files()
   ↓
salesforce_files.py
```

---

# 24. `bulk_upload.py`

`process_files()` coordinates the complete file-processing workflow.

The function receives:

```python
files
instance_url
access_token
object_name
field_name
visibility
```

It then determines whether record matching is required.

---

# 25. Two Upload Modes

There are two supported modes.

## Mode A — No Salesforce Relationship

If:

```text
object_name = None
```

the flow is:

```text
File
 ↓
ContentVersion
 ↓
Complete
```

No `ContentDocumentLink` is created.

## Mode B — Salesforce Relationship

If:

```text
object_name = Product2
field_name = ProductCode
```

the flow is:

```text
File
 ↓
Extract filename stem
 ↓
Find Salesforce record
 ↓
ContentVersion
 ↓
ContentDocumentLink
 ↓
Complete
```

---

# 26. Filename Matching

For a file:

```text
RES-101.pdf
```

Python uses:

```python
filename_key = Path(filename).stem
```

which produces:

```text
RES-101
```

The filename extension is removed.

---

# 27. Contains Matching

The matching requirement is **contains**, not exact equality.

For:

```text
RES-101.pdf
```

the application searches for values conceptually equivalent to:

```sql
ProductCode LIKE '%RES-101%'
```

Therefore:

```text
RES-101
```

can match values such as:

```text
RES-101
ABC-RES-101
RES-101-TEST
```

depending on the Salesforce data.

---

# 28. Bulk Salesforce Query Strategy

The application does not query Salesforce separately for every file.

Avoid:

```text
File 1 → Salesforce query
File 2 → Salesforce query
File 3 → Salesforce query
...
File 10000 → Salesforce query
```

Instead:

```text
10000 files
    ↓
extract keys
    ↓
batch SOQL conditions
    ↓
Salesforce
    ↓
candidate records
    ↓
local Python matching
```

This reduces the number of network round trips.

---

# 29. Local Matching

After Salesforce candidate records are retrieved, Python performs local matching.

Conceptually:

```python
for filename_key in file_keys:
    matches[filename_key] = []

    for record in records:
        field_value = record.get(field_name)

        if field_value is None:
            continue

        if filename_key in str(field_value):
            matches[filename_key].append(record["Id"])
```

This is an O(F × R) local comparison where:

- `F` = number of file keys
- `R` = number of candidate Salesforce records

For the intended utility, this is acceptable when the Salesforce candidate set is controlled.

The main performance concern is avoiding excessive Salesforce API requests.

---

# 30. Match Outcomes

Every file must result in one of these matching states.

## No Match

Example:

```text
RES-999.pdf
```

No Salesforce record contains:

```text
RES-999
```

The file is not uploaded.

Response:

```json
{
  "filename": "RES-999.pdf",
  "status": "failed",
  "reason": "No Product2 record found..."
}
```

## Single Match

Example:

```text
RES-101.pdf
```

matches:

```text
Product2.Id = 01t...
```

The file is uploaded and linked.

## Multiple Matches

If:

```text
RES-101
```

matches multiple records, the file is not uploaded.

This prevents accidental linking.

Example:

```json
{
  "filename": "RES-101.pdf",
  "status": "failed",
  "reason": "Multiple Product2 records matched..."
}
```

---

# 31. Why Unmatched Files Are Not Uploaded

Uploading first and matching later could create orphaned Salesforce files.

The safer workflow is:

```text
Match first
   ↓
Confirm exactly one record
   ↓
Upload ContentVersion
   ↓
Create ContentDocumentLink
```

This minimizes orphaned files.

---

# 32. Salesforce ContentVersion

Salesforce Files are created using:

```text
ContentVersion
```

The REST endpoint is:

```text
/services/data/v67.0/sobjects/ContentVersion
```

The request contains:

```json
{
  "Title": "RES-101",
  "PathOnClient": "RES-101.pdf",
  "VersionData": "<base64 data>"
}
```

---

# 33. Binary File to Base64

The uploaded file is read as bytes:

```python
file_bytes = await file.read()
```

Base64 encoding is then used:

```python
base64.b64encode(file_bytes).decode("ascii")
```

The transformation is:

```text
PDF binary bytes
      ↓
Base64 text
      ↓
JSON request
      ↓
Salesforce
```

Base64 increases the transmitted payload size, so this approach is simple but not optimal for very large-scale uploads.

---

# 34. ContentDocumentId

Creating `ContentVersion` initially returns the ContentVersion ID:

```text
068...
```

The application then queries:

```sql
SELECT ContentDocumentId
FROM ContentVersion
WHERE Id = '068...'
```

to retrieve:

```text
ContentDocumentId
```

The ContentDocument represents the Salesforce File.

---

# 35. ContentDocumentLink

If a Salesforce relationship is configured, the application creates a `ContentDocumentLink`.

Payload:

```json
{
  "ContentDocumentId": "069...",
  "LinkedEntityId": "01t...",
  "Visibility": "AllUsers"
}
```

The relationship becomes:

```text
ContentDocument
       |
       | ContentDocumentLink
       |
       v
Salesforce Record
```

---

# 36. Visibility

Supported visibility values:

```text
AllUsers
InternalUsers
SharedUsers
```

The selected value is passed directly to Salesforce when creating `ContentDocumentLink`.

---

# 37. Per-File Result Model

Successful linked file:

```json
{
  "filename": "RES-101.pdf",
  "status": "uploaded",
  "content_document_id": "069...",
  "record_id": "01t...",
  "content_document_link_id": "06A..."
}
```

Successful unlinked file:

```json
{
  "filename": "RES-101.pdf",
  "status": "uploaded",
  "content_document_id": "069..."
}
```

Failed file:

```json
{
  "filename": "RES-999.pdf",
  "status": "failed",
  "reason": "No Product2 record found..."
}
```

---

# 38. Upload API Response

The API returns an aggregate result:

```json
{
  "success": true,
  "total": 10,
  "uploaded": 8,
  "failed": 2,
  "results": [
    {
      "filename": "RES-101.pdf",
      "status": "uploaded",
      "content_document_id": "069..."
    },
    {
      "filename": "RES-999.pdf",
      "status": "failed",
      "reason": "No matching record"
    }
  ]
}
```

The frontend uses this object to populate the results UI.

---

# 39. JavaScript Result Processing

The frontend calls:

```javascript
const data = await response.json();
```

This converts JSON into a JavaScript object.

For example:

```javascript
data.total
data.uploaded
data.failed
data.results
```

can then be accessed directly.

---

# 40. Result Rendering

The frontend displays:

```text
Total
Uploaded
Failed
```

and a per-file result list.

Conceptually:

```text
RES-101.pdf       Uploaded
RES-102.pdf       Uploaded
RES-103.pdf       Failed
                   No matching Product2
```

This allows a bulk operation to partially succeed.

One failed file does not automatically make every other file fail.

---

# 41. Error Handling

Backend operations are wrapped with exception handling.

Conceptually:

```python
try:
    ...
except Exception as error:
    results.append({
        "filename": filename,
        "status": "failed",
        "reason": str(error)
    })
```

This makes the application resilient to individual Salesforce/API/file failures.

Frontend similarly uses:

```javascript
try {
    ...
} catch (error) {
    showUploadError(error.message);
} finally {
    ...
}
```

The `finally` block restores the upload button state.

---

# 42. Frontend Upload State

Before upload:

```text
Upload Files
```

During upload:

```text
Uploading...
```

After completion:

```text
Upload Files
```

The button is disabled during the request to reduce accidental duplicate submissions.

---

# 43. Full End-to-End Flow

## Authentication

```text
User
 |
 | enters Salesforce URL/client ID/client secret
 v
JavaScript
 |
 | POST /api/auth/login
 v
FastAPI
 |
 | requests.post()
 v
Salesforce OAuth
 |
 | access_token + instance_url
 v
FastAPI session
 |
 v
JavaScript receives success
```

## File Upload With Relationship

```text
User selects files
        |
        v
Browser File objects
        |
        v
JavaScript state.files
        |
        v
FormData
        |
        | POST /api/files/upload
        v
FastAPI
        |
        v
process_files()
        |
        +--> extract filename stems
        |
        +--> query Salesforce candidates
        |
        +--> local matching
        |
        +--> reject unmatched/ambiguous files
        |
        +--> create ContentVersion
        |
        +--> retrieve ContentDocumentId
        |
        +--> create ContentDocumentLink
        |
        v
JSON response
        |
        v
JavaScript
        |
        v
DOM/result rendering
        |
        v
User
```

---

# 44. Important Python Concepts Used

This project demonstrates:

### Variables

```python
filename = file.filename
```

### Type hints

```python
filename: str
```

### Functions

```python
def create_content_version(...):
```

### Async functions

```python
async def upload_files(...):
```

### Dictionaries

```python
{
    "filename": filename,
    "status": "uploaded"
}
```

### Lists

```python
results = []
```

### Loops

```python
for file in files:
```

### Conditions

```python
if object_name:
```

### Exceptions

```python
try:
    ...
except Exception:
    ...
```

### Modules

```python
from app.login import ...
```

### Classes

```python
class SalesforceLoginRequest(BaseModel):
```

### HTTP clients

```python
requests.post(...)
requests.get(...)
```

### JSON

```python
response.json()
```

### File handling

```python
Path(filename).stem
```

### Base64

```python
base64.b64encode(...)
```

---

# 45. Important JavaScript Concepts Used

This project demonstrates:

### Variables

```javascript
const response = ...
let state = ...
```

### Objects

```javascript
state.relation
```

### Arrays

```javascript
state.files
```

### Functions

```javascript
function showUploadResults(data) {
}
```

### Arrow functions

```javascript
file => {
    ...
}
```

### Loops

```javascript
state.files.forEach(...)
```

### Conditions

```javascript
if (state.files.length === 0) {
    return;
}
```

### DOM

```javascript
document.getElementById(...)
```

### Events

```javascript
addEventListener(...)
```

### Promises

```javascript
fetch(...)
```

### Async/Await

```javascript
await fetch(...)
```

### HTTP

```javascript
fetch("/api/files/upload", ...)
```

### JSON

```javascript
response.json()
```

### FormData

```javascript
new FormData()
```

### Error handling

```javascript
try / catch / finally
```

---

# 46. Python vs JavaScript Mapping

| Concept | Python | JavaScript |
|---|---|---|
| Variable | `x = 10` | `const x = 10` |
| Mutable variable | `x = 10` | `let x = 10` |
| Function | `def foo()` | `function foo()` |
| Arrow function | N/A | `() => {}` |
| List | `[]` | `[]` |
| Dictionary/Object | `{}` | `{}` |
| Null | `None` | `null` |
| Boolean | `True` / `False` | `true` / `false` |
| Loop | `for x in items` | `forEach()` / `for...of` |
| Condition | `if` | `if` |
| Error handling | `try/except` | `try/catch` |
| Async | `async/await` | `async/await` |
| HTTP | `requests` | `fetch` |
| JSON | `response.json()` | `response.json()` |
| Type declaration | type hints | TypeScript |
| Package/module | Python module | JS module |

---

# 47. Security Considerations

## Access Token

The Salesforce access token is stored server-side and is not returned to the browser.

This prevents exposing the token through frontend JavaScript.

## Client Secret

The client secret is transmitted from browser to backend during login and should only be used over HTTPS in deployed environments.

For a public multi-user application, a stronger authentication/session architecture should be implemented.

## Dynamic Salesforce Object and Field Names

The application accepts:

```text
object_name
field_name
```

from the user.

These values are used in SOQL and therefore should be strictly validated.

A production implementation should:

1. Validate Salesforce identifiers using a strict identifier pattern.
2. Validate that the object exists.
3. Validate that the field exists on that object.
4. Avoid arbitrary SOQL construction where possible.

Identifiers cannot be safely handled using normal SOQL bind variables, so explicit validation is important.

## SOQL Query Length

Batching many `LIKE` expressions into one query can eventually exceed Salesforce query/request limits.

Batch sizes should therefore be controlled.

---

# 48. Performance Considerations

The current implementation is designed for correctness and a straightforward architecture.

For hundreds of files, the basic architecture is:

```text
Browser
  ↓
FastAPI
  ↓
Salesforce matching
  ↓
File uploads
```

For very large files, the current approach has two limitations:

### Memory

```python
file_bytes = await file.read()
```

loads the entire file into memory.

### Base64

Base64 increases payload size.

For approximately 17 MB files, this overhead becomes significant.

---

# 49. Future Scaling Architecture

For larger workloads, the upload layer can be redesigned around:

```text
Browser
   ↓
Upload batches
   ↓
FastAPI
   ↓
Streaming / temporary storage
   ↓
Salesforce upload workers
```

Possible improvements include:

- Streaming uploads.
- Temporary file storage.
- Controlled concurrency.
- Retry queues.
- Background workers.
- Resumable uploads.
- Salesforce Bulk API where appropriate.
- Progress reporting using polling or WebSockets.
- Per-user session storage.
- Redis/database-backed job state.

The current implementation intentionally keeps the architecture simple before introducing these concerns.

---

# 50. Render Deployment

The application is deployed as a Python web service.

Recommended configuration:

```text
Root Directory:
[blank]
```

The repository root should contain:

```text
Backend/
FrontEnd/
requirements.txt
```

## Build Command

```bash
pip install -r requirements.txt
```

## Start Command

```bash
uvicorn Backend.app.main:app --host 0.0.0.0 --port $PORT
```

---

# 51. Python Import Structure

The start command:

```text
uvicorn Backend.app.main:app
```

means:

```text
Backend
  └── app
       └── main.py
            └── app
```

The import path is:

```text
Backend.app.main
```

and the FastAPI object inside that module is:

```text
app
```

Therefore:

```text
Backend.app.main:app
```

has two parts:

```text
module path : application object
```

The package files:

```text
Backend/__init__.py
Backend/app/__init__.py
```

should be committed to Git.

---

# 52. Deployment Import Failure

A common deployment error is:

```text
ModuleNotFoundError: No module named 'Backend'
```

This usually means Python cannot see the repository root/package structure.

Verify:

```bash
git ls-files Backend
```

Expected files include:

```text
Backend/app/main.py
Backend/app/login.py
Backend/app/session.py
Backend/app/bulk_upload.py
Backend/app/salesforce_files.py
```

Also verify:

```text
Backend/__init__.py
Backend/app/__init__.py
```

are present and committed.

The recommended configuration is to run Uvicorn from the repository root using:

```bash
uvicorn Backend.app.main:app --host 0.0.0.0 --port $PORT
```

and keep imports consistent:

```python
from Backend.app.login import ...
from Backend.app.session import ...
from Backend.app.bulk_upload import ...
```

Do not mix:

```text
uvicorn app.main:app
```

with imports expecting:

```text
Backend.app...
```

unless the Python package structure and working directory are intentionally configured for that layout.

---

# 53. Environment Variables

The application currently does not require custom Salesforce environment variables.

The user enters:

```text
Salesforce URL
Client ID
Client Secret
```

through the frontend.

The deployment platform provides:

```text
PORT
```

which is used by:

```bash
--port $PORT
```

No custom environment variables are currently required.

---

# 54. API Summary

## Health

```http
GET /api/health
```

Example response:

```json
{
  "status": "ok",
  "service": "salesforce-bulk-uploader"
}
```

## Authentication

```http
POST /api/auth/login
Content-Type: application/json
```

Request:

```json
{
  "salesforce_url": "https://login.salesforce.com",
  "client_id": "CLIENT_ID",
  "client_secret": "CLIENT_SECRET"
}
```

## File Upload

```http
POST /api/files/upload
Content-Type: multipart/form-data
```

Fields:

```text
files
object_name
field_name
visibility
```

`object_name`, `field_name`, and `visibility` are optional when uploading without a Salesforce relationship.

---

# 55. Development Workflow

Run locally:

```bash
uvicorn Backend.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Test API:

```text
http://127.0.0.1:8000/docs
```

Typical development loop:

```text
Edit Python/JS/HTML
       ↓
Run FastAPI
       ↓
Open browser
       ↓
Test
       ↓
Inspect browser console/network
       ↓
Inspect FastAPI terminal
       ↓
Fix
       ↓
Commit
       ↓
Push
       ↓
Render deploy
```

---

# 56. Debugging Strategy

When something fails, identify which layer failed.

## Browser/UI

Check:

```text
Browser DevTools
  ├── Console
  └── Network
```

Questions:

- Did the click event execute?
- Did `fetch()` run?
- Was the request sent?
- What HTTP status was returned?
- What response body came back?

## FastAPI

Check server logs.

Questions:

- Did the request reach FastAPI?
- Did request parsing succeed?
- Did Python throw an exception?
- Did Salesforce return an error?

## Salesforce

Inspect:

- HTTP status.
- Salesforce REST response body.
- OAuth response.
- SOQL response.
- ContentVersion response.
- ContentDocumentLink response.

The debugging chain is:

```text
UI
 ↓
HTTP request
 ↓
FastAPI
 ↓
Python
 ↓
Salesforce API
```

Find the first layer where the expected behavior stops.

---

# 57. Core Design Principles

The application follows several important software engineering principles.

## Separation of Concerns

```text
HTTP/API        → main.py
Authentication  → login.py
Session         → session.py
Workflow        → bulk_upload.py
Salesforce API  → salesforce_files.py
UI              → HTML/CSS/JS
```

## Avoid Repeated Network Calls

Salesforce matching is batched instead of querying once per file.

## Fail Before Upload

Files are matched before creating Salesforce files.

## Per-File Error Isolation

One failed file does not automatically terminate all processing.

## Backend Token Protection

Salesforce access tokens are kept server-side.

---

# 58. Current Limitations

The current implementation is intentionally a first functional version.

Known limitations:

1. Salesforce session is stored in memory.
2. Application is not yet multi-user.
3. Entire files may be loaded into memory.
4. Base64 increases upload payload size.
5. Upload processing is sequential.
6. SOQL batching requires query-length management.
7. Dynamic object/field names require stronger production validation.
8. No persistent upload job tracking.
9. No resumable upload mechanism.
10. No real-time upload progress channel.

---

# 59. Recommended Future Architecture

A more scalable version could become:

```text
                    Browser
                       |
                       v
                  FastAPI API
                       |
             +---------+---------+
             |                   |
             v                   v
       Authentication       Upload Job
                                 |
                                 v
                         Background Worker
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
        Salesforce Matching                File Processing
                                                  |
                                                  v
                                          Salesforce REST API
                                                  |
                                                  v
                                        ContentVersion / Link
```

This would allow:

- Background processing.
- Retry mechanisms.
- Progress tracking.
- Better concurrency.
- Persistent job state.
- Better support for thousands of files.

---

# 60. Key Learning Outcomes

This project demonstrates a complete modern web application.

## Python

You have worked with:

```text
Python
 ├── Functions
 ├── Classes
 ├── Modules
 ├── Type hints
 ├── Lists
 ├── Dictionaries
 ├── Exceptions
 ├── File handling
 ├── HTTP requests
 ├── JSON
 ├── Base64
 ├── async/await
 ├── FastAPI
 ├── Pydantic
 └── REST APIs
```

## JavaScript

You have worked with:

```text
JavaScript
 ├── Variables
 ├── Objects
 ├── Arrays
 ├── Functions
 ├── Arrow functions
 ├── DOM
 ├── Events
 ├── File API
 ├── FormData
 ├── fetch()
 ├── Promises
 ├── async/await
 ├── JSON
 └── Error handling
```

## Integration

You have also implemented:

```text
Browser
   ↕
HTTP
   ↕
FastAPI
   ↕
OAuth
   ↕
Salesforce REST API
```

This is a real full-stack integration architecture rather than a simple frontend-only application.

---

# 61. Mental Model

The most important mental model for this project is:

```text
JavaScript
"Something happened in the browser."
        |
        | fetch()
        v
FastAPI
"Give me the request."
        |
        v
Python
"Process the business logic."
        |
        | requests
        v
Salesforce
"Perform the requested operation."
        |
        v
Python
"Convert the result into JSON."
        |
        v
JavaScript
"Update the UI."
        |
        v
User
"See the result."
```

Once this request/response cycle is understood, the rest of the application becomes a composition of smaller Python and JavaScript concepts.
