#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import os

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_vm_config_properties(vm_obj, vm, vmConfigs):
    for configPath in vmConfigs:
        try:
            keys = configPath.split('.')
            propertyValue = vm

            for key in keys:
                propertyValue = getattr(propertyValue, key)

            if propertyValue:
                vm_obj.with_property(f"vCommunity|Options|{configPath}", str(propertyValue))
            else:
                logger.debug(f"Skipped None property: {configPath}")

        except AttributeError:
            logger.warning(f"Attribute not found on VM: {configPath} propertyValue: {propertyValue}")

        except Exception as e:
            logger.error(f"Error while collecting VM config {configPath}: {e}")