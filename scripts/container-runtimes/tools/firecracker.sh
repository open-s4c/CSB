# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

TOOL_NAME=firecracker
tool_supports() { return 1; }
tool_command() { generic_command "$1"; }
tool_install() {
  local machine="$(uname -m)" url archive="${PREFIX}/packages/firecracker.tgz" extracted
  url="$(github_asset_url firecracker-microvm/firecracker "firecracker-v.*-${machine}\\.tgz$")"
  [[ -n "${url}" ]] || die "no Firecracker asset for ${machine}"
  fetch "${url}" "${archive}"; mkdir -p "${PREFIX}/firecracker"; tar -xzf "${archive}" -C "${PREFIX}/firecracker"
  extracted="$(find "${PREFIX}/firecracker" -type f -name 'firecracker-*' ! -name '*.txt' | head -n1)"
  [[ -n "${extracted}" ]] || die 'Firecracker binary missing from archive'
  install -m755 "${extracted}" "${BIN_DIR}/firecracker"
}
