#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from properties.cluster.ha_properties import collect_ha_properties
from properties.cluster.drs_properties import collect_drs_properties
from metrics.cluster.drs_metrics import collect_drs_metrics
from properties.cluster.evc_properties import collect_evc_properties
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_cluster_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
) -> None:
    container = content.rootFolder
    view_type = [vim.ClusterComputeResource]
    recursive = True
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )

    # Retrieve object types from the Aria Operations
    clusters: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["ClusterComputeResource"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the Aria Operations objects with the related identifier
    clusters_by_uuid: dict[str, Object] = {
        cluster.get_identifier_value("VMEntityObjectID"): cluster for cluster in clusters
    }

    # Push your metrics below
    children = container_view.view
    for cluster in children:
        cluster_obj = clusters_by_uuid.get(cluster._moId)
        if cluster_obj:
            collect_ha_properties(cluster_obj, cluster)
            collect_drs_properties(cluster_obj, cluster)
            collect_drs_metrics(cluster_obj, cluster)
            collect_evc_properties(cluster_obj, cluster)
            result.add_object(cluster_obj)
        else:
            logger.warning(
                f"Could not find Cluster '{cluster.name}' with MoID: {cluster._moId}."
            )