import logging
import os
import time
from enum import Enum, auto
from textwrap import dedent

import geopy
import redis
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

import elastic_api
import keyboards
import geocode


logger = logging.getLogger(__file__)


class State(Enum):
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_CART = auto()
    HANDLE_WAITING = auto()
    HANDLE_DELIVERY = auto()


def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Telegram bot encountered an error", exc_info=context.error)


def validate_token_expiration(function_to_decorate):
    def wrapper(*args, **kwagrs):
        update, context = args
        token_expiration_time = context.bot_data.get("token_expires")
        current_time = time.time()

        if current_time >= token_expiration_time:
            logger.info("Getting new Elastic token due to expiration.")

            client_id = context.bot_data["elastic_client_id"]
            client_secret = context.bot_data["elastic_client_secret"]
            new_elastic_token = elastic_api.get_credential_token(
                client_id, client_secret
            )

            context.bot_data["elastic"] = new_elastic_token["access_token"]
            context.bot_data["token_expires"] = new_elastic_token["expires"]

            updated_args = update, context
            return function_to_decorate(*updated_args, **kwagrs)

        return function_to_decorate(*args, **kwagrs)

    return wrapper


@validate_token_expiration
def handle_menu(update: Update, context: CallbackContext) -> State:
    user_first_name = update.effective_user.first_name
    elastic_token = context.bot_data.get("elastic")
    products_markup = keyboards.get_menu_markup(elastic_token)

    update.effective_message.reply_text(
        text=dedent(
            f"""
            Привет, {user_first_name}! 
            Добро пожаловать в пиццерию "Pizza time"!
            """
        ),
        reply_markup=products_markup,
    )

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def handle_description(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    query.answer()

    elastic_token = context.bot_data.get("elastic")
    product = elastic_api.get_product(
        credential_token=elastic_token, product_id=query.data
    )
    product_id = product["data"]["id"]

    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token,
        cart_id=update.effective_user.id,
    )
    products_in_cart = sum(
        [
            product["quantity"]
            for product in cart_items["data"]
            if product_id == product["product_id"]
        ]
    )

    product_details = product["data"]
    product_description = f"""
        Название: {product_details['name']}
        Стоимость: {product_details['meta']['display_price']['with_tax']['formatted']} за шт.
        Описание: {product_details['description']}
        
        В корзине: {products_in_cart} шт.
        """
    formatted_product_description = "\n".join(
        line.strip() for line in product_description.splitlines()
    )

    context.bot_data["product_id"] = product["data"]["id"]

    picture_id = product["data"]["relationships"]["main_image"]["data"]["id"]
    picture_href = elastic_api.get_file_href(
        credential_token=elastic_token, file_id=picture_id
    )

    update.effective_user.send_photo(
        photo=picture_href,
        caption=formatted_product_description,
        reply_markup=keyboards.get_description_markup(),
    )
    update.effective_message.delete()

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def update_cart(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    query.answer("Товар добавлен в корзину")

    elastic_token = context.bot_data.get("elastic")
    elastic_api.add_product_to_cart(
        credential_token=elastic_token,
        product_id=context.bot_data["product_id"],
        quantity=int(query.data),
        cart_id=update.effective_user.id,
    )

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def handle_cart(update: Update, context: CallbackContext) -> State:
    query = update.callback_query

    elastic_token = context.bot_data.get("elastic")
    cart_items = elastic_api.get_cart_items(
        credential_token=elastic_token,
        cart_id=update.effective_user.id,
    )

    product_id = query.data
    if product_id in [product["id"] for product in cart_items["data"]]:
        query.answer("Товар удален из корзины")
        elastic_api.delete_product_from_cart(
            credential_token=elastic_token,
            cart_id=update.effective_user.id,
            product_id=query.data,
        )

    update.effective_user.send_message(
        text=elastic_api.get_cart_summary_text(cart_items=cart_items["data"]),
        reply_markup=keyboards.get_cart_markup(cart_items=cart_items),
    )
    update.effective_message.delete()

    return State.HANDLE_CART


@validate_token_expiration
def handle_location(update: Update, context: CallbackContext) -> State:
    user_first_name = update.effective_user.first_name
    query = update.callback_query
    query.answer()

    update.effective_user.send_message(
        text=dedent(
            f"""
            {user_first_name},
            Отправьте ваш адрес текстом или геопозицию для доставки.
            """
        ),
        reply_markup=keyboards.get_email_markup(),
    )

    return State.HANDLE_WAITING


@validate_token_expiration
def handle_customer_creation(update: Update, context: CallbackContext) -> State:
    elastic_token = context.bot_data.get("elastic")

    if update.message.location:
        longitude = update.message.location.longitude
        latitude = update.message.location.latitude
        user_coordinates = (longitude, latitude)
    else:
        geocode_token = context.bot_data.get("geocode")
        try:
            user_coordinates = geocode.get_coordinates(
                yandex_token=geocode_token, address=update.message.text
            )
        except IndexError:
            update.effective_user.send_message(
                text=dedent(
                    f"""
                    Не нашел координаты.
                    """
                ),
                reply_markup=keyboards.get_email_markup(),
            )
            return State.HANDLE_WAITING

    pizzerias = elastic_api.get_all_entries(
        credential_token=elastic_token, slug="pizzeria"
    )["data"]
    nearest_pizzeria = geocode.get_nearest_pizzeria(
        user_coordinates=user_coordinates, pizzerias=pizzerias
    )
    context.bot_data["pizzeria"] = nearest_pizzeria
    context.bot_data["coordinates"] = user_coordinates

    longitude, latitude = user_coordinates
    coordinates_entry = elastic_api.create_coordinates_entry(
        credential_token=elastic_token,
        coordinates_slug="coordinates",
        telegram_id=update.effective_user.id,
        longitude=longitude,
        latitude=latitude,
    )

    if nearest_pizzeria["distance"] <= 0.5:
        delivery_price = "Предлагаем забрать пиццу самостоятельно или воспользоваться бесплатной доставкой."
    elif nearest_pizzeria["distance"] <= 5:
        delivery_price = "Предлагаем доплатить за доставку 100 рублей."
    elif nearest_pizzeria["distance"] <= 20:
        delivery_price = "Предлагаем доплатить за доставку 300 рублей."
    else:
        delivery_price = "Предлагаем самовывоз."

    update.effective_user.send_message(
        text=dedent(
            f"""
                Ближайшая пиццерия:
                {nearest_pizzeria['address']}
                Расстояние: {nearest_pizzeria['distance']} км.
                
                {delivery_price}
                """
        ),
        reply_markup=keyboards.get_delivery_markup(),
    )

    return State.HANDLE_DELIVERY


@validate_token_expiration
def handle_delivery(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    query.answer()

    pizzeria_courier = context.bot_data["pizzeria"]["courier"]
    longitude, latitude = context.bot_data["coordinates"]

    context.bot.send_location(
        chat_id=pizzeria_courier,
        longitude=longitude,
        latitude=latitude,
    )


def run_bot(
    telegram_token: str,
    redis_connection: redis.Redis,
    elastic_token: str,
    elastic_client_id: str,
    elastic_client_secret: str,
    geocode_token: str,
):
    updater = Updater(token=telegram_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.bot_data["redis"] = redis_connection
    dispatcher.bot_data["elastic"] = elastic_token["access_token"]
    dispatcher.bot_data["token_expires"] = elastic_token["expires"]
    dispatcher.bot_data["elastic_client_id"] = elastic_client_id
    dispatcher.bot_data["elastic_client_secret"] = elastic_client_secret
    dispatcher.bot_data["geocode"] = geocode_token

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", handle_menu)],
        states={
            State.HANDLE_MENU: [
                CallbackQueryHandler(handle_menu),
                CallbackQueryHandler(handle_cart, pattern="cart"),
            ],
            State.HANDLE_DESCRIPTION: [
                CallbackQueryHandler(handle_menu, pattern="back"),
                CallbackQueryHandler(handle_cart, pattern="cart"),
                CallbackQueryHandler(update_cart, pattern="^[0-9]+$"),
                CallbackQueryHandler(handle_description),
            ],
            State.HANDLE_CART: [
                CallbackQueryHandler(handle_menu, pattern="back"),
                CallbackQueryHandler(handle_location, pattern="checkout"),
                CallbackQueryHandler(handle_cart),
            ],
            State.HANDLE_WAITING: [
                MessageHandler(Filters.text, handle_customer_creation),
                MessageHandler(Filters.location, handle_customer_creation),
                CallbackQueryHandler(handle_cart, pattern="back"),
            ],
            State.HANDLE_DELIVERY: [
                # MessageHandler(Filters.text, handle_customer_creation),
                # MessageHandler(Filters.location, handle_customer_creation),
                CallbackQueryHandler(handle_delivery, pattern="delivery"),
            ],
        },
        fallbacks=[],
    )
    dispatcher.add_handler(conversation)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

    logger.info("Telegram bot started")


def main():
    logging.basicConfig(level=logging.INFO)

    load_dotenv()
    telegram_token = os.getenv("TELEGRAM_TOKEN")

    elastic_client_id = os.getenv("ELASTIC_CLIENT_ID")
    elastic_client_secret = os.getenv("ELASTIC_CLIENT_SECRET")
    elastic_token = elastic_api.get_credential_token(
        client_id=elastic_client_id, client_secret=elastic_client_secret
    )

    redis_connection = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        db=os.getenv("REDIS_NAME"),
        password=os.getenv("REDIS_PASSWORD"),
    )

    yandex_geocode_token = os.getenv("YANDEX_GEOCODE_TOKEN")

    run_bot(
        telegram_token=telegram_token,
        redis_connection=redis_connection,
        elastic_token=elastic_token,
        elastic_client_id=elastic_client_id,
        elastic_client_secret=elastic_client_secret,
        geocode_token=yandex_geocode_token,
    )


if __name__ == "__main__":
    main()
