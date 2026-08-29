# Multi-cgroup network fanout

This benchmark uses the existing `iperf3` tool to model a multi-tenant host
receiving traffic for many containers or services. Each reverse-loopback
client is placed in its own cgroup v2 memory cgroup, so network receive work
mixes memory-accounting charges for distinct tenants on the same CPUs.

The primary metric is aggregate received Gbit/s. `gbps_per_client`, completed
clients, failures, and elapsed time guard against false throughput wins. The
1, 8, 16, 32, and 64-client points are repeated five times. Setup, cgroup
creation, and server startup happen before the internal timed interval.

This is the real-tool companion to `memcg_stock_switch`: the focused test
pins several memory-cgroup allocation streams to each CPU, while this workload
exercises the same mixed-cgroup charge-cache behavior through actual TCP
receive paths. It specifically evaluates per-CPU multi-memcg charge stocks;
it is not a general internet or NIC benchmark because loopback deliberately
removes physical-network variance.

Run it with:

```sh
scripts/bm-external/memcg-net-fanout/configure.sh
scripts/run-single.sh config/bm-external/memcg-net-fanout.json
```

The runner needs passwordless `sudo` to create and remove its uniquely named
cgroups. The helper validates the exact cgroup prefix before moving a process.
