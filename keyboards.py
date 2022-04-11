from textwrap import dedent
import elastic_api
import geocode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_menu_markup(elastic_token: str, user_first_name: str) -> InlineKeyboardMarkup:
    welcome_text = f"""
            Привет, {user_first_name}! 
            Добро пожаловать в пиццерию "Pizza time"!
            """

    products = elastic_api.get_all_products(credential_token=elastic_token)["data"]
    product_names_and_ids = [(product["name"], product["id"]) for product in products]

    keyboard = [
        [InlineKeyboardButton(text=product_name, callback_data=product_id)]
        for product_name, product_id in product_names_and_ids
    ]
    keyboard.append([InlineKeyboardButton("Корзина", callback_data="cart")])

    menu_markup = InlineKeyboardMarkup(keyboard)

    return welcome_text, menu_markup


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


def get_cart_markup(elastic_token: str, cart_id: str) -> InlineKeyboardMarkup:
    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token,
        cart_id=cart_id,
    )

    total_price = 0
    cart_summary_lines = []

    for product in cart_items["data"]:
        price = product["value"]["amount"]
        quantity = product["quantity"]
        total_price += price * quantity

        product_summary_text = dedent(
            f"""
        Название: {product["name"]}
        Описание: {product["description"]}
        Стоимость: {price} ₽ за шт.
        Количество: {quantity} шт.
        Подитог: {price * quantity} ₽
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

    return cart_summary_text, cart_markup


def get_location_markup(user_first_name: str) -> InlineKeyboardMarkup:
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
) -> InlineKeyboardMarkup:
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
        delivery_options = "Предлагаем забрать пиццу самостоятельно или воспользоваться бесплатной доставкой."
    elif nearest_pizzeria["distance"] <= 5:
        delivery_options = "Предлагаем доплатить за доставку 100 рублей."
    elif nearest_pizzeria["distance"] <= 20:
        delivery_options = "Предлагаем доплатить за доставку 300 рублей."
    else:
        delivery_options = "Предлагаем самовывоз."

    delivery_details = f"""
    Ближайшая пиццерия:
    {nearest_pizzeria['address']}
    Расстояние: {nearest_pizzeria['distance']} км.
    {delivery_options}"""

    keyboard = [
        [InlineKeyboardButton(text="Самовывоз", callback_data="pickup")],
        [InlineKeyboardButton(text="Доставка", callback_data="delivery")],
    ]
    delivery_markup = InlineKeyboardMarkup(keyboard)

    return nearest_pizzeria, delivery_details, delivery_markup


def get_pickup_markup(nearest_pizzeria: dict) -> InlineKeyboardMarkup:
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


def get_payment_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Оплатить", callback_data="pay")],
        [InlineKeyboardButton(text="В меню", callback_data="back")],
    ]
    payment_markup = InlineKeyboardMarkup(keyboard)

    return payment_markup
