#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import re
import sys

"""
Convert an unixbench output into a set of key-value pairs.


Making it be recognized by CSB.
"""

benchmark_map = {
    # System Benchmarks
    "Dhrystone 2 using register variables": "dhry2reg",
    "Double-Precision Whetstone": "whetstone_double",
    "System Call Overhead": "syscall",
    "Pipe-based Context Switching": "context1",
    "Pipe Throughput": "pipe",
    "Process Creation": "spawn",
    "Execl Throughput": "execl",

    "File Read 256 bufsize 500 maxblocks": "fsread256",
    "File Read 1024 bufsize 2000 maxblocks": "fsread1024",
    "File Read 4096 bufsize 8000 maxblocks": "fsread4096",

    "File Write 256 bufsize 500 maxblocks": "fswrite256",
    "File Write 1024 bufsize 2000 maxblocks": "fswrite1024",
    "File Write 4096 bufsize 8000 maxblocks": "fswrite4096",

    "File Copy 1024 bufsize 2000 maxblocks": "fscopy1024",
    "File Copy 256 bufsize 500 maxblocks": "fscopy256",
    "File Copy 4096 bufsize 8000 maxblocks": "fscopy4096",

    "Shell Scripts (1 concurrent)": "shell1",
    "Shell Scripts (8 concurrent)": "shell8",
    "Shell Scripts (16 concurrent)": "shell16",

    # Graphics Benchmarks
    "2D graphics: rectangles": "2d_rects",
    "2D graphics: lines": "2d_lines",
    "2D graphics: circles": "2d_circle",
    "2D graphics: ellipses": "2d_ellipse",
    "2D graphics: polygons": "2d_shapes",
    "2D graphics: aa polygons": "2d_aashapes",
    "2D graphics: complex polygons": "2d_polys",
    "2D graphics: text": "2d_text",
    "2D graphics: images and blits": "2d_blit",
    "2D graphics: windows": "2d_window",
    "3D graphics: gears": "ubgears",

    # Non-Index Benchmarks
    "C Compiler Throughput (gcc)": "C",
    "Arithoh": "arithoh",
    "Arithmetic Test (short)": "short",
    "Arithmetic Test (int)": "int",
    "Arithmetic Test (long)": "long",
    "Arithmetic Test (float)": "float",
    "Arithmetic Test (double)": "double",
    "Dc: sqrt(2) to 99 decimal places": "dc",
    "Recursion Test -- Tower of Hanoi": "hanoi",
    "Grep a large file (system's grep)": "grep",
    "Exec System Call Overhead": "sysexec",
}

def parse_sysbench(text):

    results = {}

    re_key_value = re.compile(r"([\d\.]+)\s+(lpm|lps|KBps|MWIPS|score)")

    for ln in text.splitlines():
        for key, var in benchmark_map.items():
            if var in results:
                continue

            if ln.startswith(key):
                if match := re_key_value.search(ln):
                    results[var] = match.group(1)

    output = []
    for key, value in results.items():
        output.append(f"{key}={value}")

    return output


if __name__ == "__main__":
    text = sys.stdin.read().strip()
    if not text:
        sys.exit("No input received from STDIN.")

    results = parse_sysbench(text)

    print(";".join(results))
