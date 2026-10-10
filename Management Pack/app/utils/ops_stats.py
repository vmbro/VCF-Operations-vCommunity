#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reads stats that VCF Operations already holds (collected by the vCenter adapter)."""
import logging
import time
from typing import Dict, List
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)

LATEST_STATS_PATH = "api/resources/stats/latest"
STATS_QUERY_PATH = "api/resources/stats/query"

COLLECTION_CYCLE_MINUTES = 5

# One request asks for at most this many resources. A VM KPI needs stats for every VM,
# and a single request for thousands of VMs is slow and can time out.
RESOURCES_PER_REQUEST = 1000


def read_latest_stats(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str]
) -> Dict[str, Dict[str, float]]:
    """Returns {resource id: {stat key: latest value}}. Stats with no data are absent."""
    query = {"resourceId": resource_ids, "statKey": stat_keys}
    samples_by_resource = _query_stats(suite_api_client, LATEST_STATS_PATH, query)
    return {
        resource_id: {stat_key: samples[-1] for stat_key, samples in samples_by_key.items()}
        for resource_id, samples_by_key in samples_by_resource.items()
    }


def read_stat_totals(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str], window_minutes: int
) -> Dict[str, Dict[str, float]]:
    """Returns {resource id: {stat key: total over the last window_minutes}}."""
    now_ms = int(time.time() * 1000)
    query = {
        "resourceId": resource_ids,
        "statKey": stat_keys,
        "begin": now_ms - window_minutes * 60 * 1000,
        "end": now_ms,
        "rollUpType": "AVG",
        "intervalType": "MINUTES",
        "intervalQuantifier": COLLECTION_CYCLE_MINUTES,
    }
    samples_by_resource = _query_stats(suite_api_client, STATS_QUERY_PATH, query)
    return {
        resource_id: {stat_key: sum(samples) for stat_key, samples in samples_by_key.items()}
        for resource_id, samples_by_key in samples_by_resource.items()
    }


def _query_stats(suite_api_client: SuiteApiClient, path: str, query: dict) -> Dict[str, Dict[str, List[float]]]:
    """Returns {resource id: {stat key: [samples, oldest first]}}. Resources of a failed request are absent."""
    resource_ids = query["resourceId"]
    samples_by_resource = {}

    for start in range(0, len(resource_ids), RESOURCES_PER_REQUEST):
        request = {**query, "resourceId": resource_ids[start:start + RESOURCES_PER_REQUEST]}
        response = suite_api_client.post(path, json=request)
        if response.status_code != 200:
            logger.warning(f"Stats query {path} failed with HTTP {response.status_code}")
            continue

        for resource in response.json().get("values", []):
            # The JSON key is "stat-list" on the wire, but the API reference calls it "stats".
            stat_list = resource.get("stat-list") or resource.get("stats") or {}
            samples_by_key = samples_by_resource.setdefault(resource.get("resourceId"), {})
            for stat in stat_list.get("stat", []):
                stat_key = stat.get("statKey", {}).get("key")
                samples = stat.get("data") or []
                if stat_key and samples:
                    samples_by_key[stat_key] = [float(sample) for sample in samples]
    return samples_by_resource
