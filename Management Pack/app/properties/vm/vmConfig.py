#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os

NULL_STATUS = "null"
logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
#vmConfigs = os.path.join(current_directory, "../../constants/vm/vmConfigs.yaml")

def collect_vm_config_properties(vm_obj, vm, vmConfigs):
    for configPath in vmConfigs:
        try:
            keys = configPath.split('.')
            propertyValue = vm

            for key in keys:
                propertyValue = getattr(propertyValue, key)

            if propertyValue:
                visibleKeys = keys[1:] if keys[0] == "config" else keys
                #propertyName = "Config|" + "|".join(visibleKeys)
                propertyName = "vCommunity|Options|" + "|".join(visibleKeys)
                #vm_obj.with_property(propertyName, str(propertyValue))
                vm_obj.with_property(f"vCommunity|Options|{configPath}", str(propertyValue))
            else:
                logger.debug(f"Skipped None property: {configPath}")

        except AttributeError:
            logger.warning(f"Attribute not found on VM: {configPath} propertyValue: {propertyValue}")

        except Exception as e:
            logger.error(f"Error while collecting VM config {configPath}: {e}")






    #with open(vmConfigs, "r") as file:
    #    data = yaml.safe_load(file)
#
    #for group_name, group_content in data.items():
    #    if group_name and group_name == "Config" and "properties" in group_content:
    #        for item in group_content["properties"]:
    #            propertyName = item["name"]
    #            configPath = item["configPath"]
    #            keys = configPath.split('.')
    #            propertyValue = vm
    #            for key in keys:
    #                propertyValue = getattr(propertyValue, key)
    #            vm_obj.with_property(propertyName, str(propertyValue))