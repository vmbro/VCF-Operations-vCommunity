#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import os
import yaml

logger = logging.getLogger(__name__)

current_directory = os.path.dirname(os.path.abspath(__file__))
#vmExtraConfig = os.path.join(current_directory, "../../constants/vm/vmExtraConfig.yaml")

def collect_vm_extraconfig_properties(vm_obj, vm, vmAdvParameters):

    extraConfigDict = {extraConfigKey.key: extraConfigKey.value for extraConfigKey in vm.config.extraConfig}
    commonKeys = [key for key in vmAdvParameters if key in extraConfigDict]
    for extraConfigKey in commonKeys:
        extraConfigValue = extraConfigDict[extraConfigKey]
        #vm_obj.with_property(f"vCommunity|Configuration|Advanced Parameters|{'|'.join(extraConfigKey.split('.'))}", extraConfigValue)
        vm_obj.with_property(f"vCommunity|Configuration|Advanced Parameters|{extraConfigKey}", extraConfigValue)









    #with open(vmExtraConfig, "r") as file:
    #    data = yaml.safe_load(file)
    #extraConfig = data.get("vmConfig", [])
    #extraConfigDict = {extraConfigKey.key: extraConfigKey.value for extraConfigKey in vm.config.extraConfig}
    #commonKeys = [key for key in extraConfig if key in extraConfigDict]
    #for extraConfigKey in commonKeys:
    #    extraConfigValue = extraConfigDict[extraConfigKey]
    #    vm_obj.with_property(f"Config|VM Agent|{'|'.join(extraConfigKey.split('.'))}", extraConfigValue)
