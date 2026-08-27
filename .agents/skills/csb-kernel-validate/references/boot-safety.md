# Remote Kernel Boot Safety

Read this entire reference before installing or booting a candidate kernel.
Commands vary by distribution; inspect generated entries and vendor documentation
instead of assuming paths or menu titles.
Complete the separate reboot-readiness probe and persist all campaign-critical
volatile state before applying this boot procedure.
Complete the access-safety gate, including direct and reverse SSH paths plus
pre-change and candidate-boot rollback timers, before any mutation.
Complete [host-recovery-safety.md](host-recovery-safety.md), including proven
out-of-band control, a boot-tested rescue environment, clean stable baseline
boots, and verified snapshot/image recovery, before any mutation.

## Recovery Contract

Use all available layers:

1. Keep the known-good kernel installed and configured as the persistent default.
2. Select the candidate with a one-shot boot entry only.
3. Configure reboot after panic/oops and preserve persistent kernel logs.
4. Configure a hardware watchdog for a hard hang when `/dev/watchdog*` and a
   functioning watchdog driver exist.
5. Require verified out-of-band console, power/reset, and recovery-media control.
6. Require an independently bootable rescue environment and verified baseline
   snapshot/image restoration path.

One-shot booting makes the next reboot return to stable, but it cannot initiate a
reboot from a hard lockup. Panic settings cannot recover a kernel that hangs before
they take effect. Without a tested watchdog or an operator/BMC power cycle, report
that hard-hang recovery is not guaranteed.

## Inventory Before Mutation

Capture at least:

```text
uname -a; cat /proc/cmdline; cat /etc/os-release
findmnt / /boot /boot/efi; df -h /boot /boot/efi
ls -l /boot; ls /lib/modules
bootctl status                 # when systemd-boot is present
grub-editenv list              # when GRUB is present
efibootmgr -v                  # on EFI, when available
systemctl status systemd-pstore
ls -l /dev/watchdog*; wdctl
journalctl -k -b; dmesg
```

Also record the stable entry identifier, kernel/initramfs/module hashes, current
boot ID, root device/filesystem, storage health indicators, and whether the stable
kernel has been boot-tested recently.

## One-Shot Selection

- **GRUB:** keep the stable entry as the configured default and use the
  distribution-supported `grub-reboot`/`next_entry` mechanism for the candidate.
  Inspect `grubenv` and generated menu entries before reboot. Do not rely on a
  guessed numeric index; submenu ordering changes after kernel installation.
- **systemd-boot:** keep the stable default and use `bootctl set-oneshot` with the
  exact candidate entry. Inspect `bootctl list` and `bootctl status` afterward.
  Use boot counting only when the installed system is already configured for it
  and its behavior has been verified.
- **extlinux/U-Boot/vendor loaders:** require a documented, testable one-shot or
  boot-count fallback. If only a permanent default can be changed, stop unless
  an operator-controlled console/BMC recovery plan is explicitly authorized.

After selection, prove both facts independently: candidate is next boot only, and
stable remains the persistent default after that attempt.

## Fatal-Error Reboot

Use distribution-supported persistent sysctl or kernel command-line settings for
nonzero `kernel.panic` and `kernel.panic_on_oops=1`. Consider lockup/NMI panic
settings only when supported and appropriate for the architecture and workload;
they can create false positives during extreme benchmark oversubscription. Record
every change and its rollback.

For hard hangs, configure the existing watchdog stack rather than inventing one.
Verify the watchdog device, timeout, daemon/systemd ownership, and an accepted
non-destructive test procedure. Do not run a destructive watchdog test on a busy
host. If no watchdog is available, retain one-shot fallback but label automatic
hard-hang recovery unavailable.

Provision watchdog policy separately on the stable host, activate it through a
planned stable reboot, and load-test it before candidate installation. Never
first-enable or shorten a watchdog in a candidate installer, and never combine
watchdog changes with PID 1 re-execution. `systemctl daemon-reexec` and equivalent
service-manager re-execution are prohibited during kernel validation.

Use pstore/ramoops, a serial console, netconsole, or persistent journal when
available. Verify logs survive reboot before the experiment. Never treat absent
logs as evidence that no panic occurred.

## Pre-Reboot Gate

Do not reboot until all checks pass:

- unrelated work is absent and reboot authorization is in scope;
- stable image, initramfs, modules, and boot entry remain intact;
- candidate image, initramfs, modules, release string, and root/network drivers
  match;
- boot and root filesystems are healthy and have adequate free space;
- stable is persistent default and candidate is one-shot;
- panic/oops settings and available watchdog are verified;
- SSH, console/BMC path, reconnect deadline, and recovery owner are recorded;
- out-of-band console/power/recovery-media controls and external console logging
  have been tested;
- the independent rescue environment has been booted and used to copy read-only
  evidence off-host;
- a current verified baseline snapshot/image and restoration procedure exist;
- direct reconnecting SSH and the supervised reverse tunnel pass independent
  end-to-end tests, with persistent logs and restricted credentials;
- the current pre-change rollback and candidate-boot bailout states and deadlines
  are verified from both access paths;
- the volatile-state audit, persistent continuation manifest, off-host copy, and
  post-boot prerequisite probe have been verified;
- build, install, bootloader, and preflight logs are durable off-host.

## Post-Boot Classification

Classify the attempt as successful only after kernel identity and health checks.
If the host returns on stable instead of candidate, recovery may have worked but
the candidate boot failed; collect previous-boot journal, pstore, bootloader boot
count/status, and console/BMC evidence. If the host is unreachable beyond the
declared deadline, use the authorized recovery channel and stop benchmark work.

Filesystem corruption, I/O errors, oops/panic, hung-task storms, watchdog resets,
unexpected boot IDs, missing devices, degraded arrays, failed mounts, or critical
service failures reject the candidate even if CSB performance improves.
