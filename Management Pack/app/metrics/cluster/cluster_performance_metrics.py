#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Performance KPI.

One 0-100 % score per cluster, built from the sub-metrics in METRICS below.
To add, remove or re-tune a sub-metric, edit METRICS. A new sub-metric also
needs one line in collect_cluster_performance_metrics() that supplies its value.

How the score works
-------------------
1. Every sub-metric is "lower is better" and 0 is perfect.
2. Its value falls into one of four tiers. Inside a tier the score drops in a
   straight line, by 25 points across the tier:

       tier     value range             score        weight
       green    0       up to green     100 -> 75    1
       yellow   green   up to yellow     75 -> 50    2
       orange   yellow  up to orange     50 -> 25    4
       red      orange  up to zero-at    25 ->  0    8   (stays 0 beyond zero-at)

3. The KPI is the weighted average of the sub-metric scores:

       KPI = sum(score x weight) / sum(weight)

Why the weight doubles with each tier: with a plain average, one metric in the
red tier would be hidden by nine healthy ones (score ~92). Doubling the weight
per tier makes a problem show (score ~62) while still letting the healthy
metrics count.

Where the thresholds come from: they are the values used by the
"Cluster Performance" super metric in content/supermetrics, which this code
replaces. In every row each tier limit is double the previous one. The worst-VM
rows use higher limits than the cluster-average rows, because a single VM peaks
far above the average.

Missing data: a sub-metric with no data is not published and is left out of the
KPI. It is never treated as 0, because 0 means "perfect". Full description for
people who do not read code: docs/cluster-performance-kpi.md
"""
import logging
import time
from typing import Dict, List, NamedTuple, Optional, Tuple
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)

GROUP = "Cluster Performance"
KPI_NAME = "Cluster Performance"


class Metric(NamedTuple):
    name: str               # the one name used everywhere: in this file, in adapter.py and in VCF Operations
    unit: Optional[str]
    green: float            # the green tier ends here
    yellow: float           # the yellow tier ends here
    orange: float           # the orange tier ends here
    zero_at: float          # the red tier ends here, and the score reaches 0


METRICS = [
    #       name                                unit   green  yellow  orange  zero-at
    # Average across the cluster's VMs
    Metric("CPU Ready",                         "%",   1.0,   2.0,    4.0,    8.0),
    Metric("CPU Co-Stop",                       "%",   1.0,   2.0,    4.0,    8.0),
    Metric("Memory Contention",                 "%",   0.5,   1.0,    2.0,    4.0),
    # Worst VM in the cluster
    Metric("Worst VM CPU Ready",                "%",   4.0,   8.0,    16.0,   32.0),
    Metric("Worst VM CPU Co-Stop",              "%",   2.0,   4.0,    8.0,    16.0),
    Metric("Worst VM Memory Contention",        "%",   1.0,   2.0,    4.0,    8.0),
    # Worst ESXi host in the cluster
    Metric("Worst ESXi Bad Network Packets",    "%",   0.2,   0.4,    0.8,    1.6),
    # Cluster as a whole
    Metric("vMotions per 100 Running VMs",      None,  1.0,   2.0,    4.0,    8.0),
    Metric("Memory Zip Swap",                   "%",   0.25,  0.5,    1.0,    2.0),
    Metric("Memory Ballooned",                  "%",   1.0,   2.0,    4.0,    8.0),
]

TIERS = [
    # tier      score at start of tier   weight
    ("green",   100.0,                   1.0),
    ("yellow",  75.0,                    2.0),
    ("orange",  50.0,                    4.0),
    ("red",     25.0,                    8.0),
]
SCORE_DROP_PER_TIER = 25.0

# VM stat -> (sub-metric holding the average of all VMs, sub-metric holding the worst VM).
# The 20-second peak stats are used instead of the 5-minute averages so the KPI is a leading indicator.
VM_STATS = {
    "cpu|20_sec_peak_readyPct":           ("CPU Ready",         "Worst VM CPU Ready"),
    "cpu|20_sec_peak_costopPct":          ("CPU Co-Stop",       "Worst VM CPU Co-Stop"),
    "mem|20_sec_peak_host_contentionPct": ("Memory Contention", "Worst VM Memory Contention"),
}

# summary|number_vmotion is the count for the last collection cycle, not a running total.
VMOTION_COUNT = "summary|number_vmotion"
RUNNING_VMS = "summary|number_running_vms"
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED_OUT = "mem|swapout_average"
MEM_CONSUMED = "mem|consumed_average"
MEM_SYSTEM_USAGE = "mem|sysUsage_average"
MEM_BALLOONED = "mem|vmmemctl_average"
CLUSTER_STATS = [
    VMOTION_COUNT, RUNNING_VMS, MEM_COMPRESSED, MEM_SWAPPED_OUT, MEM_CONSUMED, MEM_SYSTEM_USAGE, MEM_BALLOONED,
]

HOST_BAD_PACKET_STATS = [
    "net|errorsRx_summation_sum", "net|errorsTx_summation_sum",
    "net|droppedRx_summation_sum", "net|droppedTx_summation_sum",
]
HOST_PACKET_STATS = ["net|packetsRx_summation_sum", "net|packetsTx_summation_sum"]

# Bad packets are added up over this window. A single collection cycle is too noisy:
# one burst of drops would push the sub-metric into the red tier, where its weight is 8.
BAD_PACKET_WINDOW_MINUTES = 30
COLLECTION_CYCLE_MINUTES = 5


# ---------------------------------------------------------------------------
# Scoring. No API calls here, so it is easy to test.
# ---------------------------------------------------------------------------

def score_metric(metric: Metric, value: float) -> Tuple[float, float]:
    """Returns (score, weight) for one sub-metric value."""
    value = max(value, 0.0)
    tier_ends = [metric.green, metric.yellow, metric.orange, metric.zero_at]
    tier_start = 0.0

    for (tier_name, score_at_start, weight), tier_end in zip(TIERS, tier_ends):
        if value < tier_end or tier_name == "red":
            distance_into_tier = min((value - tier_start) / (tier_end - tier_start), 1.0)
            score = score_at_start - distance_into_tier * SCORE_DROP_PER_TIER
            return score, weight
        tier_start = tier_end


def cluster_performance_score(values: Dict[str, Optional[float]]) -> Optional[float]:
    """Returns the KPI (0-100), or None when no sub-metric has data.

    values maps a sub-metric name to its value. None means "no data".
    """
    total_weighted_score = 0.0
    total_weight = 0.0

    for metric in METRICS:
        value = values.get(metric.name)
        if value is None:
            continue
        score, weight = score_metric(metric, value)
        total_weighted_score += score * weight
        total_weight += weight

    if total_weight == 0:
        return None
    return round(total_weighted_score / total_weight, 2)


# ---------------------------------------------------------------------------
# Sub-metric formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def average_and_max(numbers: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not numbers:
        return None, None
    return sum(numbers) / len(numbers), max(numbers)


def percent(part: float, whole: float) -> Optional[float]:
    if whole <= 0:
        return None
    return part / whole * 100.0


def has_all(stats: Dict[str, float], stat_keys: List[str]) -> bool:
    return all(key in stats for key in stat_keys)


def vmotion_rate(cluster_stats: Dict[str, float]) -> Optional[float]:
    """vMotions in the last collection cycle, per 100 running VMs."""
    if not has_all(cluster_stats, [VMOTION_COUNT, RUNNING_VMS]):
        return None
    return percent(cluster_stats[VMOTION_COUNT], cluster_stats[RUNNING_VMS])


def memory_compressed_or_swapped_pct(cluster_stats: Dict[str, float]) -> Optional[float]:
    """Share of VM memory that is compressed or swapped out."""
    if not has_all(cluster_stats, [MEM_COMPRESSED, MEM_SWAPPED_OUT, MEM_CONSUMED, MEM_SYSTEM_USAGE]):
        return None
    zipped_or_swapped = cluster_stats[MEM_COMPRESSED] + cluster_stats[MEM_SWAPPED_OUT]
    consumed_by_vms = cluster_stats[MEM_CONSUMED] - cluster_stats[MEM_SYSTEM_USAGE]
    return percent(zipped_or_swapped, zipped_or_swapped + consumed_by_vms)


def memory_ballooned_pct(cluster_stats: Dict[str, float]) -> Optional[float]:
    """Share of VM memory that is ballooned."""
    if not has_all(cluster_stats, [MEM_BALLOONED, MEM_CONSUMED, MEM_SYSTEM_USAGE]):
        return None
    ballooned = cluster_stats[MEM_BALLOONED]
    consumed_by_vms = cluster_stats[MEM_CONSUMED] - cluster_stats[MEM_SYSTEM_USAGE]
    return percent(ballooned, ballooned + consumed_by_vms)


def vm_contention_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Average and worst-VM value of each stat in VM_STATS."""
    latest_by_vm = read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))
    values = {}

    for stat_key, (average_name, worst_name) in VM_STATS.items():
        per_vm = [vm_stats[stat_key] for vm_stats in latest_by_vm.values() if stat_key in vm_stats]
        values[average_name], values[worst_name] = average_and_max(per_vm)
    return values


def worst_host_bad_packet_pct(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[float]:
    """Highest share of errored or dropped packets on any one host, over BAD_PACKET_WINDOW_MINUTES."""
    totals_by_host = read_stat_totals(
        suite_api_client, host_ids, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS, BAD_PACKET_WINDOW_MINUTES
    )
    per_host = []

    for totals in totals_by_host.values():
        if not has_all(totals, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS):
            continue
        bad_packets = sum(totals[key] for key in HOST_BAD_PACKET_STATS)
        all_packets = sum(totals[key] for key in HOST_PACKET_STATS)
        bad_pct = percent(bad_packets, all_packets)
        if bad_pct is not None:
            per_host.append(bad_pct)

    _, worst = average_and_max(per_host)
    return worst


# ---------------------------------------------------------------------------
# Reading stats from VCF Operations.
# ---------------------------------------------------------------------------

def read_cluster_stats(suite_api_client: SuiteApiClient, cluster_id: str) -> Dict[str, float]:
    """Latest value of each stat in CLUSTER_STATS. Stats with no data are absent."""
    return read_latest_stats(suite_api_client, [cluster_id], CLUSTER_STATS).get(cluster_id, {})


def read_latest_stats(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str]
) -> Dict[str, Dict[str, float]]:
    """Returns {resource id: {stat key: latest value}}."""
    query = {"resourceId": resource_ids, "statKey": stat_keys}
    samples_by_resource = _query_stats(suite_api_client, "api/resources/stats/latest", query)
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
    samples_by_resource = _query_stats(suite_api_client, "api/resources/stats/query", query)
    return {
        resource_id: {stat_key: sum(samples) for stat_key, samples in samples_by_key.items()}
        for resource_id, samples_by_key in samples_by_resource.items()
    }


def _query_stats(suite_api_client: SuiteApiClient, path: str, query: dict) -> Dict[str, Dict[str, List[float]]]:
    """Returns {resource id: {stat key: [samples, oldest first]}}. Empty when there is nothing to ask or the call fails."""
    if not query["resourceId"]:
        return {}

    response = suite_api_client.post(path, json=query)
    if response.status_code != 200:
        logger.warning(f"Stats query {path} failed with HTTP {response.status_code}")
        return {}

    samples_by_resource = {}
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


def _child_resource_ids(vcenter_children, objects_by_moid: Dict[str, Object]) -> List[str]:
    """VCF Operations resource ids of the vCenter children (VMs or hosts) that VCF Operations knows about."""
    resource_ids = []
    for child in vcenter_children:
        child_obj = objects_by_moid.get(getattr(child, "_moId", ""))
        if child_obj:
            resource_ids.append(child_obj.get_id())
    return resource_ids


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_performance_metrics(
    cluster_obj: Object,
    cluster_name: str,
    cluster_ref,
    vms_by_uuid: Dict[str, Object],
    hosts_by_uuid: Dict[str, Object],
    suite_api_client: SuiteApiClient
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Performance KPI computed from them."""
    try:
        if not cluster_obj or not cluster_obj.get_id():
            return

        cluster_stats = read_cluster_stats(suite_api_client, cluster_obj.get_id())
        vm_ids = _child_resource_ids(getattr(cluster_ref, "vm", []), vms_by_uuid)
        host_ids = _child_resource_ids(getattr(cluster_ref, "host", []), hosts_by_uuid)

        values = vm_contention_stats(suite_api_client, vm_ids)
        values["Worst ESXi Bad Network Packets"] = worst_host_bad_packet_pct(suite_api_client, host_ids)
        values["vMotions per 100 Running VMs"] = vmotion_rate(cluster_stats)
        values["Memory Zip Swap"] = memory_compressed_or_swapped_pct(cluster_stats)
        values["Memory Ballooned"] = memory_ballooned_pct(cluster_stats)

        # Round first, so the KPI is computed from exactly the numbers that are published.
        values = {name: round(value, 2) for name, value in values.items() if value is not None}

        for name, value in values.items():
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{name}", value)

        kpi = cluster_performance_score(values)
        if kpi is not None:
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{KPI_NAME}", kpi)

        no_data = [metric.name for metric in METRICS if metric.name not in values]
        if no_data:
            logger.info(f"Cluster Performance for {cluster_name}: no data, so left out: {', '.join(no_data)}")

        logger.debug(f"Successfully collected vSphere Cluster Performance metrics for the cluster: {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster Performance metrics for : {cluster_name} - {repr(e)}")
