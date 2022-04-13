from textwrap import dedent

from more_itertools import chunked
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import elastic_api
import geocode


PRODUCTS_ON_MENU_PAGE = 8


def get_menu_markup(
    elastic_token: str,
    user_first_name: str,
    button_pressed: str,
) -> tuple[str, InlineKeyboardMarkup]:
    welcome_text = f"""
            Привет, {user_first_name}! 
            Добро пожаловать в пиццерию "Pizza time"!
            """

    if button_pressed in ("/start", "back"):
        current_page = 1
    else:
        _, current_page = button_pressed.split(" ")
        current_page = int(current_page)

    products = elastic_api.get_all_products(credential_token=elastic_token)
    product_chunks = list(chunked(iterable=products["data"], n=PRODUCTS_ON_MENU_PAGE))
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
    print(f"PRODUCTS ON PAGE {PRODUCTS_ON_MENU_PAGE}")
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
            InlineKeyboardButton("<-", callback_data=f"page {prev_page}"),
            InlineKeyboardButton("Корзина", callback_data="cart"),
            InlineKeyboardButton("->", callback_data=f"page {next_page}"),
        ]
    )

    # product_names_and_ids = [(product["name"], product["id"]) for product in products]

    # keyboard = [
    #     [InlineKeyboardButton(text=product_name, callback_data=product_id)]
    #     for product_name, product_id in product_names_and_ids
    # ]
    # keyboard.append([InlineKeyboardButton("Корзина", callback_data="cart")])

    menu_markup = InlineKeyboardMarkup(keyboard)

    return welcome_text, menu_markup


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

    return InlineKeyboardMarkup(keyboard)


def get_product_in_cart_count(elastic_token: str, product_id: str, cart_id: str) -> int:
    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token, cart_id=cart_id
    )
    product_in_cart_count = sum(
        [
            product["quantity"]
            for product in cart_items["data"]
            if product_id == product["product_id"]
        ]
    )

    return product_in_cart_count


def get_description_markup(
    elastic_token: str, product_id: str, user_id: str
) -> tuple[str, str, InlineKeyboardMarkup]:

    product = elastic_api.get_product(
        credential_token=elastic_token, product_id=product_id
    )
    product_details = product["data"]
    product_in_cart_count = get_product_in_cart_count(
        elastic_token=elastic_token, product_id=product_id, cart_id=user_id
    )

    picture_href = elastic_api.get_file_href(
        credential_token=elastic_token,
        file_id=product["data"]["relationships"]["main_image"]["data"]["id"],
    )

    product_description = f"""
        Название: {product_details['name']}
        Стоимость: {product_details['meta']['display_price']['with_tax']['formatted']} за шт.
        Описание: {product_details['description']}
        
        В корзине: {product_in_cart_count} шт.
        """

    keyboard = [
        [InlineKeyboardButton("Добавить в корзину", callback_data=1)],
        [InlineKeyboardButton(text="В меню", callback_data="back")],
        [InlineKeyboardButton("Корзина", callback_data="cart")],
    ]
    description_markup = InlineKeyboardMarkup(keyboard)

    return picture_href, product_description, description_markup


def get_cart_markup(
    elastic_token: str, cart_id: str
) -> tuple[str, InlineKeyboardMarkup]:
    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token,
        cart_id=cart_id,
    )

    total_price = 0
    cart_summary_lines = []

    for product in cart_items["data"]:
        total_price += product["value"]["amount"]

        product_summary_text = dedent(
            f"""
        Название: {product["name"]}
        Описание: {product["description"]}
        Стоимость: {product["unit_price"]["amount"]} ₽ за шт.
        Количество: {product["quantity"]} шт.
        Подитог: {product["value"]["amount"]} ₽
        -----------------"""
        )

        cart_summary_lines.append(product_summary_text)

    cart_summary_lines_text = "\n".join(cart_summary_lines)
    cart_summary_text = f"ИТОГО: {total_price} ₽\n{cart_summary_lines_text}"

    keyboard = [
        [InlineKeyboardButton(f"Убрать {product['name']}", callback_data=product["id"])]
        for product in cart_items["data"]
    ]
    keyboard.append([InlineKeyboardButton(text="К оплате", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton(text="В меню", callback_data="back")])
    cart_markup = InlineKeyboardMarkup(keyboard)

    return total_price, cart_summary_text, cart_markup


def get_location_markup(user_first_name: str) -> tuple[str, InlineKeyboardMarkup]:
    location_text = f"""
            {user_first_name},
            Отправьте ваш адрес текстом или геопозицию для доставки.
            """

    keyboard = [
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    location_markup = InlineKeyboardMarkup(keyboard)

    return location_text, location_markup


def get_delivery_markup(
    elastic_token: str, user_coordinates: tuple[str, str], user_id: str
) -> tuple[dict, str, InlineKeyboardMarkup]:
    longitude, latitude = user_coordinates
    elastic_api.create_coordinates_entry(
        credential_token=elastic_token,
        coordinates_slug="coordinates",
        telegram_id=user_id,
        longitude=longitude,
        latitude=latitude,
    )

    all_pizzerias = elastic_api.get_all_entries(
        credential_token=elastic_token, slug="pizzeria"
    )
    nearest_pizzeria = geocode.get_nearest_pizzeria(
        user_coordinates=user_coordinates, pizzerias=all_pizzerias["data"]
    )

    if nearest_pizzeria["distance"] <= 0.5:
        delivery_description = "Предлагаем забрать пиццу самостоятельно или воспользоваться бесплатной доставкой."
        delivery_price = 0
    elif nearest_pizzeria["distance"] <= 5:
        delivery_description = "Предлагаем доплатить за доставку 100 рублей."
        delivery_price = 100
    elif nearest_pizzeria["distance"] <= 20:
        delivery_description = "Предлагаем доплатить за доставку 300 рублей."
        delivery_price = 300
    else:
        delivery_description = "Предлагаем самовывоз."
        delivery_price = 0

    delivery_text = f"""
    Ближайшая пиццерия:
    {nearest_pizzeria['address']}
    Расстояние: {nearest_pizzeria['distance']} км.
    {delivery_description}"""

    keyboard = [
        [InlineKeyboardButton(text="Самовывоз", callback_data="pickup")],
        [InlineKeyboardButton(text="Доставка", callback_data="delivery")],
    ]
    delivery_markup = InlineKeyboardMarkup(keyboard)

    return nearest_pizzeria, delivery_text, delivery_price, delivery_markup


def get_pickup_markup(nearest_pizzeria: dict) -> tuple[str, InlineKeyboardMarkup]:
    pickup_text = f"""
                Ближайшая пиццерия:
                {nearest_pizzeria['address']}
                Расстояние: {nearest_pizzeria['distance']} км.
                Самовывоз - бесплатно.

                Спасибо за заказ!
                """
    keyboard = [
        [InlineKeyboardButton(text="OK", callback_data="end")],
    ]
    pickup_markup = InlineKeyboardMarkup(keyboard)

    return pickup_text, pickup_markup
