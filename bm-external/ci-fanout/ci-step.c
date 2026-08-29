// Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
// SPDX-License-Identifier: MIT

#include <stddef.h>
#include <stdint.h>

static uint64_t
rotate_left(uint64_t value, unsigned int shift)
{
    return (value << shift) | (value >> (64U - shift));
}

uint64_t
validate_ci_manifest(const unsigned char *data, size_t length)
{
    uint64_t checksum = UINT64_C(0xcbf29ce484222325);

    for (size_t i = 0; i < length; i++) {
        checksum ^= data[i];
        checksum = rotate_left(checksum, 7U) * UINT64_C(0x100000001b3);
    }
    return checksum;
}
