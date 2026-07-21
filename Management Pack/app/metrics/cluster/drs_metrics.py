#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)


def collect_drs_metrics(cluster_obj, cluster_name, prop_dict):
    try:
        drsScore = "vCommunity|Cluster Configuration|DRS|DRS Score"
        drsSummary = prop_dict.get("summary")
        drsScoreValue= getattr(drsSummary, "drsScore")
        drsEnabled = prop_dict.get("configuration.drsConfig.enabled")

        if not drsEnabled:
            cluster_obj.with_metric(drsScore, 0)

        elif drsScoreValue < 0:
            cluster_obj.with_metric(drsScore, 0)

        else:
            cluster_obj.with_metric(drsScore, int(drsScoreValue))

        logger.debug(f"Successfully collected vSphere Cluster DRS metrics for the cluster: {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster DRS metrics for : {cluster_name} - {repr(e)}")