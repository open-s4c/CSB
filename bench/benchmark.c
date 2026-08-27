/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#include <CSB/thread_launcher.h>
#include <CSB/time.h>
#include <CSB/bm_params.h>
#include <CSB/bm_error.h>
#include <CSB/bm_stats.h>
#include <CSB/bm_helper.h>
#include <CSB/bm_target.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#define DISTRIBUTION_BOUND 1024
#define BM_NOFILE_LIMIT    1024
#define BM_PRINT_DELIMITER ';'

/**
 * parameters
 * @TODO: do we need a calibration parameter?
 *
 *
 * stats
 * @TODO: collect custom stats e.g. remaining unfreed nodes
 *
 */

atomic_bool g_stop = false;
pthread_barrier_t g_start_barrier;
pthread_barrier_t g_stop_barrier;
bm_stat_t g_stats;
bm_params_t g_params;
size_t g_ops[DISTRIBUTION_BOUND];

/* functions prototypes */
void bm_env_prepare(void);
void bm_phase_warmup(void);
void bm_phase_run(void);
void bm_phase_conclude(void);
void bm_phase_cooldown(void);
static void bm_nofile_limit_set(void);

int
main(int argc, char *argv[])
{
    bm_error_t ret =
        bm_params_extract(argc, argv, &g_params, bm_target_op_count());
    if (ret != BM_ERR_NONE) {
        fprintf(stderr, "Error in param extraction %d\n", ret);
        return ret;
    }
    bm_env_prepare();
    bm_phase_warmup();
    bm_phase_run();
    bm_phase_conclude();
    bm_phase_cooldown();
    return BM_ERR_NONE;
}

bool
stop(void)
{
    return atomic_load_explicit(&g_stop, memory_order_relaxed);
}

void *
run(void *args)
{
    size_t tid             = (size_t)(uintptr_t)args;
    bool skip              = false;
    uint64_t op_start_time = 0;
    uint64_t op_end_time   = 0;
    uint64_t op_time       = 0;
    size_t i               = 0;
    size_t op              = 0;
    thread_ctx_t ctx       = {0};

    unsigned int cpu;

    /* threads start at different positions */
    i = DISTRIBUTION_BOUND * tid / g_params.num_threads;

    getcpu(&cpu, NULL);

    bm_target_reg(&ctx, tid);
    pthread_barrier_wait(&g_start_barrier);

    while (!stop()) {
        /* pick an operation to perform */
        op = g_ops[i % DISTRIBUTION_BOUND];

        op_start_time      = read_time_stamp_counter();
        bm_op_res_t result = bm_dispatch_operation(&ctx, op);
        op_end_time        = read_time_stamp_counter();
        op_time            = op_end_time - op_start_time;

        // skip this stat if the thread was preempted mid operation
        skip = false;
        bm_stat_add_op(&g_stats, tid, op, result, op_time, skip);

        bm_generate_noise(g_params.max_noise, false);
        i++;
    }

    pthread_barrier_wait(&g_stop_barrier);

    bm_target_dereg(&ctx, tid);

    return NULL;
}

void
bm_env_prepare(void)
{
    bm_nofile_limit_set();

    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR) {
        perror("Failed to ignore sigpipe.");
        exit(-1);
    }
}

static void
bm_nofile_limit_set(void)
{
    const struct rlimit requested = {
        .rlim_cur = BM_NOFILE_LIMIT,
        .rlim_max = BM_NOFILE_LIMIT,
    };
    struct rlimit effective = {0};

    if (setrlimit(RLIMIT_NOFILE, &requested) != 0) {
        perror("Failed to set RLIMIT_NOFILE");
        exit(EXIT_FAILURE);
    }
    if (getrlimit(RLIMIT_NOFILE, &effective) != 0) {
        perror("Failed to read RLIMIT_NOFILE");
        exit(EXIT_FAILURE);
    }
    if (effective.rlim_cur != requested.rlim_cur ||
        effective.rlim_max != requested.rlim_max) {
        fprintf(stderr,
                "Unexpected RLIMIT_NOFILE: soft=%llu hard=%llu, expected=%d\n",
                (unsigned long long)effective.rlim_cur,
                (unsigned long long)effective.rlim_max, BM_NOFILE_LIMIT);
        exit(EXIT_FAILURE);
    }
}

void
bm_phase_warmup(void)
{
    // start from a fixed thread
    random_init_seed(0);
    bm_stat_init(&g_stats, g_params.num_threads, bm_target_op_count());

    assert(g_params.port <= UINT16_MAX);
    if (g_params.port > UINT16_MAX) {
        perror("Invalid port value");
        exit(-1);
    }
    uint16_t port = (uint16_t)g_params.port;
    bm_target_init(port, g_params.num_threads);

    size_t total = 0;
    for (size_t i = 0; i < g_params.op_dist_len; i++) {
        total += g_params.op_dist[i];
    }
    assert(total == DISTRIBUTION_BOUND);

    for (size_t i = 0; i < DISTRIBUTION_BOUND; i++) {
        g_ops[i] = UINT32_MAX;
    }

    /* fill the array of operations based on the given distribution */
    for (size_t i = 0; i < g_params.op_dist_len; i++) {
        for (size_t j = 0; j < g_params.op_dist[i]; j++) {
            /* find an empty slot to place the operation */
            while (true) {
                size_t pos = random_next_int(0, DISTRIBUTION_BOUND - 1);
                if (g_ops[pos] == UINT32_MAX) {
                    g_ops[pos] = i;
                    break;
                }
            }
        } /* fill as many slots with this operation's index as specified in the
           distribution value */
    }     /* for each operation */

    // double check every slot is occupied
    for (size_t i = 0; i < DISTRIBUTION_BOUND; i++) {
        assert(g_ops[i] < g_params.op_dist_len);
    }
}

void
bm_phase_run(void)
{
    cpu_time_t duration_min_start_ms = {0};
    cpu_time_t duration_max_start_ms = {0};
    cpu_time_t duration_min_stop_ms  = {0};
    cpu_time_t duration_max_stop_ms  = {0};
    uint64_t duration_min_start_clk  = 0;
    uint64_t duration_max_start_clk  = 0;
    uint64_t duration_min_stop_clk   = 0;
    uint64_t duration_max_stop_clk   = 0;
    uint64_t duration_min_ms         = 0;
    uint64_t duration_min_clk        = 0;
    uint64_t duration_max_ms         = 0;
    uint64_t duration_max_clk        = 0;

    pthread_t *threads = malloc(sizeof(pthread_t) * g_params.num_threads);
    pthread_barrier_init(&g_start_barrier, NULL, g_params.num_threads + 1);
    pthread_barrier_init(&g_stop_barrier, NULL, g_params.num_threads + 1);

    for (size_t i = 0; i < g_params.num_threads; i++) {
        pthread_create(&threads[i], NULL, run, (void *)i);
    }

    usleep(1000);
    duration_max_start_clk = read_time_stamp_counter();
    record_time(&duration_max_start_ms);

    pthread_barrier_wait(&g_start_barrier); /* barrier start */

    duration_min_start_clk = read_time_stamp_counter();
    record_time(&duration_min_start_ms);

    sleep(g_params.duration);
    /* signal stop */
    atomic_store_explicit(&g_stop, true, memory_order_relaxed);

    duration_min_stop_clk = read_time_stamp_counter();
    record_time(&duration_min_stop_ms);

    pthread_barrier_wait(&g_stop_barrier); /* barrier stop */

    duration_max_stop_clk = read_time_stamp_counter();
    record_time(&duration_max_stop_ms);

    for (size_t i = 0; i < g_params.num_threads; i++) {
        pthread_join(threads[i], NULL);
    }

    pthread_barrier_destroy(&g_start_barrier);
    pthread_barrier_destroy(&g_stop_barrier);

    free(threads);

    duration_min_clk = duration_min_stop_clk - duration_min_start_clk;
    duration_max_clk = duration_max_stop_clk - duration_max_start_clk;
    duration_min_ms =
        calc_spent_time(duration_min_start_ms, duration_min_stop_ms);
    duration_max_ms =
        calc_spent_time(duration_max_start_ms, duration_max_stop_ms);

    bm_stat_add_spent_time(&g_stats, duration_min_clk, duration_max_clk,
                           duration_min_ms, duration_max_ms);
}

void
bm_phase_conclude(void)
{
    bm_target_destroy(g_params.num_threads);
    bm_print_params(&g_params, BM_PRINT_DELIMITER);
    bm_print_stats(&g_stats, BM_PRINT_DELIMITER, bm_target_op_count());
    printf("\n");
}

void
bm_phase_cooldown(void)
{
    bm_stat_destroy(&g_stats);
}
