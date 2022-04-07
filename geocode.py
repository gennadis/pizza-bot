from geopy import distance

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


def calculate_distsnce(point_a: tuple[str, str], point_b: tuple[str, str]) -> float:
    return distance.distance(point_a, point_b).km


def get_nearest_pizzeria(user_coordinates: tuple[str, str], pizzerias: list[dict]):
    for pizzeria in pizzerias:
        pizzeria_coordinates = (
            pizzeria["longitude"],
            pizzeria["latitude"],
        )
        pizzeria["distance"] = distance.distance(
            user_coordinates, pizzeria_coordinates
        ).km

    return min(pizzerias, key=lambda x: x["distance"])
