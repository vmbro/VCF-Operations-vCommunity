#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

def collect_vm_config_properties(vm_obj, vm_name, prop_dict, vmConfigs):
    try:
        for configPath in vmConfigs:
            value = prop_dict.get(configPath)

            if value is None:
                continue

            vm_obj.with_property(f"vCommunity|Options|{configPath}", str(value))
            logger.debug(f"VM config property {configPath} for {vm_name} has been pushed | Value: {value}")

    except Exception as e:
        logger.warning(f"Failed to retrieve VM configuration properties for : {vm_name} - {repr(e)}")