# Dark Site Installation

This document describes a workaround for environments where Cloud Proxies have no internet access, by pulling the VCF Operations vCommunity MP container image manually and pushing it to a private registry.

> **Do you actually need this?** If your Cloud Proxy already has internet access to pull the container image, you don't need this workaround — once the Adapter Instance is configured, the Cloud Proxy will automatically pull the image on its own. See [How It Works](how-it-works.md) for the normal (internet-connected) flow.

**On this page:**

- [Step 1–4: On the Local Machine](#step-14-on-the-local-machine)
- [Step 5: On Each VCF Operations Cluster Node](#step-5-on-each-vcf-operations-cluster-node-excluding-cloud-proxies)
- [Step 6: On Each Cloud Proxy](#step-6-on-each-cloud-proxy)

---

## Step 1–4: On the Local Machine

**Step 1: Find the latest image tag.**

Find the latest VCF Operations vCommunity MP container image on GitHub, corresponding to the Management Pack version you want to install:

```
https://github.com/vmbro/VCF-Operations-vCommunity/pkgs/container/vcf-operations-vcommunity
```

> The latest `0.2.0` tag as of Sep 2025 is `0.2.0_1757946951.149835`. You may find a newer tag — if so, replace the tag in every example command below with that newer version.

**Step 2: Pull the image to your local machine.**

```bash
docker pull ghcr.io/vmbro/vcf-operations-vcommunity:0.2.0_1757946951.149835
```

**Step 3: Re-tag the image for your private registry.**

> Replace `private-registry.local.network` with your own registry's FQDN in every command below. You may also replace the path `ghcr.io/vmbro/` with a different path in your registry, as long as you use the same replacement consistently in steps 3 and 4.

```bash
docker tag ghcr.io/vmbro/vcf-operations-vcommunity:0.2.0_1757946951.149835 private-registry.local.network/ghcr.io/vmbro/vcf-operations-vcommunity:0.2.0_1757946951.149835
```

**Step 4: Push the image to your private registry.**

```bash
docker push private-registry.local.network/ghcr.io/vmbro/vcf-operations-vcommunity:0.2.0_1757946951.149835
```

---

## Step 5: On Each VCF Operations Cluster Node (excluding Cloud Proxies)

Edit the `REGISTRY` field in `VCFOperationsvCommunity.conf` on every node:

```
$VCOPS_BASE/user/plugins/inbound/VCFOperationsvCommunity.conf
```

```
REGISTRY=private-registry.local.network
```

---

## Step 6: On Each Cloud Proxy

Restart the collector so it picks up the new registry setting:

```bash
service collector restart
```

---

Once steps 1–6 are complete, proceed with [Adapter Instance configuration](configuration.md) as normal — the container image will now be pulled from your private registry (`private-registry.local.network`) instead of the public one.

---

**Next:** [Configuration](configuration.md) · [How It Works](how-it-works.md)
