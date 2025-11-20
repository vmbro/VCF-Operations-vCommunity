#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)


def collect_vm_extraconfig_properties(vm_obj, vm, vmAdvParameters):

    extraConfigDict = {extraConfigKey.key: extraConfigKey.value for extraConfigKey in vm.config.extraConfig}
    commonKeys = [key for key in vmAdvParameters if key in extraConfigDict]
    for extraConfigKey in commonKeys:
        extraConfigValue = extraConfigDict[extraConfigKey]
        vm_obj.with_property(f"vCommunity|Configuration|Advanced Parameters|{extraConfigKey}", extraConfigValue)