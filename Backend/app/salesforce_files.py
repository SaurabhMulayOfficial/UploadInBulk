from pathlib import Path
from urllib.parse import quote
import requests
import base64


API_VERSION = "v67.0"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def query_matching_records(
    instance_url: str,
    access_token: str,
    object_name: str,
    field_name: str,
    filenames: list[str],
) -> dict[str, list[str]]:
    """
    Returns:

    {
        "RES-101": ["001xxx"],
        "RES-102": ["001yyy", "001zzz"]
    }

    A list is used because multiple Salesforce records
    may contain the same filename.
    """

    # Get filename keys without extensions
    file_keys = list({
        Path(filename).stem
        for filename in filenames
    })

    if not file_keys:
        return {}

    records = []

    # Salesforce SOQL has URL/query-length limitations,
    # so process filenames in batches.
    batch_size = 50

    for start in range(0, len(file_keys), batch_size):

        batch = file_keys[start:start + batch_size]

        conditions = []

        for key in batch:
            escaped_key = (
                key
                .replace("\\", "\\\\")
                .replace("'", "\\'")
            )

            conditions.append(
                f"{field_name} LIKE '%{escaped_key}%'"
            )

        where_clause = " OR ".join(conditions)

        soql = (
            f"SELECT Id, {field_name} "
            f"FROM {object_name} "
            f"WHERE {where_clause}"
        )

        url = (
            f"{instance_url}"
            f"/services/data/{API_VERSION}/query/"
            f"?q={quote(soql)}"
        )

        response = requests.get(
            url,
            headers=_headers(access_token),
            timeout=60,
        )

        if not response.ok:
            raise Exception(
                f"Salesforce record query failed: "
                f"{response.text}"
            )

        data = response.json()

        records.extend(
            data.get("records", [])
        )

        # Handle Salesforce queryMore
        while not data.get("done", True):

            next_url = (
                instance_url +
                data["nextRecordsUrl"]
            )

            response = requests.get(
                next_url,
                headers=_headers(access_token),
                timeout=60,
            )

            if not response.ok:
                raise Exception(
                    f"Salesforce queryMore failed: "
                    f"{response.text}"
                )

            data = response.json()

            records.extend(
                data.get("records", [])
            )

    # Build:
    #
    # filename key -> record IDs
    #
    matches = {}

    for filename in file_keys:

        matches[filename] = []

        for record in records:

            field_value = record.get(field_name)

            if field_value is None:
                continue

            if filename in str(field_value):

                matches[filename].append(
                    record["Id"]
                )

    return matches


def create_content_version(
    instance_url: str,
    access_token: str,
    filename: str,
    file_bytes: bytes,
) -> str:

    url = (
        f"{instance_url}"
        f"/services/data/{API_VERSION}"
        f"/sobjects/ContentVersion"
    )

    payload = {
        "Title": Path(filename).stem,
        "PathOnClient": filename,
        "VersionData": base64.b64encode(
            file_bytes
        ).decode("ascii"),
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=300,
    )

    if not response.ok:
        raise Exception(
            f"ContentVersion creation failed "
            f"for {filename}: {response.text}"
        )

    content_version_id = response.json()["id"]

    query = (
        "SELECT ContentDocumentId "
        "FROM ContentVersion "
        f"WHERE Id = '{content_version_id}'"
    )

    query_url = (
        f"{instance_url}"
        f"/services/data/{API_VERSION}/query/"
        f"?q={quote(query)}"
    )

    response = requests.get(
        query_url,
        headers=_headers(access_token),
        timeout=30,
    )

    if not response.ok:
        raise Exception(
            f"Unable to retrieve ContentDocumentId "
            f"for {filename}: {response.text}"
        )

    records = response.json()["records"]

    return records[0]["ContentDocumentId"]

def create_content_document_link(
    instance_url: str,
    access_token: str,
    content_document_id: str,
    record_id: str,
    visibility: str,
):
    """
    Creates ContentDocumentLink between the file
    and Salesforce record.
    """

    url = (
        f"{instance_url}"
        f"/services/data/{API_VERSION}"
        f"/sobjects/ContentDocumentLink"
    )

    payload = {
        "ContentDocumentId": content_document_id,
        "LinkedEntityId": record_id,
        "Visibility": visibility,
    }

    response = requests.post(
        url,
        headers=_headers(access_token),
        json=payload,
        timeout=60,
    )

    if not response.ok:
        raise Exception(
            f"ContentDocumentLink creation failed: "
            f"{response.text}"
        )

    return response.json()["id"]