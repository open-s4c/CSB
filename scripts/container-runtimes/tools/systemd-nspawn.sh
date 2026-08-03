# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=systemd-nspawn
TRACE_AS_ROOT=1
tool_supports() { [[ "$1" =~ ^(create-start|bind-mount|tmpfs|network|cgroup|failure)$ ]]; }
tool_command() { generic_command "$1"; }
tool_install() { install_package_tool systemd-container systemd-nspawn; }
