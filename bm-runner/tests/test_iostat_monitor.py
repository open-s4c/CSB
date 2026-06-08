# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import json

from monitors.iostat import IostatStats


def iostat_sample():
    return {
        "sysstat": {
            "hosts": [
                {
                    "statistics": [
                        {
                            "disk": [
                                disk_sample("nvme0n1", 1.0),
                                disk_sample("loop0", 0.0),
                            ]
                        },
                        {
                            "disk": [
                                disk_sample("nvme0n1", 3.0),
                                disk_sample("loop0", 0.0),
                            ]
                        },
                    ]
                }
            ]
        }
    }


def disk_sample(device, value):
    return {
        "disk_device": device,
        "r/s": value,
        "w/s": value + 1,
        "d/s": value + 2,
        "f/s": value + 3,
        "rkB/s": value + 4,
        "wkB/s": value + 5,
        "dkB/s": value + 6,
        "rrqm/s": value + 7,
        "wrqm/s": value + 8,
        "drqm/s": value + 9,
        "rrqm": value + 10,
        "wrqm": value + 11,
        "drqm": value + 12,
        "r_await": value + 13,
        "w_await": value + 14,
        "d_await": value + 15,
        "f_await": value + 16,
        "rareq-sz": value + 17,
        "wareq-sz": value + 18,
        "dareq-sz": value + 19,
        "aqu-sz": value + 20,
        "util": value + 21,
    }


def test_iostat_cmd_enforces_extended_json_output():
    assert IostatStats.iostat_cmd(["nvme0n1"]) == [
        "iostat",
        "-x",
        "-o",
        "JSON",
        "-y",
        "nvme0n1",
        "1",
    ]


def test_iostat_dataframe_from_json_flattens_samples():
    df = IostatStats.dataframe_from_json(iostat_sample())

    assert list(df["time"]) == [0, 0, 1, 1]
    assert list(df["disk_device"]) == ["nvme0n1", "loop0", "nvme0n1", "loop0"]
    assert list(df["r/s"]) == [1.0, 0.0, 3.0, 0.0]


def test_iostat_aggregate_results_sanitizes_metric_names():
    df = IostatStats.dataframe_from_json(iostat_sample())
    results = IostatStats.aggregate_results(df)
    entries = dict(item.split("=", maxsplit=1) for item in results.rstrip(";").split(";"))

    assert float(entries["iostat_nvme0n1_r_s"]) == 2.0
    assert float(entries["iostat_nvme0n1_rareq_sz"]) == 19.0
    assert float(entries["iostat_loop0_util"]) == 21.0


def test_iostat_dump_plots_for_tree_generates_plots_for_all_runs(tmp_path):
    first_run = tmp_path / "container_cnt-1" / "run-1"
    second_run = tmp_path / "container_cnt-2" / "run-1"
    first_run.mkdir(parents=True)
    second_run.mkdir(parents=True)
    (first_run / IostatStats.OUTPUT_FILE).write_text(json.dumps(iostat_sample()))
    (second_run / IostatStats.OUTPUT_FILE).write_text(json.dumps(iostat_sample()))

    IostatStats.dump_plots_for_tree(tmp_path)

    for run_dir in [first_run, second_run]:
        assert (run_dir / "iostat-iops.png").stat().st_size > 0
        assert (run_dir / "iostat-throughput.png").stat().st_size > 0
        assert (run_dir / "iostat-util.png").stat().st_size > 0
