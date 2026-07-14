/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#ifndef BM_STATS_H
#define BM_STATS_H

#include <stdlib.h>
#include <stdint.h>
#include "bm_target.h"
#include "math.h"

#define STAT_OP_NAME_op_name_MAX_LEN 20
#define CACHELINE_SIZE               128U
#define ALIGNMENT_SIZE(x)                                                      \
    (((x) % CACHELINE_SIZE) == 0 ?                                             \
         (x) :                                                                 \
         ((((x) / CACHELINE_SIZE) + 1) * CACHELINE_SIZE))

typedef struct bm_op_stat_s {
    uint64_t succ_count;
    uint64_t count;
    uint64_t skipped_count;
    uint64_t sum;
    uint64_t min;
    uint64_t max;
} bm_op_stat_t;

typedef struct bm_thread_stat_s {
    /* array of ops */
    bm_op_stat_t *ops;
    size_t len;
} bm_thread_stat_t;

typedef struct bm_stat_s {
    /* array of threads */
    bm_thread_stat_t *threads;
    size_t len;
    uint64_t min_duration_clk;
    uint64_t max_duration_clk;
    uint64_t min_duration_ms;
    uint64_t max_duration_ms;
} bm_stat_t;

#define BM_PRINT_OP_STAT(_op_name_, _idx_, _fmt_, _stat_, _deli_)              \
    printf(                                                                    \
        "%s_%s="_fmt_                                                          \
        "%c",                                                                  \
        _op_name_, #_stat_, _stat_[_idx_], _deli_)

#define BM_PRINT_UNIV_STAT(_fmt_, _stat_, _deli_)                              \
    printf(                                                                    \
        "%s="_fmt_                                                             \
        "%c",                                                                  \
        #_stat_, _stat_, _deli_)

#define BM_PRINT_EXTRA_STAT(_stat_, _deli_) printf("%s%c", _stat_, _deli_)

static inline void
bm_stat_init(bm_stat_t *stats, size_t num_threads, size_t num_ops)
{
    assert(stats);
    stats->threads = aligned_alloc(
        CACHELINE_SIZE, ALIGNMENT_SIZE(num_threads * sizeof(bm_thread_stat_t)));
    memset(stats->threads, 0, num_threads * sizeof(bm_thread_stat_t));
    stats->len = num_threads;

    for (size_t i = 0; i < stats->len; i++) {
        /* calloc needed all var must be initialized to zero except for min */
        stats->threads[i].ops = aligned_alloc(
            CACHELINE_SIZE, ALIGNMENT_SIZE(num_ops * sizeof(bm_op_stat_t)));
        memset(stats->threads[i].ops, 0, num_ops * sizeof(bm_op_stat_t));
        stats->threads[i].len = num_ops;

        for (size_t op = 0; op < num_ops; op++) {
            stats->threads[i].ops[op].min = UINT64_MAX;
        }
    }
}

static inline void
bm_stat_destroy(bm_stat_t *stats)
{
    assert(stats);
    for (size_t i = 0; i < stats->len; i++) {
        free(stats->threads[i].ops);
    }
    free(stats->threads);
}

static inline void
bm_stat_add_op(bm_stat_t *stats, size_t tid, size_t op, bm_op_res_t result,
               uint64_t duration, bool skipped)
{
    bm_op_stat_t *op_stat = NULL;
    assert(stats);
    assert(tid < stats->len);
    assert(op < stats->threads[tid].len);

    op_stat = &stats->threads[tid].ops[op];
    if (skipped) {
        op_stat->skipped_count++;
    } else {
        op_stat->succ_count += result.succ_count;
        op_stat->sum += duration;
        op_stat->count += result.op_count;

        op_stat->max = VMAX(op_stat->max, duration);
        op_stat->min = VMIN(op_stat->min, duration);
    }
}

static inline void
bm_stat_add_spent_time(bm_stat_t *stats, uint64_t min_duration_clk,
                       uint64_t max_duration_clk, uint64_t min_duration_ms,
                       uint64_t max_duration_ms)
{
    stats->min_duration_clk = min_duration_clk;
    stats->max_duration_clk = max_duration_clk;
    stats->min_duration_ms  = min_duration_ms;
    stats->max_duration_ms  = max_duration_ms;
}

static inline void
bm_print_stats(bm_stat_t *stats, char delimiter, const size_t op_len)
{
    assert(stats);
    char op_name[STAT_OP_NAME_op_name_MAX_LEN] = {0};
    /* stats per operation type */
    uint64_t max[op_len]; /* max operation time */
    uint64_t min[op_len]; /* min operation time */
    uint64_t sum[op_len]; /* sum of time for all operations of the same type */
    uint64_t count[op_len];      /* count of operations of a certain type */
    uint64_t succ_count[op_len]; /* count of successful (returned true)
                                     operations of a certain type */
    uint64_t skipped_count[op_len];
    double avg[op_len];          /* average operation time of certain type */
    double succ_percent[op_len]; /* success percent of operations */

    /* universal stats regardless of operation type */
    uint64_t univ_max           = 0;
    uint64_t univ_min           = UINT64_MAX;
    uint64_t univ_sum           = 0;
    uint64_t univ_count         = 0;
    uint64_t univ_succ_count    = 0;
    uint64_t univ_skipped_count = 0;
    double univ_succ_percent    = 0;
    double univ_avg             = 0;
    bm_thread_stat_t *thrd_stat = NULL;

    /* init op stats arrays */
    for (size_t op = 0; op < op_len; op++) {
        max[op]           = 0;
        min[op]           = UINT64_MAX;
        sum[op]           = 0;
        count[op]         = 0;
        avg[op]           = 0;
        succ_percent[op]  = 0;
        succ_count[op]    = 0;
        skipped_count[op] = 0;
    }

    /* collect stats from all threads */
    for (size_t i = 0; i < stats->len; i++) {
        thrd_stat = &stats->threads[i];
        assert(thrd_stat->len == op_len);

        for (size_t op = 0; op < op_len; op++) {
            max[op] = VMAX(max[op], thrd_stat->ops[op].max);
            min[op] = VMIN(min[op], thrd_stat->ops[op].min);
            sum[op] += thrd_stat->ops[op].sum;
            count[op] += thrd_stat->ops[op].count;
            succ_count[op] += thrd_stat->ops[op].succ_count;
            skipped_count[op] += thrd_stat->ops[op].skipped_count;
        }
    }

    char *algo_name = bm_target_get_name();
    char info[1000] = {0};
    BM_PRINT_UNIV_STAT("%s", algo_name, delimiter);

    bm_target_extra_info(info, sizeof(info));
    if (strlen(info) > 0) {
        BM_PRINT_EXTRA_STAT(info, delimiter);
    }

    /* collect universal stats, print operation stats */
    for (size_t op = 0; op < op_len; op++) {
        univ_max = VMAX(univ_max, max[op]);
        univ_min = VMIN(univ_min, min[op]);
        univ_sum += sum[op];
        univ_count += count[op];
        univ_succ_count += succ_count[op];
        univ_skipped_count += skipped_count[op];

        /* calculate operation average time */
        if (count[op] != 0) {
            avg[op] = ((double)sum[op]) / ((double)count[op]);
            succ_percent[op] =
                ((double)succ_count[op] * 100U) / ((double)count[op]);
        }

        bm_target_get_op_name(op_name, STAT_OP_NAME_op_name_MAX_LEN, op);

        /* overwrite with zero if no real min was found */
        min[op] = ((min[op] == UINT64_MAX) ? 0 : min[op]);
        BM_PRINT_OP_STAT(op_name, op, "%lu", max, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%lu", min, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%lu", sum, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%lu", count, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%lu", succ_count, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%lu", skipped_count, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%.2f", avg, delimiter);
        BM_PRINT_OP_STAT(op_name, op, "%.2f", succ_percent, delimiter);
    }

    /* calculate universal average */
    if (univ_count != 0) {
        univ_avg = ((double)univ_sum) / ((double)univ_count);
        univ_succ_percent =
            ((double)univ_succ_count * 100U) / ((double)univ_count);
    }

    /* print universal stats */
    BM_PRINT_UNIV_STAT("%zu", univ_max, delimiter);
    BM_PRINT_UNIV_STAT("%zu", univ_min, delimiter);
    BM_PRINT_UNIV_STAT("%zu", univ_sum, delimiter);
    BM_PRINT_UNIV_STAT("%zu", univ_count, delimiter);
    BM_PRINT_UNIV_STAT("%zu", univ_succ_count, delimiter);
    BM_PRINT_UNIV_STAT("%zu", univ_skipped_count, delimiter);
    BM_PRINT_UNIV_STAT("%.2f", univ_avg, delimiter);
    BM_PRINT_UNIV_STAT("%.2f", univ_succ_percent, delimiter);

    // calculate #of operations per milliseconds
    double throughput_max =
        (double)(univ_count * 1000.0f) / (double)(stats->min_duration_ms);
    double throughput_min =
        (double)(univ_count * 1000.0f) / (double)(stats->max_duration_ms);
    uint64_t ticks_to_ms     = calc_ticks_in_ms();
    double throughput_min_ts = (double)(univ_count * 1000.0f * ticks_to_ms) /
                               (double)(stats->max_duration_clk);
    double throughput_max_ts = (double)(univ_count * 1000.0f * ticks_to_ms) /
                               (double)(stats->min_duration_clk);

    BM_PRINT_UNIV_STAT("%.8f", throughput_max, delimiter);
    BM_PRINT_UNIV_STAT("%.8f", throughput_min, delimiter);
    BM_PRINT_UNIV_STAT("%.8f", throughput_max_ts, delimiter);
    BM_PRINT_UNIV_STAT("%.8f", throughput_min_ts, delimiter);
    BM_PRINT_UNIV_STAT("%zu", ticks_to_ms, delimiter);

    uint64_t duration_max_ms  = stats->max_duration_ms;
    uint64_t duration_max_clk = stats->max_duration_clk;
    uint64_t duration_min_ms  = stats->min_duration_ms;
    uint64_t duration_min_clk = stats->min_duration_clk;

    BM_PRINT_UNIV_STAT("%zu", duration_max_ms, delimiter);
    BM_PRINT_UNIV_STAT("%zu", duration_max_clk, delimiter);
    BM_PRINT_UNIV_STAT("%zu", duration_min_ms, delimiter);
    BM_PRINT_UNIV_STAT("%zu", duration_min_clk, delimiter);

    uint64_t sys_time   = 0;
    uint64_t usr_time   = 0;
    uint64_t max_rss_kb = 0;
    get_usr_sys_time(&sys_time, &usr_time, &max_rss_kb);
    BM_PRINT_UNIV_STAT("%lu", sys_time, delimiter);
    BM_PRINT_UNIV_STAT("%lu", usr_time, delimiter);
    BM_PRINT_UNIV_STAT("%lu", max_rss_kb, delimiter);
}

#endif
