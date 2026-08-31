# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

"""Detect kernel correctness failures emitted during a benchmark run."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from monitors.monitor import Monitor


class KernelAnomaly(Monitor):
    """Fail result collection on new soft lockups or list corruption reports."""

    CURSOR_PREFIX = "-- cursor: "
    PATTERNS = {
        "soft_lockup": re.compile(r"\bsoft lockup\b", re.IGNORECASE),
        "list_add_corruption": re.compile(r"\blist_add corruption\b", re.IGNORECASE),
    }

    def __init__(self, output_dir, args):
        super().__init__(dir=output_dir, args=args)
        self.output_dir = Path(output_dir)
        self.cursor: str | None = None
        self.matches: dict[str, list[str]] = {name: [] for name in self.PATTERNS}
        self.journal_path = self.output_dir / "kernel-anomaly-journal.log"
        self.summary_path = self.output_dir / "kernel-anomaly-summary.json"
        if args:
            raise ValueError("kernel_anomaly monitor does not accept arguments")

    @classmethod
    def classify(cls, text: str) -> dict[str, list[str]]:
        lines = text.splitlines()
        return {
            name: [line for line in lines if pattern.search(line)]
            for name, pattern in cls.PATTERNS.items()
        }

    @classmethod
    def parse_cursor(cls, text: str) -> str:
        for line in reversed(text.splitlines()):
            if line.startswith(cls.CURSOR_PREFIX):
                cursor = line[len(cls.CURSOR_PREFIX) :].strip()
                if cursor:
                    return cursor
        raise RuntimeError("journalctl did not return a journal cursor")

    @staticmethod
    def _journalctl(arguments: list[str]) -> str:
        try:
            completed = subprocess.run(
                ["journalctl", *arguments],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("journalctl is required for kernel anomaly detection") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"journalctl failed: {detail}")
        return completed.stdout

    def start(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output = self._journalctl(["-k", "-n", "0", "--show-cursor", "--no-pager"])
        self.cursor = self.parse_cursor(output)

    def stop(self):
        if self.cursor is None:
            return
        try:
            output = self._journalctl(
                [
                    "-k",
                    "--after-cursor",
                    self.cursor,
                    "--show-cursor",
                    "--no-pager",
                    "-o",
                    "short-iso",
                ]
            )
            end_cursor = self.parse_cursor(output)
            journal = "\n".join(
                line for line in output.splitlines() if not line.startswith(self.CURSOR_PREFIX)
            )
            if journal:
                journal += "\n"
            self.journal_path.write_text(journal)
            self.matches = self.classify(journal)
            summary = {
                "start_cursor": self.cursor,
                "end_cursor": end_cursor,
                "counts": {name: len(lines) for name, lines in self.matches.items()},
                "matches": self.matches,
                "status": "failed" if any(self.matches.values()) else "clean",
            }
            self.summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
            self.cursor = end_cursor
        except Exception as exc:
            # Monitor.stop() runs inside framework cleanup. Preserve the error
            # and defer raising until collect_results(), after all cleanup ran.
            self.matches = {name: [] for name in self.PATTERNS}
            self.matches["monitor_error"] = [str(exc)]
            self.summary_path.write_text(
                json.dumps(
                    {
                        "start_cursor": self.cursor,
                        "status": "monitor-error",
                        "error": str(exc),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )

    def collect_results(self) -> str:
        errors = self.matches.get("monitor_error", [])
        if errors:
            raise RuntimeError(
                f"kernel anomaly detection failed: {errors[0]}; see {self.summary_path}"
            )
        counts = {name: len(self.matches[name]) for name in self.PATTERNS}
        if any(counts.values()):
            detail = ", ".join(f"{name}={count}" for name, count in counts.items())
            raise RuntimeError(f"kernel anomaly detected ({detail}); see {self.summary_path}")
        return (
            f"kernel_soft_lockups={counts['soft_lockup']};"
            f"kernel_list_add_corruptions={counts['list_add_corruption']};"
        )
