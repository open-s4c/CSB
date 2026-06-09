# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
from typing import Optional
from pathlib import Path
from bm_utils import ensure_exists
from bm_utils import resolve_path


class Adapter(dict):
    DEFAULT_DIR = "scripts/adapters"  # relative to the project root

    def __init__(self, name: str, path: Optional[Path] = None):
        """
        Adapters used to transform the output of an external benchmark into
        the format understood by the framework: a line of `<key>:<val>;`
        pairs e.g. `throughput:1000;latency:20;`.
        If an adapter is used the output of the benchmark is piped
        to the adapter script. See scripts/adapters for examples.

        Parameters
        ----------
        name: str
            Adapter script filename.
        path: Optional[Path]
            The dir where the script exists. Required if it does not exist
            system wide, or under script/adapters.
        -
        """
        super().__init__(name=name, path=path)
        self.default_abs_dir = resolve_path(self.DEFAULT_DIR)
        self.fname = ensure_exists(name, dir=self.default_abs_dir if path is None else path)

    def adapt(self, output: str) -> str:
        # This is a blocking call
        result = subprocess.run([self.fname], text=True, capture_output=True, input=output)
        return result.stdout
