# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=minijail
TRACE_AS_ROOT=1
tool_supports() { [[ "$1" =~ ^(create-start|bind-mount|tmpfs|network|userns|cgroup|seccomp|failure)$ ]]; }
tool_command() { generic_command "$1"; }
tool_install() {
  local src="${PREFIX}/src/minijail"
  install_package_tool libcap-dev libcap-devel
  prefix_build_env
  [[ -d "${src}/.git" ]] || github_clone google/minijail "${src}"
  # Current Linux UAPI headers reuse BPF_H, which triggers an upstream
  # macro-redefinition warning. Do not turn that external-header warning into
  # a build failure; all other compiler diagnostics remain enabled.
  sed -i 's/-Werror /-Wno-error /' "${src}/common.mk"
  make -C "${src}" OUT="${src}/out" -j"$(nproc)"; install -m755 "${src}/out/minijail0" "${BIN_DIR}/minijail"
}
