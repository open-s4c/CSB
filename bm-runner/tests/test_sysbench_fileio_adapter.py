# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path


ADAPTER = Path(__file__).parents[2] / "scripts/adapters/sysbench-adapter.py"


def test_sysbench_adapter_parses_fileio_metrics():
    output = """\
File operations:
    reads/s:                      1234.56
    writes/s:                     987.65

Throughput:
    read, MiB/s:                  4.82
    written, MiB/s:               3.86

Latency (ms):
         min:                          0.01
         avg:                          0.31
         max:                          3.42
         95th percentile:              0.95
"""
    result = subprocess.run([ADAPTER], input=output, text=True, capture_output=True, check=True)

    assert "file_operations.reads_s=1234.56" in result.stdout
    assert "throughput.read_mib_s=4.82" in result.stdout
    assert "latency.95th_percentile=0.95" in result.stdout
