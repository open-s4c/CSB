# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from config.benchmark import MonitorType
from monitors.mpstat import SystemStats
from monitors.redis_bench import RedisStats
from monitors.perf import FlameGraph
from monitors.sarnet import SarNetStats
from monitors.monitor import Monitor
from monitors.perfstat import PerfStat
from utils.logger import bm_log, LogType
import sys
from config.env_config import EnvUniversalConfig, UniversalConfig


class DummyMonitor(Monitor):
    def __init__(self, name: str):
        super().__init__(dir="", args=[])
        self.name = name

    def start(self):
        bm_log(
            f"Requested monitor `{self.name}` from config is not started, since environment variable `{UniversalConfig.CSB_ANALYZE}` "
            f"is set to `false`."
            f"To reactivate monitors remove `{UniversalConfig.CSB_ANALYZE}` or set it to `true`",
            LogType.WARNING,
        )

    def stop(self):
        pass

    def collect_results(self) -> str:
        return ""


class MonitorFactory:
    @staticmethod
    def create(monitor_type: MonitorType, results_dir, args) -> Monitor:
        # if the user has requested to disable the monitors,
        # we return a dummy monitor that does nothing,
        # so that the rest of the code can remain unchanged
        if not EnvUniversalConfig.is_on(UniversalConfig.CSB_ANALYZE):
            return DummyMonitor(name=f"{monitor_type}")  # Return a dummy monitor that does nothing
        match monitor_type:
            case MonitorType.MPSTAT:
                return SystemStats(output_dir=results_dir, args=args)
            case MonitorType.PERF:
                return FlameGraph(output_dir=results_dir, args=args)
            case MonitorType.REDIS_BENCHMARK:
                return RedisStats(output_dir=results_dir, args=args)
            case MonitorType.SAR_NET:
                return SarNetStats(output_dir=results_dir, args=args)
            case MonitorType.PERF_STAT:
                return PerfStat(output_dir=results_dir, args=args)
            case _:
                bm_log(f"Unsupported monitor type {monitor_type}", LogType.FATAL)
                sys.exit(1)
