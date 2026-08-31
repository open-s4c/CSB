# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import Optional
from config.list import ListConfig
from monitors.perflock import PerfLock
from utils.logger import bm_log, LogType
from config.env_config import EnvUniversalConfig, UniversalConfig


class ExecutionType(str, Enum):
    """
    Execution environment of the benchmarks.

    Members
    ----------
    NATIVE: Launches the benchmark(s) directly on the host OS.
    CONTAINER: Launches the benchmark(s) inside a container.
    BWRAP: Launches the benchmark(s) with bubblewrap.
    """

    NATIVE = "native"  # indicates that the benchmark should run natively
    CONTAINER = "container"  # indicates that the benchmark should run inside the container
    BWRAP = "bwrap"  # indicates that the benchmark should run with bubblewrap


EXECUTION_TYPE_PREFIX = {
    ExecutionType.CONTAINER: "C",
    ExecutionType.NATIVE: "N",
    ExecutionType.BWRAP: "B",
}


class MonitorType(str, Enum):
    """
    Monitors are used to monitor performance.
    They can be used to analyze the behavior of the benchmarks.

    Members
    ----------
    MPSTAT: Runs mpstat and generates related graphs.
    PERF: Runs perf and generates flame-graphs.
    IOSTAT: Runs iostat -x and generates block-device graphs.
    REDIS_BENCHMARK: parses the output of redis_benchmark.
    SAR_NET: monitors network traffic.
    PERF_STAT: Runs perf stat.
    PERF_LOCK: Runs perf lock, and perf lock contention if supported. Lock-contention output is generated when the kernel exposes the required `perf lock` trace-points. Note that `perf_lock` monitor invokes `perf` monitor even if it was not added by the user. Also when tracepoint events are configured, incompatible frequency arguments (`-F <freq>`, `-F<freq>`,`--freq <freq>`, and `--freq=<freq>`) are automatically removed.
    BPF_TRACE: Runs [bpftrace](https://bpftrace.org/docs/release_025/stdlib) with the given programs. Users may list programs from scripts/bpftrace. Giving multiple programs as arguments, will result in launching multiple instances of bpftrace.
    KERNEL_ANOMALY: Detects kernel anomalies during the benchmark and writes journal and summary artifacts.
    """

    MPSTAT = "mpstat"
    PERF = "perf"
    IOSTAT = "iostat"
    REDIS_BENCHMARK = "redis_benchmark"
    SAR_NET = "sar_net"
    PERF_STAT = "perf_stat"
    PERF_LOCK = "perf_lock"
    BPF_TRACE = "bpftrace"
    KERNEL_ANOMALY = "kernel_anomaly"


class BenchmarkConfig(dict):
    CONFIG_KEY: str = "benchmark_config"

    def __init__(
        self,
        duration: int = 3,
        repeat: int = 1,
        exec_env: dict[ExecutionType, list[str]] = {
            ExecutionType.NATIVE: [],
            ExecutionType.CONTAINER: [],
        },
        monitors: dict[MonitorType, list[str]] = {},
        threads: Optional[ListConfig] = None,
    ):
        """
        General configuration for benchmarks, as well as a collection
        of system-level metrics (specified under monitors).
        Represented as one JSON object.
        Parameters
        ----------
        duration: int
            Duration of the benchmark in seconds.
            JSON example: `"duration": 1`
        repeat: int
            Number of times the benchmark should be repeated.
            JSON example: `"repeat": 3`
        exec_env: dict[ExecutionType, list[str]] = {"native":[], "container":[]}
            Dictates in which environments the benchmark is executed, and which
            extra arguments are used. Note that currently the arguments are
            only considered in case of `bwrap`.
            JSON example: `"exec_env" : {"native":[], "container":[], "bwrap":["--die-with-parent"]}`
        monitors: dict[MonitorType, list[str]]
            Monitors to run in the background.
        threads: ListConfig = {"values": [[1]]}
            Determines number of threads to run target benchmarks with.
            If not provided all applications will be run with 1 thread.
        -
        """
        self.duration = duration
        self.repeat = repeat
        self.exec_env = exec_env
        self.monitors = self.__resolve_monitor_dependency(monitors)
        self.threads = (
            ListConfig.from_dict(threads).get_list()
            if threads is not None
            else ListConfig([[1]]).get_list()
        )

    @staticmethod
    def __resolve_monitor_dependency(
        monitors: dict[MonitorType, list[str]],
    ) -> dict[MonitorType, list[str]]:
        """
        Enforces the right order of monitors, if there is a dependency
        between monitors, e.g. `perf_lock` must occur after `perf`.
        """
        if (
            EnvUniversalConfig.is_off(UniversalConfig.CSB_ANALYZE)
            or MonitorType.PERF_LOCK not in monitors
        ):
            return monitors

        if not PerfLock.is_supported():
            bm_log(
                f"{MonitorType.PERF_LOCK.value} is not supported by the perf/system. This monitor is auto-removed!",
                LogType.ERROR,
            )
            del monitors[MonitorType.PERF_LOCK]
            return monitors

        perf_args = list(monitors.get(MonitorType.PERF, []))
        perf_args.extend(PerfLock.get_args())
        perf_args.extend(monitors[MonitorType.PERF_LOCK])

        resolved_monitors: dict[MonitorType, list[str]] = {}
        resolved_monitors[MonitorType.PERF] = perf_args
        resolved_monitors[MonitorType.PERF_LOCK] = monitors[MonitorType.PERF_LOCK]

        for k, v in monitors.items():
            if k not in {MonitorType.PERF, MonitorType.PERF_LOCK}:
                resolved_monitors[k] = v

        return resolved_monitors

    def get_exec_env_args(self, exec_type: ExecutionType) -> list[str]:
        return self.exec_env.get(exec_type, [])
