# VM Shares

**Share per vCPU** and **Share per MB of Memory** normalise the CPU and memory shares of a VM by its size, so VMs of different sizes can be compared. Shares only matter when there is contention: a VM above Normal then gets more than its fair part, one below gets less.

They replace the "Share per vCPU" and "Share per GB of Memory" super metrics. Unlike a super metric, they need no manual enablement in the policy.

Code: [`Management Pack/app/metrics/vm/vm_shares.py`](../Management%20Pack/app/metrics/vm/vm_shares.py)

## Known limitations

> **Read this before using the metrics.**

- **"Share per GB of Memory" is now "Share per MB of Memory".** The super metric calculated shares ÷ memoryKB × 1024, which is per MB, not per GB. The values are the same as before; only the name is correct now. Normal is 10.
- **No value when the VM has no vCPU count, no memory size or no shares in VCF Operations**, instead of a division by zero.
- **Custom shares are compared as they are.** A VM with custom shares can be anywhere; the Normal, Low and High values below apply to the standard levels only.

## The metrics

Published on every VM, powered on or off, in the VM's `vCommunity|Configuration` group, next to the share levels.

| Metric | Calculation | Low | Normal | High |
| :--- | :--- | :--- | :--- | :--- |
| `vCommunity\|Configuration\|Share per vCPU` | CPU shares ÷ vCPUs | 500 | 1000 | 2000 |
| `vCommunity\|Configuration\|Share per MB of Memory` | Memory shares ÷ configured memory in MB | 5 | 10 | 20 |

**Inputs**, from VCF Operations, as in the super metrics: `config|cpuAllocation|shares|shares`, `config|memoryAllocation|shares|shares`, `config|hardware|numCpu` and `config|hardware|memoryKB`.

## Design considerations

- **Code, not a super metric**, so the values are there as soon as the pack is installed, without enabling anything in the policy.
- **Every VM, powered on or off.** Shares are configuration, and apply as soon as the VM is powered on.
- **Read once per cycle for all VMs.** The shares are read in one request; the vCPU count and memory size are already read for the KPIs. The shares are read as properties, or as stats when VCF Operations stores them as stats.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Example

A VM with 4 vCPU and 16 GB at Normal has 4,000 CPU shares and 163,840 memory shares: Share per vCPU = 1,000, Share per MB of Memory = 10.

The same example is checked by the tests in [`Management Pack/tests/test_vm_shares.py`](../Management%20Pack/tests/test_vm_shares.py).
