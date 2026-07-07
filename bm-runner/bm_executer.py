# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.shell.shell import shell_out
import os
import sys
import time
from typing import Optional

from config.plugin import ExecutionTime
import bm_config
from bm_utils import is_port_free_to_use
from monitors.monitor_factory import MonitorFactory
from utils.logger import bm_log, LogType
from bm_utils import resolve_path
from config.container import ContainersConfig
from bm_process import Process
from bm_container import Container
from bm_bwrap import Bubblewrap
from bm_exec_unit import ExecutionUnit, ExecutionType
from config.application import Application


class Executer:
    SLEEP_IN_SEC = 5

    def __init__(
        self,
        config: ContainersConfig,
        type: ExecutionType,
        apps: list[Application],
        home_dir,
        results_dir,
        count: int,
    ):
        assert bm_config.g_config
        self.home_dir = home_dir
        self.results_dir = results_dir
        self.exec_units = []
        self.plugins = bm_config.g_config.get_plugins()
        self.nics = bm_config.g_config.get_nics()
        self.config = config
        self.apps = apps
        self.count = count
        self.monitors = [
            MonitorFactory.create(monitor_type=type, results_dir=results_dir, args=args)
            for type, args in bm_config.g_config.get_benchmark_cfg().monitors.items()
        ]
        assert len(apps) == count, "[BUG] Application list length must be equal to count"
        for idx in range(self.count):
            eu = self.__create_eu(type, idx)
            self.exec_units.append(eu)

    def __call_plugins(self, exec_time):
        plugins = [plugin for plugin in self.plugins if plugin.exec_time == exec_time]
        for plugin in plugins:
            plugin.execute(
                self.results_dir,
                n_units=len(self.exec_units),
                homedir=self.home_dir,
                res_dir=self.results_dir,
            )

    def __check_plugins(self, exec_time):
        plugins = [plugin for plugin in self.plugins if plugin.exec_time == exec_time]
        for plugin in plugins:
            plugin.check()

    def __wrap_plugins(self) -> str:
        """
        Retuns command line string with all plugins that run "with" the benchmarked applications.
        """
        plugins = [
            plugin.get_command()
            for plugin in self.plugins
            if plugin.exec_time == ExecutionTime.WITH
        ]
        return " ".join(plugins)

    def __create_eu(self, type: ExecutionType, idx: int) -> ExecutionUnit:
        core_set = self.config.get_cpus(idx)
        match type:
            case ExecutionType.CONTAINER:
                return Container(
                    idx=idx,
                    home_dir=self.home_dir,
                    image=self.config.image,
                    core_set=core_set,
                    record_data_dir=self.results_dir,
                    port=self.config.port,
                    app=self.apps[idx],
                    nic=self.nics.get_cfg(idx) if self.nics else None,
                )
            case ExecutionType.NATIVE:
                return Process(
                    idx=idx,
                    home_dir=self.home_dir,
                    core_set=core_set,
                    record_data_dir=self.results_dir,
                    app=self.apps[idx],
                )
            case ExecutionType.BWRAP:
                return Bubblewrap(
                    idx=idx,
                    home_dir=self.home_dir,
                    core_set=core_set,
                    record_data_dir=self.results_dir,
                    app=self.apps[idx],
                )
            case _:
                bm_log(f"Unsupported execution type = {type}", LogType.FATAL)
                sys.exit(1)

    def __stop_plugins(self):
        for plugin in self.plugins:
            plugin.stop()

    def __start_monitors(self):
        for monitor in self.monitors:
            monitor.start()

    def __stop_monitors(self):
        for monitor in self.monitors:
            monitor.stop()

    def exec_all(self, threads, duration, noise, initial_size, port_start: Optional[int]):
        try:
            for idx, eu in enumerate(self.exec_units):
                if port_start is not None:
                    sz = idx + port_start
                    # TODO: At the moment initial_size is exploited to pass the port number,
                    # make sure that initial_size is not used when port is available
                    # or find a proper way to pass the port number to the micro-bm
                    if not is_port_free_to_use(sz):
                        bm_log(
                            f"Port {sz} is already in use!, make sure ports in this range [{port_start}:{len(self.exec_units)-1}] are free to use.",
                            LogType.FATAL,
                        )
                        sys.exit(1)
                else:
                    sz = initial_size
                ret = eu.exec(
                    eu.app.get_cmd(
                        plugins_cmds=self.__wrap_plugins(),
                        threads=threads,
                        duration=duration,
                        noise=noise,
                        initial_size=sz,
                        index=idx,
                        work_dir=self.home_dir,
                        n_units=len(self.exec_units),
                        homedir=self.home_dir,
                        res_dir=eu.get_results_dir(),
                        host_ip=bm_config.get_host_ip(),
                    )
                )
                if not ret:
                    break

            # give start signal
            self.signal_start()
            # wait for all containers to finish
            for eu in self.exec_units:
                eu.wait()
        except KeyboardInterrupt:
            # Warn the user not to press it again, and shutdown to propagate.
            bm_log(
                "User pressed ctrl+c! The benchmark will be interrupted and cleaning up resources will start. Don't press ctrl+c again! Otherwise, you have to clean up containers and monitors manually!",
                LogType.FATAL,
            )
            sys.exit(1)
        finally:
            self.cleanup()

    def collect_results(self) -> str:
        stat_prefix = "".join([monitor.collect_results().strip() for monitor in self.monitors])
        result = "".join(f"{stat_prefix}{eu.get_output()}" for eu in self.exec_units)
        return result

    def signal_start(self):
        bm_log(f"Waiting for {self.SLEEP_IN_SEC}, before giving the start signal")
        time.sleep(self.SLEEP_IN_SEC)
        self.__call_plugins(ExecutionTime.PRE)
        self.__start_monitors()
        shell_out(
            f"touch {ExecutionUnit.START_FILE}",
            current_dir=self.home_dir,
            output_is_log=False,
            print_file_shell_cmd=False,
        )
        # ensure no errors happened in pre plugins
        self.__check_plugins(ExecutionTime.PRE)
        self.__call_plugins(ExecutionTime.POST)

    def cleanup(self):
        bm_log("cleaning up, stopping all processes/containers")
        for eu in self.exec_units:
            eu.stop()
        start_file = resolve_path(ExecutionUnit.START_FILE)
        if os.path.exists(start_file):
            os.remove(start_file)
        self.__stop_monitors()
        self.__call_plugins(ExecutionTime.CLEANUP)
        self.__stop_plugins()
