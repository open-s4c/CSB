# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import json

import pytest

from monitors.kernel_anomaly import KernelAnomaly


def test_classify_detects_soft_lockup_and_list_add_corruption():
    matches = KernelAnomaly.classify(
        "watchdog: BUG: soft lockup - CPU#4 stuck for 171s! [dockerd]\n"
        "list_add corruption. prev->next should be next\n"
        "ordinary kernel message\n"
    )

    assert len(matches["soft_lockup"]) == 1
    assert len(matches["list_add_corruption"]) == 1


def test_parse_cursor_uses_last_cursor():
    assert KernelAnomaly.parse_cursor("-- cursor: first\nmessage\n-- cursor: second\n") == "second"


def test_monitor_records_only_messages_after_start(tmp_path, monkeypatch):
    outputs = iter(
        [
            "-- cursor: before\n",
            "kernel: ordinary\nkernel: list_add corruption. next->prev mismatch\n"
            "-- cursor: after\n",
        ]
    )
    monkeypatch.setattr(KernelAnomaly, "_journalctl", staticmethod(lambda _args: next(outputs)))
    monitor = KernelAnomaly(tmp_path, [])

    monitor.start()
    monitor.stop()

    summary = json.loads((tmp_path / "kernel-anomaly-summary.json").read_text())
    assert summary["start_cursor"] == "before"
    assert summary["end_cursor"] == "after"
    assert summary["counts"]["list_add_corruption"] == 1
    with pytest.raises(RuntimeError, match="kernel anomaly detected"):
        monitor.collect_results()


def test_clean_monitor_exports_zero_metrics(tmp_path, monkeypatch):
    outputs = iter(["-- cursor: before\n", "kernel: ordinary\n-- cursor: after\n"])
    monkeypatch.setattr(KernelAnomaly, "_journalctl", staticmethod(lambda _args: next(outputs)))
    monitor = KernelAnomaly(tmp_path, [])

    monitor.start()
    monitor.stop()

    assert monitor.collect_results() == ("kernel_soft_lockups=0;kernel_list_add_corruptions=0;")
