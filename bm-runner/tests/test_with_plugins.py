# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from pathlib import Path

from bm_utils import ensure_exists
from bm_container import Container
from bm_native import Native
from config.application import Application


def csb_dir() -> Path:
    return Path(os.getcwd()).parent


# Necessary arguments for Execution Unit that do not interfere with this test

image = "ubuntu"
core_set = "0"
work_dir = Path("/home")


def get_command(
    results_dir,
    args,
    index,
    plugins="strace -o {res_dir}/test-container{index}.log",
    is_process=True,
):
    app = Application("ls", args=args)

    if is_process:
        eu = Native(
            app=app,
            idx=0,
            record_data_dir=results_dir,
            home_dir=work_dir,
            core_set=core_set,
        )
    else:
        eu = Container(
            app=app,
            idx=0,
            record_data_dir=results_dir,
            image=image,
            home_dir=work_dir,
            core_set=core_set,
        )

    return eu.app.get_cmd(
        plugins_cmds=plugins,
        threads=1,
        duration=1,
        noise=0,
        port=0,
        index=index,
        n_units=2,
        work_dir=work_dir,
        homedir=str(work_dir),
        res_dir=eu.get_results_dir(),
    )


def test_results_dir_container():
    input_path = "results"
    out = get_command(input_path, "", 0, is_process=False)

    homedir = csb_dir()
    expected_out = "strace -o /home/results/test-container0.log ls"
    not_expected_out = f"strace -o {homedir}/results/test-container0.log ls"

    assert expected_out == out and not_expected_out != out


def test_results_dir_process():
    input_path = "results"
    out = get_command(input_path, "", 0)

    homedir = csb_dir()
    expected_out = f"strace -o {homedir}/results/test-container0.log ls"
    not_expected_out = "strace -o /home/results/test-container0.log ls"

    assert expected_out == out and not_expected_out != out


def test_results_dir_with_args_process():
    input_path = "results"
    out = get_command(input_path, "subdir/ myfile", 0)

    homedir = csb_dir()
    expected_out = f"strace -o {homedir}/results/test-container0.log ls subdir/ myfile"
    not_expected_out = "strace -o /home/results/test-container0.log ls subdir/ myfile"

    assert expected_out == out and not_expected_out != out


def test_results_dir_with_args_container():
    input_path = "results"
    out = get_command(input_path, "subdir/ myfile", 0, is_process=False)

    homedir = csb_dir()
    expected_out = "strace -o /home/results/test-container0.log ls subdir/ myfile"
    not_expected_out = f"strace -o {homedir}/results/test-container0.log ls subdir/ myfile"

    assert expected_out == out and not_expected_out != out


def test_results_dir_with_script_process():
    input_path = "results"
    input_plugin = "collect_strace.sh"

    input_plugin = ensure_exists(input_plugin, dir="scripts/plugins")
    out = get_command(input_path, "subdir/ myfile", 0, plugins=input_plugin)
    expected_out = "scripts/plugins/collect_strace.sh ls subdir/ myfile"

    assert expected_out == out


def test_results_dir_with_script_container():
    input_path = "results"
    input_plugin = "collect_strace.sh"

    input_plugin = ensure_exists(input_plugin, dir="scripts/plugins")
    out = get_command(input_path, "subdir/ myfile", 0, plugins=input_plugin, is_process=False)
    expected_out = "scripts/plugins/collect_strace.sh ls subdir/ myfile"

    assert expected_out == out
