#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os
from constants.checkUpdatedValues import checkLastValue

NULL_STATUS = "null"
logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
clusterConfigs = os.path.join(current_directory, "../../constants/cluster/clusterConfigs.yaml")


def collect_ha_properties(cluster_obj, cluster):
    with open(clusterConfigs, "r") as file:
        data = yaml.safe_load(file)

    for group_name, group_content in data.items():
        if group_name and group_name == "vSphereHA" and "properties" in group_content:
            for item in group_content["properties"]:
                propertyName = item["name"]
                if cluster.configuration.dasConfig.enabled == False or cluster.configuration.dasConfig.hostMonitoring == 'disabled':
                    #cluster_obj.with_property(propertyName, NULL_STATUS)
                    if checkLastValue(cluster_obj, propertyName, NULL_STATUS, "property"):
                        cluster_obj.with_property(propertyName, NULL_STATUS)
                else:
                    configPath = item["configPath"]
                    keys = configPath.split('.')
                    propertyValue = cluster
                    for key in keys:
                        propertyValue = getattr(propertyValue, key)
                    #cluster_obj.with_property(propertyName, str(propertyValue))
                    if checkLastValue(cluster_obj, propertyName, str(propertyValue), "property"):
                        cluster_obj.with_property(propertyName, str(propertyValue))