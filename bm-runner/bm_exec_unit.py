# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from abc import abstractmethod

from config.application import Application
from config.benchmark import ExecutionType, EXECUTION_TYPE_PREFIX
from bm_utils import resolve_path


class ExecutionUnit:
    START_FILE = f"{Application.BUILTIN_APP_DIR}/start"
    RETRY_COUNT = 16 * 60  # 16 mins
    NOFILE_LIMIT = 1024
    CMD_WHILE_NOT_START = f"for i in $(seq 1 $((10 * {RETRY_COUNT}))); do if [ -e {START_FILE} ]; then break; fi; sleep 0.1; done;"

    def __init__(self, idx, home_dir, app: Application, type: ExecutionType):
        self.app = app
        self.idx = idx
        self.type = type
        self.home_dir = home_dir
        self.name = EXECUTION_TYPE_PREFIX[type]
        self.name += f"{idx:03d}_{app.name}"
        self.output_file = os.path.join(Application.BUILTIN_APP_DIR, self.name)
        self.err_file = os.path.join(Application.BUILTIN_APP_DIR, f"{self.name}_err")

    @abstractmethod
    def get_results_dir(self) -> str:
        pass

    @abstractmethod
    def exec(self, command: str) -> bool:
        return False

    @abstractmethod
    def wait(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def get_output(self) -> str:
        line = open(resolve_path(self.output_file), "r").read()
        # If there is an adapter, it means that
        # the applications' output needs to be transformed
        # after collection. This is important to have
        # a format complying to dict `key=val;...`
        if self.app.adapter is not None:
            line = self.app.adapter.adapt(line)
        return f"execution_unit={self.name};app={self.app.name};{line}"
