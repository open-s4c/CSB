# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import Optional
from config.list import ListConfig


class ExecutionType(str, Enum):
    """
    Execution environment of the benchmarks.

    Members
    ----------
    NATIVE: Launches the benchmark(s) directly on the host OS.
    CONTAINER: Launches the benchmark(s) inside a container.
    """

    NATIVE = "native"  # indicates that the benchmark should run natively
    CONTAINER = "container"  # indicates that the benchmark should run inside the container


class MonitorType(str, Enum):
    """
    Monitors are used to monitor performance.
    They can be used to analyze the behavior of the benchmarks.

    Members
    ----------
    MPSTAT: Runs mpstat and generates related graphs.
    PERF: Runs perf and generates flame-graphs.
    REDIS_BENCHMARK: parses the output of redis_benchmark.
    SAR_NET: monitors network traffic.
    PERF_STAT: Runs perf stat.
    """

    MPSTAT = "mpstat"
    PERF = "perf"
    REDIS_BENCHMARK = "redis_benchmark"
    SAR_NET = "sar_net"
    PERF_STAT = "perf_stat"


class BenchmarkConfig(dict):
    CONFIG_KEY: str = "benchmark_config"

    def __init__(
        self,
        duration: int = 3,
        repeat: int = 1,
        initial_size: list[int] = [0],
        noise: list[int] = [0],
        exec_env: list[ExecutionType] = [ExecutionType.NATIVE, ExecutionType.CONTAINER],
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
            JSON example: `"repeat": 3`
        repeat: int
            Number of times the benchmark should be repeated.
            JSON example: `"repeat": 1`
        initial_size: list[int]
            The initial size parameter that should be passed
            to the benchmark initialization.
            JSON example: `"initial_size" : [1, 1000]`
        noise: list[int]
            How many `nop` operations to run between real
            operations.
            JSON example: `"noise" : [0, 1000]`
        exec_env: list[ExecutionType] = ["native", "container"]
            Whether to execute the benchmark in a container or
            natively. JSON example: `"exec_env" : ["container", "native"]`
        monitors: dict[MonitorType, list[str]]
            Monitors to run in the background.
        threads: ListConfig = {"values": [[1]]}
            Determines number of threads to run target benchmarks with.
            If not provided all applications will be run with 1 thread.
        -
        """
        self.duration = duration
        self.repeat = repeat
        self.initial_size = initial_size
        self.noise = noise
        self.exec_env = exec_env
        self.monitors = monitors
        self.threads = (
            ListConfig.from_dict(threads).get_list()
            if threads is not None
            else ListConfig([[1]]).get_list()
        )
