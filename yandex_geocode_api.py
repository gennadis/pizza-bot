import requests


def get_coordinates(yandex_token: str, address: str) -> tuple[str, str]:
    response = requests.get(
        url="https://geocode-maps.yandex.ru/1.x",
        params={
            "geocode": address,
            "apikey": yandex_token,
            "format": "json",
        },
    )
    response.raise_for_status()

    found_places = response.json()["response"]["GeoObjectCollection"]["featureMember"]
    most_relevant = found_places[0]
    longitude, latitude = most_relevant["GeoObject"]["Point"]["pos"].split(" ")

    return longitude, latitude
