#  Copyright 2026 VCF Operations vCommunity Management Pack

import logging
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.world.cluster_summary_metrics import collect_cluster_summary_metrics
from metrics.world.availability_summary_metrics import collect_availability_summary_metrics

logger = logging.getLogger(__name__)


def collect_world_data(suite_api_client: SuiteApiClient, result: CollectResult) -> None:
    """Publishes the summary metrics on the vSphere World object. There is one, for all vCenters."""
    try:
        worlds: List[Object] = suite_api_client.query_for_resources(
            {"adapterKind": [VCENTER_ADAPTER_KIND], "resourceKind": ["vSphere World"]}
        )
        if not worlds:
            logger.debug("No vSphere World object found in VCF Operations. Skipping the summary metrics.")
            return

        world_obj = worlds[0]
        collect_cluster_summary_metrics(world_obj, suite_api_client)
        collect_availability_summary_metrics(world_obj, suite_api_client)
        result.add_object(world_obj)

    except Exception as e:
        logger.warning(f"Failed to collect vSphere World data - {repr(e)}")
