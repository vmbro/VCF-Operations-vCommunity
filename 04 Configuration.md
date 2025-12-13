# Configuration and Integration

Once the **VCF Operations vCommunity Management Pack** has been installed, the first step is to create an Adapter Instance to connect to your vCenter Server(s).

## 1. Creating the Adapter Instance

Follow these steps within VCF Operations:

1.  Navigate to **Administration** --> **Integrations** --> **Repository** Tab.
2.  Click on the **"VCF Operations vCommunity"** tile.
3.  Click **"Add Account"**.

### 1.1. Account Details

Provide the required information in the fields:

| Field | Description | Important Note |
| :--- | :--- | :--- |
| **Name** | A descriptive name for your Adapter Instance. | E.g., `VCF-Ops-vCenter-Prod` |
| **Description** | A brief description of this instance's purpose. | |
| **vCenter Server** | The **FQDN** or **IP** of your target vCenter Server. | **Crucially, this must be the exact same FQDN/IP used for your native vCenter Adapter Instance.** |
| **Credential** | Select your vCenter credential and, if needed, your Windows credential. | The Windows credential is only required if you are collecting **Windows Services** and/or **Events**. |
| **Collector/Group** | Select a **Cloud Proxy** from the dropdown. | Ensure the Cloud Proxy has connectivity. Data collection should begin within 5 minutes. |

### 1.2. Configuration File Selection

The management pack uses customizable XML configuration files to define what data to collect. These default files are located under **Infrastructure Operations** --> **Configurations** --> **Management Pack Configuration** --> **System Defined**.

| Field | Configuration File (Default) | Description of Collected Data |
| :--- | :--- | :--- |
| **ESXi Advanced System Settings Config File** | `esxi_advanced_system_settings.xml` | System --> Advanced System Settings as seen on ESXi Hosts via vCenter's **Configure** tab. |
| **ESXi Software Packages Config File** | `esxi_packages.xml` | System --> Packages as seen on ESXi Hosts via vCenter's **Configure** tab. |
| **VM Advanced Parameters Config File** | `vm_advanced_parameters.xml` | Advanced Parameters for VMs (visible in vCenter MOB UI under `config -> extraConfig` section). |
| **VM Options Config File** | `vm_options.xml` | VM Options for VMs (visible in vCenter MOB UI under `config` option). |

---

## 2. Advanced Settings (Optional)

You can expand the adapter configuration by clicking **Advanced Settings**.

| Advanced Setting | Default Value | Description |
| :--- | :--- | :--- |
| **Port** | `443` | The default port for connectivity to vCenter. |
| **Windows Service Configuration File** | `windows_service_list.xml` | File used to define which Windows Services to monitor. (Location: System Defined configurations) |
| **Service Monitoring Enabled** | `Enabled/Disabled` | Toggles Windows Service monitoring using the `windows_service_list.xml` file. |
| **Windows Event Log Configuration File** | `windows_event_list.xml` | File used to define which Windows Event Logs to monitor. (Location: System Defined configurations) |
| **Windows Event Log Monitoring Status** | `Enabled/Disabled` | Toggles Windows Event Log Monitoring using the `windows_event_list.xml` file. |

---

## 3. Advanced Configuration: Tailoring Monitoring Scope

You can **tailor the monitoring scope** for different vCenter servers or environments (e.g., Production vs. Non-Production).

### 3.1. Steps to Create Custom Configuration Files

1.  **Duplicate the Default File:** Navigate to **Infrastructure Operations** --> **Configurations** --> **Management Pack Configuration** --> **System Defined**.
2.  Locate the desired file (e.g., `esxi_advanced_system_settings.xml`).
3.  Click the **Clone** icon to create a copy.
    * **Name the new file** to reflect its purpose (e.g., `esxi_adv_settings_non_prod.xml`).
4.  **Edit the New File:** Modify the content of the cloned file to include only the settings or items you wish to monitor for the specific environment.
5.  **Reference in New Adapter Instance:** Create a new Adapter Instance (Section 1), but when you reach the **Configuration File Selection** fields, enter the **custom file name** you created (e.g., `esxi_adv_settings_non_prod.xml`).

---

## 4. Validate the Configuration

1. Click **Validate Connection** to validate the adapter instance connection

Once completed your management pack will now be configured and will begin collecting data.