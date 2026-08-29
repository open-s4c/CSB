/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/mount.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct result {
    uint64_t operations;
    uint64_t failures;
};

struct worker_state {
    unsigned int index;
    uint32_t sequence;
    char base[PATH_MAX];
    char new_root[PATH_MAX];
};

static double
now(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts)) {
        perror("clock_gettime");
        exit(2);
    }
    return ts.tv_sec + ts.tv_nsec / 1000000000.0;
}

static unsigned int
parse_uint(const char *text, const char *name)
{
    char *end;
    unsigned long value = strtoul(text, &end, 10);

    if (!*text || *end || !value || value > 4096) {
        fprintf(stderr, "%s must be a positive integer: %s\n", name, text);
        exit(2);
    }
    return value;
}

static int
pin_worker(unsigned int worker)
{
    cpu_set_t allowed, one;
    unsigned int seen = 0;
    int cpu;

    if (sched_getaffinity(0, sizeof(allowed), &allowed))
        return -1;
    for (cpu = 0; cpu < CPU_SETSIZE; cpu++) {
        if (!CPU_ISSET(cpu, &allowed))
            continue;
        if (seen++ != worker)
            continue;
        CPU_ZERO(&one);
        CPU_SET(cpu, &one);
        return sched_setaffinity(0, sizeof(one), &one);
    }
    errno = E2BIG;
    return -1;
}

static int
op_uid_unique(struct worker_state *state)
{
    uid_t uid =
        1000000U + state->index * 131071U + (state->sequence++ & 65535U);

    if (setresuid(uid, (uid_t)-1, 0) || getuid() != uid ||
        setresuid(0, (uid_t)-1, 0) || getuid() != 0)
        return -1;
    return 0;
}

static int
op_uid_shared(struct worker_state *state)
{
    uid_t uid = 1000000U + (state->sequence++ & 65535U);

    if (setresuid(uid, (uid_t)-1, 0) || getuid() != uid ||
        setresuid(0, (uid_t)-1, 0) || getuid() != 0)
        return -1;
    return 0;
}

static int
op_netns(struct worker_state *state)
{
    pid_t pid = fork();
    int status;

    (void)state;
    if (pid < 0)
        return -1;
    if (!pid) {
        int fd;

        if (unshare(CLONE_NEWNET))
            _exit(1);
        fd = open("/sys/class/net/lo", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
        if (fd < 0)
            _exit(1);
        close(fd);
        _exit(0);
    }
    if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status) ||
        WEXITSTATUS(status))
        return -1;
    return 0;
}

static int
op_fsopen(struct worker_state *state)
{
    int fd;

    (void)state;
    fd = syscall(__NR_fsopen, "tmpfs", FSOPEN_CLOEXEC);
    if (fd < 0)
        return -1;
    return close(fd);
}

static int
op_proc_filesystems(struct worker_state *state)
{
    char buf[4096];
    ssize_t n;
    int fd;

    (void)state;
    fd = open("/proc/filesystems", O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    do {
        n = read(fd, buf, sizeof(buf));
    } while (n > 0);
    if (close(fd))
        return -1;
    return n < 0 ? -1 : 0;
}

static int
op_pivot_root(struct worker_state *state)
{
    pid_t pid = fork();
    int status;

    if (pid < 0)
        return -1;
    if (!pid) {
        char old_root[PATH_MAX];
        struct stat root_stat, old_stat;

        if (unshare(CLONE_NEWNS) ||
            syscall(SYS_mount, NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) ||
            syscall(SYS_mount, "tmpfs", state->new_root, "tmpfs", 0,
                    "size=4m") ||
            (size_t)snprintf(old_root, sizeof(old_root), "%s/old-root",
                             state->new_root) >= sizeof(old_root) ||
            mkdir(old_root, 0700) || chdir(state->new_root) ||
            syscall(SYS_pivot_root, ".", "old-root") || chdir("/") ||
            stat("/", &root_stat) || stat("/old-root", &old_stat) ||
            (root_stat.st_dev == old_stat.st_dev &&
             root_stat.st_ino == old_stat.st_ino))
            _exit(1);
        _exit(0);
    }
    if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status) ||
        WEXITSTATUS(status))
        return -1;
    return 0;
}

static int (*select_operation(const char *test))(struct worker_state *)
{
    if (!strcmp(test, "uid-unique"))
        return op_uid_unique;
    if (!strcmp(test, "uid-shared"))
        return op_uid_shared;
    if (!strcmp(test, "netns"))
        return op_netns;
    if (!strcmp(test, "fsopen"))
        return op_fsopen;
    if (!strcmp(test, "proc-filesystems"))
        return op_proc_filesystems;
    if (!strcmp(test, "pivot-root"))
        return op_pivot_root;
    return NULL;
}

static void
worker(unsigned int index, double deadline, int result_fd,
       int (*operation)(struct worker_state *))
{
    struct worker_state state = {.index = index};
    struct result result      = {0};

    if (pin_worker(index)) {
        result.failures++;
        goto out;
    }
    if (operation == op_pivot_root &&
        ((size_t)snprintf(state.base, sizeof(state.base),
                          "/tmp/active-mm-pivot-%ld",
                          (long)getpid()) >= sizeof(state.base) ||
         (size_t)snprintf(state.new_root, sizeof(state.new_root), "%s/new-root",
                          state.base) >= sizeof(state.new_root) ||
         mkdir(state.base, 0700) || mkdir(state.new_root, 0700))) {
        result.failures++;
        goto out;
    }
    while (now() < deadline) {
        if (operation(&state)) {
            result.failures++;
            break;
        }
        result.operations++;
    }
    if (operation == op_pivot_root &&
        (rmdir(state.new_root) || rmdir(state.base)))
        result.failures++;
out:
    if (write(result_fd, &result, sizeof(result)) != sizeof(result))
        perror("result write");
    close(result_fd);
    _exit(result.failures ? 1 : 0);
}

int
main(int argc, char **argv)
{
    int (*operation)(struct worker_state *);
    struct result total = {0};
    unsigned int workers, duration, i;
    int(*pipes)[2];
    pid_t *pids;
    double start, deadline, elapsed;

    if (argc != 4 || !(operation = select_operation(argv[1]))) {
        fprintf(stderr,
                "usage: %s uid-unique|uid-shared|netns|fsopen|"
                "proc-filesystems|pivot-root WORKERS DURATION_SECONDS\n",
                argv[0]);
        return 2;
    }
    workers  = parse_uint(argv[2], "workers");
    duration = parse_uint(argv[3], "duration");
    if ((!strncmp(argv[1], "uid-", 4) || !strcmp(argv[1], "netns") ||
         !strcmp(argv[1], "fsopen") || !strcmp(argv[1], "pivot-root")) &&
        geteuid()) {
        fprintf(stderr, "%s must run as root\n", argv[1]);
        return 2;
    }
    if (!strcmp(argv[1], "fsopen") && operation(&(struct worker_state){0})) {
        fprintf(stderr, "fsopen preflight failed: %s\n", strerror(errno));
        return 2;
    }
    pipes = calloc(workers, sizeof(*pipes));
    pids  = calloc(workers, sizeof(*pids));
    if (!pipes || !pids) {
        perror("calloc");
        return 2;
    }
    for (i = 0; i < workers; i++)
        if (pipe2(pipes[i], O_CLOEXEC)) {
            perror("pipe2");
            return 2;
        }
    start    = now();
    deadline = start + duration;
    for (i = 0; i < workers; i++) {
        pids[i] = fork();
        if (pids[i] < 0) {
            perror("fork");
            return 2;
        }
        if (!pids[i]) {
            unsigned int j;

            for (j = 0; j < workers; j++) {
                close(pipes[j][0]);
                if (j != i)
                    close(pipes[j][1]);
            }
            worker(i, deadline, pipes[i][1], operation);
        }
        close(pipes[i][1]);
    }
    for (i = 0; i < workers; i++) {
        struct result one = {0};
        int status;

        if (read(pipes[i][0], &one, sizeof(one)) != sizeof(one))
            total.failures++;
        close(pipes[i][0]);
        if (waitpid(pids[i], &status, 0) != pids[i] || !WIFEXITED(status) ||
            WEXITSTATUS(status))
            total.failures++;
        total.operations += one.operations;
        total.failures += one.failures;
    }
    elapsed = now() - start;
    /* Network namespace destruction completes on a workqueue. */
    if (!strcmp(argv[1], "netns"))
        sleep(1);
    printf(
        "operations_per_second=%.3f;operations=%llu;failures=%llu;"
        "elapsed_seconds=%.6f;workers=%u;test=%s;\n",
        total.operations / elapsed, (unsigned long long)total.operations,
        (unsigned long long)total.failures, elapsed, workers, argv[1]);
    free(pids);
    free(pipes);
    return total.failures ? 1 : 0;
}
