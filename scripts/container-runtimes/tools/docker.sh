# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=docker
TRACE_AS_ROOT=1
tool_supports() { all_points "$@"; }
tool_command() { generic_command "$1"; }
tool_install() { install_package_tool docker.io moby-engine; }
