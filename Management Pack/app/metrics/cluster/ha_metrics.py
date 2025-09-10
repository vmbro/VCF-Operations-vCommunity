#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os

logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
clusterConfigs = os.path.join(current_directory, "../../constants/cluster/clusterConfigs.yaml")


# collect your ha metrics below
def collect_ha_metrics(cluster_obj, cluster):
    with open(clusterConfigs, "r") as file:
        data = yaml.safe_load(file)

    for group_name, group_content in data.items():
        if group_name and group_name == "vSphereHA" and "metrics" in group_content:
            for item in group_content["metrics"]:
                propertyName = item["name"]
                if cluster.configuration.drsConfig.enabled == False:
                    cluster_obj.with_metric(propertyName, 0)
                else:
                    configPath = item["configPath"]
                    keys = configPath.split('.')
                    propertyValue = cluster
                    for key in keys:
                        propertyValue = getattr(propertyValue, key)
                    cluster_obj.with_metric(propertyName, str(propertyValue))