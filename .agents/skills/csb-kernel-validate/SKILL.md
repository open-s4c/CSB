---
name: csb-kernel-validate
description: "Use when an evidence-backed Linux kernel patch from csb-analysis and csb-refine must be built, installed, recovery-booted, and benchmarked on a remote CSB host. Compose csb-analysis, csb-refine, and csb-remote to compare stable and patched kernels, reject unmeasurable or unsafe candidates, and iterate toward a functional scalability improvement."
---

# CSB Kernel Validate

Turn a CSB-derived RFC patch into a controlled remote A/B experiment. Load and
follow `csb-analysis`, `csb-refine`, and `csb-remote`; use `csb` for benchmark
execution. Preserve their evidence, cleanup, copy-back, and reporting rules.
Read [references/boot-safety.md](references/boot-safety.md) before changing a
remote boot configuration or installing a kernel. Read
[references/reboot-readiness.md](references/reboot-readiness.md) before the
first build and again before every reboot. Read and apply
[references/access-safety.md](references/access-safety.md) before the first
change to networking, SSH, bootloader, watchdog, panic, or reboot configuration.
Read and complete
[references/host-recovery-safety.md](references/host-recovery-safety.md) before
the first mutation of any remote host. Perform only read-only inventory and
non-mutating probes until its off-host gate record passes. Re-run affected gates
whenever recovery, storage, boot, access, watchdog, or baseline state changes.

## Preconditions

- Require an identified remote host, remote CSB checkout, complete stable-kernel
  result set, matching Linux source/config, patch artifact, and focused rerun
  matrix from the refinement report.
- Obtain authorization for package installation, bootloader changes, kernel
  installation, and reboot unless the user's request already explicitly covers
  them. Never reboot while unrelated campaigns or users are active.
- Record dirty state, running kernel release and build ID, bootloader, firmware,
  root filesystem, free `/boot` space, console/BMC access, watchdog capability,
  and the exact persistent stable boot entry.
- Require proven out-of-band console, power/reset, and recovery-media control; a
  boot-tested rescue environment independent of the normal root filesystem; two
  clean stable baseline boots; and a verified off-host baseline plus restorable
  native snapshot or image. If any required layer cannot be tested, stop before
  changing the host.
- Probe the remote machine against the reboot-readiness reference. Inventory all
  prerequisites and volatile state, move campaign-critical inputs, logs, ledgers,
  build state, credentials/configuration, and restart instructions from tmpfs or
  other ephemeral storage to persistent storage, and copy the recovery manifest
  off-host. Do not assume `/tmp`, `/run`, `/dev/shm`, tmux, shell state, runtime
  directories, temporary mounts, or manually applied host tuning survives reboot.
- Establish and test two independent SSH paths before reboot-related mutation:
  a controller-side reconnecting SSH client in a dedicated tmux/screen session,
  and a remote-supervised reverse SSH tunnel to a controller endpoint. Arm a
  tested, generously timed stable-kernel rollback before each risky change. Keep
  access credentials restricted and never weaken SSH or firewall policy merely
  to make the tunnel work.
- Treat direct SSH, reverse or separately routed SSH, and out-of-band management
  as three distinct required access layers. SSH and OS-level timers do not cover
  failures before init, root mount, networking, or SSH startup.
- Require a verified one-shot boot path that leaves the stable kernel as the
  persistent default. If unavailable, stop before reboot and report the missing
  recovery mechanism. A timeout alone is not recovery.
- Separate stable-host recovery provisioning from candidate installation.
  Candidate installers must not re-execute PID 1, first-enable or shorten a
  watchdog, change SSH/networking, or apply live global panic policy. Prohibit
  `systemctl daemon-reexec` and equivalent service-manager re-execution during
  validation. Activate and load-test watchdog policy through a planned stable
  boot before installing candidates.

## Candidate Loop

Use a durable iteration ledger. Default to at most three patch candidates unless
the user supplies another budget. For each candidate:

1. **Freeze the comparison.** Record the stable kernel identity, source commit,
   config hash, compiler/toolchain, firmware/microcode, CSB commit, config hash,
   topology, runtime state, and original analysis/refinement artifacts. Predeclare
   primary metric, tested scaling points, repetitions, noise threshold, acceptance
   rule, correctness checks, and material regressions.
2. **Prepare the source remotely.** Use an isolated remote worktree matching the
   stable kernel source. Preserve localversion and provenance, apply the patch
   with `git apply --check`, then apply it. Do not disturb the host's existing
   kernel tree or CSB checkout.
3. **Build and verify.** Reuse the stable kernel config, run the appropriate
   `olddefconfig`, build the kernel, modules, and required initramfs/package with
   logged exit statuses. Run the relevant narrow object/subsystem tests plus the
   kernel's build-time checks. Verify image, modules, initramfs, symbol/map, and
   release-name consistency before installation.
4. **Arm access and recovery.** Verify both SSH paths and out-of-band recovery
   from end to end, preserve
   their logs outside tmpfs, and arm the pre-change stable rollback before any
   reboot-safety mutation. Reverify the independent rescue boot and baseline
   snapshot/image. Keep the known-good kernel persistent default, install the
   uniquely named candidate beside it, use candidate command-line panic/oops
   policy, verify the already provisioned and stable-load-tested watchdog, and
   prepare a post-boot bailout timer. Select the candidate for one boot only.
   Save bootloader state and the commands needed to undo every change.
5. **Preflight and reboot.** Run the complete reboot-readiness and access-safety
   gates. Recheck idle
   state, stable default, candidate
   one-shot entry, filesystem health, free space, initramfs contents, root-device
   support, network driver, SSH service, watchdog, rescue boot, snapshot/image
   rollback, out-of-band console capture, durable logs, persistent
   campaign state, both SSH paths, armed rollback/bailout state, and the tested
   post-boot continuation command. Reboot once.
   Poll with bounded reconnect attempts; use BMC/console evidence when available.
6. **Verify identity and health.** Do not benchmark merely because SSH returned.
   Confirm hostname, `uname -r`, build ID/version, `/proc/cmdline`, loaded modules,
   boot ID, bootloader state, mounts, filesystems, storage/network health, and
   current-boot kernel logs. Re-probe campaign prerequisites, restore only the
   recorded transient host setup, and verify persistent inputs and ledgers before
   resuming. Confirm the stable kernel remains the next reboot's persistent
   default. On oops, panic, corruption warning, missing prerequisite, service
   failure, wrong kernel, or unexplained reboot, preserve logs and reject or block
   the candidate rather than starting a partial campaign.
7. **Rerun the evidence workflow.** Repeat the same focused CSB matrix and the
   same `csb-analysis` and `csb-refine` process used for the stable result. Keep
   execution types and monitor variants separate. Include monitor-off runs and
   correctness/success-rate checks. Do not compare runs with different workload,
   config, CPU policy, frequency policy, topology, runtime, or environment.
8. **Compare.** Prefer interleaved stable/patched boots when practical; otherwise
   bracket patched measurements with stable runs. Use enough repetitions to
   estimate run-to-run noise. Report raw values, median and spread/confidence
   interval, effect size, scaling-curve changes, resource movement, profiler
   evidence, failures, and regressions. Never infer improvement from a single run.
9. **Decide.** Accept only when the predeclared primary scalability improvement
   is larger than noise, repeatable, explained by the expected kernel-path
   movement, functionally correct, and free of material regressions. Reject when
   unsafe, incorrect, or confidently neutral/negative. Mark inconclusive when
   uncertainty is too large; sharpen the experiment before changing the patch.
10. **Iterate or finish.** For a rejected/inconclusive performance candidate,
    use the combined analysis to state why the hypothesis failed and design the
    smallest evidence-backed successor patch. Return to step 2. Stop at the
    iteration budget, a non-kernel bottleneck, insufficient evidence, unavailable
    recovery, or semantic uncertainty; do not invent a patch to force success.

After every candidate, boot back into the stable kernel with a one-shot selection
when necessary, verify its identity and health, and preserve the candidate kernel
until all evidence and recovery logs have been copied back. Do not delete kernels
or results unless explicitly requested.

## Durable Artifacts

Store controller copies under
`results/remote/<remote>/<task>/kernel-validation/`:

```text
inventory/        stable and candidate identities, configs, boot state
continuation/     prerequisite probes, volatile-state inventory, restart manifest
patches/          each candidate and source commit
build/            commands, logs, exit-status ledger, artifact hashes
boot/             preflight, bootloader state, watchdog, journal/dmesg
access/           direct/reverse SSH probes, service state, rollback timers/logs
recovery/         OOB proof, rescue boot, baseline backup/snapshot, restore test
stable/           baseline results and analysis
candidate-N/      results, analysis, refine reports, health evidence
comparison/       A/B tables, statistics, decision and iteration ledger
```

For each attempted boot, record candidate, timestamps, old/new boot IDs, expected
entry, observed kernel, reconnect outcome, fatal evidence, fallback outcome, and
stable-kernel recovery verification. A `.done` marker or reachable SSH session is
not proof of a successful kernel validation.

## Final Outcome

Classify the patch as `accepted`, `rejected`, `inconclusive`, or `blocked`. State
the exact kernel identities, build and boot verification, fallback status,
benchmark deltas and uncertainty, correctness results, profiler-path change,
regressions, iterations attempted, copied-back paths, and any cleanup intentionally
left for recovery. An accepted patch remains an RFC until its wider correctness,
subsystem, architecture, and upstream review requirements are satisfied.
