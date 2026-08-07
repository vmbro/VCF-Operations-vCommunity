# Metrics & Properties Reference

Every property and metric the vCommunity Management Pack pushes to VCF Operations, organized by object type. Paths shown with a `<placeholder>` segment are **instanced** - they repeat once per matching item on the object (e.g. once per virtual disk, once per configured VIB package), so the real property count on a given object is usually higher than the number of rows below.

> **Note:** Guest OS properties (Windows Services, Windows Event Logs, Operating System info) are not included in this reference yet - their source collectors haven't been verified against this document. If you'd like them added, please open an issue or a PR.

**On this page:**

- [Cluster](#cluster) (22 items)
- [Host](#host) (46 items)
- [Datastore](#datastore) (9 items)
- [Virtual Machine](#virtual-machine) (51 items)
- [vCenter](#vcenter) (11 items)

---

## Cluster

| Type | Path | Description |
| :--- | :--- | :--- |
| ⚪ Property | `vCommunity\|Cluster Configuration\|Configuration Status` | Overall configuration status of the cluster (green/yellow/red/gray) - vCenter's computed health summary for the cluster. |
| 🟢 Metric | `vCommunity\|Cluster Configuration\|Number of Effective Hosts` | Number of hosts in the cluster that are effectively contributing resources (not in maintenance mode). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|Overall Status` | Overall health status of the cluster (green/yellow/red) - a combined assessment of its sub-components (hosts, DRS, HA, etc.). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Host Monitoring` | Whether vSphere HA's host monitoring feature is enabled/disabled - hosts monitor each other's heartbeat. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Host Isolation` | The response HA applies when a host becomes network-isolated (e.g. powerOff, shutdown, none). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Default VM Restart Priority` | Restart priority (low/medium/high) assigned to VMs when a host fails and they are restarted on other hosts. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Datastore APD` | HA's response policy for VMs when a datastore becomes fully inaccessible (All Paths Down). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Datastore PDL` | HA's response policy for VMs when a datastore becomes permanently inaccessible (Permanent Device Loss). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|VM Monitoring` | Status of VM Monitoring - whether frozen/crashed VMs are automatically restarted based on VMware Tools heartbeat. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Heartbeat Datastore` | HA's candidate policy for selecting heartbeat datastores, used by hosts to check each other during a network isolation event. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Failure Interval` | Number of seconds without a VMware Tools heartbeat before a VM is considered 'failed' (seconds). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Max Failure Window` | Time window (seconds) within which VM Monitoring allows a maximum number of restart attempts (works together with Max Failures). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Max Failures` | Maximum number of restart attempts VM Monitoring allows within the Max Failure Window. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Minimum Up Time` | Minimum uptime (seconds) a VM must run after a restart before VM Monitoring resumes watching it. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|DRS\|Proactive DRS` | Whether Proactive DRS is enabled - proactively migrates VMs ahead of predicted hardware failures. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|DRS\|Scale Descendants Shares` | Whether share values of descendant VMs in the resource pool hierarchy are automatically scaled. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|DRS\|CPU Over-Commitment` | Value of the 'MaxVcpusPerCore' advanced option, which caps the max vCPU-to-pCPU ratio DRS will allow. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|DRS\|Virtual Machine Automation Enabled` | Whether DRS allows per-VM automation level overrides (Enable VM Overrides). |
| 🟢 Metric | `vCommunity\|Cluster Configuration\|DRS\|DRS Score` | vCenter's computed DRS Score (0-100) - a summary indicator of resource imbalance in the cluster (100 = perfectly balanced). |
| ⚪ Property | `vCommunity\|Cluster Configuration\|EVC\|Enabled` | Whether Enhanced vMotion Compatibility (EVC) mode is enabled on the cluster. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|EVC\|Mode` | If enabled, the EVC mode key the cluster is running (e.g. intel-cascadelake) - determines the exposed CPU feature baseline. |
| ⚪ Property | `vCommunity\|Cluster Configuration\|DPM\|Host Power Action Rate` | If Distributed Power Management (DPM) is enabled, the aggressiveness level (1-5) controlling how fast hosts are powered on/off. |

[⬆ Back to top](#metrics--properties-reference)

---

## Host

| Type | Path | Description |
| :--- | :--- | :--- |
| ⚪ Property | `vCommunity\|Configuration\|Advanced System Settings\|`<setting_name>`` | The value of an ESXi advanced system setting (e.g. Disk.DiskRetryPeriod) tracked via the esxi_advanced_system_settings config file. One property per tracked setting. |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|Device` | Device name of the Host Bus Adapter (HBA), e.g. vmhba0. One instance per HBA. |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|Bus` | PCI bus number the HBA is attached to. |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|Model` | Hardware model name of the HBA (e.g. NVMe SSD Controller). |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|PCI` | PCI address of the HBA (bus:device.function format). |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|Status` | Operational status of the HBA (e.g. online, unknown, offline). |
| ⚪ Property | `vCommunity\|Storage Adapter:`<hba_device>`\|Type` | Storage protocol type of the HBA (e.g. scsi, nvme, fc, iscsi). |
| ⚪ Property | `vCommunity\|Storage Adapter\|Number of HBA` | Total number of Host Bus Adapters detected on the host. |
| ⚪ Property | `vCommunity\|Configuration\|VAAI\|ATS Heartbeat` | Value of the VMFS3.UseATSForHBOnVMFS5 advanced setting - whether the VAAI ATS (Atomic Test and Set) heartbeat mechanism is used. |
| ⚪ Property | `vCommunity\|Configuration\|VAAI\|ATS Locking` | Value of the VMFS3.HardwareAcceleratedLocking advanced setting - status of VAAI hardware-accelerated locking. |
| ⚪ Property | `vCommunity\|Configuration\|Config Status` | Overall configuration health status of the host (green/yellow/red/gray). |
| ⚪ Property | `vCommunity\|Configuration\|Max EVC` | The highest EVC (Enhanced vMotion Compatibility) mode the host's CPU supports. |
| ⚪ Property | `vCommunity\|Network\|DHCP` | Whether the host's management network uses DHCP (True/False). |
| ⚪ Property | `vCommunity\|Network\|Search Domain` | The host's DNS search domain(s) (comma-separated if multiple). |
| ⚪ Property | `vCommunity\|Configuration\|Time Zone\|Name` | Short name of the time zone assigned to the host (e.g. UTC). |
| ⚪ Property | `vCommunity\|Configuration\|Time Zone\|Description` | Human-readable description of the host's time zone. |
| ⚪ Property | `vCommunity\|Configuration\|Time Zone\|GMT Offset` | The host's time zone offset from GMT, in seconds. |
| ⚪ Property | `vCommunity\|Runtime\|Boot Time` | Timestamp of the host's (ESXi's) most recent boot. |
| ⚪ Property | `vCommunity\|Hardware\|BIOS Vendor` | Name of the BIOS/firmware vendor for the host's hardware. |
| ⚪ Property | `vCommunity\|Capability\|Storage vMotion Supported` | Whether the host supports Storage vMotion (True/False). |
| ⚪ Property | `vCommunity\|Configuration\|Install Date\|UTC` | Date/time (UTC, ISO 8601) when ESXi was installed on this host. Retrieved via a live RPC call through imageConfigManager. |
| ⚪ Property | `vCommunity\|Licensing:`<license_name>`\|Name` | Name of the license assigned to the host (e.g. Evaluation Mode, vSphere Enterprise Plus). |
| ⚪ Property | `vCommunity\|Licensing:`<license_name>`\|License Key` | Key of the assigned license (may be returned in a partially masked format). |
| ⚪ Property | `vCommunity\|Licensing:`<license_name>`\|Edition Key` | Edition/product identifier of the license (e.g. esxEval, esxEnterprisePlus). |
| ⚪ Property | `vCommunity\|Licensing:`<license_name>`\|License Expiration Date` | Expiration date of the license (only pushed if an expirationDate is present, e.g. for evaluation licenses). |
| 🟢 Metric | `vCommunity\|Licensing:`<license_name>`\|Remaining Days` | Number of days remaining until the license expires (only computed and pushed if an expirationDate exists). |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Package Name` | Name of a VIB (VMware Installation Bundle) package tracked via the esxi_packages config file. |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Package Version` | Version number of the VIB package (including build metadata). |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Acceptance Level` | VMware acceptance level of the VIB package (e.g. vmware_certified, partner, community). |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Maintenance Mode Required` | Whether the host must be in maintenance mode to install/remove this package. |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Package Summary` | Short summary/description of the VIB package. |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Package Type` | Type of the package (e.g. bootbank, tools). |
| ⚪ Property | `vCommunity\|Configuration\|Packages:`<package_name>`\|Package Vendor` | Vendor/publisher of the VIB package (e.g. VMware, VMW, Broadcom). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Device Name` | Device name of the physical network adapter (pNIC), e.g. vmnic0. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Driver Version` | Driver software version used by the pNIC. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Firmware Version` | Firmware version of the pNIC hardware. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Status` | Link status of the pNIC - 'Connected' if link speed info is present, otherwise 'Disconnected'. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI Vendor Name` | Vendor name of the pNIC's matched PCI device (e.g. VMware Inc., Broadcom). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI Device Name` | Model/product name of the pNIC's matched PCI device. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI Vendor ID (VID)` | PCI vendor identifier of the device (hex format, e.g. 15ad). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI Device ID (DID)` | PCI product/model identifier of the device (hex format). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI SubVendor ID (SVID)` | PCI sub-vendor identifier of the device (hex format). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|MAC` | Physical MAC address of the pNIC. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Wake On Lan Supported` | Whether the pNIC supports Wake-on-LAN. |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|PCI` | PCI slot address of the pNIC (bus:device.function format). |
| ⚪ Property | `vCommunity\|Network\|Device:`<vmnic>`\|Duplex` | Whether the pNIC link is running full-duplex or half-duplex. |

[⬆ Back to top](#metrics--properties-reference)

---

## Datastore

| Type | Path | Description |
| :--- | :--- | :--- |
| ⚪ Property | `vCommunity\|Identifiers\|Number of Extents` | Number of VMFS extents (physical disk segments) making up the datastore. 0 if not VMFS or no extents present. |
| ⚪ Property | `vCommunity\|Identifiers\|Extent:`<index>`\|ID` | Unique disk identifier (naa.* format) of each physical extent making up the datastore. |
| ⚪ Property | `vCommunity\|Summary\|MOID` | The datastore's Managed Object ID within vCenter (e.g. datastore-15). |
| ⚪ Property | `vCommunity\|Summary\|Block Size` | Block size (MB) of the VMFS datastore. Only pushed for VMFS-type datastores. |
| ⚪ Property | `vCommunity\|Summary\|Max Blocks` | Maximum number of blocks the VMFS datastore can hold. Only pushed for VMFS-type datastores. |
| ⚪ Property | `vCommunity\|Summary\|VMFS Upgradable` | Whether the VMFS version can be upgraded to a newer version. Only pushed for VMFS-type datastores. |
| ⚪ Property | `vCommunity\|Summary\|Status` | Overall health status of the datastore (green/yellow/red/gray). |
| ⚪ Property | `vCommunity\|Summary\|SIOC Enabled` | Whether Storage I/O Control (SIOC) is enabled for this datastore. |
| ⚪ Property | `vCommunity\|Summary\|SIOC Threshold` | Latency threshold (ms) at which SIOC engages. |

[⬆ Back to top](#metrics--properties-reference)

---

## Virtual Machine

| Type | Path | Description |
| :--- | :--- | :--- |
| ⚪ Property | `vCommunity\|Options\|`<config_path>`` | Value of a VM config field (e.g. config.bootOptions.bootDelay) tracked via the vm_options config file. One property per tracked field; skipped entirely if the value is None. |
| ⚪ Property | `vCommunity\|Configuration\|Advanced Parameters\|`<key>`` | Value of a VM advanced parameter (extraConfig, e.g. svga.present) tracked via the vm_advanced_parameters config file. |
| 🟢 Metric | `vCommunity\|Configuration\|SCSI Controllers\|Count` | Number of SCSI controllers attached to the VM. |
| ⚪ Property | `vCommunity\|Configuration\|SCSI Controllers:`<bus_number>`\|Type` | Type of a given SCSI controller (e.g. VMware Paravirtual (PVSCSI), LSI Logic SAS, LSI Logic Parallel, BusLogic). |
| ⚪ Property | `vCommunity\|Network\|Network Adapters:`<adapter_name>`\|Type` | MAC address assignment type of the VM network adapter (e.g. assigned, generated, manual). |
| ⚪ Property | `vCommunity\|Network\|Network Adapters:`<adapter_name>`\|Starts Connected` | Whether the network adapter is set to auto-connect on VM power-on. |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Label` | Display label of the virtual disk (e.g. Hard disk 1). |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Key` | Unique device key of the virtual disk within the VM. |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Controller Key` | Device key of the SCSI/NVMe controller the disk is attached to. |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Eagerly Scrub` | Whether the disk was created with 'eager zeroed thick' provisioning. |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Split` | Whether the virtual disk file is split into 2GB chunks (split disk format). |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Write Through` | Whether the disk operates in write-through (synchronous write) mode. |
| ⚪ Property | `vCommunity\|Virtual Disk:`<disk_name>`\|Storage Allocation Share Level` | Storage I/O resource share level of the disk (low/normal/high/custom). |
| ⚪ Property | `vCommunity\|Configuration\|NUMA\|Hot Add Exposed` | Whether the vNUMA topology is exposed to the guest while CPU hot-add is enabled. |
| ⚪ Property | `vCommunity\|Configuration\|CPU Allocation Share Level` | CPU resource share level of the VM (low/normal/high/custom). |
| ⚪ Property | `vCommunity\|Configuration\|Boot Options\|Delay` | Delay (ms) applied before the BIOS/UEFI screen during VM boot. |
| ⚪ Property | `vCommunity\|Configuration\|Boot Options\|Retry Delay` | Wait time (ms) before retrying boot after a failed boot attempt. |
| ⚪ Property | `vCommunity\|Configuration\|Boot Options\|Retry Enabled` | Whether automatic retry is enabled after a failed boot attempt. |
| ⚪ Property | `vCommunity\|Configuration\|Boot Options\|Enter BIOS Setup` | Whether the VM will boot directly into the BIOS/UEFI setup screen on next power-on. |
| ⚪ Property | `vCommunity\|Configuration\|Change Version` | Last-modified timestamp/version marker of the VM configuration (used for concurrent-update detection). |
| ⚪ Property | `vCommunity\|Configuration\|Firmware` | Firmware type used by the VM (bios or efi). |
| ⚪ Property | `vCommunity\|Configuration\|Flags\|Disk UUID Enabled` | Status of the flag that exposes disk UUIDs to the guest operating system. |
| ⚪ Property | `vCommunity\|Configuration\|Latency Sensitivity Level` | Latency sensitivity level of the VM (normal/medium/high/low) - higher levels reserve dedicated CPU/network resources. |
| ⚪ Property | `vCommunity\|Configuration\|Reboot PowerOff` | Whether a reboot request from the guest OS powers off the VM instead (used in specific edge-case scenarios). |
| ⚪ Property | `vCommunity\|Configuration\|Hardware Upgrade\|Status` | Current status of a scheduled VM hardware version upgrade (e.g. none, pending, error). |
| ⚪ Property | `vCommunity\|Configuration\|Hardware Upgrade\|Policy` | Policy that determines when the VM hardware version is automatically upgraded (e.g. never, onSoftPowerOff, always). |
| ⚪ Property | `vCommunity\|Configuration\|Hardware Upgrade\|Target Version` | Target VM hardware version key of the scheduled upgrade. |
| ⚪ Property | `vCommunity\|Configuration\|Op Notification Timeout` | Timeout (seconds) for guest operation notifications (vmOpNotification); negative values are clamped to 0. |
| ⚪ Property | `vCommunity\|Configuration\|Memory Allocation Share Level` | Memory resource share level of the VM (low/normal/high/custom). |
| ⚪ Property | `vCommunity\|Configuration\|Config Status` | Overall health status of the VM configuration (green/yellow/red/gray). |
| ⚪ Property | `vCommunity\|Guest\|State` | Running state of the guest operating system (e.g. running, notRunning, shuttingDown). |
| ⚪ Property | `vCommunity\|Guest\|Application Status` | Application-level heartbeat/monitoring status inside the guest. |
| ⚪ Property | `vCommunity\|Guest\|Kernel Crash State` | Whether the guest OS kernel has crashed (kernel panic/BSOD detection). |
| ⚪ Property | `vCommunity\|Guest\|Operation Ready` | Whether guest operations (e.g. file/process management) are available. |
| ⚪ Property | `vCommunity\|Guest\|State Change Support` | Whether the guest OS supports state-change notifications (standby/hibernate, etc.). |
| ⚪ Property | `vCommunity\|Guest\|Interactive Guest` | Whether VMware Tools is running in interactive mode (inside a logged-in user session). |
| ⚪ Property | `vCommunity\|Guest\|Tools Sync Time` | Setting controlling whether VMware Tools synchronizes the guest clock with the host. |
| ⚪ Property | `vCommunity\|Guest\|Tools Upgrade Policy` | Automatic upgrade policy for VMware Tools (e.g. manual, upgradeAtPowerCycle). |
| ⚪ Property | `vCommunity\|Runtime\|Consolidation Needed` | Whether the VM's snapshot files need to be consolidated. |
| ⚪ Property | `vCommunity\|Runtime\|DAS protection` | Whether the VM is protected by vSphere HA (DAS). |
| ⚪ Property | `vCommunity\|Runtime\|Min Required EVC Mode Key` | Minimum EVC mode required for the VM to run (derived from the CPU features the VM is using). |
| ⚪ Property | `vCommunity\|Guest\|Customization Status` | Status of guest OS customization (sysprep/cloud-init), with the TOOLSDEPLOYPKG_ prefix stripped. |
| ⚪ Property | `vCommunity\|Guest\|Heartbeat Status` | VMware Tools heartbeat status (green/yellow/red/gray) - a summary indicator of guest liveness. |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Build Number` | Build number of the guest OS (parsed via regex from VMware Tools guestDetailedData). |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|CPE String` | Common Platform Enumeration (CPE) identifier of the guest OS. |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Distro Additional Version` | Additional version information for the guest OS distribution. |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Distro Name` | Name of the guest OS distribution (e.g. Ubuntu, VMware Photon OS). |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Distro Version` | Version number of the guest OS distribution. |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Kernel Version` | Kernel version of the guest OS. |
| ⚪ Property | `vCommunity\|Guest\|Detailed Data\|Pretty Name` | Human-readable / full name of the guest OS (e.g. Ubuntu 24.04.4 LTS). |
| ⚪ Property | `vCommunity\|Summary\|VM Path Name` | Full datastore path to the VM's .vmx configuration file. |

[⬆ Back to top](#metrics--properties-reference)

---

## vCenter

| Type | Path | Description |
| :--- | :--- | :--- |
| ⚪ Property | `vCommunity\|Configuration\|Patch Level` | The applied patch level of the vCenter Server software. |
| ⚪ Property | `vCommunity\|Configuration\|User Directory Timeout` | Timeout (seconds) for user directory (AD/LDAP) queries. |
| ⚪ Property | `vCommunity\|Configuration\|Enable MOB` | Whether the vCenter Managed Object Browser (MOB) debug interface is enabled. |
| ⚪ Property | `vCommunity\|Configuration\|Database\|Event retention (days)` | Number of days event records are retained in the vCenter database. |
| ⚪ Property | `vCommunity\|Configuration\|Database\|Event Cleanup Enabled` | Whether automatic cleanup of old event records is enabled. |
| ⚪ Property | `vCommunity\|Configuration\|Database\|Task retention (days)` | Number of days task records are retained in the vCenter database. |
| ⚪ Property | `vCommunity\|Configuration\|Database\|Task Cleanup Enabled` | Whether automatic cleanup of old task records is enabled. |
| ⚪ Property | `vCommunity\|Configuration\|Runtime\|vCenter Unique ID` | Unique instance identifier of the vCenter Server. |
| ⚪ Property | `vCommunity\|Configuration\|Runtime\|vCenter managed address` | The managed (published) IP address of the vCenter Server. |
| ⚪ Property | `vCommunity\|Configuration\|Database\|Maximum Connections` | Maximum number of connections allowed to the vCenter database. |
| ⚪ Property | `vCommunity\|Configuration\|Log Level` | Configured log level of the vCenter Server (e.g. info, debug, warning). |

[⬆ Back to top](#metrics--properties-reference)

---

**Total: 139 template rows across 5 object types.**
