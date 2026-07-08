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
    PERF_LOCK: Runs perf lock, and perf lock contention if supported. Lock-contention output is generated when the kernel exposes the required `perf lock` trace-points. Running `perf_lock` together with `perf` monitor can corrupt the `perf` monitor results.
    BPF_TRACE: Runs [bpftrace](https://bpftrace.org/docs/release_025/stdlib) with the given programs. Users may list programs from scripts/bpftrace. Giving multiple programs as arguments, will result in launching multiple instances of bpftrace.
    """

    MPSTAT = "mpstat"
    PERF = "perf"
    IOSTAT = "iostat"
    REDIS_BENCHMARK = "redis_benchmark"
    SAR_NET = "sar_net"
    PERF_STAT = "perf_stat"
    PERF_LOCK = "perf_lock"
    BPF_TRACE = "bpftrace"


class BenchmarkConfig(dict):
    CONFIG_KEY: str = "benchmark_config"

    def __init__(
        self,
        duration: int = 3,
        repeat: int = 1,
        initial_size: list[int] = [0],
        noise: list[int] = [0],
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
        self.initial_size = initial_size
        self.noise = noise
        self.exec_env = exec_env
        self.monitors = monitors
        self.threads = (
            ListConfig.from_dict(threads).get_list()
            if threads is not None
            else ListConfig([[1]]).get_list()
        )

    def get_exec_env_args(self, exec_type: ExecutionType) -> list[str]:
        return self.exec_env.get(exec_type, [])
