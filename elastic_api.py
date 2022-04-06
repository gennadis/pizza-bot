import os
from pprint import pprint

import requests
from dotenv import load_dotenv


def get_json_data(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def get_credential_token(client_id: str, client_secret: str) -> dict:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    response = requests.post(url="https://api.moltin.com/oauth/access_token", data=data)
    response.raise_for_status()

    return response.json()


def main():
    load_dotenv()
    pizza_addresses_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904587/128/"
    )
    pizza_menus_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904588/129/"
    )

    elastic_token = get_credential_token(
        client_id=os.getenv("ELASTIC_CLIENT_ID"),
        client_secret=os.getenv("ELASTIC_CLIENT_SECRET"),
    )
    print(elastic_token)


if __name__ == "__main__":
    main()
