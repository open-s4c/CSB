#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WDIR="$SCRIPT_DIR/../../../bm-external/cgroups"
cd $WDIR

echo "=========================================="
echo "Detecting Architecture"
echo "=========================================="
arch=$(uname -m)
case "$arch" in
    x86_64)
        echo "ARM x86_64 arch detected!"
        TOYBOX_URL=https://landley.net/toybox/bin/toybox-x86_64
        ;;
    aarch64)
        echo "ARM 64-bit arch detected!"
        TOYBOX_URL=https://landley.net/toybox/bin/toybox-aarch64
        ;;
    *)
        echo "[ERROR] Unsupported architecture: $arch"
        exit 1
        ;;
esac

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

# ls -lR

echo "=========================================="
echo "Creating config"
echo "=========================================="
cd ../../
rm -f config.json
runc spec

sed -i 's|"terminal": true,|"terminal": false,|' config.json
sed -i 's|"sh"|"/bin/sh", "-c", "echo hello"|' config.json

echo "=========================================="
echo "Test (run & delete) container"
echo "=========================================="
CONTAINER_NAME="test-container"
sudo runc run -d $CONTAINER_NAME
sudo runc delete -f $CONTAINER_NAME
