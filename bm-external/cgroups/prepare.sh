#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -e

TOYBOX_URL=https://landley.net/toybox/bin/toybox-x86_64

echo "=========================================="
echo "Cleaning up and creating dir rootfs"
echo "=========================================="
rm -rf rootfs
mkdir rootfs
cd rootfs

echo "=========================================="
echo "Downloading toybox"
echo "=========================================="
wget -O toybox ${TOYBOX_URL}
chmod +x toybox

echo "=========================================="
echo "Preparing rootfs"
echo "=========================================="
mkdir bin
cd bin
for cmd in $(../toybox); do ln -s ../toybox  "$cmd"; done

echo "=========================================="
echo "Verify symbolic links point to toybox"
echo "=========================================="

ls -lR

echo "=========================================="
echo "Creating config"
echo "=========================================="
cd ../../
rm -f config.json
runc spec

echo "=========================================="
echo "Test running and removing test container"
echo "=========================================="
CONTAINER_NAME="test-container"
sudo runc run $CONTAINER_NAME


