// Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
// SPDX-License-Identifier: MIT

#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

struct worker {
    pthread_barrier_t *barrier;
    uint64_t *deadline_ns;
    uint64_t completed;
    uint64_t failures;
    uint64_t total_ns;
    uint64_t max_ns;
};

static uint64_t
now_ns(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)ts.tv_sec * UINT64_C(1000000000) + (uint64_t)ts.tv_nsec;
}

static void *
run_worker(void *argument)
{
    static char *const child_argv[] = {"true", NULL};
    struct worker *worker           = argument;

    pthread_barrier_wait(worker->barrier);
    while (now_ns() < *worker->deadline_ns) {
        uint64_t start_ns = now_ns();
        pid_t pid         = fork();
        int status        = 0;
        pid_t waited;
        int failed = 0;

        if (pid == 0) {
            execve("/bin/true", child_argv, environ);
            _exit(127);
        }
        if (pid < 0) {
            failed = 1;
        } else {
            do {
                waited = waitpid(pid, &status, 0);
            } while (waited < 0 && errno == EINTR);
            if (waited != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 0)
                failed = 1;
        }

        uint64_t elapsed_ns = now_ns() - start_ns;
        worker->total_ns += elapsed_ns;
        if (elapsed_ns > worker->max_ns)
            worker->max_ns = elapsed_ns;
        if (failed)
            worker->failures++;
        else
            worker->completed++;
    }
    return NULL;
}

static uint64_t
parse_uint(const char *name, const char *text, uint64_t min, uint64_t max)
{
    char *end = NULL;
    unsigned long long value;

    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < min ||
        value > max) {
        fprintf(stderr, "%s must be an integer in [%" PRIu64 ", %" PRIu64 "]\n",
                name, min, max);
        exit(2);
    }
    return (uint64_t)value;
}

static double
parse_duration(const char *text)
{
    char *end = NULL;
    double value;

    errno = 0;
    value = strtod(text, &end);
    if (errno != 0 || end == text || *end != '\0' || value < 0.1 ||
        value > 3600.0) {
        fputs("--duration must be in [0.1, 3600] seconds\n", stderr);
        exit(2);
    }
    return value;
}

int
main(int argc, char **argv)
{
    uint64_t worker_count = 1;
    uint64_t memory_mib   = 256;
    double duration       = 10.0;
    pthread_barrier_t barrier;
    pthread_t *threads;
    struct worker *workers;
    volatile unsigned char *memory = NULL;
    uint64_t deadline_ns;
    uint64_t start_ns;
    uint64_t end_ns;
    uint64_t completed = 0;
    uint64_t failures  = 0;
    uint64_t total_ns  = 0;
    uint64_t max_ns    = 0;

    for (int i = 1; i < argc; i++) {
        if (i + 1 >= argc) {
            fprintf(stderr,
                    "Usage: %s --workers N --duration SEC --memory-mib N\n",
                    argv[0]);
            return 2;
        }
        if (strcmp(argv[i], "--workers") == 0)
            worker_count = parse_uint("--workers", argv[++i], 1, 1024);
        else if (strcmp(argv[i], "--duration") == 0)
            duration = parse_duration(argv[++i]);
        else if (strcmp(argv[i], "--memory-mib") == 0)
            memory_mib = parse_uint("--memory-mib", argv[++i], 0, 16384);
        else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            return 2;
        }
    }

    if (memory_mib > 0) {
        size_t bytes = (size_t)memory_mib * 1024 * 1024;

        memory = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (memory == MAP_FAILED) {
            perror("mmap");
            return 1;
        }
        for (size_t offset = 0; offset < bytes; offset += (size_t)getpagesize())
            memory[offset] = (unsigned char)(offset >> 12);
    }

    threads = calloc((size_t)worker_count, sizeof(*threads));
    workers = calloc((size_t)worker_count, sizeof(*workers));
    if (threads == NULL || workers == NULL) {
        perror("calloc");
        return 1;
    }
    if (pthread_barrier_init(&barrier, NULL, (unsigned int)worker_count + 1) !=
        0) {
        fputs("pthread_barrier_init failed\n", stderr);
        return 1;
    }
    for (uint64_t i = 0; i < worker_count; i++) {
        workers[i].barrier     = &barrier;
        workers[i].deadline_ns = &deadline_ns;
        if (pthread_create(&threads[i], NULL, run_worker, &workers[i]) != 0) {
            fputs("pthread_create failed\n", stderr);
            return 1;
        }
    }

    start_ns    = now_ns();
    deadline_ns = start_ns + (uint64_t)(duration * 1000000000.0);
    pthread_barrier_wait(&barrier);
    for (uint64_t i = 0; i < worker_count; i++) {
        pthread_join(threads[i], NULL);
        completed += workers[i].completed;
        failures += workers[i].failures;
        total_ns += workers[i].total_ns;
        if (workers[i].max_ns > max_ns)
            max_ns = workers[i].max_ns;
    }
    end_ns = now_ns();

    double elapsed    = (double)(end_ns - start_ns) / 1000000000.0;
    uint64_t attempts = completed + failures;
    double throughput = elapsed > 0.0 ? (double)completed / elapsed : 0.0;
    double mean_us =
        attempts > 0 ? (double)total_ns / (double)attempts / 1000.0 : 0.0;

    printf("fork_execs_per_second=%.6f;completed=%" PRIu64 ";failures=%" PRIu64
           ";elapsed_seconds=%.6f;mean_fork_exec_us=%.3f;max_fork_exec_us=%.3f"
           ";workers=%" PRIu64 ";runner_memory_mib=%" PRIu64 ";\n",
           throughput, completed, failures, elapsed, mean_us,
           (double)max_ns / 1000.0, worker_count, memory_mib);

    if (memory != NULL)
        munmap((void *)memory, (size_t)memory_mib * 1024 * 1024);
    pthread_barrier_destroy(&barrier);
    free(workers);
    free(threads);
    return failures == 0 ? 0 : 1;
}
