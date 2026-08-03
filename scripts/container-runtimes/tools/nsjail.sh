# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=nsjail
TRACE_AS_ROOT=1
tool_supports() { [[ "$1" =~ ^(create-start|bind-mount|tmpfs|network|userns|cgroup|seccomp|failure)$ ]]; }
tool_command() { generic_command "$1"; }
tool_install() {
  local src="${PREFIX}/src/nsjail"
  install_package_tool pkg-config pkgconf
  install_package_tool protobuf-compiler protobuf-compiler
  install_package_tool libprotobuf-dev protobuf-devel
  install_package_tool libnl-route-3-dev libnl3-devel
  install_package_tool libseccomp-dev libseccomp-devel
  local package; for package in flex bison; do install_package_tool "${package}"; done
  prefix_build_env
  [[ -d "${src}/.git" ]] || github_clone google/nsjail "${src}"
  # Ubuntu's libc and Linux UAPI headers expose two equivalent RT_TOS macros.
  # Keep the warning visible without allowing an external-header collision to
  # fail nsjail's otherwise warning-clean build.
  sed -i 's/-Werror /-Wno-error /g' "${src}/Makefile"
  # Ubuntu 22.04's libc headers predate this Linux prctl scope constant.
  # Defining the upstream UAPI value keeps the source build portable there.
  make -C "${src}" USER_DEFINES=-DPR_SCHED_CORE_SCOPE_THREAD_GROUP=1 -j"$(nproc)"
  install -m755 "${src}/nsjail" "${BIN_DIR}/nsjail"
}
