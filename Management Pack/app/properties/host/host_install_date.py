#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging
from datetime import timezone

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_host_install_date(host_obj, host_name, prop_dict):
    imageConfigManager = prop_dict.get("configManager.imageConfigManager")
    
    if not imageConfigManager:
        host_obj.with_property("vCommunity|Configuration|Install Date|UTC", NULL_STATUS)
        return

    try:
        installDate = imageConfigManager.installDate()
        if installDate:
            dt_utc = installDate.astimezone(timezone.utc)
            host_obj.with_property("vCommunity|Configuration|Install Date|UTC", str(dt_utc.isoformat()))
            logger.debug(f"Successfully retrieved install date for host '{host_name}': {dt_utc.isoformat()}")
        else:
            host_obj.with_property("vCommunity|Configuration|Install Date|UTC", NULL_STATUS)
            
    except Exception as e:
        logger.debug(f"Could not retrieve install date for host {host_name}: {repr(e)}")
        host_obj.with_property("vCommunity|Configuration|Install Date|UTC", NULL_STATUS)