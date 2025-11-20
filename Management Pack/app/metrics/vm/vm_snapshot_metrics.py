#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import yaml
import os

logger = logging.getLogger(__name__)
current_directory = os.path.dirname(os.path.abspath(__file__))
vmConfigs = os.path.join(current_directory, "../../constants/vm/vmConfigs.yaml")

def get_Snapshot_Count(snapshots, snapshotCount=0):
    for snapshot in snapshots:
        snapshotCount += 1
        snapshotCount = get_Snapshot_Count(snapshot.childSnapshotList, snapshotCount)
    return snapshotCount


def collect_vm_metrics(vm_obj, vm):
    noSnapshot = 0
    with open(vmConfigs, "r") as file:
        data = yaml.safe_load(file)
    for group_name, group_content in data.items():
        if group_name and group_name == "Snapshot" and "metrics" in group_content:
            for item in group_content["metrics"]:
                propertyName = item["name"]
                if vm.rootSnapshot:
                    totalSnapshot = get_Snapshot_Count(vm.snapshot.rootSnapshotList)
                    vm_obj.with_metric(propertyName, totalSnapshot)
                else:
                    vm_obj.with_metric(propertyName, noSnapshot)