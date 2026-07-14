/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
/**
 * @file bm_empty.h
 * @brief This benchmark is only for testing and checking the overhead of the
 * benchmark
 *
 */
#include <CSB/bm_target.h>
#include <CSB/bm_helper.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define NOP_PER_OP   100U
#define MAX_NAME_LEN 20U
#define NUM_SYSCALLS 1U

static inline char *
bm_target_get_name(void)
{
    return "bm_empty";
}

static inline size_t
bm_target_op_count(void)
{
    return NUM_SYSCALLS;
}

struct thread_ctx_s {
    size_t tid;
};

static inline void
bm_target_get_op_name(char *out_str, const size_t len, size_t op_id)
{
    assert(len >= MAX_NAME_LEN && "output buffer too small");
    sprintf(out_str, "op0_nop");
    V_UNUSED(len, op_id);
}

static inline void
bm_target_init(uint16_t port, size_t num_threads)
{
    V_UNUSED(num_threads);
}

static inline void
bm_target_reg(thread_ctx_t *ctx, size_t tid)
{
    assert(ctx);
    ctx->tid = tid;
}

static inline bm_op_res_t
bm_dispatch_operation(thread_ctx_t *ctx, size_t op_id)
{
    bm_op_res_t res = {.op_count = 1, .succ_count = 1};
    bm_generate_noise(NOP_PER_OP, false);
    return res;
}

static inline void
bm_target_dereg(thread_ctx_t *ctx, size_t tid)
{
    V_UNUSED(ctx, tid);
}

static inline void
bm_target_destroy(size_t num_threads)
{
    V_UNUSED(num_threads);
}

static inline void
bm_target_extra_info(char *buf, size_t len)
{
    V_UNUSED(buf, len);
}
