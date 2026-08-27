// Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
// SPDX-License-Identifier: MIT

#include <sys/utsname.h>

char *testcase_description = "uname system call";

void
testcase(unsigned long long *iterations, unsigned long nr)
{
    struct utsname name;

    (void)nr;
    while (1) {
        uname(&name);
        (*iterations)++;
    }
}
