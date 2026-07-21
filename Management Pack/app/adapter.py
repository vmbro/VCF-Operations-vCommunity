#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

#import os
import sys
#import threading
import time
import json
import atexit
import xml.etree.ElementTree as ET
import concurrent
import constants.main
import aria.ops.adapter_logging as logging
from typing import Any
from typing import List
from typing import Optional
from collections import defaultdict
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.suite_api_client import key_to_object
from aria.ops.suite_api_client import SuiteApiClient
from aria.ops.timer import Timer
from pyVim.connect import Disconnect
from pyVim.connect import SmartConnect
from collectors.cluster.collectClusterData import collect_cluster_data
from collectors.host.collectHostData import collect_host_data
from collectors.vm.collectVMData import collect_vm_data
from collectors.datastore.collectDatastoreData import collect_datastore_data
from collectors.vcenter.collectvCenterData import collect_vcenter_data
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
timingLogger = logging.getLogger("[CollectionResult]")


def get_adapter_definition() -> AdapterDefinition:
    with Timer(logger, "Get Adapter Definition"):
        definition = AdapterDefinition(constants.main.ADAPTER_KIND, constants.main.ADAPTER_NAME)

        definition.define_string_parameter(
            constants.main.HOST_IDENTIFIER,
            "vCenter Server",
            description="FQDN or IP address of the vCenter Server instance.",
        )

        definition.define_string_parameter(
            "esxi_adv_settings_config_file",
            label="ESXi Advanced System Settings Config File",
            description="Enter the configuration file name that contains ESXi Advanced System Settings.",
            default="esxi_advanced_system_settings",
            required=False,
        )

        definition.define_string_parameter(
            "esxi_vib_driver_config_file",
            label="ESXi Software Packages Config File",
            description="Enter the configuration file name that contains ESXi Software Package names.",
            default="esxi_packages",
            required=False,
        )

        definition.define_string_parameter(
            "vm_adv_settings_config_file",
            label="VM Advanced Parameters Config File",
            description="Enter the configuration file name that contains VM Advanced Parameters.",
            default="vm_advanced_parameters",
            required=False,
        )

        definition.define_string_parameter(
            "vm_configuration_config_file",
            label="VM Options Config File",
            description="Enter the configuration file name that contains VM Options.",
            default="vm_options",
            required=False,
        )

        definition.define_int_parameter(
            constants.main.PORT_IDENTIFIER, "Port", default=443, advanced=True, description="Enter the port number for vCenter Server"
        )

        definition.define_string_parameter(
            "win_service_config_file",
            label="Windows Service Configuration File",
            description="Enter the configuration file name that contains Windows Service Names.",
            default="windows_service_list",
            required=False,
            advanced=True
        )

        definition.define_string_parameter(
            "win_event_config_file",
            label="Windows Event Log Configuration File",
            description="Enter the configuration file name that contains Windows Event Log IDs.",
            default="windows_event_list",
            required=False,
            advanced=True
        )

        definition.define_enum_parameter("serviceMonitoring",
            values=["Enabled", "Disabled"],
            label="Guest OS Service Monitoring Status",
            description="Choose Yes to enable Service Monitoring",
            default="Disabled",
            required=False,
            advanced=True
        )

        definition.define_enum_parameter("winEventMonitoring",
            values=["Enabled", "Disabled"],
            label="Windows Event Log Monitoring Status",
            description="Choose Enable to activate Windows Event Log Monitoring",
            default="Disabled",
            required=False,
            advanced=True
        )


        ### --- Adapter definitions --- ###

        # Credentials
        credential = definition.define_credential_type("vsphere_user", "vCenter Credential")
        credential.define_string_parameter(constants.main.USER_CREDENTIAL, "vCenter User Name")
        credential.define_password_parameter(constants.main.PASSWORD_CREDENTIAL, "vCenter Password")
        credential.define_string_parameter("winUser", "Windows User Name", required=False)
        credential.define_password_parameter("winPass", "Windows Password", required=False)


        # Cluster Compute Resource
        clusterComputeResource = definition.define_object_type("Cluster Compute Resource", "Cluster Compute Resource")
        vCommunity = clusterComputeResource.define_group("vCommunity", "vCommunity")
        clusterConfiguration = vCommunity.define_group("Cluster Configuration", "Cluster Configuration")

        clusterConfiguration.define_string_property("Configuration Status", "Configuration Status")
        clusterConfiguration.define_metric("Number of Effective Hosts", "Number of Effective Hosts")
        clusterConfiguration.define_string_property("Overall Status", "Overall Status")

        vSphereHA = clusterConfiguration.define_group("vSphere HA", "vSphere HA")
        vSphereHA.define_string_property("Host Monitoring", "Host Monitoring")
        vSphereHA.define_string_property("Host Isolation", "Response \\ Host Isolation")
        vSphereHA.define_string_property("Default VM Restart Priority", "Response \\ Default VM Restart Priority")
        vSphereHA.define_string_property("Datastore APD", "Response \\ Datastore APD")
        vSphereHA.define_string_property("Datastore PDL", "Response \\ Datastore PDL")
        vSphereHA.define_string_property("VM Monitoring", "VM Monitoring")
        vSphereHA.define_string_property("Heartbeat Datastore", "Heartbeat Datastore")
        vSphereHA.define_string_property("Failure Interval", "Failure Interval")
        vSphereHA.define_string_property("Max Failure Window", "Max Failure Window")
        vSphereHA.define_string_property("Max Failures", "Max Failures")
        vSphereHA.define_string_property("Minimum Up Time", "Minimum Up Time")

        drs = clusterConfiguration.define_group("DRS", "DRS")
        drs.define_string_property("Proactive DRS", "Proactive DRS")
        drs.define_string_property("Scale Descendants Shares", "Scale Descendants Shares")
        drs.define_string_property("CPU Over-Commitment","CPU Over-Commitment")
        drs.define_string_property("Virtual Machine Automation Enabled","Virtual Machine Automation Enabled")
        drs.define_metric("DRS Score", "DRS Score")

        evc = clusterConfiguration.define_group("EVC", "EVC")
        evc.define_string_property("Enabled", "Enabled")
        evc.define_string_property("Mode", "Mode")

        dpm = clusterConfiguration.define_group("DPM", "DPM")
        dpm.define_string_property("Host Power Action Rate", "Host Power Action Rate")


        # Host System
        hostSystem = definition.define_object_type("Host System", "Host System")
        vCommunity = hostSystem.define_group("vCommunity", "vCommunity")
        hostSystemConfiguration = vCommunity.define_group("Configuration", "Configuration")

        hostSystemConfiguration.define_string_property("Config Status", "Config Status")
        hostSystemConfiguration.define_string_property("Max EVC", "Max EVC")
        
        hostVAAI = hostSystemConfiguration.define_group("VAAI", "VAAI")
        hostVAAI.define_string_property("ATS Heartbeat", "ATS Heartbeat")
        hostVAAI.define_string_property("ATS Locking", "ATS Locking")

        hostTimeZone = hostSystemConfiguration.define_group("Time Zone", "Time Zone")
        hostTimeZone.define_string_property("Time Zone Name", "Time Zone Name")
        hostTimeZone.define_string_property("Description", "Description")
        hostTimeZone.define_string_property("GMT Offset", "GMT Offset")

        advancedSystemSettings = hostSystemConfiguration.define_group("AdvancedSystemSettings", "Advanced System Settings")
        advancedSystemSettings.define_string_property("Key", "Key")

        licensing = vCommunity.define_group("Licensing", "Licensing")
        licensing.define_string_property("License Name", "License Name")
        licensing.define_string_property("License Key", "License Key")
        licensing.define_string_property("License Expiration Date", "License Expiration Date")
        licensing.define_metric("Remaining Days", "Remaining Days")
        licensing.define_string_property("Edition Key", "Edition Key")

        installDate = hostSystemConfiguration.define_group("Install Date", "Install Date")
        installDate.define_string_property("UTC", "UTC")

        packages = hostSystemConfiguration.define_instanced_group("Packages", "Packages", instance_required=True)
        packages.define_string_property("Package Name", "Package Name")
        packages.define_string_property("Package Version", "Package Version")
        packages.define_string_property("Acceptance Level", "Acceptance Level")
        packages.define_string_property("Maintenance Mode Required", "Maintenance Mode Required")
        packages.define_string_property("Package Summary", "Package Summary")
        packages.define_string_property("Package Type", "Package Type")
        packages.define_string_property("Package Vendor", "Package Vendor")

        hostSystemNetwork = vCommunity.define_group("Network", "Network")
        hostSystemNetwork.define_string_property("DHCP", "DHCP")
        hostSystemNetwork.define_string_property("Search Domain", "Search Domain")

        networkDevice = hostSystemNetwork.define_instanced_group("Host Network Device", "Host Network Device", instance_required=True)
        networkDevice.define_string_property("Host Network Device Device Name", "Host Network Device Device Name")
        networkDevice.define_string_property("Host Network Device Driver Version", "Host Network Device Driver Version")
        networkDevice.define_string_property("Host Network Device Firmware Version", "Host Network Device Firmware Version")
        networkDevice.define_string_property("Host Network Device Status", "Host Network Device Status")
        networkDevice.define_string_property("PCI Vendor Name", "PCI Vendor Name")
        networkDevice.define_string_property("PCI Device Name", "PCI Device Name")
        networkDevice.define_string_property("PCI Vendor ID (VID)", "PCI Vendor ID (VID)")
        networkDevice.define_string_property("PCI Device ID (DID)", "PCI Device ID (DID)")
        networkDevice.define_string_property("PCI SubVendor ID (SVID)", "PCI SubVendor ID (SVID)")
        networkDevice.define_string_property("Host Network Device MAC", "Host Network Device MAC")
        networkDevice.define_string_property("Wake On Lan Supported", "Wake On Lan Supported")
        networkDevice.define_string_property("Host Network Device PCI", "Host Network Device PCI")
        networkDevice.define_string_property("Host Network Device Duplex", "Host Network Device Duplex")

        storageAdapter = vCommunity.define_group("Storage Adapter", "Storage Adapter")
        storageAdapter.define_string_property("Number of HBA", "Number of HBA")

        hbaDevice = storageAdapter.define_instanced_group("hbaDevice", "hbaDevice", instance_required=True)
        hbaDevice.define_string_property("HBA Device", "HBA Device")
        hbaDevice.define_string_property("HBA Device Bus", "HBA Device Bus")
        hbaDevice.define_string_property("HBA Device Model", "HBA Device Model")
        hbaDevice.define_string_property("HBA Device PCI", "HBA Device PCI")
        hbaDevice.define_string_property("HBA Device Status", "HBA Device Status")
        hbaDevice.define_string_property("HBA Device Type", "HBA Device Type")

        hostRuntime = vCommunity.define_group("Runtime", "Runtime")
        hostRuntime.define_string_property("Host Boot Time", "Host Boot Time")

        hostCapability = vCommunity.define_group("Capability", "Capability")
        hostCapability.define_string_property("Storage vMotion Supported", "Storage vMotion Supported")

        hostHardware = vCommunity.define_group("Hardware", "Hardware")
        hostHardware.define_string_property("Host BIOS Vendor", "Host BIOS Vendor")


        #TODO fix the object definition below
        # Datastore
        datastore = definition.define_object_type("vCommunity-Datastore", "Datastore")
        vCommunity = datastore.define_group("vCommunity", "vCommunity")

        datastoreIdentifiers = vCommunity.define_group("Identifiers", "Identifiers")
        datastoreIdentifiers.define_string_property("Number of Extents", "Number of Extents")

        datastoreExtents = datastoreIdentifiers.define_instanced_group("Extent", "Extent")
        datastoreExtents.define_string_property("Datastore Extent ID", "ID")

        datastoreSummary = vCommunity.define_group("Summary", "Summary")
        datastoreSummary.define_string_property("DS MOID", "MOID")
        datastoreSummary.define_string_property("DS Block Size", "Block Size")
        datastoreSummary.define_string_property("DS ax Blocks", "Max Blocks")
        datastoreSummary.define_string_property("DS VMFS Upgradable", "VMFS Upgradable")
        datastoreSummary.define_string_property("DS Status", "Status")
        datastoreSummary.define_string_property("DS SIOC Enabled", "SIOC Enabled")
        datastoreSummary.define_string_property("DS SIOC Threshold", "SIOC Threshold")


        # Virtual Machine
        virtualMachine = definition.define_object_type("Virtual Machine", "Virtual Machine")
        vCommunity = virtualMachine.define_group("vCommunity", "vCommunity")
        configuration = vCommunity.define_group("Configuration", "Configuration")

        configuration.define_string_property("CPU Allocation Share Level", "CPU Allocation Share Level")
        configuration.define_string_property("VM Change Version", "VM Change Version")
        configuration.define_string_property("VM Firmware", "VM Firmware")
        configuration.define_string_property("VM Latency Sensitivity Level", "VM Latency Sensitivity Level")
        configuration.define_string_property("VM Reboot PowerOff", "VM Reboot PowerOff")
        configuration.define_string_property("VM Op Notification Timeout", "VM Op Notification Timeout")
        configuration.define_string_property("VM Memory Allocation Share Level", "VM Memory Allocation Share Level")
        configuration.define_string_property("VM Config Status", "VM Config Status")
        
        vmNUMA = configuration.define_group("NUMA", "NUMA")
        vmNUMA.define_string_property("VM Hot Add Exposed", "VM Hot Add Exposed")

        vmBootOptions = configuration.define_group("Boot Options", "Boot Options")
        vmBootOptions.define_string_property("VM Boot Delay", "VM Boot Delay")
        vmBootOptions.define_string_property("VM Boot Retry Delay", "VM Boot Retry Delay")
        vmBootOptions.define_string_property("VM Boot Retry Enabled", "VM Boot Retry Enabled")
        vmBootOptions.define_string_property("VM Boot Enter BIOS Setup", "VM Boot Enter BIOS Setup")

        vmHWUpgrade = configuration.define_group("Hardware", "Hardware")
        vmHWUpgrade.define_string_property("VM HW Upgrade Status", "VM HW Upgrade Status")
        vmHWUpgrade.define_string_property("VM HW Upgrade Policy", "VM HW Upgrade Policy")
        vmHWUpgrade.define_string_property("VM HW Upgrade Target Version", "VM HW Upgrade Target Version")

        vmGuest = vCommunity.define_group("Guest", "Guest")
        vmGuest.define_string_property("State", "State")
        vmGuest.define_string_property("Application Status", "Application Status")
        vmGuest.define_string_property("Kernel Crash State", "Kernel Crash State")
        vmGuest.define_string_property("Operation Ready", "Operation Ready")
        vmGuest.define_string_property("State Change Support", "State Change Support")
        vmGuest.define_string_property("Interactive Guest", "Interactive Guest")
        vmGuest.define_string_property("Tools Sync Time", "Tools Sync Time")
        vmGuest.define_string_property("Tools Upgrade Policy", "Tools Upgrade Policy")
        vmGuest.define_string_property("Customization Status", "Customization Status")
        vmGuest.define_string_property("Heartbeat Status", "Heartbeat Status")

        vmGuestDetailed = vmGuest.define_group("Detailed Data", "Detailed Data")
        vmGuestDetailed.define_string_property("Build Number", "Build Number")
        vmGuestDetailed.define_string_property("CPE String", "CPE String")
        vmGuestDetailed.define_string_property("Distro Additional Version", "Distro Additional Version")
        vmGuestDetailed.define_string_property("Distro Name", "Distro Name")
        vmGuestDetailed.define_string_property("Distro Version", "Distro Version")
        vmGuestDetailed.define_string_property("Kernel Version", "Kernel Version")
        vmGuestDetailed.define_string_property("Pretty Name", "Pretty Name")

        vmRuntime = vCommunity.define_group("Runtime", "Runtime")
        vmRuntime.define_string_property("Consolidation Needed", "Consolidation Needed")
        vmRuntime.define_string_property("DAS protection", "DAS protection")
        vmRuntime.define_string_property("Min Required EVC Mode Key", "Min Required EVC Mode Key")

        vmFlags = configuration.define_group("Flags", "Flags")
        vmFlags.define_string_property("Disk UUID Enabled", "Disk UUID Enabled")

        advancedParameters = configuration.define_group("Advanced Parameters", "Advanced Parameters")
        advancedParameters.define_string_property("Parameter Key", "Parameter Key")

        scsiControllers = configuration.define_instanced_group("SCSI Controllers", "SCSI Controllers")
        scsiControllers.define_string_property("SCSI Controller Type", "SCSI Controller Type")
        scsiControllers.define_metric("SCSI Controllers Count", "Count")

        options = vCommunity.define_group("Options", "Options")
        options.define_string_property("Option Key", "Option Key")

        vmNetwork = vCommunity.define_group("Network", "Network")
        vmNetworkAdapters = vmNetwork.define_instanced_group("Network Adapters", "Network Adapters")
        vmNetworkAdapters.define_string_property("Network Adapter Type", "Network Adapter Type")
        vmNetworkAdapters.define_string_property("Starts Connected", "Starts Connected")

        vmSummary = vCommunity.define_instanced_group("Summary", "Summary")
        vmSummary.define_string_property("VM Path Name", "VM Path Name")

        vmVirtualDisk = vCommunity.define_instanced_group("Virtual Disk", "Virtual Disk")
        vmVirtualDisk.define_string_property("Label", "Label")
        vmVirtualDisk.define_string_property("Key", "Key")
        vmVirtualDisk.define_string_property("Controller Key", "Controller Key")
        vmVirtualDisk.define_string_property("Eagerly Scrub", "Eagerly Scrub")
        vmVirtualDisk.define_string_property("Split", "Split")
        vmVirtualDisk.define_string_property("Write Through", "Write Through")
        vmVirtualDisk.define_string_property("Storage Allocation Share Level", "Storage Allocation Share Level")

        guestOS = vCommunity.define_group("Guest OS", "Guest OS")
        services = guestOS.define_instanced_group("Services", "Services")
        services.define_string_property("Service Name", "Service Name")
        services.define_string_property("Service Status", "Service Status")
        services.define_string_property("Service Start Type", "Service Start Type")

        operatingSystem = guestOS.define_group("Operating System", "Operating System")
        operatingSystem.define_string_property("OS Name", "OS Name")
        operatingSystem.define_string_property("OS Version", "OS Version")
        operatingSystem.define_string_property("OS BuildNumber", "OS BuildNumber")
        operatingSystem.define_string_property("OS Architecture", "OS Architecture")
        operatingSystem.define_string_property("OS Last Boot Up Time", "OS Last Boot Up Time")
        operatingSystem.define_string_property("OS Release ID", "OS Release ID")


        # vCenter
        vCenter = definition.define_object_type("vCenter", "vCenter")
        vCommunity = vCenter.define_group("vCommunity", "vCommunity")
        vCenterConfiguration = vCommunity.define_group("Configuration", "Configuration")

        vCenterConfiguration.define_string_property("Patch Level", "Patch Level")
        vCenterConfiguration.define_string_property("User Directory Timeout", "User Directory Timeout")
        vCenterConfiguration.define_string_property("Enable MOB", "Enable MOB")
        vCenterConfiguration.define_string_property("Log Level", "Log Level")

        vCenterDatabase = vCenterConfiguration.define_group("Database", "Database")
        vCenterDatabase.define_string_property("Event retention (days)", "Event retention (days)")
        vCenterDatabase.define_string_property("Event Cleanup Enabled", "Event Cleanup Enabled")
        vCenterDatabase.define_string_property("Task retention (days)", "Task retention (days)")
        vCenterDatabase.define_string_property("Task Cleanup Enabled", "Task Cleanup Enabled")

        vCenterDatabaseRuntime = vCenterConfiguration.define_group("Runtime", "Runtime")
        vCenterDatabaseRuntime.define_string_property("vCenter Unique ID", "vCenter Unique ID")
        vCenterDatabaseRuntime.define_string_property("vCenter managed address", "vCenter managed address")
        vCenterDatabaseRuntime.define_string_property("Maximum Connections", "Maximum Connections")

        logger.debug(f"Returning adapter definition: {definition.to_json()}")

    return definition


def get_win_service_configFile(adapter_instance: AdapterInstance) -> str:
    win_service_config_file = adapter_instance.get_identifier_value("win_service_config_file")
    return win_service_config_file

def get_win_event_configFile(adapter_instance: AdapterInstance) -> str:
    configFile = adapter_instance.get_identifier_value("win_event_config_file")
    return configFile

def get_esxi_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    esxiAdvSettingsConfigFile = adapter_instance.get_identifier_value("esxi_adv_settings_config_file")
    return esxiAdvSettingsConfigFile

def get_esxi_vib_driver_configFile(adapter_instance: AdapterInstance) -> str:
    esxi_vib_driver_config_file = adapter_instance.get_identifier_value("esxi_vib_driver_config_file")
    return esxi_vib_driver_config_file

def get_vm_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    vm_adv_settings_config_file = adapter_instance.get_identifier_value("vm_adv_settings_config_file")
    return vm_adv_settings_config_file

def get_vm_configuration_configFile(adapter_instance: AdapterInstance) -> str:
    vm_configuration_config_file = adapter_instance.get_identifier_value("vm_configuration_config_file")
    return vm_configuration_config_file

def get_winCredential(adapter_instance: AdapterInstance) -> str:
    username = adapter_instance.get_credential_value("winUser")
    password = adapter_instance.get_credential_value("winPass")
    return username, password

def getServiceMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    serviceMonitoringStatus = adapter_instance.get_identifier_value("serviceMonitoring")
    return serviceMonitoringStatus

def getWindowsEventLogMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    WindowsEventLogMonitoringStatus = adapter_instance.get_identifier_value("winEventMonitoring")
    return WindowsEventLogMonitoringStatus    

def get_config_file_data(adapter_instance: AdapterInstance, configFile):
    apiPath = f"api/configurations/files?path=SolutionConfig/{configFile}.xml"

    with adapter_instance.suite_api_client as suite_api:
        getConfigFile = suite_api.get(url=apiPath)

    if not getConfigFile.ok:
        return []

    parsedResponse = ET.fromstring(getConfigFile.text)
    if not parsedResponse.text:
        return []

    lines = parsedResponse.text.strip()
    if not lines:
        return []

    formattedLines = [
        line.strip()
        for line in lines.split(',')
        if line.strip()
    ]

    return formattedLines


TIMINGS = defaultdict(list)

def record_timing(operationName, duration):
    TIMINGS[operationName].append(duration)


def timingSummary():
    total = 0
    timingLogger.info("====================== Collection Timing Summary ======================")

    for operationName, duration_list in TIMINGS.items():
        if not duration_list:
            continue

        currentDuration = sum(duration_list)
        total += currentDuration
        
        if currentDuration < 60:
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {currentDuration:.2f} seconds.")
        else:
            minutes = currentDuration / 60
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {minutes:.2f} minutes.")

    timingLogger.info("=======================================================================")
    
    if total < 60:
        timingLogger.info(f"Total Collection Duration: {total:.2f} seconds.")
    else:
        total_minutes = total / 60
        timingLogger.info(f"Total Collection Duration: {total_minutes:.2f} minutes.")
        
    timingLogger.info("=======================================================================")


def test(adapter_instance: AdapterInstance) -> TestResult:
    with Timer(logger, "Test connection"):
        result = TestResult()
        try:
            logger.debug(f"Returning test result: {result.get_json()}")

            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            logger.info(f"content: {content}")

        except Exception as e:
            logger.error("Unexpected connection test error")
            logger.exception(e)
            result.with_error("Unexpected connection test error: " + repr(e))
        finally:
            return result


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        try:
            start_time = time.perf_counter()
            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            ServiceMonitoringStatus = getServiceMonitoringStatus(adapter_instance)
            WindowsEventLogMonitoringStatus = getWindowsEventLogMonitoringStatus(adapter_instance)
            winUser, winPassword = get_winCredential(adapter_instance)

            windowsEventConfigFile = get_win_event_configFile(adapter_instance)
            apiPath = f"api/configurations/files?path=SolutionConfig/{windowsEventConfigFile}.xml"
            with adapter_instance.suite_api_client as suite_api:
                getConfigFile = suite_api.get(url = apiPath)

            winEventLogConfigFile = getConfigFile.text

            windowsServiceConfigFile = get_win_service_configFile(adapter_instance)
            windowsServices = get_config_file_data(adapter_instance, windowsServiceConfigFile)

            esxiAdvSettingsConfigFile = get_esxi_adv_settings_configFile(adapter_instance)
            esxiAdvSettings = get_config_file_data(adapter_instance, esxiAdvSettingsConfigFile)

            esxiVIBDriverConfigFile = get_esxi_vib_driver_configFile(adapter_instance)
            esxiVIBDrivers = get_config_file_data(adapter_instance, esxiVIBDriverConfigFile)

            vmAdvParametersConfigFile = get_vm_adv_settings_configFile(adapter_instance)
            vmAdvParameters = get_config_file_data(adapter_instance, vmAdvParametersConfigFile)

            vmConfigurationConfigFile = get_vm_configuration_configFile(adapter_instance)
            vmConfigs= get_config_file_data(adapter_instance, vmConfigurationConfigFile)

            with adapter_instance.suite_api_client as client:
                adapter_instance_id = _get_vcenter_adapter_instance_id(
                    client, adapter_instance
                )
                if adapter_instance_id is None:
                    result.with_error(
                        f"No vCenter Adapter Instance found matching vCenter Server '{adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)}'"
                    )
                    return result
                
                duration = time.perf_counter() - start_time
                record_timing("main_collect", duration)

                start_times = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as data_executor:
                    
                    # 1. Cluster feature definition
                    start_times["collect_cluster_data"] = time.perf_counter()
                    future_cls = data_executor.submit(
                        collect_cluster_data, client, adapter_instance_id, result, content
                    )

                    # 2. Host feature definition
                    start_times["collect_host_data"] = time.perf_counter()
                    future_host = data_executor.submit(
                        collect_host_data, client, adapter_instance_id, result, content, esxiAdvSettings, esxiVIBDrivers
                    )

                    # 3. VM feature definition
                    start_times["collect_vm_data"] = time.perf_counter()
                    future_vm = data_executor.submit(
                        collect_vm_data, client, adapter_instance_id, result, content, 
                        ServiceMonitoringStatus, WindowsEventLogMonitoringStatus, winUser, winPassword, 
                        winEventLogConfigFile, vmConfigs, vmAdvParameters, windowsServices
                    )

                    # 4. Datastore feature definition
                    start_times["collect_datastore_data"] = time.perf_counter()
                    future_ds = data_executor.submit(
                        collect_datastore_data, client, adapter_instance_id, result, content
                    )

                    # 5. vCenter feature definition
                    start_times["collect_vcenter_data"] = time.perf_counter()
                    future_vc = data_executor.submit(
                        collect_vcenter_data, client, adapter_instance_id, result, content
                    )

                    # Define main futures
                    main_futures = [future_cls, future_host, future_vm, future_ds, future_vc]
    
                    for future in concurrent.futures.as_completed(main_futures):
                        # Check future function
                        if future == future_cls:
                            func_name = "collect_cluster_data"
                        elif future == future_ds:
                            func_name = "collect_datastore_data"
                        elif future == future_vc:
                            func_name = "collect_vcenter_data"
                        elif future == future_host:
                            func_name = "collect_host_data"
                        else:
                            func_name = "collect_vm_data"

                        try:
                            future.result()
                            duration = time.perf_counter() - start_times[func_name]
                            record_timing(func_name, duration)
                            
                            logger.info(f"Finished {func_name} collection successfully.")
                            
                        except Exception as exc:
                            logger.error(f"Main data collection thread error in {func_name}: {exc}")
                            
                logger.info(f"Finished total data collection.")

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            timingSummary()
            return result


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        result = EndpointResult()
        logger.debug(f"Returning endpoints: {result.get_json()}")
        return result


def _get_service_instance(
    adapter_instance: AdapterInstance,
) -> Any:
    host = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    port = int(adapter_instance.get_identifier_value(constants.main.PORT_IDENTIFIER, 443))
    user = adapter_instance.get_credential_value(constants.main.USER_CREDENTIAL)
    password = adapter_instance.get_credential_value(constants.main.PASSWORD_CREDENTIAL)

    service_instance = SmartConnect(
        host=host, port=port, user=user, pwd=password, disableSslCertValidation=True
    )

    atexit.register(Disconnect, service_instance)

    return service_instance


def _get_vcenter_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[str]:
    ais: List[Object] = client.query_for_resources(
        {
            "adapterKind": [constants.main.VCENTER_ADAPTER_KIND],
            "resourceKind": ["VMwareAdapter Instance"],
        }
    )
    vcenter_server = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    for ai in ais:
        logger.debug(
            f"Considering vCenter Adapter Instance with VCURL: {ai.get_identifier_value('VCURL')}"
        )
        if ai.get_identifier_value("VCURL") == vcenter_server:
            return _get_adapter_instance_id(client, ai)
    return None


def _get_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[Any]:
    response = client.get(
        f"api/adapters?adapterKindKey={adapter_instance.get_key().adapter_kind}"
    )
    if response.status_code < 300:
        for ai in json.loads(response.content).get("adapterInstancesInfoDto", []):
            adapter_instance_key = key_to_object(ai.get("resourceKey")).get_key()
            if adapter_instance_key == adapter_instance.get_key():
                return ai.get("id")
    return None


def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        logger.error("Arguments must be <method> <inputfile> <ouputfile>")
        exit(1)

    method = argv[0]

    if method == "test":
        test(AdapterInstance.from_input()).send_results()
    elif method == "endpoint_urls":
        get_endpoints(AdapterInstance.from_input()).send_results()
    elif method == "collect":
        collect(AdapterInstance.from_input()).send_results()
    elif method == "adapter_definition":
        result = get_adapter_definition()
        if type(result) is AdapterDefinition:
            result.send_results()
        else:
            logger.info(
                "get_adapter_definition method did not return an AdapterDefinition"
            )
            exit(1)
    else:
        logger.error(f"Command {method} not found")
        exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])