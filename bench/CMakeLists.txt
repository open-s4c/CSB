# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

add_library(CSB INTERFACE)

target_include_directories(
    CSB INTERFACE "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
                  "$<INSTALL_INTERFACE:include>")

option(CSB_ADDRESS_SANITIZER "Compile with -fsanitize=address" "off")
option(CSB_THREAD_SANITIZER "Compile with -fsanitize=thread" "off")

if(CSB_ADDRESS_SANITIZER)
    target_compile_options(CSB INTERFACE -fsanitize=address,undefined)
    target_link_options(CSB INTERFACE -fsanitize=address,undefined)
elseif(CSB_THREAD_SANITIZER)
    target_compile_options(CSB INTERFACE -fsanitize=thread)
    target_link_options(CSB INTERFACE -fsanitize=thread)
endif()

# search subdirectories as well
file(GLOB_RECURSE TARGETS CONFIGURE_DEPENDS targets/*.h)
# exclude files under syz
list(FILTER TARGETS EXCLUDE REGEX ".*/syz/.*")

set(BM_DEFS _GNU_SOURCE)
set(DEFAULT_PORT 5000)
set(UNITS 1)
set(BM_PARAM
    "-t=${UNITS}"
    "-n=0" # noise
    "-d=2" # duration
    "-p=${DEFAULT_PORT}" # port
    "-op0=1024" # op0 freq in /1024
)

set(BM_PARAM_bm_server_redis
    "-t=1"
    "-n=0" # noise
    "-d=1" # duration
    "-p=${DEFAULT_PORT}" # port
    "-op0=500" # op0 freq in /1024
    "-op1=524" # op1 freq in /1024
)

set(BM_PARAM_bm_empty
    "-t=12"
    "-n=0" # noise
    "-d=1" # duration
    "-p=0" # port
    "-op0=1024" # op0 freq in /1024
)

set(BM_FILE benchmark.c)

foreach(target IN ITEMS ${TARGETS})
    get_filename_component(bm_target_prefix ${target} NAME_WLE)
    get_filename_component(PARENT "${target}" DIRECTORY)

    if("${PARENT}" STREQUAL "${CMAKE_CURRENT_SOURCE_DIR}/targets")
        set(TARGET_PREFIX "")
    else()
        # get direct parent directory name
        get_filename_component(PARENT_STRIPPED "${PARENT}" NAME)
        string(TOLOWER "${PARENT_STRIPPED}_" TARGET_PREFIX)
    endif()

    set(bm_target_name "\"${target}\"")

    set(TEST_CASE "${TARGET_PREFIX}${bm_target_prefix}")

    string(TOLOWER ${TEST_CASE} TEST_CASE)

    add_executable(${TEST_CASE} ${BM_FILE})

    target_link_libraries(${TEST_CASE} pthread CSB)

    target_compile_definitions(${TEST_CASE} PUBLIC ${BM_DEFS}
                                                   BM_TARGET=${bm_target_name})

    target_compile_options(${TEST_CASE} PUBLIC -g -O2 -Wall -Werror
                                               -Wno-unused-function)
    # use -fno-var-tracking to speed up compilation of big auto-generated test
    # cases
    if(bm_target_prefix MATCHES ".*min_.*")
        target_compile_options(${TEST_CASE} PRIVATE "-fno-var-tracking")
    endif()

    if(DEFINED BM_PARAM_${bm_target_prefix})
        set(PARAMS ${BM_PARAM_${bm_target_prefix}})
    else()
        set(PARAMS ${BM_PARAM})
    endif()

    set(META_FILE "${PARENT}/syz/${bm_target_prefix}.meta")
    if(EXISTS "${META_FILE}")
        # This test requires networking we need to prelaunch a client that
        # communicates with it TODO: generalize for server case
        set(SETUP_CLIENT ${TEST_CASE}_CLIENT)
        set(SCRIPT_PATH
            "${PROJECT_SOURCE_DIR}/scripts/plugins/generic-network-client.sh")
        set(CLIENT_BIN "${CMAKE_CURRENT_BINARY_DIR}/network/client")
        set(CLIENT_CMD
            "${SCRIPT_PATH} ${DEFAULT_PORT} ${UNITS} ${CLIENT_BIN} ${META_FILE}"
        )
        add_test(NAME ${SETUP_CLIENT}
                 COMMAND bash -c "(${CLIENT_CMD} > /dev/null 2>&1 &)")
        set_tests_properties(${SETUP_CLIENT} PROPERTIES FIXTURES_SETUP
                                                        ${SETUP_CLIENT})
        add_test(NAME ${TEST_CASE} COMMAND ${TEST_CASE} ${PARAMS})
        set_tests_properties(${TEST_CASE} PROPERTIES FIXTURES_REQUIRED
                                                     ${SETUP_CLIENT})
    else()
        # add the bm as a test
        add_test(NAME ${TEST_CASE} COMMAND ${TEST_CASE} ${PARAMS})
    endif()
endforeach()

add_subdirectory(network)
