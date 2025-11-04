
## Configuration and Integration
Once the vCommunity Management Pack has been installed, you will create an Adapter Instance for your vCenter/s.  

![Adapter Config](/Documentation-Images/screenshots/Configuration/Adapter_Instance_Configuration_v2.png)

You will need the following fields:

1. Name: name of your Adapter Instance
2. Description: description of your Adapter Instance
3. vCenter Server: FQDN or IP of your vCenter target.  Be sure to use the exact same FQDN/IP that you're using for your vCenter Adapter Instance.
4. ESXi Advanced Parameters Config File: esxi_advanced_system_settings.  This can be adjusted to include additional Advanced System Settings via Infrastructure Operations - Configurations - Management Pack Configuration - System Defined - esxi_advanced_system_settings.xml.  These are the System - Advanced System Settings as seen on ESXi Hosts in vCenter via the Configure tab.
5. ESXi Software Packages Config File: esxi_packages.  This can be adjusted to include additional Packages via Infrastructure Operations - Configurations - Management Pack Configuration - System Defined - esxi_packages.xml.  These are the System - Packages as seen on ESXi Hosts in vCenter via the Configure tab.
6. VM Advanced Paramters Config File: vm_advanced_parameters.  This can be adjusted to include additional Advanced Parameters via Infrastructure Operations - Configurations - Management Pack Configuration - System Defined - vm_advanced_parameters.xml.  These are the Advanced Parameters as seen on VMs in vCenter via Edit Settings.  They can also be seen via the vCenter MOB UI for the VM in question and the config - extraConfig section.
7. VM Options Config File: vm_options.  This can be adjusted to include additional Configurations via Infrastructure Operations - Configurations - Management Pack Configuration - System Defined - vm_options.xml.  These are the VM Options as seen on VMs in vCenter via Edit Settings.  For Configuration names go to the vCenter MOB for the VM in question and the config option.
8. Credential: this will be your vCenter credential.
9. Collector/Group: you must select a Cloud Proxy here.  If the Cloud Proxy has internet access then Adapter Instance should start collecting data within 5m.
10. Advanced Settings - Windows Event Log Configuration File: windows_event_list.  This can be adjusted to include additional Events via Infrastructure Operations - Configurations - Management Pack Configuration - System Defined.
11. Advanced Settings - Port: 443.  This is the default port for connectivity to vCenter
12. Advanced Settings - Service Monitoring Enabled: Enabled/Disabled.  This will enable/disable Windows Service monitoring.  By default, we monitor all Windows Services that are set to Automatic.
13. Advanced Settings - Windows Event Log Monitoring Status: Enabled/Disabled.  This will enable/disable Windows Event Log Monitoring as defined by the windows_event_list.xml cconfiguration file.

