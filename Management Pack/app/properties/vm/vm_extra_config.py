#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)


def collect_vm_extraconfig_properties(vm_obj, vm_name, prop_dict, vmAdvParameters):
    try:
        extraConfigs = prop_dict.get("config.extraConfig", [])
        if not extraConfigs:
            return

        extraConfigDict = {ec.key: ec.value for ec in extraConfigs}

        for key in vmAdvParameters:
            if key in extraConfigDict:
                extraConfigValue = extraConfigDict[key]
                logger.debug(f"Found common extraConfig key {key} with value {extraConfigValue} - pushing property for VM {vm_name}")
                vm_obj.with_property(f"vCommunity|Configuration|Advanced Parameters|{key}",str(extraConfigValue))
            else:
                logger.debug(f"Can not find extraConfig key {key} not present for VM {vm_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve VM advanced parameter properties for : {vm_name} - {repr(e)}")