import requests


def get_access_token_info(
    login_url: str,
    client_id: str,
    client_secret: str
):
    token_url = f"{login_url}/services/oauth2/token"

    response = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        },
        timeout=30
    )

    if not response.ok:

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        raise Exception(
            f"Salesforce authentication failed: {error_data}"
        )

    token_data = response.json()

    if not token_data.get("access_token"):
        raise Exception(
            "Salesforce did not return an access token."
        )

    if not token_data.get("instance_url"):
        raise Exception(
            "Salesforce did not return an instance URL."
        )

    return token_data