#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Operational Availability of ESXi hosts and clusters, and its summary on vSphere World.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.availability import operational_availability as oa
from metrics.world import availability_summary_metrics as summary
from utils import ops_inventory as inv
from fakes import FakeObject, FakeSuiteApi

UP = {"runtime|connectionState": "connected", "runtime|maintenanceState": "notInMaintenance",
      "runtime|quarantineState": "notInQuarantine"}


# --- Host --------------------------------------------------------------------

def test_a_fully_available_host_is_100():
    assert oa.host_availability(1.0, UP) == 100.0


def test_a_disconnected_host_is_not_connected():
    # The super metric used "contains 'connected'", which "disconnected" also matches.
    assert oa.host_availability(1.0, {**UP, "runtime|connectionState": "disconnected"}) == 75.0


def test_each_condition_is_worth_25():
    assert oa.host_availability(1.0, {**UP, "runtime|maintenanceState": "inMaintenance"}) == 75.0
    assert oa.host_availability(0.0, {**UP, "runtime|connectionState": "notResponding"}) == 50.0


def test_a_host_with_no_data_is_0():
    assert oa.host_availability(None, {}) == 0.0


# --- Cluster -------------------------------------------------------------------

def test_n_plus_0_healthy_cluster_is_100():
    # The super metric gave (400 - 100) / 4 = 75 here.
    assert oa.cluster_availability([100.0] * 4, 4, 0) == 100.0


def test_n_plus_0_counts_every_host():
    assert oa.cluster_availability([100.0, 100.0, 100.0, 75.0], 4, 0) == 93.75


def test_n_plus_1():
    assert oa.cluster_availability([100.0, 100.0, 100.0, 0.0], 4, 1) == 100.0       # one host down
    assert round(oa.cluster_availability([100.0, 100.0, 0.0, 0.0], 4, 1), 2) == 66.67
    # A degraded host counts unless it is one of the k worst: (350 - 75) / 3
    assert round(oa.cluster_availability([100.0, 100.0, 75.0, 75.0], 4, 1), 2) == 91.67


def test_n_plus_2_sets_two_hosts_aside():
    assert oa.cluster_availability([100.0] * 8 + [0.0, 0.0], 10, 2) == 100.0         # two hosts down
    assert oa.cluster_availability([100.0] * 7 + [50.0] * 3, 10, 2) == 93.75          # (850 - 100) / 8


def test_capped_at_100():
    assert oa.cluster_availability([100.0] * 4, 4, 1) == 100.0


def test_no_failover_level_counts_as_n_plus_0():
    assert oa.cluster_availability([100.0, 100.0, 100.0, 0.0], 4, None) == 75.0


def test_a_counted_host_without_data_is_0():
    # VCF Operations counts 4 hosts, but only 3 were found: the 4th is 0 %, so the cluster cannot look better.
    assert oa.cluster_availability([100.0] * 3, 4, 0) == 75.0


def test_no_value_when_ha_tolerates_every_host():
    assert oa.cluster_availability([100.0, 100.0], 2, 2) is None


def test_worst_leaves_out_clusters_without_a_value():
    assert oa.worst([91.67, None, 100.0]) == 91.67
    assert oa.worst([None]) is None


# --- Reading one vCenter ------------------------------------------------------------

def vcenter(status_code=200):
    return FakeSuiteApi(
        status_code=status_code,
        resources={"HostSystem": [("h1", "esx-01", "host-1"), ("h2", "esx-02", "host-2")],
                   "ClusterComputeResource": [("c1", "Cluster A", "domain-c1")]},
        properties={
            "h1": {inv.HOST_PARENT_CLUSTER: "Cluster A", **UP},
            "h2": {inv.HOST_PARENT_CLUSTER: "Cluster A", **UP, "runtime|connectionState": "disconnected"},
            "c1": {oa.CLUSTER_FAILOVER_LEVEL: "1"},
        },
        samples={"h1": {oa.HOST_POWERED_ON: [1.0]}, "h2": {oa.HOST_POWERED_ON: [1.0]},
                 "c1": {oa.CLUSTER_HOST_COUNT: [2.0]}},
    )


def test_reads_hosts_and_clusters_of_one_vcenter():
    values = oa.read_operational_availability(vcenter(), "adapter-1")
    assert values.by_host == {"h1": 100.0, "h2": 75.0}
    # N+1 with 2 hosts: (175 - 75) / 1. The failover level was stored as a property.
    assert values.by_cluster == {"Cluster A": 100.0}
    assert values.worst_cluster() == 100.0


def test_failed_requests_publish_nothing_instead_of_0():
    assert oa.read_operational_availability(vcenter(status_code=500), "adapter-1") == oa.NO_DATA


def test_published_under_availability():
    host = FakeObject("esx-01")
    oa.publish(host, oa.HOST_METRIC, 91.666)
    oa.publish(host, oa.CLUSTER_METRIC, None)
    assert host.metrics == {"vCommunity|Availability|ESXi Host Operational Availability": 91.67}


# --- vSphere World -------------------------------------------------------------

def test_world_summary_over_all_vcenters():
    api = FakeSuiteApi(
        resources={"ClusterComputeResource": [("c1", "A", "c-1"), ("c2", "B", "c-2")],
                   "HostSystem": [("h1", "esx-01", "h-1"), ("h2", "esx-02", "h-2"), ("h3", "esx-03", "h-3")]},
        samples={"c1": {summary.STORED_CLUSTER_VALUE: [91.67]}, "c2": {summary.STORED_CLUSTER_VALUE: [100.0]},
                 "h1": {summary.STORED_HOST_VALUE: [100.0]}, "h2": {summary.STORED_HOST_VALUE: [75.0]}},
    )
    world = FakeObject("vSphere World")
    summary.collect_availability_summary_metrics(world, api)
    # h3 has no stored value (for example, its vCenter has no account of this pack): left out.
    assert world.metrics == {
        "vCommunity|Availability|Worst Cluster Operational Availability": 91.67,
        "vCommunity|Availability|ESXi Hosts Operational Availability": 87.5,
    }
    assert all("adapterInstanceId" not in query for query in api.resource_queries)
