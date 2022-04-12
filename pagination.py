import os
from pprint import pprint

import elastic_api

from dotenv import load_dotenv
from more_itertools import chunked
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


""" PAGINATION IS NOT IMPLEMENTED YET. WORK IN PROGRESS..."""


def build_paginated_keyboard(
    products: list[dict], products_on_page: int, current_page: int
) -> InlineKeyboardMarkup:
    product_chunks = list(chunked(iterable=products["data"], n=products_on_page))
    product_buttons_details = [
        (product["name"], product["id"]) for product in product_chunks[current_page - 1]
    ]

    total_pages = len(product_chunks)
    next_page, prev_page = current_page + 1, current_page - 1
    # cycle through pages
    if current_page == total_pages:
        next_page = 1
    elif current_page == 1:
        prev_page = total_pages

    print(f"PRODUCTS COUNT {len(products['data'])}")
    print(f"PRODUCTS ON PAGE {products_on_page}")
    print(f"TOTAL PAGES {total_pages}")
    print()

    keyboard = []
    for product in product_buttons_details:
        product_name, product_id = product
        keyboard.append(
            [InlineKeyboardButton(text=product_name, callback_data=product_id)]
        )

    keyboard.append(
        [
            InlineKeyboardButton(prev_page, callback_data="prev"),
            InlineKeyboardButton("CART", callback_data="cart"),
            InlineKeyboardButton(next_page, callback_data="next"),
        ]
    )

    return keyboard


def main():
    load_dotenv()

    elastic_client_id = os.getenv("ELASTIC_CLIENT_ID")
    elastic_client_secret = os.getenv("ELASTIC_CLIENT_SECRET")
    elastic_token = elastic_api.get_credential_token(
        client_id=elastic_client_id,
        client_secret=elastic_client_secret,
    )

    all_products = elastic_api.get_all_products(
        credential_token=elastic_token["access_token"]
    )

    current_page = 1
    keyboard = build_paginated_keyboard(
        products=all_products, products_on_page=5, current_page=current_page
    )

    print(f"CURRENT PAGE {current_page}")
    for row in keyboard:
        for button in row:
            print(button.text)


if __name__ == "__main__":
    main()
