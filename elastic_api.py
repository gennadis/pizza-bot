from pprint import pprint

import requests


def get_json_data(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def main():
    pizza_addresses_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904587/128/"
    )
    pizza_menus_data = get_json_data(
        url="https://dvmn.org/filer/canonical/1558904588/129/"
    )

    pprint(pizza_addresses_data)
    pprint(pizza_menus_data)


if __name__ == "__main__":
    main()
