from elastic_api import get_all_products
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_menu_markup(elastic_token: str) -> InlineKeyboardMarkup:
    products = get_all_products(credential_token=elastic_token)["data"]
    product_names_and_ids = [(product["name"], product["id"]) for product in products]

    keyboard = [
        [InlineKeyboardButton(text=product_name, callback_data=product_id)]
        for product_name, product_id in product_names_and_ids
    ]
    keyboard.append([InlineKeyboardButton("Корзина", callback_data="cart")])

    menu_markup = InlineKeyboardMarkup(keyboard)

    return menu_markup


def get_description_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Добавить в корзину", callback_data=1)],
        [InlineKeyboardButton(text="В меню", callback_data="back")],
        [InlineKeyboardButton("Корзина", callback_data="cart")],
    ]
    description_markup = InlineKeyboardMarkup(keyboard)

    return description_markup


def get_cart_markup(cart_items: dict) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                f"Убрать {product['name']} из корзины", callback_data=product["id"]
            )
            for product in cart_items["data"]
        ],
        [InlineKeyboardButton(text="К оплате", callback_data="checkout")],
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    cart_markup = InlineKeyboardMarkup(keyboard)

    return cart_markup


def get_email_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    email_markup = InlineKeyboardMarkup(keyboard)

    return email_markup
