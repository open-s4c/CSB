# Using will-it-scale

Install a C compiler, make, and the hwloc development package, then clone and
build the pinned external harness with CSB's configure script:

```bash
scripts/bm-external/will-it-scale/configure.sh
sudo scripts/run-single.sh config/bm-external/will-it-scale/uname.json
```

The configure script copies CSB's published `uname1.c` test into the external
checkout before building its process and thread executables. The CSB config
runs the thread variant because readers in one UTS namespace contend on the
same kernel state. Run the process variant separately as a useful control.

The committed settings are a functional 1/2/4/8-thread example. For kernel
performance claims, include every relevant task count through the machine's
CPU count, run at least five complete sweeps per kernel, and keep the harness
revision, topology, affinity, and frequency policy fixed. Compare operations/s
and scaling relative to one thread. Profile the old and candidate kernels to
confirm reduced reader-side UTS lock/cacheline traffic, and run a concurrent
hostname writer test separately to validate coherent snapshots and retry
behavior.

Neither sysbench nor UnixBench contains a timed, high-concurrency `uname()`
workload, so their aggregate scores are not evidence for the UTS patch.
