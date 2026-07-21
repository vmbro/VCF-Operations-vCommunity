#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import re

logger = logging.getLogger(__name__)

def collect_vm_configurations(vm_obj, prop_dict, vm_name):
    try:
        bootDelay = prop_dict.get("config.bootOptions.bootDelay")
        bootRetryDelay = prop_dict.get("config.bootOptions.bootRetryDelay")
        bootRetryEnabled = prop_dict.get("config.bootOptions.bootRetryEnabled")
        enterBIOSSetup = prop_dict.get("config.bootOptions.enterBIOSSetup")
        changeVersion = prop_dict.get("config.changeVersion")
        firmware = prop_dict.get("config.firmware")
        diskUuidEnabled = prop_dict.get("config.flags.diskUuidEnabled")
        latencySensitivityLevel = prop_dict.get("config.latencySensitivity.level")
        rebootPowerOff = prop_dict.get("config.rebootPowerOff")
        scheduledHardwareUpgradeStatus = prop_dict.get("config.scheduledHardwareUpgradeInfo.scheduledHardwareUpgradeStatus")
        upgradePolicy = prop_dict.get("config.scheduledHardwareUpgradeInfo.upgradePolicy")
        versionKey = prop_dict.get("config.scheduledHardwareUpgradeInfo.versionKey")
        guestState = prop_dict.get("guest.guestState")
        appState = prop_dict.get("guest.appState")
        guestKernelCrashed = prop_dict.get("guest.guestKernelCrashed")
        guestOperationsReady = prop_dict.get("guest.guestOperationsReady")
        guestStateChangeSupported = prop_dict.get("guest.guestStateChangeSupported")
        interactiveGuestOperationsReady = prop_dict.get("guest.interactiveGuestOperationsReady")
        consolidationNeeded = prop_dict.get("runtime.consolidationNeeded")
        dasProtected = prop_dict.get("runtime.dasVmProtection.dasProtected")
        minRequiredEVCModeKey = prop_dict.get("runtime.minRequiredEVCModeKey")
        raw_timeout = prop_dict.get("config.vmOpNotificationTimeout")
        vmOpNotificationTimeout = max(0, int(raw_timeout)) if raw_timeout is not None else 0
        tools_info = prop_dict.get("config.tools")
        syncTimeWithHost = getattr(tools_info, "syncTimeWithHost", None) if tools_info else None
        toolsUpgradePolicy = getattr(tools_info, "toolsUpgradePolicy", None) if tools_info else None
        vnumaOnCpuHotaddExposed = prop_dict.get("config.numaInfo.vnumaOnCpuHotaddExposed")
        cpuAllocationSharesLevel = prop_dict.get("config.cpuAllocation.shares.level")
        configStatus = prop_dict.get("configStatus", None)
        rawCustomizationStatus = prop_dict.get("guest.customizationInfo.customizationStatus", None)

        if rawCustomizationStatus:
            formattedCustomizationStatus = str(rawCustomizationStatus).strip()
            customizationStatus = formattedCustomizationStatus.replace("TOOLSDEPLOYPKG_", "") if "TOOLSDEPLOYPKG_" in formattedCustomizationStatus else formattedCustomizationStatus
        else:
            customizationStatus = "null"
            
        guestHeartbeatStatus = prop_dict.get("summary.quickStats.guestHeartbeatStatus", None)
        vmPathName = prop_dict.get("summary.config.vmPathName", None)
        memoryAllocationSharesLevel = prop_dict.get("config.memoryAllocation.shares.level", None)

        guest = prop_dict.get("guest", None)
        rawGuestDetailedData = getattr(guest, "guestDetailedData", None)


        guestInfoFields = {
            "buildNumber": "null",
            "cpeString": "null",
            "distroAddlVersion": "null",
            "distroName": "null",
            "distroVersion": "null",
            "kernelVersion": "null",
            "prettyName": "null"
        }

        if rawGuestDetailedData:
            try:
                raw_str = str(rawGuestDetailedData).strip()
                pattern = r"(\w+)=['\"](.*?)['\"]"
                matches = re.findall(pattern, raw_str)

                for key, value in matches:
                    if key in guestInfoFields:
                        guestInfoFields[key] = str(value).strip() if value else "null"

            except Exception as regex_err:
                logger.warning(f"Regex parsing failed for guestDetailedData: {repr(regex_err)}")

        buildNumber = guestInfoFields["buildNumber"]
        cpeString = guestInfoFields["cpeString"]
        distroAddlVersion = guestInfoFields["distroAddlVersion"]
        distroName = guestInfoFields["distroName"]
        distroVersion = guestInfoFields["distroVersion"]
        kernelVersion = guestInfoFields["kernelVersion"]
        prettyName = guestInfoFields["prettyName"]


        vm_obj.with_property("vCommunity|Configuration|NUMA|Hot Add Exposed", str(vnumaOnCpuHotaddExposed))
        vm_obj.with_property("vCommunity|Configuration|CPU Allocation Share Level", str(cpuAllocationSharesLevel))
        vm_obj.with_property("vCommunity|Configuration|Boot Options|Delay", str(bootDelay))
        vm_obj.with_property("vCommunity|Configuration|Boot Options|Retry Delay", str(bootRetryDelay))
        vm_obj.with_property("vCommunity|Configuration|Boot Options|Retry Enabled", str(bootRetryEnabled))
        vm_obj.with_property("vCommunity|Configuration|Boot Options|Enter BIOS Setup", str(enterBIOSSetup))
        vm_obj.with_property("vCommunity|Configuration|Change Version", str(changeVersion))
        vm_obj.with_property("vCommunity|Configuration|Firmware", str(firmware))
        vm_obj.with_property("vCommunity|Configuration|Flags|Disk UUID Enabled", str(diskUuidEnabled))
        vm_obj.with_property("vCommunity|Configuration|Latency Sensitivity Level", str(latencySensitivityLevel))
        vm_obj.with_property("vCommunity|Configuration|Reboot PowerOff", str(rebootPowerOff))
        vm_obj.with_property("vCommunity|Configuration|Hardware Upgrade|Status", str(scheduledHardwareUpgradeStatus))
        vm_obj.with_property("vCommunity|Configuration|Hardware Upgrade|Policy", str(upgradePolicy))
        vm_obj.with_property("vCommunity|Configuration|Hardware Upgrade|Target Version", str(versionKey))
        vm_obj.with_property("vCommunity|Configuration|Op Notification Timeout", str(vmOpNotificationTimeout))
        vm_obj.with_property("vCommunity|Configuration|Memory Allocation Share Level", str(memoryAllocationSharesLevel))
        vm_obj.with_property("vCommunity|Configuration|Config Status", str(configStatus))
        vm_obj.with_property("vCommunity|Guest|State", str(guestState))
        vm_obj.with_property("vCommunity|Guest|Application Status", str(appState))
        vm_obj.with_property("vCommunity|Guest|Kernel Crash State", str(guestKernelCrashed))
        vm_obj.with_property("vCommunity|Guest|Operation Ready", str(guestOperationsReady))
        vm_obj.with_property("vCommunity|Guest|State Change Support", str(guestStateChangeSupported))
        vm_obj.with_property("vCommunity|Guest|Interactive Guest", str(interactiveGuestOperationsReady))
        vm_obj.with_property("vCommunity|Guest|Tools Sync Time", str(syncTimeWithHost))
        vm_obj.with_property("vCommunity|Guest|Tools Upgrade Policy", str(toolsUpgradePolicy))
        vm_obj.with_property("vCommunity|Runtime|Consolidation Needed", str(consolidationNeeded))
        vm_obj.with_property("vCommunity|Runtime|DAS protection", str(dasProtected))
        vm_obj.with_property("vCommunity|Runtime|Min Required EVC Mode Key", str(minRequiredEVCModeKey))
        vm_obj.with_property("vCommunity|Guest|Customization Status", str(customizationStatus))
        vm_obj.with_property("vCommunity|Guest|Heartbeat Status", str(guestHeartbeatStatus))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Build Number", str(buildNumber))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|CPE String", str(cpeString))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Distro Additional Version", str(distroAddlVersion))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Distro Name", str(distroName))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Distro Version", str(distroVersion))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Kernel Version", str(kernelVersion))
        vm_obj.with_property("vCommunity|Guest|Detailed Data|Pretty Name", str(prettyName))
        vm_obj.with_property("vCommunity|Summary|VM Path Name", str(vmPathName))

        logger.debug(f"Successfully collected all configuration properties for VM '{vm_name}'.")

    except Exception as e:
        logger.warning(f"Failed to retrieve VM configuration properties for : {vm_name} - {repr(e)}")