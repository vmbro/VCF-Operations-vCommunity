#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reading who runs where, and how big it is, from VCF Operations.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import ops_inventory as inv
from utils import ops_stats
from fakes import FakeSuiteApi

API = FakeSuiteApi(
    resources={
        "VirtualMachine": [("vm-id-1", "vm-1", "vm-1"), ("vm-id-2", "vm-2", "vm-2"), ("vm-id-3", "vm-3", "vm-3")],
        "HostSystem": [("host-id-1", "esx-01", "host-1"), ("host-id-2", "esx-02", "host-2")],
    },
    properties={
        "vm-id-1": {inv.VM_PARENT_HOST: "esx-01", inv.VM_POWER_STATE: "Powered On",
                    inv.VM_VCPUS: "4", inv.VM_MEMORY_KB: "16777216"},
        "vm-id-2": {inv.VM_PARENT_HOST: "esx-01", inv.VM_POWER_STATE: "Powered Off",
                    inv.VM_VCPUS: "8", inv.VM_MEMORY_KB: "8388608"},
        "vm-id-3": {inv.VM_PARENT_HOST: "esx-02", inv.VM_POWER_STATE: "Powered On"},
        "host-id-1": {inv.HOST_PARENT_CLUSTER: "Cluster A", inv.HOST_CORES: "32",
                      inv.HOST_HYPERTHREAD_AVAILABLE: "true", inv.HOST_HYPERTHREAD_ACTIVE: "true"},
        "host-id-2": {inv.HOST_PARENT_CLUSTER: "Cluster A", inv.HOST_CORES: "16",
                      inv.HOST_HYPERTHREAD_AVAILABLE: "true", inv.HOST_HYPERTHREAD_ACTIVE: "false"},
    },
)


def test_vms_come_with_their_host_power_state_and_size():
    vms = {vm.name: vm for vm in inv.read_vms(API, "adapter-1")}
    assert vms["vm-1"] == inv.VmInfo("vm-id-1", "vm-1", "vm-1", "esx-01", True, 4.0, 16384.0)
    assert vms["vm-2"].powered_on is False
    assert vms["vm-3"].vcpus is None                     # no size properties


def test_only_powered_on_vms_are_placed_on_their_host_by_name():
    by_host = inv.powered_on_vms_by_host(inv.read_vms(API, "adapter-1"))
    assert {name: [vm.name for vm in vms] for name, vms in by_host.items()} == {"esx-01": ["vm-1"], "esx-02": ["vm-3"]}


def test_hosts_come_with_their_cluster_cores_and_threads():
    hosts = {host.name: host for host in inv.read_hosts(API, "adapter-1")}
    assert hosts["esx-01"] == inv.HostInfo("host-id-1", "esx-01", "host-1", "Cluster A", 32.0, 64.0)
    assert hosts["esx-02"].threads == 16.0               # hyper-threading available but not active


def test_threads_are_twice_the_cores_only_when_hyperthreading_is_available_and_active():
    on = {inv.HOST_HYPERTHREAD_AVAILABLE: "true", inv.HOST_HYPERTHREAD_ACTIVE: "true"}
    assert inv.threads(32.0, on) == 64.0
    assert inv.threads(32.0, {**on, inv.HOST_HYPERTHREAD_ACTIVE: "false"}) == 32.0
    assert inv.threads(32.0, {**on, inv.HOST_HYPERTHREAD_AVAILABLE: "false"}) == 32.0
    assert inv.threads(32.0, {}) == 32.0                 # properties missing
    assert inv.threads(None, on) is None                 # cores unknown


def test_hosts_are_grouped_by_cluster_name():
    by_cluster = inv.hosts_by_cluster(inv.read_hosts(API, "adapter-1"))
    assert [host.name for host in by_cluster["Cluster A"]] == ["esx-01", "esx-02"]


def test_the_right_suite_api_endpoints_are_used():
    api = FakeSuiteApi(resources={"HostSystem": [("host-id-1", "esx-01", "host-1")]})
    inv.read_hosts(api, "adapter-1")
    assert api.paths == [ops_stats.RESOURCES_QUERY_PATH, "api/resources/properties/latest/query"]
    assert ops_stats.LATEST_STATS_PATH == "api/resources/stats/latest/query"


def test_as_number():
    assert ops_stats.as_number("4") == 4.0
    assert ops_stats.as_number("Powered On") is None
    assert ops_stats.as_number(None) is None
