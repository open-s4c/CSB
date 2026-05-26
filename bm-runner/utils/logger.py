# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from datetime import datetime
from enum import Enum
import sys


class LogType(str, Enum):
    FATAL = "\033[1;95m"
    ERROR = "\033[1;31m"
    WARNING = "\033[1;33m"
    DEBUG = "\033[1;39m"
    INFO = "\033[1;32m"


def bm_log(msg: str, t: LogType = LogType.DEBUG):
    RESET: str = "\033[0m"
    current_time = datetime.now().strftime("%H:%M:%S.%f")
    match t:
        case LogType.ERROR | LogType.FATAL:
            file = sys.stderr
        case _:
            file = sys.stdout
    print(f"{t.value}{current_time} [{t.name}] {msg}{RESET}", file=file)
