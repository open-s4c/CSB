# Remote Reboot Readiness

Treat reboot survival as a prerequisite, not a cleanup detail. Probe the actual
remote machine before building and immediately before every reboot. Store the
probe, continuation manifest, and critical state on persistent remote storage and
copy them to the controller.

Complete [host-recovery-safety.md](host-recovery-safety.md) before any host
mutation. Reboot readiness supplements, rather than replaces, its mandatory
out-of-band, rescue-boot, stable-baseline, and snapshot/image recovery gates.

## Machine and Boot Prerequisites

Record and verify:

- architecture, CPU topology, memory, firmware/microcode, clock source, NUMA,
  kernel config, compiler/toolchain, required kernel modules, and initramfs tools;
- root, boot, EFI, data, network, and remote filesystems plus UUID/PARTUUID/LVM,
  RAID, encryption, and mount dependencies needed during early boot;
- free space and inodes for source, build, modules, initramfs, `/boot`, logs, and
  every result repetition;
- bootloader entries/default/one-shot support, stable kernel artifacts, console
  or BMC, watchdog, persistent journal/pstore, SSH/network startup, DNS/routes,
  firewall, and time synchronization;
- externally logged out-of-band console, power/reset, firmware boot selection,
  recovery media, independent rescue OS/initramfs, and named recovery operator;
- baseline image or native snapshot identity, consistency point, capacity,
  expiry, off-host metadata, and tested restoration procedure;
- direct and reverse SSH endpoints, host keys, restricted credentials, supervised
  service ordering/restart behavior, allocated reverse port, and persistent logs;
- CSB checkout and submodule commits/dirty state, configs, generated headers,
  benchmark executables, runtime images/rootfs, Python environment, kernel source,
  patch, build config, toolchain, packages, sudo rights, and monitor tools;
- Docker/containerd/runc/youki/bwrap, cgroups, tracefs/debugfs, perf permissions,
  BPF, sysstat, required services, devices, NICs, storage, and benchmark datasets.

Check that boot-critical drivers are built in or present in the candidate
initramfs. Verify the initramfs contains the required root-storage, filesystem,
encryption, RAID/LVM, network, and console support. Use distribution tools to
inspect it; do not infer contents from the build config alone.

Require two clean stable boots and a successful rescue-environment boot before
the first candidate series. Verify that rescue can activate the actual storage
stack, mount the normal root read-only, inspect initramfs/bootloader/journal, and
copy evidence to the controller without depending on the normal userspace.

## Volatile-State Audit

Enumerate mounts and filesystem types with `findmnt`, paying particular attention
to tmpfs/ramfs and ephemeral or network-backed paths. At minimum inspect `/tmp`,
`/var/tmp`, `/run`, `/dev/shm`, user runtime directories, container runtime state,
tmux sockets, build/output directories, result paths, monitor scratch paths, and
task-specific environment variables.

Search running campaign processes for dependencies on volatile or deleted files:

```text
process command, cwd, root, executable, open file descriptors
tmux/systemd session command and working directory
temporary configs, generated headers, FIFOs, sockets, lock/barrier files
virtual environments, compiler caches, source/build trees, datasets and rootfs
perf.data, traces, monitor output, journals, ledgers, logs and partial results
SSH agents/control sockets, credentials, tokens and configuration paths
```

Do not print secret contents. Record only the protected persistent location and
required ownership/mode. Treat `/tmp` as volatile even when it currently resides
on disk; cleanup policy may remove it during boot. Treat `/var/tmp` as persistent
only after verifying the distribution's mount and cleanup policy.

## Persist Campaign State

Stop at a clean stage boundary. Do not checkpoint an actively writing benchmark
by copying its directory and calling it resumable. Flush and close task-owned
writers, then copy every required input and completed artifact to a dedicated
persistent directory outside tmpfs. Preserve ownership, modes, timestamps, links,
xattrs, ACLs, sparse files, and checksums when relevant. Keep unrelated files and
processes untouched.

Create a continuation manifest containing:

- campaign/task ID, host, stable and candidate kernel identities, boot ID, CSB
  and submodule commits, dirty-state patch/status, source/config/patch hashes;
- durable absolute paths for configs, headers, binaries, datasets, images/rootfs,
  build artifacts, logs, results, stage ledger, and recovery evidence;
- exact completed, failed, active, and pending stages based on result/log/exit
  evidence rather than `.done` markers alone;
- required mounts, services, modules, sysctls, cgroups, runtime state, permissions,
  CPU/frequency/IRQ/NUMA policy, hugepages, NIC/storage tuning, environment, and
  monitor preparation that must be reconstructed after boot;
- an idempotent post-boot probe, setup sequence, continuation command, expected
  process/session names, validation commands, rollback commands, and stop gates.
- exact direct/reverse SSH verification commands plus pre-change rollback and
  candidate-boot bailout unit names, deadlines, hashes, logs, and disarm rules.

Copy the manifest and irreplaceable evidence to the controller before reboot.
Verify checksums at the destination. Never move credentials to the controller or
another location unless authorized; instead ensure their normal protected source
will exist after boot.

## Continuation Dry Run

Before reboot, execute the post-boot prerequisite probe without changing the
kernel and validate that it identifies the current healthy host. Validate the
continuation command in a no-op, list, dry-run, or narrowly scoped wiring mode when
supported. Confirm it references only persistent paths and can recreate its tmux
or systemd-run session without inherited shell state.

Do not configure automatic benchmark execution at boot. First require SSH or
console reconnection, candidate-kernel identity and health verification, stable
fallback verification, and prerequisite parity. Automation may start only an
idempotent probe that records readiness without mutating benchmark results.
Test both SSH paths and timed rollback in non-mutating/check mode before reboot.

## Post-Boot Parity Gate

After reconnecting, compare the new probe with the pre-reboot manifest. Verify:

- expected kernel/build ID and new boot ID, with no intervening unexplained boot;
- all required local/remote filesystems, storage, NICs, services, runtimes,
  devices, modules, cgroups, tracefs/debugfs, perf/BPF permissions, and time sync;
- persistent files and checksums, CSB/source commits, configs, headers, binaries,
  datasets, images, Python/toolchain versions, free space, and ownership/modes;
- restored CPU/frequency/IRQ/NUMA, hugepage, sysctl, monitor, and runtime setup;
- absence of oops, panic, watchdog reset, filesystem/I/O errors, degraded storage,
  failed units, stale workload processes, or partial campaign writers.

Resume only from the last evidenced clean stage. If parity cannot be restored,
classify the attempt as blocked or failed and preserve diagnostics; do not weaken
the benchmark or silently regenerate missing inputs because tmpfs was cleared.
