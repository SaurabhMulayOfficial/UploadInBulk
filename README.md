# Salesforce Bulk File Uploader

A FastAPI-based utility for bulk uploading files to Salesforce and optionally associating those files with Salesforce records.

The application provides a simple web-based wizard:

1. Connect to Salesforce
2. Configure file-to-record relationship
3. Select and upload files
4. View individual upload results

---

## Features

* Salesforce OAuth 2.0 Client Credentials authentication
* Backend-managed Salesforce access token
* Browser-based file selection
* Bulk file upload
* Optional Salesforce record association
* Filename-based record matching
* `ContentVersion` creation
* `ContentDocumentLink` creation
* Configurable file visibility
* Per-file success/failure results
* Support for files without Salesforce record relationships

---

## Architecture

```text
Browser
   │
   │ Salesforce URL
   │ Client ID
   │ Client Secret
   ▼
FastAPI Backend
   │
   ├── Salesforce Authentication
   │       │
   │       └── OAuth 2.0 Client Credentials
   │
   ├── File Matching
   │       │
   │       └── Filename → Salesforce Record
   │
   └── File Upload
           │
           ├── ContentVersion
           │
           └── ContentDocumentLink
```

### Application Structure

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
│       ├── salesforce_files.py
│       └── file_matching.py
│
├── FrontEnd/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── requirements.txt
└── README.md
```

---

# Prerequisites

* Python 3.10+
* Salesforce org
* Salesforce Connected App / External Client App configured for OAuth
* Salesforce Client ID
* Salesforce Client Secret

---

# Installation

Clone the repository:

```bash
git clone https://github.com/SaurabhMulayOfficial/UploadInBulk.git
cd UploadInBulk
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Requirements

The application currently uses:

```text
fastapi
uvicorn[standard]
requests
python-multipart
```

`python-multipart` is required because FastAPI receives uploaded files using `multipart/form-data`.

Example `requirements.txt`:

```text
fastapi
uvicorn[standard]
requests
python-multipart
```

---

# Running the Application

Run the FastAPI server from the project root:

```bash
uvicorn Backend.app.main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

Open the application in your browser:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Salesforce Authentication

The application uses the Salesforce OAuth 2.0 Client Credentials Flow.

The frontend sends:

```text
Salesforce URL
Client ID
Client Secret
```

to:

```http
POST /api/auth/login
```

The backend authenticates with Salesforce.

The Salesforce access token is stored **only on the backend**.

The token is not returned to the browser.

The response contains only:

```json
{
    "success": true,
    "message": "Successfully connected to Salesforce.",
    "instance_url": "https://yourorg.my.salesforce.com"
}
```

The backend stores the session in memory:

```python
salesforce_session = {
    "access_token": "...",
    "instance_url": "..."
}
```

This is suitable for the current single-user/local utility.

> For a multi-user production deployment, the session must be associated with the individual user/session instead of using a single global in-memory object.

---

# Upload Workflow

## Step 1 — Salesforce Connection

The user enters:

```text
Salesforce URL
Client ID
Client Secret
```

The frontend calls:

```http
POST /api/auth/login
```

After successful authentication, Step 2 becomes available.

---

## Step 2 — File Relationship

The user can optionally define:

```text
Object API Name
Field API Name
File Visibility
```

Example:

```text
Object:
Product2

Field:
ProductCode

Visibility:
AllUsers
```

### No Relationship

If the user leaves the object empty:

```text
Object = None
```

the files are uploaded only as Salesforce Files.

No `ContentDocumentLink` is created.

```text
File
  │
  ▼
ContentVersion
  │
  ▼
Done
```

---

# File Matching

When an object and field are provided, the filename is used to identify the Salesforce record.

For example:

```text
RES-101.pdf
```

The file extension is removed:

```text
RES-101
```

The application searches the configured Salesforce field using a `contains` condition.

Example:

```text
ProductCode = "Premium Villa RES-101"
```

matches:

```text
RES-101.pdf
```

Conceptually:

```sql
WHERE ProductCode LIKE '%RES-101%'
```

The matching flow is:

```text
RES-101.pdf
      │
      ▼
RES-101
      │
      ▼
Product2.ProductCode
      │
      ▼
Contains "RES-101"
      │
      ▼
Product2.Id
```

The application does not query Salesforce once for every file. Filename keys are batched when querying Salesforce, and matching is then performed locally.

---

# File Upload Flow

For a file with a matching Salesforce record:

```text
RES-101.pdf
      │
      ▼
Find Salesforce Record
      │
      ▼
Product2.Id
      │
      ▼
Create ContentVersion
      │
      ▼
ContentDocumentId
      │
      ▼
Create ContentDocumentLink
      │
      ▼
Linked to Product2
```

The `ContentDocumentLink` contains:

```json
{
    "ContentDocumentId": "069...",
    "LinkedEntityId": "01t...",
    "Visibility": "AllUsers"
}
```

---

# ContentVersion

Each uploaded file creates a Salesforce `ContentVersion`.

The application uses:

```text
Title
PathOnClient
VersionData
```

The resulting:

```text
ContentDocumentId
```

is then used to create the relationship.

---

# ContentDocumentLink

When a Salesforce object is configured, the application creates a `ContentDocumentLink`.

Supported visibility values:

```text
AllUsers
InternalUsers
SharedUsers
```

Example:

```text
ContentDocument
      │
      │ ContentDocumentLink
      ▼
Product2
```

---

# Handling Unmatched Files

If relationship configuration is provided but a file cannot be matched to a Salesforce record, the file is **not uploaded**.

Example:

```text
RES-999.pdf
```

No matching `Product2` is found.

Result:

```json
{
    "filename": "RES-999.pdf",
    "status": "failed",
    "reason": "No Product2 record found..."
}
```

This prevents orphaned Salesforce Files.

---

# Handling Multiple Matches

If a filename matches multiple Salesforce records, the file is not uploaded.

For example:

```text
RES-101.pdf
```

matches:

```text
Product2 A
Product2 B
```

The result is reported as a failure because the relationship is ambiguous.

Example:

```json
{
    "filename": "RES-101.pdf",
    "status": "failed",
    "reason": "Multiple Product2 records matched..."
}
```

This prevents the application from linking a file to the wrong record.

---

# API Endpoints

## Health Check

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

---

## Salesforce Login

```http
POST /api/auth/login
```

Request:

```json
{
    "salesforce_url": "https://yourorg.my.salesforce.com",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
}
```

Response:

```json
{
    "success": true,
    "message": "Successfully connected to Salesforce.",
    "instance_url": "https://yourorg.my.salesforce.com"
}
```

---

## Upload Files

```http
POST /api/files/upload
```

Content type:

```text
multipart/form-data
```

Parameters:

```text
files
object_name
field_name
visibility
```

Example:

```text
files = RES-101.pdf
files = RES-102.pdf
files = RES-103.pdf

object_name = Product2
field_name = ProductCode
visibility = AllUsers
```

---

# Upload Response

Example:

```json
{
    "success": true,
    "total": 3,
    "uploaded": 2,
    "failed": 1,
    "results": [
        {
            "filename": "RES-101.pdf",
            "status": "uploaded",
            "content_document_id": "069XXXXXXXXXXXX",
            "record_id": "01tXXXXXXXXXXXX",
            "content_document_link_id": "06AXXXXXXXXXXX"
        },
        {
            "filename": "RES-102.pdf",
            "status": "uploaded",
            "content_document_id": "069XXXXXXXXXXXX",
            "record_id": "01tXXXXXXXXXXXX",
            "content_document_link_id": "06AXXXXXXXXXXX"
        },
        {
            "filename": "RES-999.pdf",
            "status": "failed",
            "reason": "No matching Salesforce record found."
        }
    ]
}
```

The frontend displays these results after the upload completes.

---

# Frontend Result Display

The frontend displays:

```text
Total      Uploaded      Failed
400        397           3
```

and provides a per-file result:

```text
RES-101.pdf    Uploaded    069XXXXXXXX
RES-102.pdf    Uploaded    069XXXXXXXX
RES-999.pdf    Failed      No matching record
```

---

# Frontend Flow

```text
┌──────────────────────────────┐
│ 1. Salesforce Connection     │
│                              │
│ Salesforce URL               │
│ Client ID                    │
│ Client Secret                │
│                              │
│ [ Connect to Salesforce ]    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 2. File Relationship         │
│                              │
│ Object: Product2             │
│ Field: ProductCode           │
│ Visibility: AllUsers         │
│                              │
│ [ Continue ]                 │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 3. Select Files              │
│                              │
│ RES-101.pdf                  │
│ RES-102.pdf                  │
│ RES-103.pdf                  │
│                              │
│ [ Upload Files ]             │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Upload Results               │
│                              │
│ Total:     3                 │
│ Uploaded:  2                 │
│ Failed:    1                 │
└──────────────────────────────┘
```

---

# Project Development

Start the application:

```bash
uvicorn Backend.app.main:app --reload
```

After modifying Python code, FastAPI's reload mode automatically restarts the application.

For a clean restart:

```bash
CTRL+C
```

then:

```bash
uvicorn Backend.app.main:app --reload
```

---

# Important Security Considerations

The current application is designed primarily as a local/internal utility.

The Salesforce Client Secret is sent from the browser to the FastAPI backend.

The Salesforce access token is **not** sent to the browser.

For production or multi-user deployment, consider:

* HTTPS
* Per-user backend sessions
* Secure session cookies
* Encrypted token storage
* CSRF protection
* Authentication for the FastAPI application
* Server-side storage for Salesforce credentials
* Input validation for Salesforce object and field API names
* Request size limits
* File type validation
* File size limits
* Background processing for very large uploads
* Persistent upload/job status

---

# Large File / Bulk Upload Considerations

The application is intended to support bulk uploads.

For example:

```text
400 files
×
17 MB
```

can represent several GB of data.

The application should therefore avoid unnecessarily loading all files into memory at the same time.

For very large uploads, the preferred architecture is:

```text
Browser
   │
   ▼
FastAPI
   │
   ├── Receive batch
   │
   ├── Process file
   │
   ├── Upload to Salesforce
   │
   └── Return result
```

For significantly larger workloads, background jobs and persistent job tracking can be introduced later.

---

# Future Improvements

Potential future enhancements:

* Upload progress tracking
* Batch processing
* Background workers
* Retry failed files
* Resume interrupted uploads
* Downloadable result report
* CSV result export
* Salesforce metadata validation
* Object/field lookup
* Record matching preview before upload
* Duplicate match handling UI
* File size validation
* File type validation
* Concurrent Salesforce uploads
* Persistent job history
* Multi-user support
* Secure production authentication

---

# License

Internal utility / project-specific use.
