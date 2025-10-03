
### Platform Requirements
* VCF Operations 9.0 or higher
* vCenter Server 8 and higher including VCF 9.x
* VCF Operations Cloud Proxy
* Container Registry access to allow Cloud Proxy to install adapter requirements *(For the dark-site environments please see the [Questions & Answers ](https://github.com/vmbro/VCF-Operations-vCommunity/tree/main?tab=readme-ov-file#questions--answers) section for the workaround)*

Cloud Proxy will try to pull that container image from following example registry to set-up the adapter. This is by design of the VCF Operations Integration SDK.
```
ghcr.io/vmbro/vcf-operations-vcommunity:x.x.x_x.x
```
HTTPS access is required for all Cloud Proxies that runs VCF Operations vCommunity Management pack to Container Registry access to **ghcr.io**

After installing the .PAK file for the first time Cloud Proxy will try to pull the related container image from the registry. However, Cloud Proxy will try to pull the new container image after .PAK file upgrade process too. Since VCF Operations vCommunity MP continuesly updated it is recommended to have container registry access. This way, administrators can always easily upgrade this package.

If your Cloud Proxy does not have Internet access, follow this to work with public registry.
[Using a Private Registry for VCF Operations vCommunity MP](https://github.com/vmbro/VCF-Operations-vCommunity/blob/main/Working-with-Private-Registry.md#using-a-private-registry-for-vcf-operations-vcommunity-mp)

FYI, Internet proxy setting is available durng the OVF deployment.

### User Account Requirements
#### vCenter Server:
* An account with read-only permission
* Propagate to children option must be selected
* ```Host.Configuration.ImageConfiguration``` (Need for collecting ESXi VIB packages)
