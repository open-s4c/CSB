# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT


from monitors.iostat import IoStat


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


def test_iostat_dataframe_from_json_flattens_samples():
    df = IoStat._IoStat__transform_json_to_df(iostat_sample())  # ty: ignore[unresolved-attribute]
    assert list(df["time"]) == [0, 0, 1, 1]
    assert list(df["disk_device"]) == ["nvme0n1", "loop0", "nvme0n1", "loop0"]
    assert list(df["r/s"]) == [1.0, 0.0, 3.0, 0.0]


def test_iostat_aggregate_results_sanitizes_metric_names():
    stat = IoStat("test", [])
    df = IoStat._IoStat__transform_json_to_df(iostat_sample())  # ty: ignore[unresolved-attribute]
    results = stat._IoStat__get_metric_means(df)  # ty: ignore[unresolved-attribute]
    entries = dict(item.split("=", maxsplit=1) for item in results.rstrip(";").split(";"))

    assert float(entries["iostat_nvme0n1_r_s"]) == 2.0
    assert float(entries["iostat_nvme0n1_rareq_sz"]) == 19.0
    assert float(entries["iostat_loop0_util"]) == 21.0
