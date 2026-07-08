# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import sys
from bm_exec_unit import ExecutionUnit
from bm_config import Application
from config.benchmark import ExecutionType
from utils.logger import bm_log, LogType
from bm_utils import resolve_path
from utils.process import BackgroundProcess
from pathlib import Path


class Native(ExecutionUnit):

    def __init__(self, idx, home_dir, record_data_dir, core_set, app: Application):
        super().__init__(idx=idx, home_dir=home_dir, app=app, type=ExecutionType.NATIVE)
        self.record_data_dir = record_data_dir
        self.core_set = core_set
        self.process = None

    def get_results_dir(self) -> str:
        return str(resolve_path(self.record_data_dir, use_in_container=False))

    def exec(self, command):
        change_dir = ""
        if self.app.cd:
            assert self.app.path is not None, "path is not set while change directory is requested!"
            change_dir = f" cd {self.app.path} && "
        inner_cmd = f"{self.CMD_WHILE_NOT_START} {change_dir} {command}"

        cmds = [
            "/bin/bash",
            "-c",
            inner_cmd,
        ]

        self.process = BackgroundProcess(
            name=self.name,
            cmds=cmds,
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
                    f"Native process {self.name} failed/crashed with return code {returncode}",
                    LogType.FATAL,
                )
                sys.exit(1)

    def stop(self):
        if self.process:
            self.process.force_stop()
