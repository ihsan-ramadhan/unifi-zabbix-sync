import logging

from config import Config
from unifi import UniFiClient
from zabbix import ZabbixClient

logger = logging.getLogger(__name__)


class UniFiZabbixSync:

    def __init__(self):
        config_data = Config().get()
        self.unifi = UniFiClient()
        self.zbx = ZabbixClient()
        self.sync_cfg = config_data.get("sync", {})
        self.group_name = self.sync_cfg.get("host_group", "UniFi")
        self.host_groups_cfg = self.sync_cfg.get("host_groups", {})
        self.default_host_groups = {
            "uap": "UniFi AP",
            "usw": "UniFi Switch",
            "gateway": "UniFi Gateway",
            "default": self.group_name
        }
        self.group_cache = {}
        self.delete_missing = self.sync_cfg.get("delete_missing", False)
        self.template_mappings = self.sync_cfg.get("templates", {})

    def get_or_create_group(self, group_name):
        if group_name in self.group_cache:
            return self.group_cache[group_name]
        groups = self.zbx.zapi.hostgroup.get(filter={"name": group_name})
        if groups:
            group_id = groups[0]["groupid"]
        else:
            res = self.zbx.zapi.hostgroup.create(name=group_name)
            group_id = res["groupids"][0]
        self.group_cache[group_name] = group_id
        return group_id

    def get_group_name(self, dev_type):
        if dev_type in self.host_groups_cfg:
            return self.host_groups_cfg[dev_type]
        return self.default_host_groups.get(dev_type) or self.default_host_groups.get("default") or "UniFi"

    def get_template_ids(self):
        if not self.template_mappings:
            return {}
        zbx_templates = self.zbx.get_templates()
        name_to_id = {t["host"]: t["templateid"] for t in zbx_templates}
        return {
            dev_type: name_to_id[tpl]
            for dev_type, tpl in self.template_mappings.items()
            if tpl in name_to_id
        }

    def run(self):
        try:
            unifi_devices = self.unifi.get_devices()
        except Exception as e:
            logger.error("UniFi fetch failed: %s", e)
            return

        try:
            managed_group_names = set()
            for gname in self.host_groups_cfg.values():
                managed_group_names.add(gname)
            for gname in self.default_host_groups.values():
                managed_group_names.add(gname)

            managed_group_ids = [self.get_or_create_group(name) for name in sorted(managed_group_names)]
            template_ids = self.get_template_ids()

            zbx_hosts = self.zbx.zapi.host.get(
                groupids=managed_group_ids,
                output=["hostid", "host", "name"],
                selectGroups=["groupid", "name"],
                selectInterfaces=["interfaceid", "ip", "main", "type", "port", "details"],
                selectInventory=["macaddress_a", "model", "software", "hardware"]
            )
        except Exception as e:
            logger.error("Zabbix fetch failed: %s", e)
            return

        zbx_map = {h["host"].lower(): h for h in zbx_hosts}
        seen_hosts = set()

        for dev in unifi_devices:
            mac = dev.get("macAddress", "").lower()
            ip = dev.get("ipAddress")
            if not mac or not ip:
                continue

            host_key = mac.replace(":", "")
            seen_hosts.add(host_key)

            dev_name = dev.get("name") or dev.get("model") or f"UniFi {mac}"

            # Detect device type from features array
            features = dev.get("features", [])
            if "accessPoint" in features:
                dev_type = "uap"
            elif "switching" in features:
                dev_type = "usw"
            elif "gateway" in features or "routing" in features:
                dev_type = "gateway"
            else:
                dev_type = "default"

            gname = self.get_group_name(dev_type)
            group_id = self.get_or_create_group(gname)

            tpl_id = template_ids.get(dev_type) or template_ids.get("default")
            templates = [{"templateid": tpl_id}] if tpl_id else []

            # Interface setup: SNMP (Type 2), port 161, version 2c, community public
            # ponytail: SNMP details hardcoded. Upgrade to configurable SNMP v2/v3 when needed.
            interface_details = {
                "version": 2,
                "bulk": 1,
                "community": "public"
            }

            zbx_host = zbx_map.get(host_key)
            if not zbx_host:
                try:
                    self.zbx.zapi.host.create(
                        host=host_key,
                        name=dev_name,
                        groups=[{"groupid": group_id}],
                        templates=templates,
                        interfaces=[{
                            "type": 2,  # SNMP
                            "main": 1,
                            "useip": 1,
                            "ip": ip,
                            "dns": "",
                            "port": "161",
                            "details": interface_details
                        }],
                        inventory_mode=0,
                        inventory={
                            "macaddress_a": mac,
                            "model": dev.get("model", ""),
                            "software": dev.get("firmwareVersion", ""),
                            "hardware": dev_type
                        }
                    )
                    logger.info("Created host %s (%s) in group %s", dev_name, host_key, gname)
                except Exception as e:
                    logger.error("Host create failed %s: %s", host_key, e)
            else:
                hostid = zbx_host["hostid"]
                updates = {}

                if zbx_host["name"] != dev_name:
                    updates["name"] = dev_name

                # Check if group needs to be updated
                current_group_ids = {g["groupid"] for g in zbx_host.get("groups", [])}
                if current_group_ids != {group_id}:
                    updates["groups"] = [{"groupid": group_id}]

                # Primary SNMP interface update check
                primary = next((i for i in zbx_host.get("interfaces", []) if i["main"] == "1" and i["type"] == "2"), None)
                if primary:
                    if primary["ip"] != ip:
                        try:
                            self.zbx.zapi.hostinterface.update(
                                interfaceid=primary["interfaceid"],
                                ip=ip
                            )
                            logger.info("Updated IP for %s: %s", dev_name, ip)
                        except Exception as e:
                            logger.error("Interface update failed %s: %s", dev_name, e)
                else:
                    try:
                        self.zbx.zapi.hostinterface.create(
                            hostid=hostid,
                            type=2,
                            main=1,
                            useip=1,
                            ip=ip,
                            dns="",
                            port="161",
                            details=interface_details
                        )
                    except Exception as e:
                        logger.error("Interface create failed %s: %s", dev_name, e)

                current_inv = zbx_host.get("inventory") or {}
                new_inv = {
                    "macaddress_a": mac,
                    "model": dev.get("model", ""),
                    "software": dev.get("firmwareVersion", ""),
                    "hardware": dev_type
                }
                inv_updates = {k: v for k, v in new_inv.items() if current_inv.get(k) != v}
                if inv_updates:
                    updates["inventory"] = inv_updates

                if updates:
                    try:
                        self.zbx.zapi.host.update(hostid=hostid, **updates)
                        logger.info("Updated host %s attributes", dev_name)
                    except Exception as e:
                        logger.error("Host update failed %s: %s", dev_name, e)

        if self.delete_missing:
            for host_key, zbx_host in zbx_map.items():
                if host_key not in seen_hosts:
                    try:
                        self.zbx.zapi.host.delete(zbx_host["hostid"])
                        logger.info("Deleted host %s", zbx_host["name"])
                    except Exception as e:
                        logger.error("Host delete failed %s: %s", zbx_host["name"], e)
