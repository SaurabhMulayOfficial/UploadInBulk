from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from app.login import get_access_token_info
from app.session import (
    set_salesforce_session
)

from app.session import (
    get_salesforce_session )

from typing import Optional
from fastapi import (
    File,
    Form,
    UploadFile,
)

from app.bulk_upload import process_files
from app.progress import get_progress, clear_progress  # ADDED

class SalesforceLoginRequest(BaseModel):
    salesforce_url: str
    client_id: str
    client_secret: str


app = FastAPI(
    title="Salesforce Bulk File Uploader",
    version="1.0.0"
)


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "FrontEnd"


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "salesforce-bulk-uploader"
    }


@app.post("/api/auth/login")
def login(request: SalesforceLoginRequest):

    try:
        token_data = get_access_token_info(
            login_url=request.salesforce_url,
            client_id=request.client_id,
            client_secret=request.client_secret
        )

        set_salesforce_session(
            access_token=token_data["access_token"],
            instance_url=token_data["instance_url"]
        )

        return {
            "success": True,
            "message": "Successfully connected to Salesforce.",
            "instance_url": token_data["instance_url"]
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error)
        }


# ADDED: progress polling endpoint
@app.get("/api/files/upload/progress/{job_id}")
def upload_progress(job_id: str):
    progress = get_progress(job_id)

    if not progress:
        return {"total": 0, "completed": 0}

    return progress


@app.post("/api/files/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    object_name: Optional[str] = Form(None),
    field_name: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    numberofThreads: Optional[int] = Form(1),
    job_id: Optional[str] = Form(None),  # ADDED
):
    try:

        if object_name and not field_name:

            return {
                "success": False,
                "message": (
                    "field_name is required when "
                    "object_name is supplied."
                ),
            }

        if object_name and visibility not in {
            "AllUsers",
            "InternalUsers",
            "SharedUsers",
        }:

            return {
                "success": False,
                "message": (
                    "Invalid visibility."
                ),
            }

        session = get_salesforce_session()

        results = await process_files(
            files=files,
            instance_url=session["instance_url"],
            access_token=session["access_token"],
            object_name=object_name,
            field_name=field_name,
            visibility=visibility,
            numberofThreads=numberofThreads,
            job_id=job_id,  # ADDED
        )

        if job_id:  # ADDED
            clear_progress(job_id)

        return {
            "success": True,
            "total": len(files),
            "uploaded": sum(
                1
                for result in results
                if result["status"] == "uploaded"
            ),
            "failed": sum(
                1
                for result in results
                if result["status"] == "failed"
            ),
            "results": results,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
        }


app.mount(
    "/",
    StaticFiles(
        directory=str(FRONTEND_DIR),
        html=True
    ),
    name="frontend"
)