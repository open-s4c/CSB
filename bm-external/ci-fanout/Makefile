SHELL := /bin/sh

CC ?= cc
STEPS ?= 1024
FIXTURE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))ci-step.c
TARGETS := $(addprefix ci-step-,$(shell seq 1 $(STEPS)))

.PHONY: all $(TARGETS)

all: $(TARGETS)

$(TARGETS):
	@set -e; $(CC) -fsyntax-only -std=c11 -Wall -Wextra $(FIXTURE); test -r /proc/self/status
