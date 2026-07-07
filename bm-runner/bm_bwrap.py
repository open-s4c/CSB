# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys

from bm_executer import Executer, ExecutionUnit
from bm_utils import resolve_path
from config.application import Application
from config.benchmark import ExecutionType
from config.container import ContainersConfig
from utils.logger import bm_log, LogType
from pathlib import Path
from utils.process import BackgroundProcess
from bm_utils import ensure_exists


class Bubblewrap(ExecutionUnit):

    ro_binding_map: dict[str, str] = {
        "/usr": "/usr",
        "/bin": "/bin",
        "/lib": "/lib",
        "/lib64": "/lib64",
        "/etc": "/etc",
    }

    def __init__(self, idx, home_dir, record_data_dir, core_set, app: Application):
        super().__init__(idx=idx, home_dir=home_dir, app=app, type=ExecutionType.BWRAP)
        self.record_data_dir = record_data_dir
        self.core_set = core_set
        self.process = None
        ensure_exists("bwrap")

    def get_results_dir(self) -> str:
        # Inside bwrap, CSB project dir is mounted at /home.
        return str(resolve_path(self.record_data_dir, use_in_container=True))

    def __bwrap_prefix(self) -> list[str]:
        host_home = resolve_path(self.home_dir)
        args: list[str] = [
            "bwrap",
            # Namespace isolation.
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup",
            # Keep network shared by default to match current native/container behavior
            # unless CSB later adds explicit networking policy.
            "--share-net",
            # Basic runtime filesystems.
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            # Host resources needed by CSB benchmarks.
            "--bind",
            str(host_home),
            "/home",
            "--chdir",
            "/home",
        ]
        for src, dst in self.ro_binding_map.items():
            if os.path.exists(Path(src)):
                args.extend(["--ro-bind", src, dst])

        return args

    def exec(self, command: str) -> bool:
        change_dir = ""
        if self.app.cd:
            assert self.app.path is not None, "path is not set while change directory is requested!"
            change_dir = f"cd {self.app.path} && "

        inner_command = f"{self.CMD_WHILE_NOT_START} " f"{change_dir}" f" {command}"

        commands = self.__bwrap_prefix() + ["/bin/bash", "-c", inner_command]

        self.process = BackgroundProcess(
            name=self.name,
            cmds=commands,
            out_dir=str(resolve_path(Path(self.output_file).parent)),
            efile_name=Path(self.err_file).name,
            ofile_name=Path(self.output_file).name,
            wdir=self.home_dir,
            pin=self.core_set,
        )
        self.process.start()
        return True

    def wait(self):
        if self.process:
            returncode = self.process.wait_indefinitely()
            if returncode != 0:
                bm_log(
                    f"bwrap process {self.name} failed/crashed with return code {returncode}",
                    LogType.FATAL,
                )
                sys.exit(1)

    def stop(self):
        if self.process is not None:
            self.process.force_stop()


class Bubblewraps(Executer):
    def __init__(
        self,
        config: ContainersConfig,
        apps: list[Application],
        home_dir,
        count,
        record_data_dir,
    ):
        super().__init__(home_dir=home_dir, results_dir=record_data_dir)
        assert len(apps) == count, "[BUG] Application list length must be equal to count"

        for i in range(count):
            core_set = config.get_cpus(i)
            bwrap = Bubblewrap(
                idx=i,
                home_dir=home_dir,
                core_set=core_set,
                record_data_dir=record_data_dir,
                app=apps[i],
            )
            self.add_exec_unit(bwrap)
