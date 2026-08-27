# Host-Independent Recovery Safety

Complete this entire gate before the first mutation of a remote Linux host for
kernel validation. It applies across distributions, architectures, bootloaders,
storage layouts, virtualization platforms, and physical machines. Read-only
inventory and non-mutating probes are allowed before the gate. Package
installation, kernel or module installation, network or SSH changes, bootloader
changes, snapshot creation, watchdog or panic configuration, service-manager
reload/re-execution, and reboot are mutations and must wait.

## Contents

- [Hard Stop Conditions](#hard-stop-conditions)
- [Out-of-Band Recovery](#out-of-band-recovery)
- [Independent Rescue Environment](#independent-rescue-environment)
- [Stable Baseline, Backup, and Snapshot](#stable-baseline-backup-and-snapshot)
- [Mutation Boundary](#mutation-boundary)
- [Watchdog and Fatal-Error Policy](#watchdog-and-fatal-error-policy)
- [Recovery Layers and Limits](#recovery-layers-and-limits)
- [Before-Mutation Evidence](#before-mutation-evidence)

## Hard Stop Conditions

Do not mutate the host unless all of these are proven:

1. an authenticated out-of-band recovery operator can observe the console,
   control power/reset, and select or attach recovery boot media without relying
   on the installed operating system;
2. a boot-tested rescue environment can start independently of the normal root
   filesystem and provides storage, volume, filesystem, bootloader, network,
   SSH, journal, and copy-out tools needed for that host;
3. the known-good stable kernel and a tested stable userspace boot remain the
   persistent default;
4. a verified baseline backup or revertible snapshot exists, with its restore
   procedure and prerequisites copied off-host;
5. direct SSH, a separately routed or reverse SSH path, and the out-of-band
   console work concurrently and have independently recorded identities;
6. off-host copies contain the recovery manifest, boot/storage inventory,
   artifact hashes, rollback commands, and credentials-location metadata;
7. task-specific pre-change rollback and candidate-boot bailout mechanisms pass
   non-mutating checks and do not represent OS-level recovery as sufficient for
   failures that occur before init.

If the platform cannot provide a required layer, stop and classify validation as
blocked. Authorization to reboot does not waive recovery readiness.

## Out-of-Band Recovery

Use a dedicated BMC, service processor, hypervisor console, cloud serial console
plus rescue controls, or an equivalent management plane isolated from the
workload OS. Verify, rather than assume:

- console input and externally persisted output;
- power status, reset/power-cycle controls, and audit timestamps;
- firmware/boot-menu control or virtual-media attachment;
- host identity and management-plane access after the workload network is down;
- restricted credentials, ownership, and a named recovery operator;
- a documented recovery-media boot sequence that does not overwrite disks.

Continuously capture console output off-host for every install and boot attempt.
Do not expose management interfaces publicly or weaken their authentication.

## Independent Rescue Environment

Provide a small recovery OS or self-contained recovery initramfs on separate
media, a separate disk/partition, immutable network boot, or management-plane
virtual media. It must not require the normal root filesystem, its dynamic
loader, its system manager, or the candidate kernel. Include the tools needed for
the actual storage stack, such as LVM, RAID, encryption, filesystem checking,
bootloader repair, initramfs inspection, storage-health queries, networking,
restricted SSH, checksumming, and evidence copy-out.

Boot the rescue environment before validation, verify its console and restricted
SSH access, activate the real storage without modifying it, mount the root
read-only, and demonstrate that logs and selected evidence can be copied to the
controller. Record its image hash, boot entry/media, network identity, unlock
requirements without secret contents, and exact recovery commands.

## Stable Baseline, Backup, and Snapshot

Before validation, require at least two clean stable boots with distinct boot
IDs and successful post-boot health probes. Record stable kernel, initramfs,
modules, root filesystem, loader/interpreter, bootloader, storage topology, and
service-manager identities and hashes where practical.

Create and verify an off-host baseline sufficient to recover:

- partition/GPT and EFI/boot metadata;
- bootloader configuration and environment;
- stable kernel, initramfs, configuration, symbols, and module tree;
- root-volume and volume-manager metadata;
- critical system-manager, SSH, network, and early-boot configuration;
- recovery media, continuation manifest, and restoration procedure.

Use a native snapshot or image rollback when the platform supports one. Record
capacity, consistency point, identifier, parent, expiry, and restore procedure.
Never call a file copy of a live root filesystem an atomic snapshot. If a safe
snapshot or restorable image cannot be made and verified, stop.

## Mutation Boundary

Separate host provisioning from each candidate installation.

Provision and prove access, recovery, persistent logging, watchdog ownership,
panic policy, and rescue boot while running the stable system. Apply changes
through their normal boot-time activation path and complete a clean stable reboot
plus health audit before candidate work. Never first-enable or shorten a
watchdog, change panic policy, reconfigure SSH/networking, or re-execute the
service manager as part of a candidate installer.

Candidate installation may write only uniquely named candidate artifacts and
the exact bootloader data needed to register them. It must not replace stable
artifacts, mutate unrelated root files, change the persistent default, or combine
installation with reboot. Prefer distribution-native signed packages. If an
archive is unavoidable, reject absolute paths, traversal, escaping symlinks,
unexpected top-level paths, duplicate paths, devices, FIFOs, and writes outside
the unique candidate module tree before extraction. Extract to a staging root,
compare the resulting inventory, then install explicitly.

Prohibit service-manager re-execution (`systemctl daemon-reexec` or equivalent)
during kernel validation. Ordinary unit-file changes, when separately
authorized, may use the least disruptive supported reload only after proving it
does not re-execute PID 1; otherwise defer activation to a planned stable boot.

## Watchdog and Fatal-Error Policy

Configure a hardware or platform watchdog only during stable-host provisioning.
Identify its owner, device, timeout limits, pretimeout behavior, reset-cause
evidence, and interaction with firmware and the service manager. Start with a
generous timeout that exceeds worst-case stable boot and maximum validated host
load with margin; do not default to a short timeout. Test configuration parsing
non-destructively, activate it through a planned stable reboot, then prove the
stable system services it under representative maximum load.

Never dynamically enable or shorten a watchdog immediately before PID 1 reload,
re-execution, package installation, initramfs generation, bootloader writes, or
other unbounded operations. Do not use watchdog expiry as the only rollback
mechanism. Prefer candidate-specific panic/oops command-line arguments over live
global sysctl changes, and verify persistent crash/reset evidence through serial
console, pstore/ramoops, firmware logs, or equivalent facilities.

## Recovery Layers and Limits

Use all layers, recognizing their boundaries:

1. direct SSH reconnect protects against a dropped client connection;
2. reverse or separately routed SSH protects against one ingress path failing;
3. a pre-change rollback timer protects while stable userspace works;
4. a candidate bailout protects after candidate userspace starts;
5. one-shot boot plus stable persistent default protects the next boot attempt;
6. watchdog and panic reboot protect some hangs and crashes;
7. out-of-band control plus independent rescue protects early-boot, root-mount,
   loader, PID 1, network, and repeated stable-boot failures;
8. verified snapshot/image restoration protects persistent-system corruption.

No SSH tunnel or systemd timer can recover a host that cannot execute init. No
one-shot candidate fallback repairs a damaged stable root filesystem. Do not
represent a higher layer as covered by a lower one.

## Before-Mutation Evidence

Create a checksummed gate record containing pass/fail and evidence paths for
every item above. Copy it to the controller and verify the destination hash.
Record the exact first authorized mutation and require it to match the reviewed
command. Any missing, stale, contradictory, or untested item is a stop.
