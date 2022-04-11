import elastic_api
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_menu_markup(elastic_token: str) -> InlineKeyboardMarkup:
    products = elastic_api.get_all_products(credential_token=elastic_token)["data"]
    product_names_and_ids = [(product["name"], product["id"]) for product in products]

    keyboard = [
        [InlineKeyboardButton(text=product_name, callback_data=product_id)]
        for product_name, product_id in product_names_and_ids
    ]
    keyboard.append([InlineKeyboardButton("Корзина", callback_data="cart")])

    menu_markup = InlineKeyboardMarkup(keyboard)

    return menu_markup


def get_product_in_cart_count(elastic_token: str, product_id: str, cart_id: str) -> int:
    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token, cart_id=cart_id
    )
    product_in_cart = sum(
        [
            product["quantity"]  # TODO: replace by '1'
            for product in cart_items["data"]
            if product_id == product["product_id"]
        ]
    )

    return product_in_cart


def get_description_markup(
    elastic_token: str, product_id: str, user_id: str
) -> InlineKeyboardMarkup:

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


def get_cart_markup(cart_items: dict) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(f"Убрать {product['name']}", callback_data=product["id"])]
        for product in cart_items["data"]
    ]
    keyboard.append([InlineKeyboardButton(text="К оплате", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton(text="В меню", callback_data="back")])
    cart_markup = InlineKeyboardMarkup(keyboard)

    return cart_markup


def get_email_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    email_markup = InlineKeyboardMarkup(keyboard)

    return email_markup


def get_delivery_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Самовывоз", callback_data="pickup")],
        [InlineKeyboardButton(text="Доставка", callback_data="delivery")],
    ]
    delivery_markup = InlineKeyboardMarkup(keyboard)

    return delivery_markup


def get_payment_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Оплатить", callback_data="pay")],
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    payment_markup = InlineKeyboardMarkup(keyboard)

    return payment_markup
