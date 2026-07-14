/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
/**
 * @file bm_empty.h
 * @brief This benchmark is only for testing and checking the overhead of the
 * benchmark
 */
#include <CSB/bm_target.h>
#include <CSB/bm_helper.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <assert.h>
#include <stdio.h>
#define NOP_PER_OP     100U
#define MAX_NAME_LEN   20U
#define NUM_SYSCALLS   2U
#define MAX_EVENTS     10U
#define TIMEOUT_MS     10U
#define MAX_BUFFER_LEN 1024U

int g_socket   = -1;
int g_epoll_fd = -1;

/**
 * Covered syscalls:
 * epoll_create(1024) (USED) / epoll_create (NOT USED) -> epoll_pwait (NOT
 * USED)/ epoll_wait (USED)
 * socket(USED) -> bind(USED) -> listen(USED) ->
 * accept(USED) -> fcntl(USED) -> setsockopt(USED) -> epoll_ctl(USED) -> read
 * (USED) / write(USED)
 */


static inline char *
bm_target_get_name(void)
{
    return "bm_server_redis";
}

static inline size_t
bm_target_op_count(void)
{
    return NUM_SYSCALLS;
}

struct thread_ctx_s {
    size_t tid;
    int cnt;
};

static inline void
bm_target_get_op_name(char *out_str, const size_t len, size_t op_id)
{
    assert(len >= MAX_NAME_LEN && "output buffer too small");
    sprintf(out_str, "op0_read_write");
    V_UNUSED(len, op_id);
}
int
make_socket_nonblocking(int fd)
{
    /* get current flags on the socket */
    int flags = fcntl(fd, F_GETFL, 0);
    /* add non blocking flag
     * effects of this
     * accept() returns -1 with errno == EAGAIN if no connection is waiting.
     * read() returns immediately if no data is available.
     * write() returns immediately if the buffer can’t accept more data.
     */
    int r = fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    assert(r != -1);
    return r;
}
static inline void
bm_target_init(uint16_t port, size_t num_threads)
{
    /* domain specifies a communication domain */
    int domain = AF_INET; //  IPv4 Internet protocols
    /* socket type SOCK_STREAM
     *  Provides sequenced, reliable, two-way, connection-based
     *  byte streams.  An out-of-band data transmission mechanism
     *  may be supported.
     */
    int type     = SOCK_STREAM;
    int protocol = 0;
    int s        = socket(domain, type, protocol);
    assert(s != -1);

    int yes = 1;
    /* Make sure connection-intensive things like the redis benchmark
     * will be able to close/open sockets a zillion of times
     * Enable (yes) SO_REUSEADDR on this socket
     */
    int r = setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    assert(r != -1);

    /* assigns the address specified by addr to the socket referred to by the
     * file descriptor sockfd */
    struct sockaddr_in address = {0};
    address.sin_family         = AF_INET; /* IPv4 */
    address.sin_addr.s_addr = INADDR_ANY; /* bind on all network interfaces */
    address.sin_port =
        htons(port); /* converts the port from host byte order to network byte
                        order (big‑endian), which is required for sockets. */
    r = bind(s, (struct sockaddr *)&address, sizeof(address));
    assert(r != -1);

    r = listen(s, SOMAXCONN);
    assert(r != -1);

    make_socket_nonblocking(s);

    // open an epoll file descriptor
    g_epoll_fd = epoll_create(1024); /* what latest redis uses */
    assert(g_epoll_fd != -1);

    struct epoll_event event = {0};
    event.events             = EPOLLIN; // we are interested in read events
    event.data.fd            = s; // associate the socket fd with this event

    r = epoll_ctl(g_epoll_fd, EPOLL_CTL_ADD, s, &event);
    assert(r != -1);

    g_socket = s;
    V_UNUSED(r);
    //    fprintf(stderr, "Fake Redis server listening on %zu...\n", port);
}

static inline void
bm_target_reg(thread_ctx_t *ctx, size_t tid)
{
    assert(ctx);
    ctx->tid = tid;
    ctx->cnt = 0;
}

int
_bm_accept_connection(bm_op_res_t *res)
{
    assert(res);
    int client_fd = accept(g_socket, NULL, NULL);
    res->op_count++;
    if (client_fd != -1) {
        make_socket_nonblocking(client_fd);
        struct epoll_event event = {0};
        event.events             = EPOLLIN; /* Register for read events */
        event.data.fd            = client_fd;
        epoll_ctl(g_epoll_fd, EPOLL_CTL_ADD, client_fd, &event);
        res->succ_count++;
    }
    // fprintf(stderr, "Accepted new connection: fd %d\n", client_fd);
    return client_fd;
}

/**
 * Acceptable Reply formats
 *
 * Simple string reply: +<str>\r\n
 * Error reply: -ERR unknown command\r\n
 * Integer reply: :<number>\r\n
 * Bulk reply: $<length>\r\n<bytes>\r\n
 * Array reply: *<number of elements>\r\n<element1><element2>
 */
#define MAX_REPLY_LEN 1000U
int
_bm_handle_get(int fd, thread_ctx_t *ctx)
{
    char reply[MAX_REPLY_LEN] = {0};
    char *msg                 = "HI";
    // snprintf(reply, sizeof(reply), "$%d\r\nPong#%d\r\n", MAX_REPLY_LEN,
    // ctx->cnt++);
    snprintf(reply, sizeof(reply), "$%zu\r\n%s\r\n", strlen(msg), msg);
    // printf("Sending reply: %s %zu", reply, strlen(reply));
    return write(fd, reply, strlen(reply));
}

int
_bm_handle_set(int fd)
{
#define OK_REPLY "+OK\r\n"
    return write(fd, "+OK\r\n", strlen(OK_REPLY));
}

static inline int
_bm_respond(thread_ctx_t *ctx, int fd, char *buf)
{
    if (strstr(buf, "SET")) {
        return _bm_handle_set(fd);
    } else if (strstr(buf, "GET")) {
        return _bm_handle_get(fd, ctx);
    } else {
        assert(false && "Unknown command");
        return -1;
    }
}

static inline bm_op_res_t
bm_dispatch_operation(thread_ctx_t *ctx, size_t op_id)
{
    bm_op_res_t result = {.op_count = 0, .succ_count = 0};
    struct epoll_event events[MAX_EVENTS];
    if (g_socket == -1 || g_epoll_fd == -1) {
        return result;
    }
    int n = epoll_wait(g_epoll_fd, events, MAX_EVENTS, TIMEOUT_MS);
    if (n == -1 || n == 0) {
        /* either an error or no connections available! */
        return result;
    }
    for (int i = 0; i < n; i++) {
        int fd = events[i].data.fd;
        if (fd == g_socket) {
            // Accept new connection
            _bm_accept_connection(&result);
        } else {
            // Handle client data
            char buf[MAX_BUFFER_LEN];
            int count = read(fd, buf, sizeof(buf));
            result.op_count++;
            if (count <= 0) {
                close(fd);
            } else {
                // count read success
                result.succ_count++;
                assert(count < MAX_BUFFER_LEN);
                buf[count] = '\0';
                int ret    = _bm_respond(ctx, fd, buf);
                if (ret != -1) {
                    // write happened
                    result.op_count++;
                    if (ret > 0) {
                        // count write success
                        result.succ_count++;
                    }
                }
            }
        }
    }
    return result;
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
