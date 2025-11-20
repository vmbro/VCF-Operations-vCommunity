#  Copyright 2025 vCommunity MP
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging
from datetime import timezone
from aria.ops.event import Criticality

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_host_install_date(host_obj, host):
    imageConfigManager = host.configManager.imageConfigManager
    if imageConfigManager:
        try:
            install_dt = imageConfigManager.installDate()  # datetime in UTC (vim.DateTime)
            if install_dt:
                dt_utc = install_dt.astimezone(timezone.utc)
                host_obj.with_property("vCommunity|Configuration|Install Date|UTC", dt_utc.isoformat())
            else:
                host_obj.with_property("vCommunity|Configuration|Install Date|UTC", NULL_STATUS)
        except Exception as e:
            message = f"Failed to retrieve install date for host '{host.name}' (MoID: {host._moId}): {e}"
            logger.exception(message)
            host_obj.with_event(message = message, criticality=Criticality.CRITICAL)