#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
cmake --build ../build --target syz_single.h.in
cmake --build ../build --target fg_single.json.in
