# Container runtime trace harness

This directory installs container and sandbox tools into an isolated prefix and
captures one lifecycle operation per trace. It is intended to be copied to an
arm64 machine; native arm64 execution is required for authoritative arm64
traces.

```bash
cd scripts/container-runtimes
./install.sh runc
./run.sh --trace runc create
./verify.sh traces/runc/create.strace
./sweep.sh --trace
```

The harness has been exercised on Ubuntu (`apt`/`dpkg`, amd64 and arm64) and
openEuler (`dnf`/RPM, arm64). Downloads and package extraction stay below the
temporary `PREFIX`; installers do not add packages to the host. Operations
that need namespaces, cgroups, an engine daemon, or KVM still require the
corresponding host capability.

`run.sh` accepts `--trace` or `--no-trace`. Trace mode delegates to CSB's
`scripts/plugins/collect_strace.sh`, including its architecture metadata
sidecar. Set `PREFIX`, `TRACE_DIR`, or `WORK_DIR` to override defaults below
`${TMPDIR:-/tmp}`. Use `./run.sh --list` to print the complete matrix.

Each capture is separate: `create`, `create-start`, `stop`, `kill`, `delete`,
`force-delete`, `bind-mount`, `tmpfs`, `network`, `userns`, `cgroup`, `seccomp`,
and deliberate `failure`.

Unsupported cells produce only an explanatory `.skip` file. The harness does
not trace an installation probe for these cells because such output is not a
trace of the named lifecycle operation.

`requirements.tsv` is the machine-readable requirement inventory and
`requirements.sh --check` checks the current host. Self-contained release
binaries are downloaded into `PREFIX`. Host-integrated tools still require
their host services, libraries, or setuid helpers. Kata and Firecracker require
`/dev/kvm` plus an arm64 guest kernel/rootfs. They are intentionally not run
under userspace emulation because that would produce the wrong syscall stream.

Package installation is backend-neutral. Debian/Ubuntu uses `apt-get download`
plus `dpkg-deb`; Fedora/RHEL-family systems use `dnf download --resolve` plus
`rpm2cpio`. Both extract into `PREFIX` without modifying the host. When package
names differ, adapters pass the Debian and RPM names together at the call site.

Set `GITHUB_MIRROR` to an audited URL-rewriting prefix when direct GitHub access
is slow, for example `GITHUB_MIRROR=https://gh-proxy.com/`. The setting applies
only to public GitHub downloads and clones; never route credentials through an
untrusted mirror, and verify release checksums independently.

For Rust-heavy source builds, `RUST_MIRROR=https://rsproxy.cn` redirects rustup
and the crates.io sparse index to a China-local mirror without affecting other
tool downloads.

Set `CSB_CONTAINER_IMAGE` when Docker Hub is unavailable, for example to an
audited registry mirror of `docker.io/library/alpine:3.20`. Docker and Podman
use the same value so their capture points remain comparable.

For harness development only, `ALLOW_NON_ARM64=1` permits a smoke trace on the
current architecture. Such traces are stored below `traces/<architecture>/`
and must not be presented as arm64 results.

Unsupported combinations produce visible `.skip` files; strict sweeps fail if
any combination is skipped. This matters for one-shot sandboxes: they genuinely
have no separate create, stop, or delete API.

Docker and Podman runners exercise their CLI against the configured engine.
Those traces describe client-side behavior. To study daemon-side syscalls, run
the engine daemon itself under `collect_strace.sh`; attaching `strace` to an
already-running daemon is intentionally outside this non-invasive harness.

Current adapter coverage is deliberately explicit:

- OCI runtimes (`runc`, `crun`, `youki`, `runsc`): all capture points.
- Docker and Podman: all capture points, using a short Alpine container.
- One-shot sandboxes: start and applicable mount/network/userns/cgroup/seccomp
  variants; lifecycle operations without a corresponding API are skipped.
- systemd-nspawn: short start, mount, network, cgroup, and failure variants.
- LXC, containerd, Kata, and Firecracker currently have installers and
  requirement records but no generic run recipe. Their image/network/guest
  inputs are site-specific, so the matrix emits honest skips until supplied.
