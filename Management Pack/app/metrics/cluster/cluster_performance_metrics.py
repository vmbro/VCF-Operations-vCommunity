#  Copyright 2026 VCF Operations vCommunity Management Pack
import logging
from typing import Dict, List, Tuple
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)


def _score_component(val: float, t1: float, t2: float, t3: float, max_span: float) -> Tuple[float, float]:
    """Calculates weighted tier score and weight for one component metric."""
    if val < t1:
        score = (100.0 - ((val - 0.0) / t1 * 25.0)) * 1.0
        weight = 1.0
    elif val < t2:
        score = (75.0 - ((val - t1) / (t2 - t1) * 25.0)) * 2.0
        weight = 2.0
    elif val < t3:
        score = (50.0 - ((val - t2) / (t3 - t2) * 25.0)) * 4.0
        weight = 4.0
    else:
        over = min(val - t3, max_span)
        score = (25.0 - (over / max_span * 25.0)) * 8.0
        weight = 8.0
    return score, weight


def compute_cluster_performance_kpi(sub_metrics: Dict[str, float]) -> float:
    """Computes overall Cluster Performance (%) using the 10 created sub-metric values."""
    specs = {
        "ready": (sub_metrics.get("ready", 0.0), 1.0, 2.0, 4.0, 4.0),
        "co_stop": (sub_metrics.get("co_stop", 0.0), 1.0, 2.0, 4.0, 4.0),
        "mem_latc": (sub_metrics.get("mem_latc", 0.0), 0.5, 1.0, 2.0, 2.0),
        "m_ready": (sub_metrics.get("m_ready", 0.0), 4.0, 8.0, 16.0, 16.0),
        "m_co_stop": (sub_metrics.get("m_co_stop", 0.0), 2.0, 4.0, 8.0, 8.0),
        "m_mem_latc": (sub_metrics.get("m_mem_latc", 0.0), 1.0, 2.0, 4.0, 4.0),
        "bad_net": (sub_metrics.get("bad_net", 0.0), 0.2, 0.4, 0.8, 0.8),
        "vmotion": (sub_metrics.get("vmotion", 0.0), 1.0, 2.0, 4.0, 4.0),
        "mem_stress": (sub_metrics.get("mem_stress", 0.0), 0.25, 0.5, 1.0, 1.0),
        "balloon": (sub_metrics.get("balloon", 0.0), 1.0, 2.0, 4.0, 4.0),
    }

    total_score = 0.0
    total_weight = 0.0

    for val, t1, t2, t3, max_span in specs.values():
        s, w = _score_component(val, t1, t2, t3, max_span)
        total_score += s
        total_weight += w

    return round(total_score / total_weight, 2) if total_weight > 0 else 100.0


def collect_cluster_performance_metrics(
    cluster_obj: Object,
    cluster_ref,
    vms_by_uuid: Dict[str, Object],
    hosts_by_uuid: Dict[str, Object],
    suite_api_client: SuiteApiClient
) -> None:
    """Collects raw stats, creates 10 individual metrics on cluster_obj, then computes Cluster Performance (%) from them."""
    if not cluster_obj or not cluster_obj.get_id():
        return

    # 1. Fetch Cluster direct metrics
    res_id = cluster_obj.get_id()
    cluster_stats = {}
    res = suite_api_client.get(f"api/resources/{res_id}/stats/latest")
    if res.status_code == 200:
        for item in res.json().get("values", []):
            k = item.get("statKey", {}).get("key")
            stats = item.get("stat-list", {}).get("stat", [])
            if k and stats:
                cluster_stats[k] = float(stats[-1]["value"])

    vmotion_num = cluster_stats.get("summary|number_vmotion", 0.0)
    vmotion_den = cluster_stats.get("summary|number_running_vms", 1.0)
    vmotion_pct = round((vmotion_num / vmotion_den * 100.0) if vmotion_den > 0 else 0.0, 2)

    compressed = cluster_stats.get("mem|compressed_average", 0.0)
    swapout = cluster_stats.get("mem|swapout_average", 0.0)
    consumed = cluster_stats.get("mem|consumed_average", 0.0)
    sys_usage = cluster_stats.get("mem|sysUsage_average", 0.0)
    vmmemctl = cluster_stats.get("mem|vmmemctl_average", 0.0)

    mem_denom = (compressed + swapout + consumed - sys_usage)
    mem_stress_pct = round(((compressed + swapout) / mem_denom * 100.0) if mem_denom > 0 else 0.0, 2)

    balloon_denom = (vmmemctl + consumed - sys_usage)
    balloon_pct = round((vmmemctl / balloon_denom * 100.0) if balloon_denom > 0 else 0.0, 2)

    # 2. Bulk Fetch Child VM Metrics
    vm_res_ids = [vms_by_uuid[getattr(v, "_moId", "")].get_id() for v in getattr(cluster_ref, "vm", []) if getattr(v, "_moId", "") in vms_by_uuid]
    vm_readies, vm_costops, vm_intentions = [], [], []

    if vm_res_ids:
        payload = {
            "resourceId": vm_res_ids,
            "statKey": ["cpu|20_sec_peak_readyPct", "cpu|20_sec_peak_costopPct", "mem|20_sec_peak_host_contentionPct"]
        }
        res_vm = suite_api_client.post("api/resources/stats/latest", json=payload)
        if res_vm.status_code == 200:
            for rstat in res_vm.json().get("values", []):
                for stat in rstat.get("stat-list", {}).get("stat", []):
                    k = stat.get("statKey", {}).get("key")
                    v = float(stat.get("value", 0.0))
                    if k == "cpu|20_sec_peak_readyPct": vm_readies.append(v)
                    elif k == "cpu|20_sec_peak_costopPct": vm_costops.append(v)
                    elif k == "mem|20_sec_peak_host_contentionPct": vm_intentions.append(v)

    avg_ready = round(sum(vm_readies) / len(vm_readies) if vm_readies else 0.0, 2)
    max_ready = round(max(vm_readies) if vm_readies else 0.0, 2)

    avg_costop = round(sum(vm_costops) / len(vm_costops) if vm_costops else 0.0, 2)
    max_costop = round(max(vm_costops) if vm_costops else 0.0, 2)

    avg_mem_latc = round(sum(vm_intentions) / len(vm_intentions) if vm_intentions else 0.0, 2)
    max_mem_latc = round(max(vm_intentions) if vm_intentions else 0.0, 2)

    # 3. Bulk Fetch Child Host Bad Network Packets
    host_res_ids = [hosts_by_uuid[getattr(h, "_moId", "")].get_id() for h in getattr(cluster_ref, "host", []) if getattr(h, "_moId", "") in hosts_by_uuid]
    host_bad_nets = []

    if host_res_ids:
        payload_host = {
            "resourceId": host_res_ids,
            "statKey": [
                "net|errorsRx_summation_sum", "net|errorsTx_summation_sum",
                "net|droppedRx_summation_sum", "net|droppedTx_summation_sum",
                "net|packetsRx_summation_sum", "net|packetsTx_summation_sum"
            ]
        }
        res_host = suite_api_client.post("api/resources/stats/latest", json=payload_host)
        if res_host.status_code == 200:
            for rstat in res_host.json().get("values", []):
                h_stats = {s.get("statKey", {}).get("key"): float(s.get("value", 0.0)) for s in rstat.get("stat-list", {}).get("stat", [])}
                err_rx = h_stats.get("net|errorsRx_summation_sum", 0.0)
                err_tx = h_stats.get("net|errorsTx_summation_sum", 0.0)
                drop_rx = h_stats.get("net|droppedRx_summation_sum", 0.0)
                drop_tx = h_stats.get("net|droppedTx_summation_sum", 0.0)
                pkt_rx = h_stats.get("net|packetsRx_summation_sum", 0.0)
                pkt_tx = h_stats.get("net|packetsTx_summation_sum", 0.0)
                
                pkt_total = pkt_rx + pkt_tx
                bad_pct = ((err_rx + err_tx + drop_rx + drop_tx) / pkt_total * 100.0) if pkt_total > 0 else 0.0
                host_bad_nets.append(bad_pct)

    max_bad_net = round(max(host_bad_nets) if host_bad_nets else 0.0, 2)

    # 4. Emit the 10 individual super metrics under Cluster Performace group
    sub_metrics = {
        "ready": avg_ready,
        "co_stop": avg_costop,
        "mem_latc": avg_mem_latc,
        "m_ready": max_ready,
        "m_co_stop": max_costop,
        "m_mem_latc": max_mem_latc,
        "bad_net": max_bad_net,
        "vmotion": vmotion_pct,
        "mem_stress": mem_stress_pct,
        "balloon": balloon_pct,
    }

    group_prefix = "vCommunity|Cluster Performance"
    cluster_obj.with_metric(f"{group_prefix}|CPU Ready", avg_ready)
    cluster_obj.with_metric(f"{group_prefix}|CPU Co-Stop", avg_costop)
    cluster_obj.with_metric(f"{group_prefix}|Memory Contention", avg_mem_latc)
    cluster_obj.with_metric(f"{group_prefix}|Worst VM CPU Ready", max_ready)
    cluster_obj.with_metric(f"{group_prefix}|Worst VM CPU Co-Stop", max_costop)
    cluster_obj.with_metric(f"{group_prefix}|Worst VM Memory Contention", max_mem_latc)
    cluster_obj.with_metric(f"{group_prefix}|Worst ESXi Bad Network Packets", max_bad_net)
    cluster_obj.with_metric(f"{group_prefix}|Total vMotions", vmotion_pct)
    cluster_obj.with_metric(f"{group_prefix}|Memory Zip Swap", mem_stress_pct)
    cluster_obj.with_metric(f"{group_prefix}|Memory Ballooned", balloon_pct)

    # 5. Calculate overall Cluster Performance (%) using the 10 created sub-metrics
    kpi = compute_cluster_performance_kpi(sub_metrics)
    cluster_obj.with_metric(f"{group_prefix}|Cluster Performance", kpi)
