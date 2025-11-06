#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os
from datetime import datetime, timezone


NULL_STATUS = "null"
logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
vmConfigs = os.path.join(current_directory, "../../constants/vm/vmConfigs.yaml")


def getVMAge(vmCreateDate):
    vmCreateDate = str(vmCreateDate)
    vmCreateDate = datetime.fromisoformat(vmCreateDate)
    now = datetime.now(timezone.utc)
    if vmCreateDate > now:
        vmAge = NULL_STATUS
    else:
        vmAge = (now - vmCreateDate).days

    return vmAge


def collect_vm_Age_metrics(vm_obj, vm):
    with open(vmConfigs, "r") as file:
        data = yaml.safe_load(file)

    for group_name, group_content in data.items():
        if group_name and group_name == "Age" and "properties" in group_content:
            for item in group_content["properties"]:
                propertyName = item["name"]
                configPath = item["configPath"]
                keys = configPath.split('.')
                propertyValue = vm
                for key in keys:
                    propertyValue = getattr(propertyValue, key)
                propertyValue = getVMAge(propertyValue)
                if not propertyValue == NULL_STATUS:
                    vm_obj.with_metric(propertyName, str(propertyValue))