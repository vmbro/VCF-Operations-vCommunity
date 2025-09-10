#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging


NULL_STATUS = "null"
logger = logging.getLogger(__name__)


def collect_evc_properties(cluster_obj, cluster):
    evcManager=cluster.EvcManager()
    evcState=evcManager.evcState
    currentEVCModeKey= evcState.currentEVCModeKey
    if(currentEVCModeKey):
            cluster_obj.with_property("configuration|EVC|Enabled", "True")
            cluster_obj.with_property("configuration|EVC|EVC Mode", currentEVCModeKey)
    else:
            cluster_obj.with_property("configuration|EVC|Enabled", "False")
            cluster_obj.with_property("configuration|EVC|EVC Mode", NULL_STATUS)