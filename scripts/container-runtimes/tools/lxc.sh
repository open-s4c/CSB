# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=lxc
tool_supports() { return 1; }
tool_command() { generic_command "$1"; }
tool_install() { install_apt_tool lxc; }
