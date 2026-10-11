#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the ESXi Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.kpi_score import kpi_score
from metrics.host import esxi_performance_metrics as ep
from metrics import vm_contention as vc
from fakes import FakeSuiteApi, FakeObject

HOST_1_VMS = [f"vm-{n}" for n in range(1, 11)]      # 10 VMs: the 90th percentile is the 9th lowest
HOST_2_VMS = ["vm-11"]


def host_packets(bad_per_cycle, packets_per_cycle):
    samples = {key: [0.0] * len(bad_per_cycle) for key in vc.HOST_BAD_PACKET_STATS + vc.HOST_PACKET_STATS}
    samples["net|droppedRx_summation_sum"] = bad_per_cycle
    samples["net|packetsRx_summation_sum"] = packets_per_cycle
    return samples


HEALTHY = {
    **{vm_id: {key: [0.0] for key in vc.VM_STATS} for vm_id in HOST_1_VMS + HOST_2_VMS},
    "host-1": host_packets([0.0] * 6, [1000.0] * 6),
    "host-2": host_packets([0.0] * 6, [1000.0] * 6),
}


def collect(samples, host_id="host-1", vm_ids=HOST_1_VMS, status_code=200):
    api = FakeSuiteApi(samples, status_code)
    stats = ep.read_esxi_performance_stats(api, HOST_1_VMS + HOST_2_VMS, ["host-1", "host-2"])
    host_obj = FakeObject(host_id)
    ep.collect_esxi_performance_metrics(host_obj, host_id, vm_ids, stats)
    return {key.split("|")[-1]: value for key, value in host_obj.metrics.items()}


def test_limits_match_the_source_table():
    # docs/Complex Metrics/vSphere ESXi Performance metric.png
    limits = {m.name: (m.green, m.yellow, m.orange, m.zero_at, m.skip_when_green) for m in ep.METRICS}
    assert limits["Worst VM CPU Ready"] == (4, 8, 16, 32, False)
    assert limits["Worst VM Disk Latency"] == (40, 80, 160, 320, False)
    assert limits["90th Percentile VM CPU Co-Stop"] == (0.5, 1, 2, 4, False)
    assert limits["90th Percentile VM Disk Latency"] == (20, 40, 60, 80, False)
    assert limits["ESXi Bad Network Packets"] == (0, 0.2, 0.4, 0.8, True)          # green is "Excluded"


def test_healthy_host_publishes_every_metric_and_scores_100():
    published = collect(HEALTHY)
    assert set(published) == {metric.name for metric in ep.METRICS} | {ep.KPI_NAME}
    assert published[ep.KPI_NAME] == 100.0


def test_only_the_vms_of_this_host_count():
    # vm-11 runs on host-2 and has 30 % CPU Ready. host-1 does not see it.
    samples = {**HEALTHY, "vm-11": {**HEALTHY["vm-11"], "cpu|20_sec_peak_readyPct": [30.0]}}
    assert collect(samples)["Worst VM CPU Ready"] == 0.0
    assert collect(samples, "host-2", HOST_2_VMS)["Worst VM CPU Ready"] == 30.0


def test_one_bad_vm_is_deep_but_not_broad():
    # One VM has 200 ms disk latency: a quarter of the way through red (160 to 320), 18.75 with weight 8.
    # The 90th percentile stays 0. Bad packets are 0, in their excluded green, so they are left out.
    # KPI = (7 x 100 + 18.75 x 8) / (7 + 8) = 850 / 15 = 56.67
    samples = {**HEALTHY, "vm-1": {**HEALTHY["vm-1"], "virtualDisk|20_sec_peak_totalLatency_average": [200.0]}}
    published = collect(samples)
    assert published["Worst VM Disk Latency"] == 200.0
    assert published["90th Percentile VM Disk Latency"] == 0.0
    assert published[ep.KPI_NAME] == 56.67


def test_bad_packets_are_this_hosts_own():
    # host-1 drops 15 of 6000 packets over the window: 0.25 %, orange.
    samples = {**HEALTHY, "host-1": host_packets([15.0, 0.0, 0.0, 0.0, 0.0, 0.0], [1000.0] * 6)}
    assert collect(samples)["ESXi Bad Network Packets"] == 0.25
    assert collect(samples, "host-2", HOST_2_VMS)["ESXi Bad Network Packets"] == 0.0


def test_host_without_vms_is_scored_on_its_network():
    published = collect(HEALTHY, "host-2", [])
    # No VM sub-metric has data. Bad packets are 0 and skipped. Nothing is wrong, so the KPI is 100.
    assert published == {"ESXi Bad Network Packets": 0.0, ep.KPI_NAME: 100.0}


def test_failed_stats_calls_publish_nothing():
    assert collect(HEALTHY, status_code=500) == {}
