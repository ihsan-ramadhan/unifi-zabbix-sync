import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


class Config:

    def __init__(self):
        root = Path(__file__).resolve().parent.parent

        load_dotenv(root / ".env")

        config_file = root / "config" / "config.yaml"
        with open(config_file, "r") as f:
            data = yaml.safe_load(f) or {}

        data.setdefault("unifi", {})
        data["unifi"]["url"] = os.environ["UNIFI_URL"]
        data["unifi"]["api_key"] = os.environ["UNIFI_API_KEY"]
        data["unifi"]["site_id"] = os.environ["UNIFI_SITE_ID"]
        data["unifi"]["verify_ssl"] = os.environ.get("UNIFI_VERIFY_SSL", "true").lower() == "true"

        data.setdefault("zabbix", {})
        data["zabbix"]["url"] = os.environ["ZABBIX_URL"]
        data["zabbix"]["token"] = os.environ["ZABBIX_TOKEN"]

        self.data = data

    def get(self):
        return self.data
