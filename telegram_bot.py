import logging
import os
import time
from enum import Enum, auto
from textwrap import dedent

import redis
from dotenv import load_dotenv
from telegram import Update, LabeledPrice

from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
    PreCheckoutQueryHandler,
)

import elastic_api
import keyboards
import geocode


logger = logging.getLogger(__file__)


class State(Enum):
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_CART = auto()
    HANDLE_LOCATION = auto()
    HANDLE_DELIVERY = auto()
    HANDLE_PAYMENT = auto()


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
    welcome_text, menu_markup = keyboards.get_menu_markup(
        elastic_token=context.bot_data.get("elastic"),
        user_first_name=update.effective_user.first_name,
    )

    update.effective_message.reply_text(
        text=dedent(welcome_text),
        reply_markup=menu_markup,
    )
    update.effective_message.delete()

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def handle_description(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    context.bot_data["product_id"] = query.data

    (
        picture_href,
        product_description,
        description_markup,
    ) = keyboards.get_description_markup(
        elastic_token=context.bot_data.get("elastic"),
        product_id=query.data,
        user_id=update.effective_user.id,
    )

    update.effective_user.send_photo(
        photo=picture_href,
        caption=dedent(product_description),
        reply_markup=description_markup,
    )
    update.effective_message.delete()

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def handle_add_to_cart(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    query.answer("Товар добавлен в корзину")

    elastic_api.add_product_to_cart(
        credential_token=context.bot_data.get("elastic"),
        product_id=context.bot_data["product_id"],
        quantity=int(query.data),
        cart_id=update.effective_user.id,
    )

    return State.HANDLE_DESCRIPTION


@validate_token_expiration
def handle_delete_from_cart(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    query.answer("Товар удален из корзины")

    elastic_api.delete_product_from_cart(
        credential_token=context.bot_data.get("elastic"),
        cart_id=update.effective_user.id,
        product_id=query.data,
    )
    handle_cart(update, context)

    return State.HANDLE_CART


@validate_token_expiration
def handle_cart(update: Update, context: CallbackContext) -> State:
    cart_summary_text, cart_markup = keyboards.get_cart_markup(
        elastic_token=context.bot_data.get("elastic"),
        cart_id=update.effective_user.id,
    )

    update.effective_user.send_message(
        text=dedent(cart_summary_text),
        reply_markup=cart_markup,
    )
    update.effective_message.delete()

    return State.HANDLE_CART


@validate_token_expiration
def handle_location(update: Update, context: CallbackContext) -> State:
    query = update.callback_query
    location_text, location_markup = keyboards.get_location_markup(
        user_first_name=update.effective_user.first_name
    )

    update.effective_user.send_message(
        text=dedent(location_text),
        reply_markup=location_markup,
    )
    update.effective_message.delete()

    return State.HANDLE_LOCATION


@validate_token_expiration
def handle_delivery(update: Update, context: CallbackContext) -> State:
    # address was sent in location with coordinates format
    if update.message.location:
        user_coordinates = (
            update.message.location.longitude,
            update.message.location.latitude,
        )

    # address was sent in text format
    else:
        try:
            user_coordinates = geocode.get_coordinates(
                yandex_token=context.bot_data.get("geocode"),
                address=update.message.text,
            )

        # address wasn't recognized
        except IndexError:
            location_text, location_markup = keyboards.get_location_markup(
                user_first_name=update.effective_user.first_name
            )
            update.effective_user.send_message("Адрес не распознан. Повторите попытку.")
            update.effective_user.send_message(
                text=dedent(location_text),
                reply_markup=location_markup,
            )
            update.effective_message.delete()
            return State.HANDLE_LOCATION

    (
        nearest_pizzeria,
        delivery_details,
        delivery_markup,
    ) = keyboards.get_delivery_markup(
        elastic_token=context.bot_data.get("elastic"),
        user_coordinates=user_coordinates,
        user_id=update.effective_user.id,
    )
    context.bot_data["pizzeria"] = nearest_pizzeria
    context.bot_data["coordinates"] = user_coordinates

    update.effective_user.send_message(
        text=dedent(delivery_details),
        reply_markup=delivery_markup,
    )
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
    )

    return State.HANDLE_DELIVERY


def handle_courier_notification(update: Update, context: CallbackContext) -> State:
    pizzeria_courier = context.bot_data["pizzeria"]["courier"]
    longitude, latitude = context.bot_data["coordinates"]

    context.bot.send_message(
        chat_id=pizzeria_courier,
        text="Сообщение для курьера. Доставьте заказ.",
    )
    context.bot.send_location(
        chat_id=pizzeria_courier,
        longitude=longitude,
        latitude=latitude,
    )

    handle_payment(update, context)

    context.job_queue.run_once(
        callback=remind_delivery_status,
        when=10,  # seconds
        context=update.effective_user.id,
    )

    return State.HANDLE_DELIVERY


def remind_delivery_status(context: CallbackContext):
    job = context.job
    context.bot.send_message(
        chat_id=job.context,
        text=dedent(
            f"""
            Приятного аппетита! *место для рекламы*
            *сообщение что делать если пицца не пришла*
            """
        ),
    )

    return State.HANDLE_DELIVERY


def handle_pickup(update: Update, context: CallbackContext) -> State:
    pickup_text, pickup_markup = keyboards.get_pickup_markup(
        nearest_pizzeria=context.bot_data["pizzeria"]
    )

    update.effective_user.send_message(
        text=dedent(pickup_text),
        reply_markup=pickup_markup,
    )
    update.effective_message.delete()

    return State.HANDLE_DELIVERY


def handle_payment(update: Update, context: CallbackContext) -> State:
    context.bot.sendInvoice(
        chat_id=update.effective_user.id,
        title="Pizza payment",
        description="Pizza payment description",
        payload=f"user_id {update.effective_user.id}",
        provider_token=context.bot_data.get("payment_token"),
        start_parameter="test-payment",
        currency="RUB",
        prices=[LabeledPrice("Test", 123 * 100)],
    )

    return State.HANDLE_PAYMENT


def precheckout_callback(update: Update, context: CallbackContext) -> State:
    query = update.pre_checkout_query

    if query.invoice_payload != f"user_id {update.effective_user.id}":
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id,
            ok=False,
            error_message="Something went wrong...",
        )
    else:
        context.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


def run_bot(
    telegram_token: str,
    redis_connection: redis.Redis,
    elastic_token: str,
    elastic_client_id: str,
    elastic_client_secret: str,
    geocode_token: str,
    payment_token: str,
):
    updater = Updater(token=telegram_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.bot_data["redis"] = redis_connection
    dispatcher.bot_data["elastic"] = elastic_token["access_token"]
    dispatcher.bot_data["token_expires"] = elastic_token["expires"]
    dispatcher.bot_data["elastic_client_id"] = elastic_client_id
    dispatcher.bot_data["elastic_client_secret"] = elastic_client_secret
    dispatcher.bot_data["geocode"] = geocode_token
    dispatcher.bot_data["payment_token"] = payment_token

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
                CallbackQueryHandler(handle_add_to_cart, pattern="^[0-9]+$"),
                CallbackQueryHandler(handle_description),
            ],
            State.HANDLE_CART: [
                CallbackQueryHandler(handle_menu, pattern="back"),
                CallbackQueryHandler(handle_location, pattern="checkout"),
                CallbackQueryHandler(handle_delete_from_cart, pattern="[0-9a-zA-Z_-]+"),
                CallbackQueryHandler(handle_cart),
            ],
            State.HANDLE_LOCATION: [
                MessageHandler(Filters.text, handle_delivery),
                MessageHandler(Filters.location, handle_delivery),
                CallbackQueryHandler(handle_menu, pattern="back"),
            ],
            State.HANDLE_DELIVERY: [
                CallbackQueryHandler(
                    handle_courier_notification, pattern="delivery", pass_job_queue=True
                ),
                CallbackQueryHandler(handle_pickup, pattern="pickup"),
            ],
            State.HANDLE_PAYMENT: [
                CallbackQueryHandler(handle_payment, pattern="pay"),
            ],
        },
        fallbacks=[],
    )
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
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
    sber_payment_token = os.getenv("SBER_PAYMENT_TOKEN")

    run_bot(
        telegram_token=telegram_token,
        redis_connection=redis_connection,
        elastic_token=elastic_token,
        elastic_client_id=elastic_client_id,
        elastic_client_secret=elastic_client_secret,
        geocode_token=yandex_geocode_token,
        payment_token=sber_payment_token,
    )


if __name__ == "__main__":
    main()
