#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Execute one isolated operation. Setup is intentionally included in the trace:
# namespace, daemon, and teardown syscalls are part of the lifecycle footprint.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/common.sh"
tool="$1" point="$2" case_dir="$3"
runtime="$(prefix_command "${tool}" || true)"
[[ -n "${runtime}" ]] || die "${tool} is not installed under PREFIX or on PATH"
mkdir -p "${case_dir}/host"; printf 'csb-bind-probe\n' >"${case_dir}/host/probe"

sandbox_payload=(/bin/sh -c 'test -r /proc/self/status; :')
run_sandbox() {
  case "${tool}" in
    bwrap)
      net=(--share-net); [[ "${point}" == network ]] && net=()
      "${runtime}" --unshare-all "${net[@]}" --ro-bind / / --proc /proc --dev /dev "${sandbox_payload[@]}"
      ;;
    nsjail) as_root "${runtime}" -Mo --chroot / --disable_proc -- "${sandbox_payload[@]}" ;;
    firejail) "${runtime}" --quiet --noprofile --private "${sandbox_payload[@]}" ;;
    minijail) as_root "${runtime}" -T static -v -p -r -e -- "$(prefix_command busybox)" sh -c 'test -r /proc/self/status; :' ;;
    *) return 1 ;;
  esac
}

case "${tool}" in
  bwrap|nsjail|firejail|minijail)
    case "${point}" in
      create|create-start|stop|kill|delete|force-delete) run_sandbox ;;
      bind-mount)
        [[ "${tool}" == bwrap ]] || run_sandbox
        [[ "${tool}" != bwrap ]] || "${runtime}" --ro-bind / / --ro-bind "${case_dir}/host" /mnt --proc /proc /bin/test -r /mnt/probe ;;
      tmpfs)
        [[ "${tool}" == bwrap ]] || run_sandbox
        [[ "${tool}" != bwrap ]] || "${runtime}" --ro-bind / / --tmpfs /tmp --proc /proc /bin/sh -c 'echo ok >/tmp/probe' ;;
      network|userns|cgroup|seccomp) run_sandbox ;;
      failure) ! "${runtime}" --csb-deliberately-invalid-option ;;
    esac
    ;;
  docker|podman)
    image="${CSB_CONTAINER_IMAGE:-docker.io/library/alpine:3.20}"
    cli=("${runtime}"); [[ "${tool}" == docker ]] && cli=(as_root "${runtime}")
    if [[ "${tool}" == podman ]]; then
      podman_run="/tmp/csb-pr-${point}"
      podman_home="${case_dir}/home"
      rm -rf "${podman_run}"; mkdir -p "${podman_home}/.config/containers" "${case_dir}/podman-root" "${podman_run}"
      cp -f "${PREFIX}/etc/containers/policy.json" "${podman_home}/.config/containers/policy.json"
      printf '[containers]\nlabel=false\n[network]\nnetwork_backend="cni"\ncni_plugin_dirs=["%s/usr/lib/cni","%s/usr/libexec/cni"]\n' \
        "${PREFIX}" "${PREFIX}" >"${case_dir}/containers.conf"
      cli=(env "HOME=${podman_home}" "CONTAINERS_CONF=${case_dir}/containers.conf" "${runtime}" --log-level=error --root "${case_dir}/podman-root" --runroot "${podman_run}" --storage-driver vfs --events-backend file --runtime "$(prefix_command runc)")
    fi
    case "${point}" in
      create) "${cli[@]}" create --name csb-trace "${image}" true; "${cli[@]}" rm csb-trace ;;
      create-start) "${cli[@]}" run --rm "${image}" true ;;
      stop) "${cli[@]}" run -d --name csb-trace "${image}" sleep 30; "${cli[@]}" stop -t 0 csb-trace; "${cli[@]}" rm csb-trace ;;
      kill) "${cli[@]}" run -d --name csb-trace "${image}" sleep 30; "${cli[@]}" kill csb-trace; "${cli[@]}" rm csb-trace ;;
      delete) "${cli[@]}" create --name csb-trace "${image}" true; "${cli[@]}" rm csb-trace ;;
      force-delete) "${cli[@]}" run -d --name csb-trace "${image}" sleep 30; "${cli[@]}" rm -f csb-trace ;;
      bind-mount) "${cli[@]}" run --rm -v "${case_dir}/host:/probe:ro" "${image}" test -r /probe/probe ;;
      tmpfs) "${cli[@]}" run --rm --tmpfs /probe "${image}" sh -c 'echo ok >/probe/file' ;;
      network) "${cli[@]}" run --rm --network none "${image}" true ;;
      userns) "${cli[@]}" run --rm --user 65534:65534 "${image}" true ;;
      cgroup) "${cli[@]}" run --rm --memory 32m --pids-limit 16 "${image}" true ;;
      seccomp) "${cli[@]}" run --rm --security-opt no-new-privileges "${image}" true ;;
      failure) ! "${cli[@]}" create --name csb-trace does-not-exist.invalid/csb/missing:never ;;
    esac
    ;;
  systemd-nspawn)
    ensure_busybox_rootfs
    machine="csb-trace-$$"
    case "${point}" in
      bind-mount) as_root "${runtime}" -q -D "${ROOTFS_DIR}" --register=no --bind-ro="${case_dir}/host:/probe" /bin/test -r /probe/probe ;;
      tmpfs) as_root "${runtime}" -q -D "${ROOTFS_DIR}" --register=no --tmpfs=/probe /bin/sh -c 'echo ok >/probe/file' ;;
      network) as_root "${runtime}" -q -D "${ROOTFS_DIR}" --register=no --private-network /bin/true ;;
      cgroup) as_root "${runtime}" -q -D "${ROOTFS_DIR}" --register=no --property=MemoryMax=32M /bin/true ;;
      failure) ! as_root "${runtime}" -D /definitely/missing /bin/true ;;
      *) as_root "${runtime}" -q -D "${ROOTFS_DIR}" --register=no --machine="${machine}" /bin/true ;;
    esac
    ;;
  *)
    die "${tool}/${point}: operation adapter is declared but not implemented"
    ;;
esac
