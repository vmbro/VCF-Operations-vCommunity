#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import os
import sys
import json
import yaml
import atexit
import xml.etree.ElementTree as ET
import constants.main
import aria.ops.adapter_logging as logging
from typing import Any
from typing import List
from typing import Optional
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.definition.units import Units
from aria.ops.suite_api_client import key_to_object
from aria.ops.suite_api_client import SuiteApiClient
from aria.ops.timer import Timer
from pyVim.connect import Disconnect
from pyVim.connect import SmartConnect
from collectors.cluster.collectClusterData import collect_cluster_data
from collectors.host.collectHostData import collect_host_data
from collectors.vm.collectVMData import collect_vm_data

logger = logging.getLogger(__name__)

current_directory = os.path.dirname(os.path.abspath(__file__))
clusterObjectTypes = os.path.join(current_directory, "constants/cluster/clusterObjectTypes.yaml")
hostObjectTypes = os.path.join(current_directory, "constants/host/hostObjectTypes.yaml")
vmObjectTypes = os.path.join(current_directory, "constants/vm/vmObjectTypes.yaml")

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

        definition.define_int_parameter(
            constants.main.PORT_IDENTIFIER, "Port", default=443, advanced=True, description="Enter the port number for vCenter Server"
        )

        # Define the credential details below. Use of credentials can be customised
        credential = definition.define_credential_type("vsphere_user", "vCenter Credential")
        credential.define_string_parameter(constants.main.USER_CREDENTIAL, "vCenter User Name")
        credential.define_password_parameter(constants.main.PASSWORD_CREDENTIAL, "vCenter Password")
        credential.define_string_parameter("winUser", "Windows User Name", required=False)
        credential.define_password_parameter("winPass", "Windows Password", required=False)

        definition.define_enum_parameter("serviceMonitoring",
            values=["Enabled", "Disabled"],
            label="Service Monitoring Enabled",
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

        #define_cluster_objects(clusterObjectTypes, definition)
        #define_host_objects(hostObjectTypes, definition)
        #define_vm_objects(vmObjectTypes, definition)


        # Object definitions #
        # Cluster Compute Resource Object Types, Groups and Metrics

        clusterComputeResource = definition.define_object_type("Cluster Compute Resource", "Cluster Compute Resource")
        vCommunity = clusterComputeResource.define_group("vCommunity", "vCommunity")
        clusterConfiguration = vCommunity.define_group("Cluster Configuration", "Cluster Configuration")
        vSphereHA = clusterConfiguration.define_group("vSphere HA", "vSphere HA")
        vSphereHA.define_string_property("Host Monitoring", "Host Monitoring")
        vSphereHA.define_string_property("Host Isolation", "Response \\ Host Isolation")
        vSphereHA.define_string_property("Default VM Restart Priority", "Response \\ Default VM Restart Priority")
        vSphereHA.define_string_property("Datastore APD", "Response \\ Datastore APD")
        vSphereHA.define_string_property("Datastore PDL", "Response \\ Datastore PDL")
        vSphereHA.define_string_property("VM Monitoring", "VM Monitoring")
        vSphereHA.define_string_property("Heartbeat Datastore", "Heartbeat Datastore")

        drs = clusterConfiguration.define_group("DRS", "DRS")
        drs.define_string_property("Proactive DRS", "Proactive DRS")
        drs.define_string_property("Scale Descendants Shares", "Scale Descendants Shares")
        drs.define_metric("DRS Score", "DRS Score")

        evc = clusterConfiguration.define_group("EVC", "EVC")
        evc.define_string_property("Enabled", "Enabled")
        evc.define_string_property("Mode", "Mode")


        hostSystem = definition.define_object_type("Host System", "Host System")
        vCommunity = hostSystem.define_group("vCommunity", "vCommunity")
        hostSystemConfiguration = vCommunity.define_group("Configuration", "Configuration")
        advancedSystemSettings = hostSystemConfiguration.define_group("AdvancedSystemSettings", "Advanced System Settings")
        advancedSystemSettings. define_string_property("Key", "Key")

        #hostProfile = hostSystemConfiguration.define_group("Host Profile", "Host Profile")
        #hostProfile.define_string_property("Last Check Time", "Last Check Time")
        #hostProfile.define_string_property("Compliance Status", "Compliance Status")
        #hostProfile.define_string_property("Profile Name", "Profile Name")

        installDate = hostSystemConfiguration.define_group("Install Date", "Install Date")
        installDate.define_string_property("UTC", "UTC")

        packages = hostSystemConfiguration.define_instanced_group("Packages", "Packages", instance_required=True)
        packages.define_numeric_property("Package Name", "Package Name")
        packages.define_numeric_property("Package Version", "Package Version")
        packages.define_numeric_property("Acceptance Level", "Acceptance Level")
        packages.define_numeric_property("Maintenance Mode Required", "Maintenance Mode Required")
        packages.define_numeric_property("Package Summary", "Package Summary")
        packages.define_numeric_property("Package Type", "Package Type")
        packages.define_numeric_property("Package Vendor", "Package Vendor")


        virtualMachine = definition.define_object_type("Virtual Machine", "Virtual Machine")
        vCommunity = virtualMachine.define_group("vCommunity", "vCommunity")

        snapshot = vCommunity.define_group("Snapshot", "Snapshot")
        snapshot.define_metric("Count", "Count")

        advancedParameters = vCommunity.define_group("Advanced Parameters", "Advanced Parameters")
        advancedParameters. define_string_property("Parameter Key", "Parameter Key")

        options = vCommunity.define_group("Options", "Options")
        options.define_string_property("Option Key", "Option Key")

        #summary = virtualMachine.define_group("Summary", "Summary")
        #summary.define_metric("VM Age", "VM Age")

        guestOS = vCommunity.define_group("Guest OS", "Guest OS")
        guestOS.define_string_property("Service Name", "Service Name")
        guestOS.define_string_property("Service Status", "Service Status")
        guestOS.define_string_property("Service Start Type", "Service Start Type")


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


#def define_cluster_objects(clusterObjectTypes, definition):
#    with open(clusterObjectTypes, "r") as file:
#        data = yaml.safe_load(file)
#
#    clusterComputeResource = definition.define_object_type("Cluster Compute Resource")
#    clusterConfiguration = clusterComputeResource.define_group("Cluster Configuration")
#    for group_name, group_content in data.items():
#        if group_name == "vSphere HA":
#            vSphereHA = clusterConfiguration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    vSphereHA.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    vSphereHA.define_metric(metric)
#
#        if group_name == "DRS":
#            drs = clusterConfiguration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    drs.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    drs.define_metric(metric)
#
#        if group_name == "EVC":
#            evc = clusterConfiguration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    evc.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    evc.define_metric(metric)
#
#
#def define_host_objects(hostObjectTypes, definition):
#    with open(hostObjectTypes, "r") as file:
#        data = yaml.safe_load(file)
#
#    HostSystem = definition.define_object_type("Host System")
#    configuration = HostSystem.define_group("Configuration")
#    for group_name, group_content in data.items():
#        if group_name == "Host Agent":
#            hostAgent = configuration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    hostAgent.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    hostAgent.define_metric(metric)
#        if group_name == "Host Profile":
#            hostProfileGroup = configuration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    hostProfileGroup.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    hostProfileGroup.define_metric(metric)
#    
#    SoftwarePackages = configuration.define_group("Software Packages")
#    SoftwarePackages.define_string_property("Package Name")
#
#
#def define_vm_objects(vmObjectTypes, definition):
#    with open(vmObjectTypes, "r") as file:
#        data = yaml.safe_load(file)
#
#    virtualMachine = definition.define_object_type("Virtual Machine")
#    diskSpace = virtualMachine.define_group("Disk Space")
#    for group_name, group_content in data.items():
#        if group_name == "Snapshot":
#            snapshot = diskSpace.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    snapshot.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    snapshot.define_metric(metric)
#
#        if group_name == "Configuration":
#            configuration = virtualMachine.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    configuration.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    configuration.define_metric(metric)
#
#        if group_name == "VM Agent":
#            configuration = virtualMachine.define_group(group_name)
#            vmAgent = configuration.define_group(group_name)
#            if "properties" in group_content:
#                for property in group_content["properties"]:
#                    vmAgent.define_string_property(property)
#            if "metrics" in group_content:
#                for metric in group_content["metrics"]:
#                    vmAgent.define_metric(metric)
#
#    summary = virtualMachine.define_group("Summary")
#    guest = summary.define_group("Guest")
#    services = guest.define_group("Services")
#    services.define_string_property("Service Name")


def get_config_file_data(adapter_instance: AdapterInstance, configFile) -> str:
    apiPath = f"api/configurations/files?path=SolutionConfig/{configFile}.xml"
    with adapter_instance.suite_api_client as suite_api:
        getConfigFile = suite_api.get(url = apiPath)
    if getConfigFile.ok:
        lines = getConfigFile.text
        parsedResponse = ET.fromstring(lines)
        formattedLines = parsedResponse.text.strip().split(',')
        objectList = []
        for line in formattedLines:
            objectList.append(line.strip())
        return objectList

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
            logger.debug(f"Returning collection result {result.get_json()}")
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
                
                collect_cluster_data(client, adapter_instance_id, result, content)
                collect_host_data(client, adapter_instance_id, result, content, esxiAdvSettings, esxiVIBDrivers)
                collect_vm_data(client, adapter_instance_id, result, content, ServiceMonitoringStatus, WindowsEventLogMonitoringStatus, winUser, winPassword, winEventLogConfigFile, vmConfigs, vmAdvParameters, windowsServices)

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
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