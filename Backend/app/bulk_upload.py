from pathlib import Path

from Backend.app.salesforce_files import (
    query_matching_records,
    create_content_version,
    create_content_document_link,
)


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

    If object_name is None:
        Create ContentVersion only.

    If object_name is supplied:
        Match filename against fieldName,
        create ContentVersion,
        then create ContentDocumentLink.
    """

    # -------------------------------------------------
    # 1. Match Salesforce records if relationship exists
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

    results = []

    # -------------------------------------------------
    # 2. Process each file
    # -------------------------------------------------

    for file in files:

        filename = file.filename

        filename_key = Path(
            filename
        ).stem

        try:

            # -----------------------------------------
            # Find matching Salesforce record
            # -----------------------------------------

            matched_records = (
                record_matches.get(
                    filename_key,
                    []
                )
                if object_name
                else []
            )

            # -----------------------------------------
            # If relationship requested
            # but no record found
            # -----------------------------------------

            if object_name and not matched_records:

                results.append({
                    "filename": filename,
                    "status": "failed",
                    "reason": (
                        f"No {object_name} record found "
                        f"where {field_name} contains "
                        f"'{filename_key}'."
                    ),
                })

                continue

            # -----------------------------------------
            # Prevent ambiguous matches
            # -----------------------------------------

            if len(matched_records) > 1:

                results.append({
                    "filename": filename,
                    "status": "failed",
                    "reason": (
                        f"Multiple {object_name} records "
                        f"matched {field_name} contains "
                        f"'{filename_key}'."
                    ),
                    "record_ids": matched_records,
                })

                continue

            # -----------------------------------------
            # Read file
            # -----------------------------------------

            file_bytes = await file.read()

            # -----------------------------------------
            # Create ContentVersion
            # -----------------------------------------

            content_document_id = (
                create_content_version(
                    instance_url=instance_url,
                    access_token=access_token,
                    filename=filename,
                    file_bytes=file_bytes,
                )
            )

            result = {
                "filename": filename,
                "status": "uploaded",
                "content_document_id": content_document_id,
            }

            # -----------------------------------------
            # Create ContentDocumentLink
            # ONLY when object is supplied
            # -----------------------------------------

            if object_name:

                record_id = matched_records[0]

                link_id = (
                    create_content_document_link(
                        instance_url=instance_url,
                        access_token=access_token,
                        content_document_id=content_document_id,
                        record_id=record_id,
                        visibility=visibility,
                    )
                )

                result.update({
                    "record_id": record_id,
                    "content_document_link_id": link_id,
                })

            results.append(result)

        except Exception as error:

            results.append({
                "filename": filename,
                "status": "failed",
                "reason": str(error),
            })

    return results