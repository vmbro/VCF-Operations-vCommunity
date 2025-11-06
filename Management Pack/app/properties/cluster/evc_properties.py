#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from constants.checkUpdatedValues import checkLastValue

NULL_STATUS = "null"
logger = logging.getLogger(__name__)


def collect_evc_properties(cluster_obj, cluster):
    evcEnabledKey = "vCommunity|Cluster Configuration|EVC|Enabled"
    evcModeKey = "vCommunity|Cluster Configuration|EVC|Mode"
    evcManager = cluster.EvcManager()
    evcState = evcManager.evcState
    currentEVCModeValue = evcState.currentEVCModeKey


    if currentEVCModeValue:
        isEnabled = "True"
        if checkLastValue(cluster_obj, evcEnabledKey, isEnabled, "property"):
            cluster_obj.with_property(evcEnabledKey, isEnabled)
    
        if checkLastValue(cluster_obj, evcModeKey, currentEVCModeValue, "property"):
            cluster_obj.with_property(evcModeKey, currentEVCModeValue)
    else:
        isEnabled = "False"
        if checkLastValue(cluster_obj, evcEnabledKey, isEnabled, "property"):
            cluster_obj.with_property(evcEnabledKey, isEnabled)
    
        if checkLastValue(cluster_obj, evcModeKey, NULL_STATUS, "property"):
            cluster_obj.with_property(evcModeKey, NULL_STATUS)