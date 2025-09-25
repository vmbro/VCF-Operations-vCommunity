## Using a Private Registry for VCF Operations vCommunity MP

This document describes a workaround for environments where Cloud Proxies have no internet access, by pulling the VCF Operations vCommunity MP container image manually and configuring it to use a private registry.


#### On local machine
1. Find the latest VCF Operations vCommunity MP container image on Github corresponding to the management pack version:
```https://github.com/vmbro/VCF-Operations-vCommunity/pkgs/container/vcf-operations-vcommunity```


2. Pull the latest VCF Operations vCommunity MP container image to internal container registry 


**Note: the latest 0.2.0 tag as of Sep 2025 is 0.2.0_1757946951.149835. You may find a newer tag version. If so, replace the tag in the example commands below with the newer tag.**


Example:
```docker pull ghcr.io/vmbro/vcf-operations-vcommunity:0.2.0_1757946951.149835```


3. Tag the image on your local machine with the target private registry FQDN and path


**Note: replace **“private-registry.local.network”** with your local registry FQDN in all following example commands.**
**Note: optionally, replace the path **“ghcr.io/vmbro/”** with the desired path in your local registry.**


Example:
```docker tag ghcr.io/vmbro:0.2.0_1757946951.149835 private-registry.local.network/ghcr.io/vmbro/0.2.0_1757946951.149835```


4. Push the image to the private registry


Example:
```docker push private-registry.local.network/ghcr.io/vmbro/0.2.0_1757946951.149835```


#### On each node in the VCF Operations cluster (excluding cloud proxies)
5. Edit the REGISTRY field in **VCFOperationsvCommunity.conf** on the nodes


Example:
```
Edit $VCOPS_BASE/user/plugins/inbound/VCFOperationsvCommunity.conf
REGISTRY=private-registry.local.network
```


#### On Each Cloud Proxy
6. Restart the cloud proxy collector


```service collector restart```


Once steps 1-5 are complete, proceed with adapter instance configuration. The container image will be pulled from the private registry (private-registry.local.network).

**Note: If Cloud Proxy already has internet access to pull the container image you don't need to apply that workaround. Once adapter integration is applied in the VCF Operations Cloud Proxy will automaticly pull the image.**
