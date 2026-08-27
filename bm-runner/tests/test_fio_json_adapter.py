# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import json
import subprocess
from pathlib import Path


ADAPTER = Path(__file__).parents[2] / "scripts/adapters/fio-json-adapter.py"


def test_fio_json_adapter_parses_io_and_latency_metrics():
    document = {
        "jobs": [
            {
                "error": 0,
                "job_runtime": 3000,
                "usr_cpu": 1.2,
                "sys_cpu": 8.4,
                "read": {
                    "iops": 123.5,
                    "bw": 494,
                    "total_ios": 371,
                    "clat_ns": {
                        "percentile": {
                            "50.000000": 1000,
                            "95.000000": 2000,
                            "99.000000": 3000,
                            "99.900000": 4000,
                        }
                    },
                },
                "write": {"iops": 0, "bw": 0, "total_ios": 0},
            }
        ]
    }
    result = subprocess.run(
        [ADAPTER],
        input=json.dumps(document),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "error=0;" in result.stdout
    assert "read_iops=123.5;" in result.stdout
    assert "read_clat_p99_9_ns=4000;" in result.stdout
    assert "write_iops=0;" in result.stdout
