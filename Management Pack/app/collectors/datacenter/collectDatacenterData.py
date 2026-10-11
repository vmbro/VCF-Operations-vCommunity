#  Copyright 2026 VCF Operations vCommunity Management Pack

import logging
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.network.network_speed_degradation import NetworkSpeed, NO_DATA, COUNT_METRIC, publish

logger = logging.getLogger(__name__)


def collect_datacenter_data(
    suite_api_client: SuiteApiClient, adapter_instance_id: str, result: CollectResult,
    network_speed: NetworkSpeed = NO_DATA,
) -> None:
    """Publishes Total Network Speed Degradation on the Datacenters of this vCenter, matched by name."""
    try:
        datacenters: List[Object] = suite_api_client.query_for_resources(
            {"adapterKind": [VCENTER_ADAPTER_KIND], "resourceKind": ["Datacenter"],
             "adapterInstanceId": [adapter_instance_id]}
        )
        for datacenter_obj in datacenters:
            count = network_speed.count_by_datacenter.get(datacenter_obj.get_key().name)
            if count is not None:
                publish(datacenter_obj, COUNT_METRIC, count)
                result.add_object(datacenter_obj)
    except Exception as e:
        logger.warning(f"Failed to collect Datacenter data - {repr(e)}")
