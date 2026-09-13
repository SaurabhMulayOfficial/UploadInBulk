from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.salesforce_files import (
    query_matching_records,
    create_content_version,
    create_content_document_link,
)


# Number of files uploaded concurrently
MAX_WORKERS = 10


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
        # -----------------------------------------
        # Find matching Salesforce record
        # -----------------------------------------

        matched_records = (
            record_matches.get(filename_key, [])
            if object_name
            else []
        )

        # -----------------------------------------
        # No match
        # -----------------------------------------

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

        # -----------------------------------------
        # Multiple matches
        # -----------------------------------------

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

        # -----------------------------------------
        # Create ContentVersion
        # -----------------------------------------

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

        # -----------------------------------------
        # Create ContentDocumentLink
        # -----------------------------------------

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
):
    """
    Main bulk upload workflow.

    Files are uploaded concurrently using a bounded
    thread pool.

    MAX_WORKERS controls how many files are processed
    simultaneously.
    """

    # -------------------------------------------------
    # 1. Match Salesforce records
    # -------------------------------------------------

    record_matches = {}

    if object_name:

        if not field_name:
            raise ValueError(
                "fieldName is required when objectName is supplied."
            )

        filenames = [
            file.filename
            for file in files
        ]

        record_matches = query_matching_records(
            instance_url=instance_url,
            access_token=access_token,
            object_name=object_name,
            field_name=field_name,
            filenames=filenames,
        )

    # -------------------------------------------------
    # 2. Read all files
    # -------------------------------------------------

    # IMPORTANT:
    # UploadFile objects should be read before sending
    # work to multiple threads.

    file_data = []

    for file in files:

        file_data.append({
            "filename": file.filename,
            "file_bytes": await file.read(),
        })

    # -------------------------------------------------
    # 3. Upload concurrently
    # -------------------------------------------------

    results = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                upload_single_file,
                file_data_item,
                instance_url,
                access_token,
                object_name,
                field_name,
                visibility,
                record_matches,
            )
            for file_data_item in file_data
        ]

        # Keep original file order
        for future in futures:
            results.append(
                future.result()
            )

    return results