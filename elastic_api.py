import os
import urllib
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


def get_all_products(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "page[limit]": "100",
        "page[offset]": "0",
    }

    response = requests.get(
        url="https://api.moltin.com/v2/products",
        headers=headers,
        params=urllib.parse.urlencode(payload, safe="[]"),
    )
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


def create_pizza_image_relationship(access_token: str, product_id: str, image_id: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    json_data = {
        "data": {
            "type": "main_image",
            "id": image_id,
        },
    }
    response = requests.post(
        f"https://api.moltin.com/v2/products/{product_id}/relationships/main-image",
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()

    return response.json()


def create_all_pizza_image_relations(
    access_token: str,
    all_products: list[dict],
    pizza_menus_data: list[dict],
):
    for pizza in pizza_menus_data:
        for product in all_products["data"]:
            if pizza.get("name") == product.get("name"):
                pizza_image = create_pizza_image(
                    access_token=access_token,
                    image_url=pizza["product_image"]["url"],
                )
                pizza_image_id = pizza_image["data"]["id"]
                create_pizza_image_relationship(
                    access_token=access_token,
                    product_id=product["id"],
                    image_id=pizza_image_id,
                )


def create_flow(access_token: str, name: str, slug: str, description: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    json_data = {
        "data": {
            "type": "flow",
            "name": name,
            "slug": slug,
            "description": description,
            "enabled": True,
        },
    }

    response = requests.post(
        "https://api.moltin.com/v2/flows", headers=headers, json=json_data
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
    #     pizza_name = pizza["name"]
    new_flow = create_flow(
        access_token=access_token,
        name="Pizzeria",
        slug="pizzeria",
        description="Custom pizzeria flow",
    )
    pprint(new_flow)


if __name__ == "__main__":
    main()
