
## System Requirements

### Platform Requirements
* Aria Operations 8.18.x and higher including VCF Operations 9.x
* vCenter Server 8 and higher including VCF 9.x
* Aria Operations Cloud Proxy
* Container Registry access to allow Cloud Proxy to install adapter requirements *(For the dark-site environments please see the [Questions & Answers ](https://github.com/vmbro/VCF-Operations-vCommunity/tree/main?tab=readme-ov-file#questions--answers) section for the workaround)*

Cloud Proxy will try to pull that container image from following example registry to set-up the adapter. This is by design of the VCF Operations Integration SDK.
```
ghcr.io/vmbro/vcf-operations-vcommunity:x.x.x_x.x
```

### User Account Requirements
#### vCenter Server:
* An account with read-only permission
* Propagate to children option must be selected
* ```Host.Configuration.ImageConfiguration``` (Need for collecting ESXi VIB packages)
