from pyzabbix import ZabbixAPI
from config import Config


class ZabbixClient:

    def __init__(self):

        cfg = Config().get()

        self.zapi = ZabbixAPI(cfg["zabbix"]["url"])
        self.zapi.login(api_token=cfg["zabbix"]["token"])

    def get_hosts(self):

        return self.zapi.host.get(
            output=["host", "hostid"]
        )

    def get_host_groups(self):

        return self.zapi.hostgroup.get(
            output=["groupid", "name"]
        )

    def get_templates(self):

        return self.zapi.template.get(
            output=["templateid", "host"]
        )

    def get_host_detail(self, hostid):

        return self.zapi.host.get(
            hostids=hostid,
            output="extend",
            selectGroups=["groupid", "name"],
            selectParentTemplates=["templateid", "host"],
            selectInterfaces="extend",
            selectInventory="extend"
        )
