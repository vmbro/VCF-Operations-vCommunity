#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reading who runs where, and how big it is, from VCF Operations.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import ops_inventory as inv
from utils import ops_stats
from fakes import FakeResponse, FakeSuiteApi

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



# The responses of VCF Operations 9.1.1 to the properties query, as captured in Swagger.
# Unlike FakeSuiteApi, a number property comes back under "data", as a number, and a text property under "values".
LIVE_HOST_ID = "03ccaab1-777e-4e06-ad1d-e991ee4d3c5a"
LIVE_HOST_PROPERTIES = [
    {"statKey": "config|hyperThread|active", "timestamps": [1775949879539], "values": ["true"]},
    {"statKey": "config|hyperThread|available", "timestamps": [1775949879539], "values": ["true"]},
    {"statKey": "hardware|cpuInfo|numCpuCores", "timestamps": [1791204748498], "data": [20]},
    {"statKey": "summary|parentCluster", "timestamps": [1775949879539], "values": ["vcf-m02-cl01"]},
]
LIVE_VM_ID = "00aa08dd-32a2-4184-a64b-6dbafffab037"
LIVE_VM_PROPERTIES = [
    {"statKey": "config|hardware|memoryKB", "timestamps": [1788025940524], "data": [33554432]},
    {"statKey": "config|hardware|numCpu", "timestamps": [1788025940524], "data": [24]},
    {"statKey": "summary|parentHost", "timestamps": [1788025940524], "values": ["sun05-esxi48.acepod.com"]},
    {"statKey": "summary|runtime|powerState", "timestamps": [1791372935387], "values": ["Powered Off"]},
]


class LivePropertiesApi:
    """Answers the properties query with the captured response of one resource."""
    def __init__(self, resource_id, property_content):
        self.resource_id = resource_id
        self.property_content = property_content

    def post(self, path, json):
        return FakeResponse({"values": [{
            "resourceId": self.resource_id,
            "property-contents": {"property-content": self.property_content},
        }]})


def test_a_live_host_properties_response_is_read_correctly():
    api = LivePropertiesApi(LIVE_HOST_ID, LIVE_HOST_PROPERTIES)
    properties = ops_stats.read_latest_properties(api, [LIVE_HOST_ID], inv.HOST_PROPERTY_KEYS)
    host = inv.host_info(ops_stats.OpsResource(LIVE_HOST_ID, "sun05-esxi45.acepod.com", "host-1"), properties[LIVE_HOST_ID])
    assert host.cluster_name == "vcf-m02-cl01"
    assert host.cores == 20
    assert host.threads == 40


def test_a_live_vm_properties_response_is_read_correctly():
    api = LivePropertiesApi(LIVE_VM_ID, LIVE_VM_PROPERTIES)
    properties = ops_stats.read_latest_properties(api, [LIVE_VM_ID], inv.VM_PROPERTY_KEYS)
    vm = inv.vm_info(ops_stats.OpsResource(LIVE_VM_ID, "vm-1", "vm-1"), properties[LIVE_VM_ID])
    assert vm.host_name == "sun05-esxi48.acepod.com"
    assert vm.powered_on is False
    assert vm.vcpus == 24
    assert vm.memory_mb == 32 * 1024
