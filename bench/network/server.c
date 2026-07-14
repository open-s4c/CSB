/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netdb.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "helper.h"
#define MAX_EVS 16

static uint8_t *sbuf;
static size_t sbuf_size = 0;

struct conn_data {
    size_t n;
    size_t step;
    int last_epoll;
    int fd;
};

static void
unregister(struct conn_data *d, int efd)
{
    epoll_ctl(efd, EPOLL_CTL_DEL, d->fd, NULL);
    close(d->fd);
    free(d);
}

static struct extracted_op eops[128];
static size_t eops_sz = 0;

static void
config_wait(struct conn_data *d, int efd)
{
    size_t step    = d->step;
    int next_epoll = eops[step].is_write ? EPOLLIN : EPOLLOUT;
    if (d->last_epoll == next_epoll) {
        return;
    }
    struct epoll_event ev_n;
    ev_n.events   = next_epoll;
    ev_n.data.ptr = d;
    d->last_epoll = next_epoll;
    if (epoll_ctl(efd, EPOLL_CTL_MOD, d->fd, &ev_n) == -1) {
        perror("epoll_ctl_mod");
    }
}

static void
advance_step(struct conn_data *d)
{
    d->n++;
    if (d->n == eops[d->step].n) {
        d->n    = 0;
        d->step = (d->step + 1) % eops_sz;
    }
}

static void
readwrite(struct epoll_event *ev, int efd)
{
    struct conn_data *d = ev->data.ptr;
    int fd              = d->fd;
    int r               = 0;
    if (ev->events & (EPOLLHUP | EPOLLERR)) {
        unregister(d, efd);
        return;
    }
    assert(eops[d->step].sz < sbuf_size);
    if (ev->events & EPOLLOUT) {
        assert(!eops[d->step].is_write);
        r = send(fd, &sbuf[0], eops[d->step].sz, 0);
    } else if (ev->events & EPOLLIN) {
        assert(eops[d->step].is_write);
        r = recv(fd, &sbuf[0], eops[d->step].sz, 0);
    }
    if (r == -1) {
        unregister(d, efd);
        return;
    }

    advance_step(d);
    if (d->step == 0) {
        unregister(d, efd);
    } else {
        config_wait(d, efd);
    }
}

static void
usage(const char *argv0)
{
    fprintf(stderr,
            "Usage: %s [-6] [-p port] [-P operation_sequence | -F "
            "op_sequence_file]\n",
            argv0);
    fprintf(
        stderr,
        "Operation sequence: <NUM_TIME>[rw]<NUM_BYTES>[-operation_sequence]*, "
        "e.g. '2r1023-1w32'\n");
}

int
main(int argc, char *argv[])
{
    uint16_t port   = 10000;
    char *program   = NULL;
    bool use_ipv6   = false;
    int opt         = 0;
    char *prog_file = NULL;
    while ((opt = getopt(argc, argv, "6p:P:F:O")) != -1) {
        switch (opt) {
            case 'p':
                port = strtoul(optarg, NULL, 0);
                if (errno == ERANGE) {
                    perror("strtoul");
                    return -1;
                }
                break;
            case '6':
                use_ipv6 = true;
            case 'P':
                program = optarg;
                break;
            case 'F':
                prog_file = optarg;
                break;
            default: /* '?' */
                usage(argv[0]);
                return -1;
        }
    }

    if (program && prog_file) {
        fprintf(stderr, "Please specify the operation sequence once.\n");
        return 1;
    }

    if (prog_file) {
        program = load_prog_file(prog_file);
        if (!program) {
            fprintf(stderr,
                    "Failed to load the operation sequence from file %s\n",
                    prog_file);
        }
    }

    if (!program) {
        fprintf(stderr, "No operation sequence specified\n");
        usage(argv[0]);
        return 'P';
    }
    eops_sz = parse_ops(program, &eops[0], sizeof(eops) / sizeof(eops[0]));
    if (eops_sz < 0) {
        fprintf(stderr, "Failed to parse operation sequence.\n");
        usage(argv[0]);
        return 'P';
    }

    // allocate buffer large enough
    sbuf_size = get_max_buffer_size(&eops[0], eops_sz) + 1;
    sbuf      = calloc(1, sbuf_size);
    assert(sbuf != NULL);

    struct epoll_event ev;
    int efd = epoll_create1(0);
    if (efd == -1) {
        fprintf(stderr, "epoll_create1 failed!\n");
        return 1;
    }
    int lsock = socket(use_ipv6 ? AF_INET6 : AF_INET, SOCK_STREAM, 0);
    if (lsock == -1) {
        fprintf(stderr, "socket failed!\n");
        return 1;
    }

    struct sockaddr_in loopback = {
        .sin_family      = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_ANY),
        .sin_port        = htons(port),
    };

    struct sockaddr_in6 loopback6 = {
        .sin6_family = AF_INET6,
        .sin6_addr   = IN6ADDR_ANY_INIT,
        .sin6_port   = htons(port),
    };

    int opt_val = 1;
    setsockopt(lsock, SOL_SOCKET, SO_REUSEPORT, &opt_val, sizeof(opt_val));

    if (bind(lsock,
             use_ipv6 ? (struct sockaddr *)&loopback6 :
                        (struct sockaddr *)&loopback,
             use_ipv6 ? sizeof(loopback6) : sizeof(loopback)) == -1) {
        return 2;
    }
    if (listen(lsock, 50) == -1) {
        return 2;
    }

    ev.events   = EPOLLIN;
    ev.data.ptr = NULL;
    if (epoll_ctl(efd, EPOLL_CTL_ADD, lsock, &ev) == -1) {
        return -1;
    }
    while (true) {
        struct epoll_event evs[MAX_EVS];
        int nfds = epoll_wait(efd, &evs[0], MAX_EVS, -1);
        if (nfds == -1) {
            perror("epoll_wait");
            continue;
        }
        for (int i = 0; i < nfds; i++) {
            if (evs[i].data.ptr == NULL) {
                int cfd = accept(lsock, NULL, 0);
                if (cfd == -1) {
                    perror("accept");
                    continue;
                }
                setnonblocking(cfd);
                struct conn_data *d = malloc(sizeof(struct conn_data));
                if (!d) {
                    perror("malloc");
                    close(cfd);
                    continue;
                }
                d->fd         = cfd;
                d->last_epoll = eops[0].is_write ? EPOLLIN : EPOLLOUT;
                d->step       = 0;
                d->n          = 0;
                ev.events     = d->last_epoll;
                ev.data.ptr   = d;
                if (epoll_ctl(efd, EPOLL_CTL_ADD, cfd, &ev) == -1) {
                    perror("epoll_ctl");
                    close(cfd);
                    free(d);
                    continue;
                }
            } else {
                readwrite(&evs[i], efd);
            }
        }
    }
    return 0;
}
