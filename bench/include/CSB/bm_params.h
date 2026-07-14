/*
 * Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * SPDX-License-Identifier: MIT
 */
#ifndef BM_PARAMS_H
#define BM_PARAMS_H

#include "bm_error.h"
#include "macros.h"

#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <regex.h>
#include <stdbool.h>

#define PARAM_VAL_NONE UINT32_MAX

#define PARAM_NTHREADS  "-t=([0-9]+)"
#define PARAM_MAX_NOISE "-n=([0-9]+)"
#define PARAM_DURATION  "-d=([0-9]+)"
#define PARAM_PORT      "-p=([0-9]+)"
#define PARAM_OP_DIST   "-op([0-9]+)=([0-9]+)"

#define PARAM_FIXED_LEN 5

typedef struct bm_params_s {
    uint32_t num_threads;
    uint32_t port;
    uint32_t max_noise;
    uint32_t duration;
    uint32_t *op_dist;
    uint32_t op_dist_len;
} bm_params_t;

static inline bm_error_t
_bm_params_extract_val(char *param, char *regex_string, uint32_t out_val[],
                       size_t out_val_len)
{
    const size_t max_gp_count = 3;
    regex_t regex_compiled;
    regmatch_t groups[max_gp_count];
    bm_error_t ret = BM_ERR_NONE;

    if (regcomp(&regex_compiled, regex_string, REG_EXTENDED)) {
        regfree(&regex_compiled);
        return BM_ERR_PARAMS_CANNOT_PARSE;
    }

    if (regexec(&regex_compiled, param, max_gp_count, groups, 0)) {
        regfree(&regex_compiled);
        return BM_ERR_PARAMS_CANNOT_PARSE;
    }

    for (size_t i = 0; i < max_gp_count; i++) {
        if (groups[i].rm_so == -1) {
            break;
        }

        // printf("Group %zu: [%2u-%2u]: %s\n", i, groups[i].rm_so,
        //        groups[i].rm_eo, param + groups[i].rm_so);

        if (i > 0 && i - 1 < out_val_len)
            out_val[i - 1] = strtoul((param + groups[i].rm_so), NULL, 0);
    }

    regfree(&regex_compiled);
    return ret;
}

static inline bool
_bm_param_check_match(char *param, char *regex, uint32_t *output)
{
    uint32_t value[1] = {0};
    if (_bm_params_extract_val(param, regex, value, 1) == BM_ERR_NONE) {
        *output = value[0];
        return true;
    }
    return false;
}

static inline bool
_bm_param_check_match_op(char *param, char *regex, uint32_t *output,
                         size_t max_idx)
{
    uint32_t value[2] = {0};
    if (_bm_params_extract_val(param, regex, value, 2) == BM_ERR_NONE) {
        assert(value[0] < max_idx);
        output[value[0]] = value[1];
        return true;
    }
    V_UNUSED(max_idx);
    return false;
}

static inline bool
_bm_params_match_field(bm_params_t *out_params, char *param)
{
    if (_bm_param_check_match(param, PARAM_NTHREADS, &out_params->num_threads))
        return true;

    if (_bm_param_check_match(param, PARAM_MAX_NOISE, &out_params->max_noise))
        return true;

    if (_bm_param_check_match(param, PARAM_DURATION, &out_params->duration))
        return true;

    if (_bm_param_check_match(param, PARAM_PORT, &out_params->port))
        return true;

    if (_bm_param_check_match_op(param, PARAM_OP_DIST, out_params->op_dist,
                                 out_params->op_dist_len))
        return true;

    return false;
}

static inline void
bm_print_params(bm_params_t *out_params, char delimiter)
{
    printf("num_threads=%u%c", out_params->num_threads, delimiter);
    printf("port=%u%c", out_params->port, delimiter);
    printf("max_noise=%u%c", out_params->max_noise, delimiter);
    printf("duration=%u%c", out_params->duration, delimiter);

    for (size_t i = 0; i < out_params->op_dist_len; i++) {
        printf("op%zu_dist=%u%c", i, out_params->op_dist[i], delimiter);
    }
}

static inline void
_bm_params_init(bm_params_t *out_params)
{
    out_params->num_threads = PARAM_VAL_NONE;
    out_params->port        = PARAM_VAL_NONE;
    out_params->max_noise   = PARAM_VAL_NONE;
    out_params->duration    = PARAM_VAL_NONE;

    for (size_t i = 0; i < out_params->op_dist_len; i++) {
        out_params->op_dist[i] = PARAM_VAL_NONE;
    }
}

static inline bool
_bm_are_params_set(bm_params_t *out_params)
{
    if (out_params->num_threads == PARAM_VAL_NONE)
        return false;
    if (out_params->port == PARAM_VAL_NONE)
        return false;
    if (out_params->max_noise == PARAM_VAL_NONE)
        return false;
    if (out_params->duration == PARAM_VAL_NONE)
        return false;

    for (size_t i = 0; i < out_params->op_dist_len; i++) {
        if (out_params->op_dist[i] == PARAM_VAL_NONE)
            return false;
    }
    return true;
}

static inline bm_error_t
bm_params_extract(int argc, char *argv[], bm_params_t *out_params,
                  size_t num_ops)
{
    assert(out_params);

    int expected_num_params = PARAM_FIXED_LEN + num_ops;
    if (argc != expected_num_params) {
        return BM_ERR_PARAMS_INCORRECT_COUNT;
    }

    out_params->op_dist = malloc(sizeof(uint32_t) * num_ops);
    // init params
    _bm_params_init(out_params);
    out_params->op_dist_len = num_ops;

    for (int i = 1; i < argc; i++) {
        _bm_params_match_field(out_params, argv[i]);
    }

    // check all parameters have been set
    if (!_bm_are_params_set(out_params)) {
        return BM_ERR_PARAM_MISSING;
    }

    return BM_ERR_NONE;
}

#endif
