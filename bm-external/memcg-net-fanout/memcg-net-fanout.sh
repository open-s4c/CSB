#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

workers=1
duration=5

usage()
{
    echo "Usage: $0 [--workers N] [--duration N]" >&2
}

require_uint()
{
    case "$2" in ''|*[!0-9]*) echo "$1 must be a positive integer" >&2; exit 2;; esac
    [ "$2" -ge 1 ] || { echo "$1 must be a positive integer" >&2; exit 2; }
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --workers) [ "$#" -ge 2 ] || { usage; exit 2; }; workers=$2; shift 2 ;;
        --duration) [ "$#" -ge 2 ] || { usage; exit 2; }; duration=$2; shift 2 ;;
        *) usage; exit 2 ;;
    esac
done
require_uint --workers "$workers"
require_uint --duration "$duration"
[ "$workers" -le 128 ] || { echo "--workers must not exceed 128" >&2; exit 2; }

for command in iperf3 python3 sudo date mktemp; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Required command is unavailable: $command" >&2
        exit 1
    }
done
sudo -n true

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cgroup_root=/sys/fs/cgroup/csb-memcg-net-$$
tmpdir=$(mktemp -d /tmp/csb-memcg-net.XXXXXX)
server_pids=
client_pids=

cleanup()
{
    for pid in $client_pids $server_pids; do
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
    i=1
    while [ "$i" -le "$workers" ]; do
        sudo -n rmdir "$cgroup_root/client-$i" 2>/dev/null || true
        i=$((i + 1))
    done
    sudo -n rmdir "$cgroup_root" 2>/dev/null || true
    rm -f "$tmpdir"/*.json "$tmpdir"/*.log
    rmdir "$tmpdir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sudo -n mkdir "$cgroup_root"
i=1
while [ "$i" -le "$workers" ]; do
    sudo -n mkdir "$cgroup_root/client-$i"
    port=$((5200 + i))
    iperf3 -s -1 -p "$port" >"$tmpdir/server-$i.log" 2>&1 &
    server_pids="$server_pids $!"
    i=$((i + 1))
done
sleep 1

start_ns=$(date +%s%N)
i=1
while [ "$i" -le "$workers" ]; do
    port=$((5200 + i))
    sudo -n "$script_dir/enter-cgroup.sh" "$cgroup_root/client-$i" \
        iperf3 -c 127.0.0.1 -p "$port" -R -t "$duration" -J \
        >"$tmpdir/client-$i.json" 2>"$tmpdir/client-$i.log" &
    client_pids="$client_pids $!"
    i=$((i + 1))
done

failures=0
for pid in $client_pids; do
    wait "$pid" || failures=$((failures + 1))
done
client_pids=
end_ns=$(date +%s%N)

metrics=$(python3 - "$tmpdir" "$workers" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
expected = int(sys.argv[2])
total = 0.0
complete = 0
for path in root.glob("client-*.json"):
    try:
        data = json.loads(path.read_text())
        total += float(data["end"]["sum_received"]["bits_per_second"])
        complete += 1
    except (OSError, ValueError, KeyError, TypeError):
        pass
print(f"{total / 1e9:.6f} {complete} {expected - complete}")
PY
)
set -- $metrics
aggregate_gbps=$1
completed=$2
parse_failures=$3
failures=$((failures + parse_failures))
elapsed_ns=$((end_ns - start_ns))
elapsed_seconds=$(python3 -c "print(f'{$elapsed_ns / 1e9:.9f}')")
gbps_per_client=$(python3 -c "print(f'{$aggregate_gbps / $workers:.6f}')")

printf 'aggregate_gbps=%s;gbps_per_client=%s;clients_completed=%s;failures=%s;elapsed_seconds=%s;workers=%s;tool=iperf3_reverse_loopback;\n' \
    "$aggregate_gbps" "$gbps_per_client" "$completed" "$failures" \
    "$elapsed_seconds" "$workers"
[ "$failures" -eq 0 ]
