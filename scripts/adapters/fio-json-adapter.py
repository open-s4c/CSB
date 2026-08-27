#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import json
import sys


def add_metric(metrics, name, value):
    if value is not None:
        metrics.append(f"{name}={value}")


def parse_fio(document):
    jobs = document.get("jobs", [])
    if not jobs:
        raise ValueError("fio JSON contains no jobs")

    job = jobs[0]
    metrics = []
    for name in ("error", "job_runtime", "usr_cpu", "sys_cpu"):
        add_metric(metrics, name, job.get(name))

    for direction in ("read", "write"):
        values = job.get(direction, {})
        for name in ("iops", "bw", "total_ios"):
            add_metric(metrics, f"{direction}_{name}", values.get(name))
        percentiles = values.get("clat_ns", {}).get("percentile", {})
        for percentile, suffix in (
            ("50.000000", "p50"),
            ("95.000000", "p95"),
            ("99.000000", "p99"),
            ("99.900000", "p99_9"),
        ):
            add_metric(
                metrics,
                f"{direction}_clat_{suffix}_ns",
                percentiles.get(percentile),
            )

    return metrics


if __name__ == "__main__":
    try:
        print(";".join(parse_fio(json.load(sys.stdin))))
    except (json.JSONDecodeError, ValueError) as error:
        sys.exit(str(error))
