# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=firejail
TRACE_AS_ROOT=1
tool_supports() { [[ "$1" =~ ^(create-start|bind-mount|tmpfs|network|userns|cgroup|seccomp|failure)$ ]]; }
tool_command() { generic_command "$1"; }
tool_install() {
  local src="${PREFIX}/src/firejail"
  [[ -d "${src}/.git" ]] || github_clone netblue30/firejail "${src}"
  (cd "${src}" && ./configure --prefix="${PREFIX}" --sysconfdir="${PREFIX}/etc")
  make -C "${src}" -j"$(nproc)"
  make -C "${src}" install-strip
}
