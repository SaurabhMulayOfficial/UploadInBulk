from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.salesforce_files import (
    query_matching_records,
    create_content_version,
    create_content_document_link,
)
from app.progress import init_progress, increment_progress  # ADDED
import asyncio

# Number of files uploaded concurrently
MAX_WORKERS = 1 # input from user in frontend, default 1

def upload_single_file(
    file_data,
    instance_url: str,
    access_token: str,
    object_name: str | None,
    field_name: str | None,
    visibility: str | None,
    record_matches: dict,
):
    """
    Upload a single file.

    This function is synchronous because the Salesforce
    requests are synchronous.
    """

    filename = file_data["filename"]
    file_bytes = file_data["file_bytes"]

    filename_key = Path(filename).stem

    try:
        matched_records = (
            record_matches.get(filename_key, [])
            if object_name
            else []
        )

        if object_name and not matched_records:
            return {
                "filename": filename,
                "status": "failed",
                "reason": (
                    f"No {object_name} record found "
                    f"where {field_name} contains "
                    f"'{filename_key}'."
                ),
            }

        if len(matched_records) > 1:
            return {
                "filename": filename,
                "status": "failed",
                "reason": (
                    f"Multiple {object_name} records "
                    f"matched {field_name} contains "
                    f"'{filename_key}'."
                ),
                "record_ids": matched_records,
            }

        content_document_id = create_content_version(
            instance_url=instance_url,
            access_token=access_token,
            filename=filename,
            file_bytes=file_bytes,
        )

        result = {
            "filename": filename,
            "status": "uploaded",
            "content_document_id": content_document_id,
        }

        if object_name:
            record_id = matched_records[0]

            link_id = create_content_document_link(
                instance_url=instance_url,
                access_token=access_token,
                content_document_id=content_document_id,
                record_id=record_id,
                visibility=visibility,
            )

            result.update({
                "record_id": record_id,
                "content_document_link_id": link_id,
            })

        return result

    except Exception as error:
        return {
            "filename": filename,
            "status": "failed",
            "reason": str(error),
        }


async def process_files(
    files,
    instance_url: str,
    access_token: str,
    object_name: str | None,
    field_name: str | None,
    visibility: str | None,
    numberofThreads: int = 1,
    job_id: str | None = None,
):
    record_matches = {}

    if object_name:
        if not field_name:
            raise ValueError(
                "fieldName is required when objectName is supplied."
            )

        filenames = [file.filename for file in files]

        # ALSO blocking - wrap this too
        record_matches = await asyncio.to_thread(
            query_matching_records,
            instance_url=instance_url,
            access_token=access_token,
            object_name=object_name,
            field_name=field_name,
            filenames=filenames,
        )

    if job_id:
        init_progress(job_id, len(files))

    BATCH_SIZE = numberofThreads
    results = []

    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=numberofThreads) as executor:

        for start in range(0, len(files), BATCH_SIZE):

            batch_files = files[start:start + BATCH_SIZE]

            batch_data = []
            for file in batch_files:
                batch_data.append({
                    "filename": file.filename,
                    "file_bytes": await file.read(),
                })

            # KEY CHANGE: run_in_executor + await, NOT future.result()
            tasks = [
                loop.run_in_executor(
                    executor,
                    upload_single_file,
                    item,
                    instance_url,
                    access_token,
                    object_name,
                    field_name,
                    visibility,
                    record_matches,
                )
                for item in batch_data
            ]

            batch_results = await asyncio.gather(*tasks)

            for item, result in zip(batch_data, batch_results):
                results.append(result)
                if job_id:
                    increment_progress(job_id, item["filename"])

            batch_data.clear()

    return results