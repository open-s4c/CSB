# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.22)

project(
    CSB
    LANGUAGES C
    VERSION 0.1.0
    DESCRIPTION "CSB: Container Scalability Benchmarks")

option(CSB_BM_GENERATOR "Turns bm-generator ON/OFF" OFF)
include(CTest)
add_subdirectory(bench)
if(CSB_BM_GENERATOR)
    add_subdirectory(bm-generator)
endif(CSB_BM_GENERATOR)

set(HELPERS ${CMAKE_SOURCE_DIR}/helpers)

# ##############################################################################
# Add license-check target
# ##############################################################################
add_custom_target(
    license-check
    COMMAND ${HELPERS}/license-check.sh
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
# ##############################################################################
# Add clang-format-apply target
# ##############################################################################
set(CLANG_STYLE_FILE ${HELPERS}/.clang-format)
set(CLANG_FMT_CMD ${HELPERS}/clang-format.sh)
add_custom_target(
    clang-format-apply
    COMMAND env STYLE=${CLANG_STYLE_FILE} SILENT=true ${CLANG_FMT_CMD}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_dependencies(clang-format-apply license-check)
# ##############################################################################
# Add cmake-format-apply target
# ##############################################################################
set(CMAKE_FMT_CMD ${HELPERS}/cmake-format.sh ${CMAKE_SOURCE_DIR})
set(CMAKE_STYLE_FILE ${HELPERS}/.cmake-format)
add_custom_target(cmake-format-apply COMMAND env STYLE=${CMAKE_STYLE_FILE}
                                             SILENT=true ${CMAKE_FMT_CMD})
add_dependencies(cmake-format-apply license-check)
# ##############################################################################
# Add git-diff-check target
# ##############################################################################
add_custom_target(git-diff-check COMMAND git --no-pager diff --exit-code)
# ##############################################################################
# Add json-format-apply target
# ##############################################################################
add_custom_target(
    json-format-apply
    COMMAND bash -c ${HELPERS}/json-format.sh ${CMAKE_SOURCE_DIR}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# ##############################################################################
# Add external benchmark setup targets
# ##############################################################################
set(EXTERNAL_SETUP ${CMAKE_SOURCE_DIR}/scripts/bm-external/setup.sh)
add_custom_target(
    external-tools
    COMMAND ${EXTERNAL_SETUP} --all
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    USES_TERMINAL VERBATIM)
add_custom_target(
    external-tools-check
    COMMAND ${EXTERNAL_SETUP} --check
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    USES_TERMINAL VERBATIM)
foreach(EXTERNAL_TOOL fio stress-ng byte-unixbench will-it-scale sysbench)
    add_custom_target(
        external-${EXTERNAL_TOOL}
        COMMAND ${EXTERNAL_SETUP} ${EXTERNAL_TOOL}
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        USES_TERMINAL VERBATIM)
endforeach()
