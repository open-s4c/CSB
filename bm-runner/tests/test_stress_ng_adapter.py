# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path


ADAPTER = Path(__file__).parents[2] / "scripts/adapters/stress-ng-adapter.sh"


def test_stress_ng_adapter_parses_summary_and_pthread_metrics():
    output = """\
stress-ng: metrc: [1] stressor bogo ops real time usr time sys time bogo ops/s
stress-ng: metrc: [1] pthread 2812 1.00 0.23 0.52 2809.25 3731.35 75.29 4204
stress-ng: metrc: [1] miscellaneous metrics:
stress-ng: metrc: [1] pthread 27946.62 nanosecs to start a pthread
stress-ng: metrc: [1] pthread 100.00 % of 128 pthreads created
stress-ng: info: [1] skipped: 0
stress-ng: info: [1] passed: 1: pthread (1)
stress-ng: info: [1] failed: 0
stress-ng: info: [1] metrics untrustworthy: 0
"""

    result = subprocess.run([ADAPTER], input=output, text=True, capture_output=True, check=True)

    assert "stressor=pthread;" in result.stdout
    assert "ops=2812;" in result.stdout
    assert "throughput_real=2809.25;" in result.stdout
    assert "pthread_start_ns=27946.62;" in result.stdout
    assert "pthread_created_percent=100.00;" in result.stdout
    assert "passed=1;" in result.stdout
    assert "failed=0;" in result.stdout
    assert "untrustworthy=0;" in result.stdout
