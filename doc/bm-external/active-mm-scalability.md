# Active-MM scalability attribution benchmarks

These native benchmarks isolate global synchronization found while profiling
parallel container creation and teardown. They complement, rather than replace,
the real workloads already in CSB.

Build the shared benchmark executable with:

```sh
scripts/bm-external/active-mm-scalability/configure.sh
```

The configs use one native execution unit with 1, 8, 32, 64, or 128 internal
workers and five repetitions:

- `active-mm-uidhash.json` repeatedly changes each worker to independent real
  UIDs and back while retaining effective and saved UID 0. It targets
  `uidhash_lock`; use `active-mm-uidhash-shared.json` as the same-bucket
  correctness and no-improvement control.
- `active-mm-netns.json` creates short-lived network namespaces and verifies
  `/sys/class/net/lo`. It exercises sysfs/kernfs creation during network
  namespace setup.
- `active-mm-fsopen.json` repeatedly resolves `tmpfs` through `fsopen(2)`.
- `active-mm-proc-filesystems.json` repeatedly enumerates
  `/proc/filesystems`. The last two configs target the read-mostly filesystem
  type registry through independent syscall paths.
- `active-mm-pivot-root.json` creates private mount namespaces and pivots each
  onto a fresh tmpfs root. It targets the system-wide `chroot_fs_refs()` scan
  used while container runtimes install a new root filesystem.

Run a config, for example, with:

```sh
scripts/run-single.sh config/bm-external/active-mm-uidhash.json
```

The configs use the `sudo` wrapper because UID transitions, network namespace
creation, and `fsopen(2)` require privilege. Each operation validates its
observable state and any failure makes the campaign point fail.

Keep the focused result beside a relatable workload:

- UID hash: rootless/multi-user container credential setup and
  `stress-ng --set`.
- Network namespace and kernfs: `config/bm-external/cgroups/runc.json` and the
  container lifecycle harness.
- Filesystem registry: runc/container lifecycle and `stress-ng --procfs`.
- Pivot root: runc lifecycle and the container harness, with fork/exit as the
  registry-maintenance no-regression control.

Do not claim a real-workload improvement from an attribution benchmark alone.
Accept a kernel change only after alternating-boot A/B runs show both a
high-core throughput improvement and reduced contention in the intended lock.
