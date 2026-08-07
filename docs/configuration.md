# Configuration and Integration

Once the **VCF Operations vCommunity Management Pack** has been installed, the first step is to create an Adapter Instance to connect to your vCenter Server(s).

**On this page:**

- [1. Creating the Adapter Instance](#1-creating-the-adapter-instance)
- [2. Advanced Settings](#2-advanced-settings-optional)
- [3. Tailoring Monitoring Scope](#3-advanced-configuration-tailoring-monitoring-scope)
- [4. Validate the Configuration](#4-validate-the-configuration)

---

## 1. Creating the Adapter Instance

Follow these steps within VCF Operations:

1. Navigate to **Administration** → **Integrations** → **Repository** tab.
2. Click on the **"VCF Operations vCommunity"** tile.
3. Click **"Add Account"**.

### 1.1. Account Details

Provide the required information in the fields:

| Field | Description | Important Note |
| :--- | :--- | :--- |
| **Name** | A descriptive name for your Adapter Instance. | E.g., `VCF-Ops-vCenter-Prod` |
| **Description** | A brief description of this instance's purpose. | |
| **vCenter Server** | The **FQDN** or **IP** of your target vCenter Server. | ⚠️ **This must be the exact same FQDN/IP used for your native vCenter Adapter Instance.** The Management Pack matches against it to link its collected objects to the native vSphere topology. |
| **Credential** | Select your vCenter credential and, if needed, your Windows credential. | The Windows credential is only required if you are collecting **Windows Services** and/or **Windows Event Logs**. |
| **Collector/Group** | Select a **Cloud Proxy** (or Collector Group) from the dropdown. | Ensure the Cloud Proxy has connectivity to the vCenter Server. Data collection should begin within 5 minutes. |

### 1.2. Configuration File Selection

The Management Pack uses customizable XML configuration files to define what data to collect. These default files are located under **Infrastructure Operations** → **Configurations** → **Management Pack Configuration** → **System Defined**.

| Field | Configuration File (Default) | Description of Collected Data |
| :--- | :--- | :--- |
| **ESXi Advanced System Settings Config File** | `esxi_advanced_system_settings.xml` | ESXi Advanced System Settings — the specific settings listed in this file (as seen on a host's **Configure** tab in vCenter). |
| **ESXi Software Packages Config File** | `esxi_packages.xml` | Installed VIB/software package details for the package names listed in this file (as seen on a host's **Configure** tab in vCenter). ⚠️ See the [performance note](#a-note-on-esxi-software-packages) below before enabling this in large environments. |
| **VM Advanced Parameters Config File** | `vm_advanced_parameters.xml` | VM Advanced Parameters for the keys listed in this file — visible in the vCenter MOB UI under a VM's `config.extraConfig`. |
| **VM Options Config File** | `vm_options.xml` | VM configuration fields for the property paths listed in this file (e.g. boot options, firmware type) — visible in the vCenter MOB UI under a VM's `config` object. |

> #### A note on ESXi Software Packages
> Retrieving VIB/software package data requires a live RPC call to each host (`fetchSoftwarePackages()`), which is significantly slower than the Management Pack's other, property-collector-based data — this is inherent to how ESXi exposes this data, not something this Management Pack can bypass. In large environments (hundreds of hosts), enabling this can meaningfully add to the total collection time. It's still designed to complete well within a typical collection interval, but if you don't need VIB/driver tracking, leaving `esxi_packages.xml` empty avoids the extra cost entirely.

---

## 2. Advanced Settings (Optional)

You can expand the adapter configuration by clicking **Advanced Settings**.

| Advanced Setting | Default Value | Description |
| :--- | :--- | :--- |
| **Port** | `443` | The port used to connect to vCenter Server. |
| **Windows Service Configuration File** | `windows_service_list.xml` | File used to define which Windows Services to monitor. (Location: System Defined configurations) |
| **Guest OS Service Monitoring Status** | `Disabled` | Toggles Windows Service monitoring using the `windows_service_list.xml` file. Set to `Enabled` to activate. |
| **Windows Event Log Configuration File** | `windows_event_list.xml` | File used to define which Windows Event Log IDs to monitor. (Location: System Defined configurations) |
| **Windows Event Log Monitoring Status** | `Disabled` | Toggles Windows Event Log monitoring using the `windows_event_list.xml` file. Set to `Enabled` to activate. |

> #### A note on Guest OS monitoring
> Both Guest OS features are **agentless**, using GuestAPI with the credentials you provide — but they still add load to both VCF Operations and the target Windows guest, proportional to how many VMs you enable this for. Before enabling either of these across hundreds of Windows machines, evaluate the additional load in your environment and consider a targeted `vm_advanced_parameters`-style scoped rollout (see [Section 3](#3-advanced-configuration-tailoring-monitoring-scope)) rather than enabling it globally on day one.

---

## 3. Advanced Configuration: Tailoring Monitoring Scope

You can **tailor the monitoring scope** for different vCenter servers or environments (e.g., Production vs. Non-Production) by creating your own configuration files instead of using the system-defined defaults.

### 3.1. Steps to Create Custom Configuration Files

1. **Duplicate the default file:** Navigate to **Infrastructure Operations** → **Configurations** → **Management Pack Configuration** → **System Defined**.
2. Locate the desired file (e.g., `esxi_advanced_system_settings.xml`).
3. Click the **Clone** icon to create a copy.
   - **Name the new file** to reflect its purpose (e.g., `esxi_adv_settings_non_prod.xml`).
4. **Edit the new file:** Modify the content of the cloned file to include only the settings or items you wish to monitor for the specific environment.
5. **Reference it in a new Adapter Instance:** Create a new Adapter Instance ([Section 1](#1-creating-the-adapter-instance)), but when you reach the **Configuration File Selection** fields, enter the **custom file name** you created (e.g., `esxi_adv_settings_non_prod.xml`).

This is also the right mechanism for scoping *what* gets monitored to match your organization's actual hardening guides, KBs, or internal best practices — see [Introduction](introduction.md#why-you-need-it) for why that matters.

---

## 4. Validate the Configuration

1. Click **Validate Connection** to validate the Adapter Instance connection.

Once completed, your Management Pack will now be configured and will begin collecting data.

---

**Next:** [How It Works](how-it-works.md) · [Metrics & Properties Reference](metrics-reference.md)
