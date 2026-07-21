#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_cluster_configuration_properties(cluster_obj, cluster_name, prop_dict):
    try:
        configStatus = "vCommunity|Cluster Configuration|Configuration Status"
        numEffectiveHosts = "vCommunity|Cluster Configuration|Number of Effective Hosts"
        overallStatus = "vCommunity|Cluster Configuration|Overall Status"

        configStatusValue = prop_dict.get("configStatus")
        numEffectiveHostsValue = prop_dict.get("summary.numEffectiveHosts", 0)
        overallStatusValue = prop_dict.get("overallStatus")

        cluster_obj.with_property(configStatus, str(configStatusValue))
        cluster_obj.with_metric(numEffectiveHosts, int(numEffectiveHostsValue))
        cluster_obj.with_property(overallStatus, str(overallStatusValue))
        
        logger.debug(f"Successfully collected vSphere Cluster configuration properties for : {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster configuration properties for : {cluster_name} - {repr(e)}")