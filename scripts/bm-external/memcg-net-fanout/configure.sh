#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
chmod +x "$root/bm-external/memcg-net-fanout/memcg-net-fanout.sh"
chmod +x "$root/bm-external/memcg-net-fanout/enter-cgroup.sh"
command -v iperf3 >/dev/null 2>&1 || {
    echo "iperf3 is required for memcg-net-fanout" >&2
    exit 1
}
sudo -n true
