import requests
import urllib3

from config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UniFiClient:

    def __init__(self):
        cfg = Config().get()

        self.base_url = cfg["unifi"]["url"]
        self.api_key = cfg["unifi"]["api_key"]
        self.site_id = cfg["unifi"]["site_id"]
        self.verify_ssl = cfg["unifi"]["verify_ssl"]

        self.headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json"
        }

    def get_devices(self):

        url = f"{self.base_url}/proxy/network/integration/v1/sites/{self.site_id}/devices"

        response = requests.get(
            url,
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=30
        )

        response.raise_for_status()

        return response.json()
