#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Print the documented requirements and optionally check this machine.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/lib/common.sh"

check=false
[[ "${1:-}" == --check ]] && check=true
column -ts $'\t' "${HARNESS_DIR}/requirements.tsv"
${check} || exit 0

failed=0
for command in bash curl strace sudo tar busybox jq zstd; do
  if ! have "${command}"; then printf 'MISSING command: %s\n' "${command}" >&2; failed=1; fi
done
backend="$(package_backend)"; printf 'package backend: %s\n' "${backend}"
if [[ "${backend}" == apt ]]; then required=(apt-cache apt-get dpkg-deb); else required=(dnf rpm2cpio cpio); fi
for command in "${required[@]}"; do have "${command}" || { printf 'MISSING command: %s\n' "${command}" >&2; failed=1; }; done
[[ -r /proc/sys/kernel/unprivileged_userns_clone ]] &&
  printf 'userns: %s\n' "$(</proc/sys/kernel/unprivileged_userns_clone)"
[[ -e /dev/kvm ]] || { printf 'MISSING: /dev/kvm (Kata/Firecracker)\n' >&2; failed=1; }
printf 'architecture: %s (%s)\n' "$(host_arch)" "$(uname -m)"
exit "${failed}"
