salesforce_session = {
    "access_token": None,
    "instance_url": None
}


def set_salesforce_session(
    access_token: str,
    instance_url: str
):
    salesforce_session["access_token"] = access_token
    salesforce_session["instance_url"] = instance_url


def get_salesforce_session():
    if not salesforce_session["access_token"]:
        raise Exception(
            "Salesforce session is not authenticated."
        )

    return salesforce_session