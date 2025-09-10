
#  Copyright 2025 vCommunity Content MP
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging
from datetime import datetime, timezone   

logger = logging.getLogger(__name__)

def collect_host_install_date(host_obj, host):
    imageConfigManager = host.configManager.imageConfigManager
    if imageConfigManager:
        try:
            install_dt = imageConfigManager.installDate()  # datetime in UTC (vim.DateTime)
            if install_dt:
                dt_utc = install_dt.astimezone(timezone.utc)
                host_obj.with_property("Config|Install Date|UTC", dt_utc.isoformat())
                host_obj.with_property("Config|Install Date|EpochSeconds", int(dt_utc.timestamp()))
            else:
                host_obj.with_property("Config|Install Date|UTC", "unknown")
        except Exception as e:
            logger.exception(f"Failed to retrieve install date for host '{host.name}' (MoID: {host._moId}): {e}")
