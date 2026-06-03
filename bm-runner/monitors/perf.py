# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys
import subprocess
import glob
from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from config.env_config import EnvUniversalConfig, UniversalConfig


class FlameGraph(Monitor):
    FG_PATH_ENV_VAR_NAME = "FLAMEGRAPH"
    ARM_SPE_PERIOD_ENV_VAR_NAME = "CSB_ARM_SPE_PERIOD"
    ARM_SPE_DEVICE_GLOB = "/sys/bus/event_source/devices/arm_spe*"
    ARM_SPE_MIN_INTERVAL_GLOB = "/sys/bus/event_source/devices/arm_spe*/caps/min_interval"
    ARM_SPE_FALLBACK_MIN_INTERVAL = 1024
    ARM_SPE_PERIOD_MULTIPLIER = 10

    def __init__(self, output_dir: str, args: list[str] = ["-a"]):
        super().__init__(dir=output_dir, args=args)
        if self.arm_spe_enabled() and not self.arm_spe_supported():
            bm_log(
                "arm_spe PMU is not available; skipping arm_spe perf event.",
                LogType.WARNING,
            )
        cmds = self.perf_record_cmd(args)
        self.perf = BackgroundProcess(
            name="perf",
            out_dir=output_dir,
            cmds=cmds,
            requires=["perf"],
            pin=self.get_cpus(),
        )
        self.fg_path = os.getenv(self.FG_PATH_ENV_VAR_NAME)
        if self.fg_path is None:
            bm_log(
                f"{self.FG_PATH_ENV_VAR_NAME} environment variable is not set. Set it to the path of `stackcollapse-perf.pl` and try again. Or remove perf from monitors",
                LogType.FATAL,
            )
            sys.exit(1)

    @classmethod
    def perf_record_cmd(cls, args: list[str]) -> list[str]:
        cmds = ["sudo", "perf", "record", "-g"]
        if not cls.arm_spe_enabled_and_supported():
            cmds.extend(["-F", "99"])
        for event in cls.perf_events():
            cmds.extend(["-e", event])
        cmds.extend(args)
        return cmds

    @classmethod
    def perf_events(cls) -> list[str]:
        events = ["cycles"]
        if cls.arm_spe_enabled_and_supported():
            events.append(cls.arm_spe_event())
        return events

    @classmethod
    def arm_spe_enabled_and_supported(cls) -> bool:
        return cls.arm_spe_enabled() and cls.arm_spe_supported()

    @classmethod
    def arm_spe_enabled(cls) -> bool:
        return EnvUniversalConfig.is_on(UniversalConfig.CSB_ARM_SPE)

    @classmethod
    def arm_spe_supported(cls) -> bool:
        for device in glob.glob(cls.ARM_SPE_DEVICE_GLOB):
            if not os.path.isdir(device):
                continue
            try:
                with open(os.path.join(device, "type"), "r") as type_file:
                    int(type_file.read().strip(), 0)
            except (OSError, ValueError):
                continue
            else:
                return True
        return False

    @classmethod
    def arm_spe_event(cls) -> str:
        return f"arm_spe/jitter=1,period={cls.arm_spe_period()}/"

    @classmethod
    def arm_spe_period(cls) -> int:
        env_period = os.getenv(cls.ARM_SPE_PERIOD_ENV_VAR_NAME)
        if env_period is not None:
            period = 0
            try:
                period = int(env_period)
            except ValueError:
                bm_log(
                    f"{cls.ARM_SPE_PERIOD_ENV_VAR_NAME} must be a positive integer.",
                    LogType.FATAL,
                )
                sys.exit(1)
            if period > 0:
                return period
            bm_log(
                f"{cls.ARM_SPE_PERIOD_ENV_VAR_NAME} must be a positive integer.",
                LogType.FATAL,
            )
            sys.exit(1)

        return cls.arm_spe_min_interval() * cls.ARM_SPE_PERIOD_MULTIPLIER

    @classmethod
    def arm_spe_min_interval(cls) -> int:
        intervals = []
        for path in glob.glob(cls.ARM_SPE_MIN_INTERVAL_GLOB):
            try:
                with open(path, "r") as min_interval_file:
                    interval = int(min_interval_file.read().strip(), 0)
            except (OSError, ValueError):
                continue
            if interval > 0:
                intervals.append(interval)
        if intervals:
            return max(intervals)
        return cls.ARM_SPE_FALLBACK_MIN_INTERVAL

    def start(self):
        # Launch perf in the background
        self.perf.start()

    def collect_results(self):
        return ""

    def __generate_flamegraph(self, errfile):
        """
        Generates flamegraph on perf.data in output dir
        """
        # run perf script on the perf.data in results folder
        perf = subprocess.Popen(
            ["sudo", "perf", "script", "-i", "perf.data"],
            cwd=self.dir,
            stdout=subprocess.PIPE,
            stderr=errfile,
        )
        # run stack collapse on the output of perf record
        stacks_file = os.path.join(self.dir, "flamegraph.stacks")
        with open(stacks_file, "w") as stacks:
            try:
                subprocess.run(
                    [f"{self.fg_path}/stackcollapse-perf.pl"],
                    stdin=perf.stdout,
                    stdout=stacks,
                    stderr=errfile,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                bm_log(f"Failed to generate flamegraph: {e}", LogType.ERROR)
            finally:
                if perf.stdout:
                    perf.stdout.close()
        svg = os.path.join(self.dir, "flamegraph.svg")
        # run flamegraph on the output of stackcollapse
        # and save the output in svg
        with open(svg, "w") as svg, open(stacks_file, "r") as stacks:
            try:
                subprocess.run(
                    [f"{self.fg_path}/flamegraph.pl"],
                    stdin=stacks,
                    stdout=svg,
                    stderr=errfile,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                bm_log(f"Failed to generate flamegraph: {e}", LogType.ERROR)

    def stop(self):
        if self.perf is not None:
            self.perf.stop()
            with open(os.path.join(self.dir, "flamegraph.errors"), "w") as errfile:
                self.__generate_flamegraph(errfile)
