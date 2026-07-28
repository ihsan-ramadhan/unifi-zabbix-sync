from zabbix import ZabbixClient


def main():

    zbx = ZabbixClient()

    templates = zbx.get_templates()

    print(f"Total Template : {len(templates)}")

    for template in templates:
        print(template)


if __name__ == "__main__":
    main()
