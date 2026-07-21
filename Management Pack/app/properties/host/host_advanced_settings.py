#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

def collect_host_properties(host_obj, host_name, prop_dict, esxiAdvSettings):
    try:
        options = prop_dict.get("config.option", [])

        advancedSettingsDict = {
            opt.key: opt.value
            for opt in options
            if hasattr(opt, "key")
        }

        for key in esxiAdvSettings:
            if key in advancedSettingsDict:
                value = advancedSettingsDict[key]
                host_obj.with_property(f"vCommunity|Configuration|Advanced System Settings|{key}", str(value))
                logger.debug(f"Found common advanced setting key {key} with value {value} - pushing property for host {host_name}")
            else:
                logger.debug(f"Can not find host advanced setting key {key} not present for host {host_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve ESX advanced parameter properties for : {host_name} - {repr(e)}")