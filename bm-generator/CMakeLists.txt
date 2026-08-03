# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set(SYZKALLER syzkaller)
set(SYZKALLER_SOURCE_DIR ${CMAKE_SOURCE_DIR}/deps/syzkaller)
add_custom_target(${SYZKALLER})
find_program(GO_EXECUTABLE go)

if(NOT GO_EXECUTABLE)
    message(FATAL_ERROR "Go compiler not found. Please install Go.")
endif()

message(STATUS "Go found at: ${GO_EXECUTABLE}")

# Tools we want to build of syzkaller
set(TOOLS trace2syz prog2c extraction progreduce)
# Build each tool
foreach(TOOL ${TOOLS})
    add_custom_target(
        ${TOOL}
        COMMAND make ${TOOL}
        WORKING_DIRECTORY "${SYZKALLER_SOURCE_DIR}")
    add_dependencies(${SYZKALLER} ${TOOL})
endforeach(TOOL in ${TOOLS})

# Save syzkaller path to a file.
file(WRITE "${CMAKE_BINARY_DIR}/syzkaller-path.txt" "${SYZKALLER_SOURCE_DIR}")
add_subdirectory(templates)
