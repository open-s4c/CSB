# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=bwrap
tool_supports() { [[ "$1" =~ ^(create-start|bind-mount|tmpfs|network|userns|failure)$ ]]; }
tool_command() { generic_command "$1"; }
tool_install() { install_apt_tool bubblewrap; }
