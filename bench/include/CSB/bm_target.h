/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#ifndef BM_TARGET_H
#define BM_TARGET_H

// An on-stack structure passed to every dispatched operation.
struct thread_ctx_s;
typedef struct thread_ctx_s thread_ctx_t;

typedef struct bm_op_res_s {
    uint64_t op_count;
    uint64_t succ_count;
} bm_op_res_t;

typedef bool (*bm_target_op)(size_t);

static inline char *bm_target_get_name(void);

static inline size_t bm_target_op_count(void);

static inline void bm_target_get_op_name(char *out_str, const size_t len,
                                         size_t op_id);

static inline void bm_target_init(uint16_t port, size_t num_threads);

static inline void bm_target_reg(thread_ctx_t *ctx, size_t tid);

static inline bm_op_res_t bm_dispatch_operation(thread_ctx_t *ctx,
                                                size_t op_id);

static inline void bm_target_dereg(thread_ctx_t *ctx, size_t tid);

static inline void bm_target_destroy(size_t num_threads);

static inline void bm_target_extra_info(char *, size_t);

#ifdef BM_TARGET
    #include BM_TARGET
#else
    #error "undefined target"
#endif

#endif
