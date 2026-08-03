# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=runc
TRACE_AS_ROOT=1
tool_supports() { all_points "$@"; }
tool_command() { emit_command "${HARNESS_DIR}/lib/oci-operation.sh" "$TOOL_NAME" "$1" "${CASE_DIR}"; }
tool_install() {
  local tag="${TOOL_VERSION:-$(github_latest_tag opencontainers/runc)}" arch="$(host_arch)"
  install_release_binary "https://github.com/opencontainers/runc/releases/download/${tag}/runc.${arch}" runc
}
