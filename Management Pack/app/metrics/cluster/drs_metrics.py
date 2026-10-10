#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com
"""DRS Score.

What it is
----------
vCenter's own DRS Score for a cluster, from 0 to 100. A high score means the
VMs in the cluster are getting the resources they need. This is a plain metric:
it is read from vCenter and published as it is. It is not a KPI and does not
use metrics/kpi_score.py.

Published on the cluster as:
    vCommunity|Cluster Configuration|DRS|DRS Score

Where the value comes from
--------------------------
The "summary" property of the cluster in vCenter (summary.drsScore). It is read
by the cluster collector, together with the other cluster properties.

Special cases
-------------
The score is published as 0 when DRS is disabled, and when vCenter reports a
negative score.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Overall approach for all metrics: metrics/README.md
"""

import logging

logger = logging.getLogger(__name__)


def collect_drs_metrics(cluster_obj, cluster_name, prop_dict):
    """Publishes the DRS Score of one cluster. prop_dict holds the cluster properties read from vCenter."""
    try:
        drsScore = "vCommunity|Cluster Configuration|DRS|DRS Score"
        drsSummary = prop_dict.get("summary")
        drsScoreValue= getattr(drsSummary, "drsScore")
        drsEnabled = prop_dict.get("configuration.drsConfig.enabled")

        # DRS is off, so vCenter has no meaningful score for this cluster
        if not drsEnabled:
            cluster_obj.with_metric(drsScore, 0)

        # A negative score is not a real score
        elif drsScoreValue < 0:
            cluster_obj.with_metric(drsScore, 0)

        # The normal case: publish the score as a whole number
        else:
            cluster_obj.with_metric(drsScore, int(drsScoreValue))

        logger.debug(f"Successfully collected vSphere Cluster DRS metrics for the cluster: {cluster_name}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data
        logger.warning(f"Failed to retrieve vSphere Cluster DRS metrics for : {cluster_name} - {repr(e)}")
