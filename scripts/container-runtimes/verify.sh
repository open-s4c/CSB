#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Reject empty/truncated traces and require syscall evidence for the operation.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/lib/common.sh"
[[ $# -ge 1 ]] || die "usage: $0 TRACE [TOOL POINT]"
trace="$1" tool="${2:-}" point="${3:-}"
[[ -s "${trace}" ]] || die "empty trace: ${trace}"
grep -Eq '^[0-9]+ +[a-zA-Z0-9_]+\(' "${trace}" || die "no decoded syscalls: ${trace}"
grep -Eq '(exit_group|\+\+\+ exited with)' "${trace}" || die "trace appears truncated: ${trace}"

case "${point}" in
  create|create-start|userns) expected='(clone3?|unshare|setns)\(' ;;
  bind-mount|tmpfs) expected='(mount|mount_setattr|open_tree|move_mount|fsopen)\(' ;;
  network) expected=' (clone3?|unshare|setns|socket|socketpair|sendmsg|bind)\(' ;;
  cgroup) expected='(openat|openat2).*cgroup|mkdir(at)?\(' ;;
  seccomp) expected=' (seccomp|prctl)\(' ;;
  stop|kill) expected='(kill|pidfd_send_signal|tgkill)\(' ;;
  delete|force-delete) expected='(unlinkat|rmdir|umount2)\(' ;;
  failure) expected='(ENOENT|EINVAL|EPERM|EACCES)' ;;
  *) expected='.' ;;
esac
# Daemon-backed CLIs do not perform the mount/cgroup/seccomp operation in their
# own process. Verify that the traced client issued an engine request; daemon
# syscall capture is a separate, explicitly documented capture boundary.
if [[ "${tool}" =~ ^(docker|podman)$ && "${point}" != failure ]]; then
  expected=' (socket|connect|sendmsg|sendto)\('
fi
grep -Eq "${expected}" "${trace}" || die "${tool}/${point}: expected syscall evidence not found (${expected})"
printf 'verified %s/%s: %s\n' "${tool:-unknown}" "${point:-unknown}" "${trace}"
