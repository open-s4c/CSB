# Remote Access and Timed Rollback Safety

Complete this gate before changing networking, firewall, SSH, bootloader,
watchdog, panic, or reboot configuration. Use two independently tested SSH paths
plus timed rollback. Independently tested out-of-band console, power/reset, and
recovery-media control is mandatory and must be recorded.

Also complete
[host-recovery-safety.md](host-recovery-safety.md) before any host mutation.
Out-of-band recovery is mandatory for kernel validation: two SSH paths plus
OS-level timers cannot recover early-boot, root-filesystem, loader, or PID 1
failures.

## Direct Persistent Controller Session

Create a dedicated controller-side tmux or screen session containing a direct SSH
client with `ServerAliveInterval`, `ServerAliveCountMax`, TCP keepalives, connection
timeout, and a reconnect loop with bounded backoff. Use a unique task-specific
session name and log reconnect timestamps to persistent controller storage. Do
not reuse or kill unrelated sessions.

Verify the session reaches the expected host and records hostname, host key,
running kernel, boot ID, source address, and route. Detaching tmux preserves the
controller process across terminal loss; it does not preserve the remote TCP
connection or survive a controller reboot. The reconnect loop must therefore be
tested by closing one SSH child and observing a successful reconnect.

## Reverse SSH Recovery Path

Establish a second path initiated by the remote host toward a known controller or
jump endpoint. Prefer `autossh` or a systemd service around OpenSSH using
`ExitOnForwardFailure=yes`, keepalives, `Restart=always`, and restart backoff. Bind
the reverse listening port to controller loopback unless broader exposure is
explicitly required. Use a unique allocated port and record both endpoints.

Use a dedicated restricted key or existing task-authorized credential. Restrict
the controller-side key and account to the required reverse forwarding and deny
unneeded shell, agent, X11, and additional forwarding capabilities when supported.
Verify host keys; do not disable checking, expose a reverse port publicly, copy
general-purpose credentials, alter `sshd_config`, or open a firewall broadly just
to establish recovery access.

Run the reverse client under remote supervision from persistent configuration,
not `/tmp`, a shell, or a tmux process. If it must reconnect after reboot, enable
it only after verifying its boot ordering, network dependency, credential path,
ownership, modes, logs, and failure behavior. Ensure it cannot start the campaign.

From the controller, open a separate SSH connection through the reverse port and
verify hostname, host key, kernel, boot ID, and source path. Then deliberately
restart only the reverse-tunnel service and prove that the tunnel disappears and
returns. Do not disrupt the host's primary network to test it. A tunnel is ready
only when direct and reverse connections work concurrently and independently.

## Pre-Change Stable Rollback

Before the first risky mutation, install a task-specific rollback script and
logs under persistent root-owned storage. The script must be idempotent and must:

1. acquire a task-specific lock and record its trigger time and reason;
2. preserve current bootloader, network, SSH, journal, and access-service state;
3. restore or explicitly select the exact known-good stable boot entry and clear
   any candidate one-shot entry using the detected bootloader's supported tools;
4. sync persistent filesystems and request a normal system reboot;
5. avoid deleting candidate artifacts, results, or unrelated configuration.

Provide a non-mutating check mode and validate it before arming. Run the actual
script only from a root-owned systemd service or equivalent scheduler. Never use
an unqualified numeric boot-menu index or a script stored on tmpfs.

Arm a one-shot pre-change timer with a generous deadline, normally at least 30
minutes and longer than the bounded configuration window plus reconnect margin.
Record its unit names, activation time, deadline, script/config hashes, status,
and rollback log path. Confirm it remains armed from both SSH paths before each
risky change. Do not perform long builds or benchmarks while this timer is armed.

After each bounded change, verify direct SSH, reverse SSH, stable default, empty
or expected one-shot state, watchdog, filesystems, services, and durable logs.
Only then cancel the old timer. Arm a fresh timer before the next risky mutation;
never extend a deadline blindly while either access path is unhealthy.

## Candidate-Boot Bailout

Prepare a separate boot-surviving bailout service/timer before selecting the
candidate. It must activate only for the expected candidate kernel or explicit
candidate boot token, wait long enough for boot and diagnosis, then select stable
and reboot unless an authenticated post-boot health step disarms it. Verify that
it will not fire on the stable kernel.

Use a deadline comfortably longer than expected boot, SSH recovery, and health
checks, but shorter than an unattended lockout; 20–30 minutes is a reasonable
starting range, adjusted for the host. The bailout is not the benchmark timeout.
Disarm it only after:

- either direct or reverse access works and the second path's state is known;
- candidate kernel identity, new boot ID, stable persistent default, filesystems,
  storage, network, SSH, watchdog, services, and kernel logs pass health checks;
- the controller has copied the post-boot evidence and explicitly records the
  disarm action.

If the candidate campaign will run longer than the bailout deadline, disarm the
boot bailout after health validation and rely on the hardware watchdog, panic/oops
reboot, and stable persistent default. Never leave a forgotten timer capable of
rebooting during a benchmark.

## Access-Loss Response

If direct SSH fails, immediately try the already-tested reverse path and console
or BMC; do not change routing or credentials speculatively. If reverse SSH fails,
retain the direct session and diagnose the supervised service. If both fail, let
the armed rollback/bailout and hardware watchdog act within their recorded
deadlines. Avoid repeated power cycles or concurrent recovery commands.

After recovery, verify the stable kernel and new boot ID, collect previous-boot
journal/pstore/console logs and rollback evidence, classify the triggering change,
and stop the candidate campaign until access safety is restored. Absence of a
rollback log is not proof that the timer did not fire.

If the host cannot execute init, mount its normal root, or start either SSH path,
stop retrying OS-level recovery. Use the tested out-of-band console and
independent rescue environment, preserve serial/reset evidence, mount storage
read-only first, and copy diagnostics off-host before repair.
