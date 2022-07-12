import requests
import json
import string
import random


SYMBOLS = string.ascii_letters + string.digits

def generate_id():
    """Generates a random sequence for use with the Wildberries API.
    """
    return ''.join(random.sample(SYMBOLS, 36))

class WbApi:
    def __init__(self, auth_token):
        self.api_url = 'https://suppliers-api.wildberries.ru'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_token,
        }
        self.data = {"jsonrpc": "2.0"}

    def parent_category_list(self):
        """Returns list of all available parent categories.
        """
        _url = f'{self.api_url}/api/v1/config/get/object/parent/list'
        return requests.get(_url, headers=self.headers)

    def categories_by_parent(self, parent):
        """Returns list of all available parent categories.
        """
        _url = f'{self.api_url}/api/v1/config/object/byparent'
        _params = {'parent': parent}
        return requests.get(_url, headers=self.headers, params=_params)

    def dictionaries(self):
        """Returns dictionaries and the number of values in them.
        """
        _url = f'{self.api_url}/api/v1/directory/get/list'
        return requests.get(_url, headers=self.headers)

    def dictionary_values(self, dictionary, amount):
        """Returns all available dictionary values.
        """
        _url = f'{self.api_url}/api/v1/directory{dictionary}'
        _params = {
            'top': amount,
        }
        return requests.get(_url, headers=self.headers, params=_params)
        