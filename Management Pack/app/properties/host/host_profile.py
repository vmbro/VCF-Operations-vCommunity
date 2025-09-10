#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os
from datetime import datetime, timezone

NULL_STATUS = "null"
logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
hostConfigs = os.path.join(current_directory, "../../constants/host/hostProfile.yaml")


def collect_host_profile_properties(host_obj, host):
    with open(hostConfigs, "r") as file:
        data = yaml.safe_load(file)

    for group_name, group_content in data.items():
        if group_name and group_name == "Host Profile" and "properties" in group_content:
            for item in group_content["properties"]:
                propertyName = item["name"]
                if host.complianceCheckResult is not None:
                    configPath = item["configPath"]
                    keys = configPath.split('.')
                    propertyValue = host
                    for key in keys:
                        propertyValue = getattr(propertyValue, key) or NULL_STATUS
                    if configPath == "complianceCheckResult.checkTime":
                        propertyValue = getLastCheckAge(propertyValue) or NULL_STATUS
                    host_obj.with_property(propertyName, str(propertyValue))                    
                else:
                    host_obj.with_property(propertyName, NULL_STATUS)


def getLastCheckAge(propertyValue):
    timestamp = str(propertyValue)
    timestamp = datetime.fromisoformat(timestamp)
    now = datetime.now(timezone.utc)
    if timestamp > now:
        lastCheckTime = "Invalid date"
    elif (now - timestamp).days == 0:
        lastCheckTime = "Today"
    else:
        lastCheckTime = (now - timestamp).days
    return lastCheckTime