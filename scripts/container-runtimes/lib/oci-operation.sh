#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Build a minimal OCI bundle and capture a single runtime lifecycle operation.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/common.sh"
tool="$1" point="$2" case_dir="$3" id="csb-${tool}-${point}-$$"
runtime="$(prefix_command "${tool}")"
ensure_busybox_rootfs
mkdir -p "${case_dir}/host"; printf 'csb-bind-probe\n' >"${case_dir}/host/probe"
bundle="${case_dir}/bundle"; mkdir -p "${bundle}"; cp -a "${ROOTFS_DIR}" "${bundle}/rootfs"
args='["/bin/sh","-c","exit 0"]'
[[ "${point}" =~ ^(create|stop|kill|force-delete)$ ]] && args='["/bin/sh","-c","sleep 30"]'
mounts='[{"destination":"/proc","type":"proc","source":"proc"},{"destination":"/dev","type":"tmpfs","source":"tmpfs","options":["nosuid","strictatime","mode=755","size=65536k"]},{"destination":"/dev/pts","type":"devpts","source":"devpts","options":["nosuid","noexec","newinstance","ptmxmode=0666","mode=0620"]}]'
namespaces='[{"type":"pid"},{"type":"mount"},{"type":"uts"},{"type":"ipc"}]'
resources='{}'; seccomp='null'; uidmaps='null'; gidmaps='null'
case "${point}" in
  bind-mount) mounts="$(jq -c --arg s "${case_dir}/host" '. + [{"destination":"/probe","type":"bind","source":$s,"options":["rbind","ro"]}]' <<<"${mounts}")" ;;
  tmpfs) mounts="$(jq -c '. + [{"destination":"/probe","type":"tmpfs","source":"tmpfs","options":["nosuid","nodev","mode=755","size=65536"]}]' <<<"${mounts}")" ;;
  network) namespaces='[{"type":"pid"},{"type":"mount"},{"type":"uts"},{"type":"ipc"},{"type":"network"}]' ;;
  userns) namespaces='[{"type":"pid"},{"type":"mount"},{"type":"uts"},{"type":"ipc"},{"type":"user"}]'; uidmaps='[{"containerID":0,"hostID":0,"size":1}]'; gidmaps="${uidmaps}" ;;
  cgroup)
    if [[ "${tool}" == runsc ]]; then
      resources='{"memory":{"limit":2147483648},"pids":{"limit":512}}'
    else
      resources='{"memory":{"limit":33554432},"pids":{"limit":16}}'
    fi
    ;;
  seccomp)
    if [[ "$(host_arch)" == arm64 ]]; then oci_arch=SCMP_ARCH_AARCH64; else oci_arch=SCMP_ARCH_X86_64; fi
    seccomp="$(jq -nc --arg arch "${oci_arch}" '{defaultAction:"SCMP_ACT_ALLOW",architectures:[$arch],syscalls:[]}')"
    ;;
esac
jq -n --arg rootfs "${bundle}/rootfs" --argjson args "${args}" --argjson mounts "${mounts}" --argjson ns "${namespaces}" \
  --argjson resources "${resources}" --argjson seccomp "${seccomp}" --argjson uid "${uidmaps}" --argjson gid "${gidmaps}" '
  {ociVersion:"1.0.2",process:{terminal:false,user:{uid:0,gid:0},args:$args,env:["PATH=/bin"],cwd:"/",noNewPrivileges:true},
   root:{path:$rootfs,readonly:false},hostname:"csb-trace",mounts:$mounts,
   linux:({namespaces:$ns,resources:$resources} + (if $seccomp==null then {} else {seccomp:$seccomp} end) +
          (if $uid==null then {} else {uidMappings:$uid,gidMappings:$gid} end))}' >"${bundle}/config.json"

rt=(as_root "${runtime}"); [[ "${tool}" == runsc ]] && rt=(as_root "${runtime}" --platform=kvm --network=none --root="${case_dir}/runsc-root")
force_flag=-f; [[ "${tool}" == runsc ]] && force_flag=--force
cleanup() { "${rt[@]}" delete "${force_flag}" "${id}" >/dev/null 2>&1 || true; }
trap cleanup EXIT
case "${point}" in
  create) "${rt[@]}" create --bundle "${bundle}" "${id}" ;;
  create-start|bind-mount|tmpfs|network|userns|cgroup|seccomp) "${rt[@]}" run --bundle "${bundle}" "${id}" ;;
  stop) "${rt[@]}" create --bundle "${bundle}" "${id}"; "${rt[@]}" start "${id}"; "${rt[@]}" kill "${id}" TERM; "${rt[@]}" delete "${force_flag}" "${id}" ;;
  kill) "${rt[@]}" create --bundle "${bundle}" "${id}"; "${rt[@]}" start "${id}"; "${rt[@]}" kill "${id}" KILL; "${rt[@]}" delete "${force_flag}" "${id}" ;;
  delete)
    "${rt[@]}" create --bundle "${bundle}" "${id}"
    "${rt[@]}" start "${id}"
    # Older crun correctly requires the init process to reach stopped state
    # before an ordinary (non-forced) deletion.
    for _ in {1..100}; do
      [[ "$("${rt[@]}" state "${id}" 2>/dev/null | jq -r .status)" == stopped ]] && break
      sleep 0.01
    done
    "${rt[@]}" delete "${id}"
    ;;
  force-delete) "${rt[@]}" create --bundle "${bundle}" "${id}"; "${rt[@]}" start "${id}"; "${rt[@]}" delete "${force_flag}" "${id}" ;;
  failure) ! "${rt[@]}" create --bundle "${case_dir}/missing" "${id}" ;;
esac
