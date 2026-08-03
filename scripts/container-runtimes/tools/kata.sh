# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=kata
tool_supports() { return 1; }
tool_command() { generic_command "$1"; }
tool_install() {
  if [[ "$(package_backend)" == dnf ]]; then
    install_package_tool kata-containers kata-containers
    return
  fi
  have zstd || die 'zstd is required to extract the Kata static bundle'
  local arch="$(host_arch)" url archive="${PREFIX}/packages/kata-static.tar.zst"
  url="$(github_asset_url kata-containers/kata-containers "kata-static-.*-${arch}\\.tar\\.zst$")"
  [[ -n "${url}" ]] || die "no Kata static asset for ${arch}"
  fetch "${url}" "${archive}"; tar --zstd -xf "${archive}" -C "${PREFIX}"
}
