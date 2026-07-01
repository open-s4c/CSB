# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from enum import Enum
from typing import Optional


class UniversalConfig(str, Enum):
    """
    CSB bm-runner has universal configuration that can overwrite default
    behavior and JSON config values. These are set via environment variables,
    and are read at runtime.

    Members
    ----------
    CSB_NO_CLEAN_BENCH: When set to `true`, it disables the cleaning of the build folder of builtin benchmarks.
    CSB_ANALYZE: When set to `false`, it disables the analysis monitors.
    CSB_PIN_MONITORS: When set to `true`, all monitors will be pinned to a specific CPU.
    CSB_NO_BUILD_BENCH: when set to `true`, it skips building *all* builtin benchmarks.
    CSB_RESULTS_GROUP: when set to <dir-name>, bm-runner dumps all results under results/<dir-name>.
    CSB_ARM_SPE: when set to `true`, it checks of availability of arm_spe perf event and captures these events.
    CSB_BPFTRACE_FILTER: can be used to overwrite the default filter of bpftrace `/ comm == "<comm>" /`. Note that `<comm>` is replaced by the first 15chars of the benchmark application name.
    """

    CSB_NO_CLEAN_BENCH = "CSB_NO_CLEAN_BENCH"
    CSB_ANALYZE = "CSB_ANALYZE"
    CSB_NO_BUILD_BENCH = "CSB_NO_BUILD_BENCH"
    CSB_PIN_MONITORS = "CSB_PIN_MONITORS"
    CSB_RESULTS_GROUP = "CSB_RESULTS_GROUP"
    CSB_ARM_SPE = "CSB_ARM_SPE"
    CSB_BPFTRACE_FILTER = "CSB_BPFTRACE_FILTER"


class EnvUniversalConfig:
    DEFAULT_ENV_CONFIG: dict[UniversalConfig, bool] = {
        UniversalConfig.CSB_NO_CLEAN_BENCH: False,
        UniversalConfig.CSB_NO_BUILD_BENCH: False,
        UniversalConfig.CSB_PIN_MONITORS: False,
        UniversalConfig.CSB_ANALYZE: True,
        UniversalConfig.CSB_ARM_SPE: False,
    }
    TRUE_VALS: set[str] = {"true", "1", "yes", "on"}

    @staticmethod
    def __read_env_var(env_var: UniversalConfig) -> bool:
        value = os.getenv(env_var.value)
        if value is not None:
            return value.lower() in EnvUniversalConfig.TRUE_VALS
        return EnvUniversalConfig.DEFAULT_ENV_CONFIG[env_var]

    @staticmethod
    def is_on(env_var: UniversalConfig) -> bool:
        if env_var in EnvUniversalConfig.DEFAULT_ENV_CONFIG:
            return EnvUniversalConfig.__read_env_var(env_var)
        else:
            # handle non-boolean env-var(s) not ideal!
            return False

    @staticmethod
    def get(env_var: UniversalConfig) -> Optional[str]:
        return os.getenv(env_var.value)
