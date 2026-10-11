#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The sub-metrics shared by Cluster Performance and ESXi Performance.

Both KPIs ask the same two questions about a group of VMs, the VMs of a cluster
or the VMs of one host:
    How deep?   The worst VM. Shows a problem that hits one VM hard.
    How broad?  The 90th percentile across the VMs. Shows a problem that many
                VMs share. 90 % of the VMs are at or below this value.
And both score the share of bad network packets of an ESXi host.

This module holds those formulas once. It reads stats through utils/ops_stats.py
and does the arithmetic. Each KPI module has its own table of limits.
"""
import math
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import percent, has_all
from utils.ops_stats import read_latest_stats, read_stat_totals


# Read from each powered-on VM.
# VM stat -> (sub-metric holding the worst VM, sub-metric holding the 90th percentile).
# The 20-second peak stats are used instead of the 5-minute averages so the KPIs are leading indicators.
VM_STATS = {
    "cpu|20_sec_peak_readyPct":                     ("Worst VM CPU Ready",       "90th Percentile VM CPU Ready"),
    "cpu|20_sec_peak_costopPct":                    ("Worst VM CPU Co-Stop",     "90th Percentile VM CPU Co-Stop"),
    "mem|20_sec_peak_host_contentionPct":           ("Worst VM Memory Latency",  "90th Percentile VM Memory Latency"),
    "virtualDisk|20_sec_peak_totalLatency_average": ("Worst VM Disk Latency",    "90th Percentile VM Disk Latency"),
}

# Read from each ESXi host. These are packet counts per collection cycle.
HOST_BAD_PACKET_STATS = [
    "net|errorsRx_summation_sum", "net|errorsTx_summation_sum",
    "net|droppedRx_summation_sum", "net|droppedTx_summation_sum",
]
HOST_PACKET_STATS = ["net|packetsRx_summation_sum", "net|packetsTx_summation_sum"]

# Bad packets are added up over this window. A single collection cycle is too noisy:
# one burst of drops would push the sub-metric into the red tier, where its weight is 8.
BAD_PACKET_WINDOW_MINUTES = 30


# ---------------------------------------------------------------------------
# Reading stats. One request for many objects, never one per object.
# ---------------------------------------------------------------------------

def read_vm_contention_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{VM resource id: {stat key: latest value}} for the stats in VM_STATS."""
    return read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))


def read_host_packet_totals(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{host resource id: {stat key: total over BAD_PACKET_WINDOW_MINUTES}} for the packet counters."""
    return read_stat_totals(
        suite_api_client, host_ids, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS, BAD_PACKET_WINDOW_MINUTES
    )


# ---------------------------------------------------------------------------
# Formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def percentile_90(numbers: List[float]) -> Optional[float]:
    """The value that 90 % of the numbers are at or below. None when the list is empty.

    Nearest-rank method: sort the numbers and take the one at position 90 % of the count, rounded up.
    With 20 VMs that is the 18th lowest. With fewer than 10 VMs it is the highest.
    """
    if not numbers:
        return None
    position = math.ceil(0.9 * len(numbers))
    return sorted(numbers)[position - 1]


def worst_and_percentile(stats_by_vm: Dict[str, Dict[str, float]], vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Worst-VM and 90th-percentile value of each stat in VM_STATS, over the VMs in vm_ids."""
    values = {}
    for stat_key, (worst_name, percentile_name) in VM_STATS.items():
        # A VM that does not have this stat is left out.
        per_vm = [stats_by_vm[vm_id][stat_key] for vm_id in vm_ids
                  if stat_key in stats_by_vm.get(vm_id, {})]
        values[worst_name] = max(per_vm) if per_vm else None
        values[percentile_name] = percentile_90(per_vm)
    return values


def bad_packet_pct(totals: Dict[str, float]) -> Optional[float]:
    """Share of errored or dropped packets of one host, from its packet totals."""
    # A host with one of the six counters missing would give a wrong share.
    if not has_all(totals, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS):
        return None
    bad_packets = sum(totals[key] for key in HOST_BAD_PACKET_STATS)
    all_packets = sum(totals[key] for key in HOST_PACKET_STATS)
    # None when the host sent and received no packets at all.
    return percent(bad_packets, all_packets)
