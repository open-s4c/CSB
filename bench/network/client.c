/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#include <arpa/inet.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdbool.h>
#include <sys/epoll.h>
#include <getopt.h>
#include <errno.h>
#include <signal.h>

#include "helper.h"

static struct extracted_op eops[128];
static size_t eops_sz = 0;

#define MAX_EVS  16
#define BUF_SIZE 1024

static uint8_t *sbuf;
static size_t sbuf_size = 0;

struct conn_data {
    size_t step;
    size_t n;
    int last_epoll;
    int fd;
};

struct epoll_st {
    int fd;
    size_t nconn;
};

static void
config_wait(struct conn_data *d, struct epoll_st *est)
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
    if (epoll_ctl(est->fd, EPOLL_CTL_MOD, d->fd, &ev_n) == -1) {
        perror("epoll_ctl_mod");
    }
}

static void
advance_step(struct conn_data *d)
{
    d->n++;
    if (d->n >= eops[d->step].n) {
        d->n    = 0;
        d->step = (d->step + 1) % eops_sz;
    }
}

static void
unregister(struct conn_data *d, struct epoll_st *est)
{
    epoll_ctl(est->fd, EPOLL_CTL_DEL, d->fd, NULL);
    close(d->fd);
    free(d);
    est->nconn--;
}

static bool
register_new(struct epoll_st *est, struct sockaddr *serv_addr, size_t addr_size,
             bool retry_on_fail)
{
    struct epoll_event ev;
    struct conn_data *d = malloc(sizeof(struct conn_data));
    if (!d) {
        return false;
    }

    d->step       = 0;
    d->n          = 0;
    d->last_epoll = eops[0].is_write ? EPOLLIN : EPOLLOUT;

    int csock = socket(serv_addr->sa_family, SOCK_STREAM, 0);
    if (csock == -1) {
        fprintf(stderr, "socket failed!\n");
        return false;
    }
    d->fd = csock;

    int connect_ret = 0;
    do {
        connect_ret = connect(csock, serv_addr, addr_size);
    } while (retry_on_fail && connect_ret != 0);

    if (connect_ret == -1) {
        fprintf(stderr, "connect failed!\n");
        return false;
    }

    setnonblocking(csock);
    ev.events   = d->last_epoll;
    ev.data.ptr = d;
    if (epoll_ctl(est->fd, EPOLL_CTL_ADD, csock, &ev) == -1) {
        fprintf(stderr, "epoll_ctl failed!\n");
        return false;
    }
    est->nconn++;
    printf("[Client] %zu connections established.\n", est->nconn);
    return true;
}

static void
readwrite(struct epoll_event *ev, struct epoll_st *est)
{
    struct conn_data *d = ev->data.ptr;
    int fd              = d->fd;
    int r               = 0;
    if (ev->events & (EPOLLHUP | EPOLLERR)) {
        unregister(d, est);
        return;
    }
    assert(eops[d->step].sz < sbuf_size);
    if (ev->events & EPOLLOUT) {
        assert(!eops[d->step].is_write);
    } else if (ev->events & EPOLLIN) {
        assert(eops[d->step].is_write);
    }

    while (r != -1) {
        if (eops[d->step].is_write) {
            r = recv(fd, &sbuf[0], eops[d->step].sz, 0);
        } else {
            r = send(fd, &sbuf[0], eops[d->step].sz, 0);
        }
        if (r != -1) {
            advance_step(d);
        }
    }
    if (r == -1 && (errno != EAGAIN && errno != ECONNRESET)) {
        unregister(d, est);
        return;
    }
    if (0 && d->step == 0) {
        unregister(d, est);
        return;
    } else {
        config_wait(d, est);
    }
}

static void
usage(const char *argv0)
{
    fprintf(stderr,
            "Usage: %s [-h host] [-p port] [-P operation_sequence | -F "
            "op_sequence_file]\n",
            argv0);
    fprintf(
        stderr,
        "Operation sequence: <NUM_TIME>[rw]<NUM_BYTES>[-operation_sequence]*, "
        "e.g. '2r1024-1w32'\n");
}

int
main(int argc, char *argv[])
{
    size_t num_conn = 1;
    uint16_t port   = 10000;
    char *host      = NULL;
    char *program   = NULL;
    char *prog_file = NULL;
    bool use_ipv6   = false;
    int opt         = 0;
    bool retry_on_fail =
        false; /* retry if the connection fails till it succeeds*/
    bool only_once = false;
    prog_file      = NULL;
    while ((opt = getopt(argc, argv, "6h:p:P:F:RO")) != -1) {
        switch (opt) {
            case 'h':
                host = optarg;
                break;
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
            case 'R':
                retry_on_fail = true;
                break;
            case 'O':
                only_once = true;
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
        fprintf(stderr, "No operation sequence specified.\n");
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

    if (!host) {
        fprintf(stderr, "No host specified\n");
        return 1;
    }

    struct addrinfo *result = NULL;
    struct addrinfo hints   = {
          .ai_family   = PF_UNSPEC,
          .ai_socktype = SOCK_STREAM,
          .ai_flags    = AI_CANONNAME,
    };
    int r = getaddrinfo(host, NULL, &hints, &result);
    if (r == -1) {
        fprintf(stderr, "getaddrinfo: %s", gai_strerror(r));
        return 1;
    }

    struct sockaddr *serv_addr = NULL;
    size_t addr_size           = 0;
    for (struct addrinfo *res = result; res != NULL; res = res->ai_next) {
        switch (res->ai_family) {
            case AF_INET:
                if (use_ipv6) {
                    continue;
                }
                serv_addr                                   = res->ai_addr;
                addr_size                                   = res->ai_addrlen;
                ((struct sockaddr_in *)serv_addr)->sin_port = htons(port);
                break;
            case AF_INET6:
                if (!use_ipv6) {
                    continue;
                }
                serv_addr                                     = res->ai_addr;
                addr_size                                     = res->ai_addrlen;
                ((struct sockaddr_in6 *)serv_addr)->sin6_port = htons(port);
                break;
            default:
                continue;
        }
        break;
    }

    struct epoll_st est = {};
    est.fd              = epoll_create1(0);
    if (est.fd == -1) {
        fprintf(stderr, "epoll_create1 failed!\n");
        return 1;
    }

    for (size_t i = 0; i < num_conn; i++) {
        if (!register_new(&est, serv_addr, addr_size, retry_on_fail)) {
            return -1;
        }
    }

    signal(SIGPIPE, SIG_IGN);

    while (est.nconn) {
        struct epoll_event evs[MAX_EVS];
        int nfds = epoll_wait(est.fd, &evs[0], MAX_EVS, -1);
        if (nfds == -1) {
            continue;
        }
        for (int i = 0; i < nfds; i++) {
            readwrite(&evs[i], &est);
        }
        while (est.nconn < num_conn) {
            if (!register_new(&est, serv_addr, addr_size, false)) {
                break;
            }
        }
        if (only_once) {
            break;
        }
    }
    printf("[Client] exited!\n");
    return 0;
}
