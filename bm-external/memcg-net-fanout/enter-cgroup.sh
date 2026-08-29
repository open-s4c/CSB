#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

group=$1
shift
case "$group" in
    /sys/fs/cgroup/csb-memcg-net-[0-9]*/client-[0-9]*) ;;
    *) echo "Refusing unexpected cgroup path: $group" >&2; exit 2 ;;
esac

printf '%s\n' "$$" >"$group/cgroup.procs"
exec "$@"
