import time
import urllib

import requests


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


def get_new_credential_token(
    credential_token: dict, client_id: str, client_secret: str
):
    if credential_token["expires"] <= time.time():
        new_credential_token = get_credential_token(client_id, client_secret)
        return new_credential_token


def get_all_products(credential_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {credential_token}"}
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


def create_product(credential_token: str, product_details: dict, sku: int) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
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


def create_pizza_image(credential_token: str, image_url: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    files = {
        "file_location": (None, image_url),
    }
    response = requests.post(
        "https://api.moltin.com/v2/files", headers=headers, files=files
    )
    response.raise_for_status()

    return response.json()


def create_pizza_image_relationship(
    credential_token: str, product_id: str, image_id: str
):
    headers = {"Authorization": f"Bearer {credential_token}"}
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
    credential_token: str,
    all_products: list[dict],
    pizza_menus_data: list[dict],
):
    for pizza in pizza_menus_data:
        for product in all_products["data"]:
            if pizza.get("name") == product.get("name"):
                pizza_image = create_pizza_image(
                    credential_token=credential_token,
                    image_url=pizza["product_image"]["url"],
                )
                pizza_image_id = pizza_image["data"]["id"]
                create_pizza_image_relationship(
                    credential_token=credential_token,
                    product_id=product["id"],
                    image_id=pizza_image_id,
                )


def create_flow(credential_token: str, name: str, slug: str, description: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
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


def create_field(
    credential_token: str, name: str, slug: str, description: str, flow_id: str
) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    json_data = {
        "data": {
            "type": "field",
            "name": name,
            "slug": slug,
            "field_type": "string",
            "description": description,
            "required": True,
            "enabled": True,
            "relationships": {
                "flow": {
                    "data": {
                        "type": "flow",
                        "id": flow_id,
                    },
                },
            },
        },
    }

    response = requests.post(
        "https://api.moltin.com/v2/fields", headers=headers, json=json_data
    )
    response.raise_for_status()

    return response.json()


def create_pizzeria_entry(
    credential_token: str,
    pizzeria_slug: str,
    address: str,
    alias: str,
    longitude: str,
    latitude: str,
):
    headers = {
        "Authorization": f"Bearer {credential_token}",
        "Content-Type": "application/json",
    }
    json_data = {
        "data": {
            "type": "entry",
            "address": address,
            "alias": alias,
            "longitude": longitude,
            "latitude": latitude,
        }
    }

    response = requests.post(
        f"https://api.moltin.com/v2/flows/{pizzeria_slug}/entries",
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()

    return response.json()


def add_product_to_cart(
    credential_token: str, product_id: str, quantity: int, cart_id: str
) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    json_data = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": quantity,
        }
    }
    response = requests.post(
        f"https://api.moltin.com/v2/carts/{cart_id}/items",
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()

    return response.json()


def delete_product_from_cart(
    credential_token: str, cart_id: str, product_id: str
) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.delete(
        f"https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}", headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_cart(credential_token: str, cart_id: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/carts/{cart_id}", headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_cart_items(credential_token: str, cart_id: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/carts/{cart_id}/items", headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_product(credential_token: str, product_id: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/products/{product_id}", headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_file_href(credential_token: str, file_id: str) -> str:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/files/{file_id}", headers=headers
    )
    response.raise_for_status()
    file_details = response.json()["data"]

    return file_details["link"]["href"]


def create_customer(credential_token: str, user_id: str, email: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    payload = {
        "data": {
            "type": "customer",
            "name": str(user_id),
            "email": str(email),
            "password": "mysecretpassword",
        },
    }

    response = requests.post(
        "https://api.moltin.com/v2/customers", headers=headers, json=payload
    )
    response.raise_for_status()

    return response.json()


def get_customer(credential_token: str, customer_id: str) -> dict:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/customers/{customer_id}", headers=headers
    )
    response.raise_for_status()

    return response.json()


def get_all_entries(credential_token: str, slug: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {credential_token}"}
    response = requests.get(
        f"https://api.moltin.com/v2/flows/{slug}/entries", headers=headers
    )
    response.raise_for_status()

    return response.json()


def create_coordinates_entry(
    credential_token: str,
    coordinates_slug: str,
    telegram_id: str,
    longitude: str,
    latitude: str,
):
    headers = {
        "Authorization": f"Bearer {credential_token}",
        "Content-Type": "application/json",
    }
    json_data = {
        "data": {
            "type": "entry",
            "telegram_id": telegram_id,
            "longitude": longitude,
            "latitude": latitude,
        }
    }

    response = requests.post(
        f"https://api.moltin.com/v2/flows/{coordinates_slug}/entries",
        headers=headers,
        json=json_data,
    )
    response.raise_for_status()

    return response.json()
