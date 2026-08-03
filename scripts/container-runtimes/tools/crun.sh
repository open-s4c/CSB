# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=crun
TRACE_AS_ROOT=1
tool_supports() { all_points "$@"; }
tool_command() { emit_command "${HARNESS_DIR}/lib/oci-operation.sh" "$TOOL_NAME" "$1" "${CASE_DIR}"; }
tool_install() { install_apt_tool crun; }
