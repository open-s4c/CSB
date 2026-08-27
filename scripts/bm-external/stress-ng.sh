#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# stress-ng's exec stressor refuses to run as root. CSB may itself be launched
# with sudo for Docker access, so return to the invoking user for the workload.
if [[ $(id -u) -eq 0 && -n ${SUDO_UID:-} && ${SUDO_UID} -ne 0 ]]; then
    exec setpriv --reuid="${SUDO_UID}" --regid="${SUDO_GID}" --init-groups \
        stress-ng "$@" 2>&1
fi

# stress-ng writes its metrics to stderr. Merge both streams so CSB's adapter
# receives the metric table for native runs as well as container runs.
exec stress-ng "$@" 2>&1
