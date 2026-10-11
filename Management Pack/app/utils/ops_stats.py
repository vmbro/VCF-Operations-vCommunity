#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reads what VCF Operations already holds: resources, their stats and their properties.

The vCenter adapter of VCF Operations has already collected all of it. The KPIs read it back through the
Suite API, so nothing is collected twice.
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)

# Suite API endpoints. Each takes many resources in one request.
RESOURCES_QUERY_PATH = "/api/resources/query"
LATEST_STATS_PATH = "api/resources/stats/latest/query"
LATEST_PROPERTIES_PATH = "api/resources/properties/latest/query"

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


def _query_stats(suite_api_client: SuiteApiClient, path: str, query: dict) -> Dict[str, Dict[str, List[float]]]:
    """Returns {resource id: {stat key: [samples, oldest first]}}. Resources of a failed request are absent."""
    resource_ids = query["resourceId"]
    requested_keys = set(query["statKey"])
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
                # VCF Operations also returns every instance of a requested stat, such as
                # "cpu:26|utilization_average" for CPU thread 26. Only the requested keys are kept.
                if stat_key in requested_keys and samples:
                    samples_by_key[stat_key] = [float(sample) for sample in samples]
    return samples_by_resource


# ---------------------------------------------------------------------------
# Resources and properties.
# ---------------------------------------------------------------------------

class OpsResource(NamedTuple):
    """One VCF Operations resource, such as an ESXi host or a VM."""
    id: str             # VCF Operations resource id, which the stats and properties API need
    name: str           # the name shown in vCenter
    moid: str           # vCenter MoRef id (identifier VMEntityObjectID), to match the SDK objects


def query_resources(
    suite_api_client: SuiteApiClient, adapter_kind: str, resource_kind: str, adapter_instance_id: str
) -> List[OpsResource]:
    """All resources of one kind under one adapter instance, with their VCF Operations ids.

    The SDK's query_for_resources() drops the resource id, so the query is made here directly.
    """
    query = {"adapterKind": [adapter_kind], "resourceKind": [resource_kind], "adapterInstanceId": [adapter_instance_id]}
    response = suite_api_client.paged_post(RESOURCES_QUERY_PATH, "resourceList", json=query)
    resources = []
    for resource in response.get("resourceList", []):
        key = resource.get("resourceKey", {})
        moid = next((identifier.get("value") for identifier in key.get("resourceIdentifiers", [])
                     if identifier.get("identifierType", {}).get("name") == "VMEntityObjectID"), None)
        resources.append(OpsResource(resource.get("identifier"), key.get("name"), moid))
    return resources


def read_latest_properties(
    suite_api_client: SuiteApiClient, resource_ids: List[str], property_keys: List[str]
) -> Dict[str, Dict[str, str]]:
    """Returns {resource id: {property key: latest value}}. Properties with no value are absent.

    Values are returned as text, as VCF Operations stores most properties. Convert numbers with as_number().
    """
    properties_by_resource = {}
    for start in range(0, len(resource_ids), RESOURCES_PER_REQUEST):
        request = {"resourceIds": resource_ids[start:start + RESOURCES_PER_REQUEST], "propertyKeys": property_keys}
        response = suite_api_client.post(LATEST_PROPERTIES_PATH, json=request)
        if response.status_code != 200:
            logger.warning(f"Properties query failed with HTTP {response.status_code}")
            continue

        for resource in response.json().get("values", []):
            contents = resource.get("property-contents", {}).get("property-content", [])
            properties = properties_by_resource.setdefault(resource.get("resourceId"), {})
            for content in contents:
                # A text property has "values", a number property has "data". Take the latest of either.
                samples = content.get("values") or content.get("data") or []
                if content.get("statKey") and samples:
                    properties[content["statKey"]] = str(samples[-1])
    return properties_by_resource


def as_number(value: Optional[str]) -> Optional[float]:
    """A property value as a number, or None when it is missing or not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
