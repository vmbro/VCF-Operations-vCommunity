#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Network Speed Degradation per host, and the count of degraded hosts per Datacenter and on vSphere World.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.network import network_speed_degradation as nsd
from utils.ops_stats import split_instance
from fakes import FakeObject, FakeSuiteApi


def test_split_instance():
    assert split_instance("net:vmnic0|speed") == ("vmnic0", "net|speed")
    assert split_instance("net|speed") == (None, "net|speed")


def test_no_degradation_is_100():
    assert nsd.speed_degradation({"vmnic0": 10000.0, "vmnic1": 10000.0},
                                 {"vmnic0": 10000.0, "vmnic1": 10000.0}) == 100.0


def test_a_nic_at_lower_speed_than_configured():
    # (1000 + 10000) / (10000 + 10000)
    assert round(nsd.speed_degradation({"vmnic0": 1000.0, "vmnic1": 10000.0},
                                       {"vmnic0": 10000.0, "vmnic1": 10000.0}), 2) == 55.0


def test_a_nic_that_is_down_is_left_out():
    # The super metric averaged the 0 in, as if the host were degraded.
    assert nsd.speed_degradation({"vmnic0": 0.0, "vmnic1": 10000.0},
                                 {"vmnic0": 10000.0, "vmnic1": 10000.0}) == 100.0


def test_a_nic_without_configured_speed_is_left_out():
    assert nsd.speed_degradation({"vmnic0": 1000.0, "vmnic1": 10000.0},
                                 {"vmnic1": 10000.0}) == 100.0


def test_no_nic_to_compare_gives_no_value():
    # The super metric divided by zero here.
    assert nsd.speed_degradation({"vmnic0": 10000.0}, {"vmnic0": 0.0}) is None
    assert nsd.speed_degradation({}, {}) is None


def test_count_of_degraded_hosts():
    assert nsd.degraded_count([100.0, 55.0, None, 99.9]) == 2


def nic(speed, configured):
    return {"net:vmnic0|speed": [speed], "net:vmnic0|configuredSpeed": [configured]}


def test_reads_one_vcenter_and_counts_per_datacenter():
    api = FakeSuiteApi(
        resources={"HostSystem": [("h1", "esx-01", "host-1"), ("h2", "esx-02", "host-2"), ("h3", "esx-03", "host-3")]},
        samples={"h1": nic(1000.0, 10000.0), "h2": nic(10000.0, 10000.0), "h3": nic(1000.0, 10000.0)},
        properties={"h1": {nsd.HOST_DATACENTER: "DC-1"}, "h2": {nsd.HOST_DATACENTER: "DC-1"},
                    "h3": {nsd.HOST_DATACENTER: "DC-2"}},
    )
    values = nsd.read_network_speed(api, "adapter-1")
    assert values.by_host == {"h1": 10.0, "h2": 100.0, "h3": 10.0}
    assert values.count_by_datacenter == {"DC-1": 1, "DC-2": 1}


def test_a_failed_request_publishes_no_count_rather_than_0():
    api = FakeSuiteApi(resources={"HostSystem": [("h1", "esx-01", "host-1")]},
                       samples={"h1": nic(1000.0, 10000.0)}, status_code=500)
    assert nsd.read_network_speed(api, "adapter-1") == nsd.NO_DATA


def test_world_counts_the_stored_values_of_all_vcenters():
    api = FakeSuiteApi(
        resources={"HostSystem": [("h1", "esx-01", "host-1"), ("h2", "esx-02", "host-2")]},
        samples={"h1": {nsd.STORED_HOST_VALUE: [55.0]}, "h2": {nsd.STORED_HOST_VALUE: [100.0]}},
    )
    world = FakeObject("vSphere World")
    nsd.collect_world_network_speed(world, api)
    assert world.metrics == {"vCommunity|Network|Total Network Speed Degradation": 1}
    assert "adapterInstanceId" not in api.resource_queries[0]


def test_published_on_the_host_under_network():
    host = FakeObject("esx-01")
    nsd.publish(host, nsd.HOST_METRIC, 55.0)
    assert host.metrics == {"vCommunity|Network|Network Speed Degradation": 55.0}
