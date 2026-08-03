#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Shared paths, diagnostics, and trace plumbing for lifecycle adapters.
set -Eeuo pipefail

HARNESS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CSB_ROOT="$(cd -- "${HARNESS_DIR}/../.." && pwd)"
PREFIX="${PREFIX:-${TMPDIR:-/tmp}/csb-container-tools}"
WORK_DIR="${WORK_DIR:-${TMPDIR:-/tmp}/csb-container-work}"
TRACE_DIR="${TRACE_DIR:-${HARNESS_DIR}/traces}"
BIN_DIR="${PREFIX}/bin"
ROOTFS_DIR="${PREFIX}/rootfs"
COLLECT_STRACE="${CSB_ROOT}/scripts/plugins/collect_strace.sh"
PREFIX_LIB_DIRS="${PREFIX}/usr/lib/$(uname -m)-linux-gnu:${PREFIX}/lib/$(uname -m)-linux-gnu:${PREFIX}/usr/lib64:${PREFIX}/lib64:${PREFIX}/usr/lib:${PREFIX}/lib"
export PATH="${BIN_DIR}:${PREFIX}/bin:${PREFIX}/sbin:${PREFIX}/usr/bin:${PREFIX}/usr/sbin:${PATH}"
export LD_LIBRARY_PATH="${PREFIX_LIB_DIRS}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

TOOLS=(runc crun youki bwrap systemd-nspawn lxc docker podman containerd runsc kata firecracker nsjail firejail minijail)
POINTS=(create create-start stop kill delete force-delete bind-mount tmpfs network userns cgroup seccomp failure)

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '==> %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }
contains() { local n="$1" v; shift; for v in "$@"; do [[ "$v" == "$n" ]] && return 0; done; return 1; }
host_arch() { case "$(uname -m)" in x86_64|amd64) echo amd64;; aarch64|arm64) echo arm64;; *) uname -m;; esac; }
require_arm64() { [[ "$(host_arch)" == arm64 ]] || die "native arm64 required; found $(uname -m)"; }
as_root() {
  if [[ ${EUID} -eq 0 ]]; then
    env "PATH=${PATH}" "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" "PREFIX=${PREFIX}" "WORK_DIR=${WORK_DIR}" "TRACE_DIR=${TRACE_DIR}" "$@"
  else
    sudo -n -- env "PATH=${PATH}" "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" "PREFIX=${PREFIX}" "WORK_DIR=${WORK_DIR}" "TRACE_DIR=${TRACE_DIR}" \
      "CSB_CONTAINER_IMAGE=${CSB_CONTAINER_IMAGE:-}" "$@"
  fi
}

clean_case_dir() {
  CASE_DIR="${WORK_DIR}/$1/$2"
  if [[ "${TRACE_AS_ROOT:-0}" == 1 ]]; then
    as_root mkdir -p -- "${WORK_DIR}"
    as_root chmod 1777 -- "${WORK_DIR}"
    as_root rm -rf -- "${CASE_DIR}"
    as_root mkdir -p -- "${CASE_DIR}"
  else
    rm -rf -- "${CASE_DIR}"
    mkdir -p -- "${CASE_DIR}"
  fi
}

trace_or_run() {
  local mode="$1" output="$2"; shift 2
  mkdir -p -- "$(dirname -- "${output}")"
  if [[ "${mode}" == trace ]]; then
    [[ ! -e "${output}" && ! -e "${output}.meta" ]] || die "trace exists: ${output}"
    if [[ "${TRACE_AS_ROOT:-0}" == 1 ]]; then
      # Elevate strace itself. Running sudo underneath ptrace disables sudo's
      # setuid transition and makes an otherwise valid rootful test fail.
      as_root "${COLLECT_STRACE}" "${output}" "$@"
    else
      "${COLLECT_STRACE}" "${output}" "$@"
    fi
  else
    if [[ "${TRACE_AS_ROOT:-0}" == 1 ]]; then as_root "$@"; else "$@"; fi
  fi
}

write_skip() { mkdir -p -- "$(dirname -- "$1")"; printf '%s\n' "$2" >"$1.skip"; note "SKIP: $2"; }
github_url() {
  local url="$1"
  if [[ -n "${GITHUB_MIRROR:-}" && "${url}" == https://github.com/* ]]; then
    printf '%s%s\n' "${GITHUB_MIRROR}" "${url}"
  else
    printf '%s\n' "${url}"
  fi
}
fetch() {
  mkdir -p -- "$(dirname -- "$2")"
  if [[ -s "$2" ]]; then
    curl -fL --retry 5 --retry-all-errors --connect-timeout 15 -C - -o "$2" "$(github_url "$1")" || {
      rm -f -- "$2"
      curl -fL --retry 5 --retry-all-errors --connect-timeout 15 -o "$2" "$(github_url "$1")"
    }
  else
    curl -fL --retry 5 --retry-all-errors --connect-timeout 15 -o "$2" "$(github_url "$1")"
  fi
}
github_clone() {
  local repo="$1" destination="$2"
  git clone --depth 1 "$(github_url "https://github.com/${repo}")" "${destination}"
}
github_latest_tag() {
  local tag
  tag="$(curl -fsSL --retry 5 --retry-all-errors --connect-timeout 15 \
    "https://api.github.com/repos/$1/releases/latest" |
    jq -r '.tag_name // empty')"
  [[ -n "${tag}" ]] || die "GitHub returned no release tag for $1"
  printf '%s\n' "${tag}"
}
github_asset_url() {
  local repo="$1" pattern="$2" url
  url="$(curl -fsSL --retry 5 --retry-all-errors --connect-timeout 15 \
    "https://api.github.com/repos/${repo}/releases/latest" |
    jq -r --arg re "${pattern}" '[.assets[] | select(.name | test($re)) | .browser_download_url][0] // empty')"
  [[ -n "${url}" ]] || die "GitHub returned no asset matching ${pattern} for ${repo}"
  printf '%s\n' "${url}"
}

ensure_busybox_rootfs() {
  mkdir -p "${ROOTFS_DIR}/bin" "${ROOTFS_DIR}/proc" "${ROOTFS_DIR}/dev/pts" "${ROOTFS_DIR}/sys" "${ROOTFS_DIR}/tmp" "${ROOTFS_DIR}/usr" "${ROOTFS_DIR}/etc"
  [[ -e "${ROOTFS_DIR}/etc/os-release" ]] || printf 'ID=csb-trace\nNAME="CSB trace root"\n' >"${ROOTFS_DIR}/etc/os-release"
  if [[ ! -x "${ROOTFS_DIR}/bin/busybox" || "$(readlink "${ROOTFS_DIR}/bin/sh" 2>/dev/null || true)" == /* ]]; then
    local bb="$(command -v busybox || true)"
    [[ -n "${bb}" ]] || die "busybox is required for the shared rootfs"
    rm -rf "${ROOTFS_DIR}/bin"; mkdir -p "${ROOTFS_DIR}/bin"
    cp -- "${bb}" "${ROOTFS_DIR}/bin/busybox"
    # Hardlinks remain valid after pivot_root; absolute symlinks do not.
    "${ROOTFS_DIR}/bin/busybox" --install "${ROOTFS_DIR}/bin"
  fi
  # RPM distributions commonly ship a dynamically linked BusyBox. Copy its
  # small runtime closure so OCI runtimes can execute it after pivot_root.
  if file "${ROOTFS_DIR}/bin/busybox" | grep -q 'dynamically linked'; then
    mkdir -p "${ROOTFS_DIR}/lib64"
    local library
    for library in libm.so.6 libresolv.so.2 libc.so.6 ld-linux-aarch64.so.1; do
      local source
      source="$(find "${PREFIX}/lib" "${PREFIX}/lib64" "${PREFIX}/usr/lib64" -name "${library}" -print -quit 2>/dev/null || true)"
      [[ -z "${source}" || -e "${ROOTFS_DIR}/lib64/${library}" ]] || cp -Lf -- "${source}" "${ROOTFS_DIR}/lib64/${library}"
    done
    mkdir -p "${ROOTFS_DIR}/lib"
    [[ ! -e "${ROOTFS_DIR}/lib64/ld-linux-aarch64.so.1" ]] || ln -sfn ../lib64/ld-linux-aarch64.so.1 "${ROOTFS_DIR}/lib/ld-linux-aarch64.so.1"
  fi
}

tool_file() { printf '%s/tools/%s.sh\n' "${HARNESS_DIR}" "$1"; }
load_tool() {
  local file; file="$(tool_file "$1")"
  [[ -r "${file}" ]] || die "missing adapter: ${file}"
  # Adapters deliberately share this shell so they can use the helpers above.
  source "${file}"
}

apt_extract() {
  local package="$1" cache="${PREFIX}/packages" deb
  mkdir -p "${cache}"
  deb="$(find "${cache}" -maxdepth 1 -name "${package}_*.deb" -print -quit)"
  [[ -n "${deb}" ]] || (cd "${cache}" && apt-get download "${package}")
  deb="$(find "${cache}" -maxdepth 1 -name "${package}_*.deb" -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-)"
  [[ -n "${deb}" ]] || die "apt did not download ${package}"
  # Alternative packages can own the same compatibility symlink. Keep the
  # first extracted entry while still unpacking the rest of each dependency.
  dpkg-deb --fsys-tarfile "${deb}" | tar --skip-old-files -x -C "${PREFIX}"
}

apt_extract_closure() {
  # apt-cache computes the dependency closure without installing it on the
  # host. Recommended packages are excluded so the prefix stays focused.
  local root="$1" package
  mapfile -t packages < <(apt-cache depends --recurse --no-recommends --no-suggests \
    --no-conflicts --no-breaks --no-replaces --no-enhances "${root}" |
    sed -n '/^[A-Za-z0-9][A-Za-z0-9+.-]*$/p' | sort -u)
  ((${#packages[@]})) || die "no dependency closure for ${root}"
  for package in "${packages[@]}"; do apt_extract "${package}"; done
}

package_backend() {
  if have apt-get && have dpkg-deb; then echo apt
  elif have dnf && have rpm2cpio && have cpio; then echo dnf
  else die 'supported package backend required: apt/dpkg-deb or dnf/rpm2cpio/cpio'
  fi
}

dnf_extract_closure() {
  local package="$1" cache="${PREFIX}/packages-rpm" markers="${PREFIX}/.extracted-rpm" rpm staging marker
  mkdir -p "${cache}" "${markers}"
  dnf download --resolve --alldeps --destdir "${cache}" "${package}"
  while IFS= read -r -d '' rpm; do
    marker="${markers}/$(basename "${rpm}")"
    [[ -e "${marker}" ]] && continue
    staging="$(mktemp -d "${TMPDIR:-/tmp}/csb-rpm.XXXXXX")"
    (cd "${staging}" && rpm2cpio "${rpm}" | cpio -idm --quiet --no-absolute-filenames --no-preserve-owner)
    chmod -R u+rwX "${staging}"
    for compatibility_path in bin sbin lib lib64; do
      if [[ -L "${staging}/${compatibility_path}" && -d "${PREFIX}/${compatibility_path}" ]]; then
        rm -f "${staging}/${compatibility_path}"
      fi
    done
    # Keep an existing directory when a distribution's filesystem package uses
    # a compatibility symlink for the same path (for example /lib -> usr/lib).
    tar -C "${staging}" -cf - . | tar -C "${PREFIX}" --no-same-owner --keep-directory-symlink -xf -
    rm -rf "${staging}"
    : >"${marker}"
  done < <(find "${cache}" -type f -name '*.rpm' -print0)
}

prefix_command() {
  local name="$1" candidate
  for candidate in "${BIN_DIR}/${name}" "${PREFIX}/bin/${name}" "${PREFIX}/sbin/${name}" "${PREFIX}/usr/bin/${name}" "${PREFIX}/usr/sbin/${name}" "${PREFIX}/opt/kata/bin/${name}"; do
    [[ -x "${candidate}" ]] && { printf '%s\n' "${candidate}"; return; }
  done
  command -v "${name}" 2>/dev/null || return 1
}

emit_command() { printf '%s\0' "$@"; }
generic_command() { emit_command "${HARNESS_DIR}/lib/operation.sh" "${TOOL_NAME}" "$1" "${CASE_DIR}"; }
all_points() { return 0; }
no_create_point() { [[ "$1" != create ]]; }

install_package_tool() {
  # The optional second argument is the RPM-family package name. Keeping this
  # mapping at each adapter makes distribution differences easy to review.
  local debian_name="$1" rpm_name="${2:-$1}"
  case "$(package_backend)" in
    apt) apt_extract_closure "${debian_name}" ;;
    dnf) dnf_extract_closure "${rpm_name}" ;;
  esac
}

# Compatibility name for existing adapters; new adapters should use the
# backend-neutral spelling above.
install_apt_tool() { install_package_tool "$@"; }

install_release_binary() {
  local url="$1" name="$2"
  fetch "${url}" "${BIN_DIR}/${name}"
  chmod 0755 "${BIN_DIR}/${name}"
}

prefix_build_env() {
  export PATH="${BIN_DIR}:${PREFIX}/usr/bin:${PREFIX}/usr/sbin:${PATH}"
  export CPATH="${PREFIX}/usr/include${CPATH:+:${CPATH}}"
  export LIBRARY_PATH="${PREFIX_LIB_DIRS}${LIBRARY_PATH:+:${LIBRARY_PATH}}"
  export LD_LIBRARY_PATH="${PREFIX_LIB_DIRS}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  export PKG_CONFIG_PATH="${PREFIX}/usr/lib/$(uname -m)-linux-gnu/pkgconfig:${PREFIX}/usr/lib64/pkgconfig:${PREFIX}/usr/lib/pkgconfig:${PREFIX}/usr/share/pkgconfig${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}"
  export PKG_CONFIG_SYSROOT_DIR="${PREFIX}"
}
