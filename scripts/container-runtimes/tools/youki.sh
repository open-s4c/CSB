# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=youki
TRACE_AS_ROOT=1
tool_supports() { all_points "$@"; }
tool_command() { emit_command "${HARNESS_DIR}/lib/oci-operation.sh" "$TOOL_NAME" "$1" "${CASE_DIR}"; }
tool_install() {
  local rustup="${PREFIX}/rustup-init" rust_arch
  [[ "$(host_arch)" == amd64 ]] && rust_arch=x86_64 || rust_arch=aarch64
  if [[ -n "${RUST_MIRROR:-}" ]]; then
    export RUSTUP_DIST_SERVER="${RUST_MIRROR}"
    export RUSTUP_UPDATE_ROOT="${RUST_MIRROR}/rustup"
    export CARGO_REGISTRIES_CRATES_IO_INDEX="sparse+${RUST_MIRROR}/index/"
  fi
  if [[ ! -x "${PREFIX}/cargo/bin/cargo" ]]; then
    fetch "${RUSTUP_DIST_SERVER:-https://static.rust-lang.org}/rustup/dist/${rust_arch}-unknown-linux-gnu/rustup-init" "${rustup}"
    chmod 0755 "${rustup}"
    CARGO_HOME="${PREFIX}/cargo" RUSTUP_HOME="${PREFIX}/rustup" "${rustup}" -y --no-modify-path --profile minimal --default-toolchain stable
  fi
  prefix_build_env
  export CARGO_HOME="${PREFIX}/cargo" RUSTUP_HOME="${PREFIX}/rustup"
  export PATH="${CARGO_HOME}/bin:${PATH}"
  if [[ -n "${RUST_MIRROR:-}" ]]; then
    mkdir -p "${CARGO_HOME}"
    printf '%s\n' \
      '[source.crates-io]' \
      "replace-with = 'rsproxy-sparse'" \
      '[source.rsproxy-sparse]' \
      "registry = 'sparse+${RUST_MIRROR}/index/'" \
      > "${CARGO_HOME}/config.toml"
  fi
  local src="${PREFIX}/src/youki"
  [[ -d "${src}/.git" ]] || github_clone youki-dev/youki "${src}"
  cargo build --locked --release --manifest-path "${src}/Cargo.toml" --package youki \
    --features systemd,seccomp,cgroupsv2_devices,v1
  install -m755 "${src}/target/release/youki" "${BIN_DIR}/youki"
}
