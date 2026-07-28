import logging

from logger import setup_logger
from sync import UniFiZabbixSync


def main():
    setup_logger()
    logger = logging.getLogger("main")
    try:
        sync = UniFiZabbixSync()
        sync.run()
    except Exception as e:
        logger.exception("Sync crashed: %s", e)


if __name__ == "__main__":
    main()
