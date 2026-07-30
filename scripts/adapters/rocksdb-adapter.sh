#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

awk '/operations/ {printf "%s%s=%d", sep, $1, $5; sep=";"} END {printf("\n")}'
