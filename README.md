# Fish Store Telegram Bot

This project is a simple telegram `pizza store bot`.
Powered by [Elasticpath Commerce Cloud CMS](https://www.elasticpath.com/elastic-path-commerce-cloud)

## Examples
Try this telegram bot: `@dvmn_pizzeria_bot`

## Features
- `long polling` Telegram API utilization
- `Elasticpath` (Moltin) CMS integration
- Create customer in `Elasticpath`
- Get all available `Elasticpath` products
- Get detailed `Elasticpath` product description
- Add or delete products from `Elasticpath` cart
- Get total price and products in `Elasticpath` cart
- Get user location for delivery distance / price calculation
- Get payments through built-in `Telegram` payments API method

## Installation
1. Clone project
```bash
git clone https://github.com/gennadis/pizza-bot.git
cd pizza-bot
```

2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install requirements
```bash
pip install -r requirements.txt
```

4. Rename `.env.example` to `.env` and fill your secrets in it.  
```bash
ELASTICPATH_CLIENT_ID=your_elasticpath_client_id
ELASTICPATH_CLIENT_SECRET=your_elasticpath_client_secret

TELEGRAM_TOKEN=your_telegram_bot_token

REDIS_HOST=your_redis_host
REDIS_PORT=your_redis_port
REDIS_PASSWORD=your_redis_db_password
REDIS_NAME=0

YANDEX_GEOCODE_TOKEN=your_geocode_token 
SBER_PAYMENT_TOKEN=your_payment_token
```

5. Run bot
```bash
python telegram_bot.py
```
