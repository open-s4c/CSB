# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=podman
TRACE_AS_ROOT=1
tool_supports() { all_points "$@"; }
tool_command() { generic_command "$1"; }
tool_install() {
  install_apt_tool podman
  install_apt_tool containernetworking-plugins
  install_apt_tool iptables
  if ! have iptables && [[ -x "${PREFIX}/usr/sbin/iptables-legacy" ]]; then
    ln -sfn "${PREFIX}/usr/sbin/iptables-legacy" "${BIN_DIR}/iptables"
  fi
}
