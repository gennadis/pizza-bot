import os
from pprint import pprint

import requests
from dotenv import load_dotenv


def get_json_data(url: str) -> list[dict]:
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


def create_product(access_token: str, product_details: dict, sku: int) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    json_data = {
        "data": {
            "type": "product",
            "name": product_details.get("name"),
            "slug": str(product_details.get("id")),
            "sku": str(sku),
            "description": product_details.get("description"),
            "manage_stock": False,
            "price": [
                {
                    "amount": product_details.get("price"),
                    "currency": "RUB",
                    "includes_tax": True,
                },
            ],
            "status": "live",
            "commodity_type": "physical",
        },
    }

    response = requests.post(
        "https://api.moltin.com/v2/products", headers=headers, json=json_data
    )
    response.raise_for_status()

    return response.json()


def create_pizza_image(access_token: str, image_url: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {
        "file_location": (None, image_url),
    }
    response = requests.post(
        "https://api.moltin.com/v2/files", headers=headers, files=files
    )
    response.raise_for_status()

    return response.json()


def main():
    load_dotenv()
    access_token = get_credential_token(
        client_id=os.getenv("ELASTIC_CLIENT_ID"),
        client_secret=os.getenv("ELASTIC_CLIENT_SECRET"),
    ).get("access_token")

    pizza_addresses_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904587/128/"
    )
    pizza_menus_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904588/129/"
    )
    test_pizza = pizza_menus_data[0]
    test_pizza_image = create_pizza_image(
        access_token=access_token,
        image_url=test_pizza["product_image"]["url"],
    )
    pprint(test_pizza_image)


if __name__ == "__main__":
    main()
