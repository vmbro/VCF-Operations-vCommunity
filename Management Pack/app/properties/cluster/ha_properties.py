#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_ha_properties(cluster_obj, cluster_name, prop_dict):
    try:
        hostMonitoring = "vCommunity|Cluster Configuration|vSphere HA|Host Monitoring"
        hostIsolation = "vCommunity|Cluster Configuration|vSphere HA|Response \\ Host Isolation"
        vmRestartPriority = "vCommunity|Cluster Configuration|vSphere HA|Response \\ Default VM Restart Priority"
        datastoreAPD = "vCommunity|Cluster Configuration|vSphere HA|Response \\ Datastore APD"
        datastorePDL = "vCommunity|Cluster Configuration|vSphere HA|Response \\ Datastore PDL"
        vmMonitoring = "vCommunity|Cluster Configuration|vSphere HA|VM Monitoring"
        heartbeatDatastore = "vCommunity|Cluster Configuration|vSphere HA|Heartbeat Datastore"
        failureInterval = "vCommunity|Cluster Configuration|vSphere HA|Failure Interval"
        maxFailureWindow = "vCommunity|Cluster Configuration|vSphere HA|Max Failure Window"
        maxFailures = "vCommunity|Cluster Configuration|vSphere HA|Max Failures"
        minUpTime = "vCommunity|Cluster Configuration|vSphere HA|Minimum Up Time"
        haEnabledValue = prop_dict.get("configuration.dasConfig.enabled")
        hostMonitoringValue = prop_dict.get("configuration.dasConfig.hostMonitoring")
        isolationResponseValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.isolationResponse")
        vmRestartPriorityValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.restartPriority")
        datastoreAPDValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForAPD")
        datastorePDLValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForPDL")
        vmMonitoringValue = prop_dict.get("configuration.dasConfig.vmMonitoring")
        heartbeatDatastoreValue = prop_dict.get("configuration.dasConfig.hBDatastoreCandidatePolicy")
        failureIntervalValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.failureInterval")
        maxFailureWindowValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow")
        maxFailuresValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailures")
        minUpTimeValue = prop_dict.get("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.minUpTime")


        if haEnabledValue == False:
            cluster_obj.with_property(hostMonitoring, NULL_STATUS)
            cluster_obj.with_property(hostIsolation, NULL_STATUS)
            cluster_obj.with_property(vmRestartPriority, NULL_STATUS)
            cluster_obj.with_property(datastoreAPD, NULL_STATUS)
            cluster_obj.with_property(datastorePDL, NULL_STATUS)
            cluster_obj.with_property(vmMonitoring, NULL_STATUS)
            cluster_obj.with_property(heartbeatDatastore, NULL_STATUS)
            cluster_obj.with_property(failureInterval, NULL_STATUS)
            cluster_obj.with_property(maxFailureWindow, NULL_STATUS)
            cluster_obj.with_property(maxFailures, NULL_STATUS)
            cluster_obj.with_property(minUpTime, NULL_STATUS)
        elif haEnabledValue == True and hostMonitoringValue == "disabled":
            cluster_obj.with_property(hostMonitoring, NULL_STATUS)
            cluster_obj.with_property(hostIsolation, NULL_STATUS)
            cluster_obj.with_property(vmRestartPriority, NULL_STATUS)
            cluster_obj.with_property(datastoreAPD, NULL_STATUS)
            cluster_obj.with_property(datastorePDL, NULL_STATUS)
            cluster_obj.with_property(vmMonitoring, str(vmMonitoringValue))
            cluster_obj.with_property(heartbeatDatastore, str(heartbeatDatastoreValue))
            cluster_obj.with_property(failureInterval, str(failureIntervalValue))
            cluster_obj.with_property(maxFailureWindow, str(maxFailureWindowValue))
            cluster_obj.with_property(maxFailures, str(maxFailuresValue))
            cluster_obj.with_property(minUpTime, str(minUpTimeValue))
        else:
            cluster_obj.with_property(hostMonitoring, str(hostMonitoringValue))
            cluster_obj.with_property(hostIsolation, str(isolationResponseValue))
            cluster_obj.with_property(vmRestartPriority, str(vmRestartPriorityValue))
            cluster_obj.with_property(datastoreAPD, str(datastoreAPDValue))
            cluster_obj.with_property(datastorePDL, str(datastorePDLValue))
            cluster_obj.with_property(vmMonitoring, str(vmMonitoringValue))
            cluster_obj.with_property(heartbeatDatastore, str(heartbeatDatastoreValue))
            cluster_obj.with_property(failureInterval, str(failureIntervalValue))
            cluster_obj.with_property(maxFailureWindow, str(maxFailureWindowValue))
            cluster_obj.with_property(maxFailures, str(maxFailuresValue))
            cluster_obj.with_property(minUpTime, str(minUpTimeValue))

        logger.debug(f"Successfully collected vSphere Cluster HA properties for : {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster HA properties for : {cluster_name} - {repr(e)}")