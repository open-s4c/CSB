# cgroups v2 Benchmark

## Requirements

### cgroups version

- First check if cgroups v2 is enabled

You can verify as follows, run:
```bash
stat -fc %T /sys/fs/cgroup/
```
Run and verify the output is `cgroup2fs`.
This is only reliable if cgroup was mounted under `/sys/fs`
A more reliable way to check is to read `/proc/mounts`

```bash
cat /proc/mounts | grep cgroup
```
Check that the output has `cgroup2`, e.g.:

```
cgroup2 /sys/fs/cgroup cgroup2 rw,nosuid,nodev,noexec,relatime,nsdelegate,memory_recursiveprot 0 0
```

- Enable `cgroup2` on openEuler
If  `cgroup2` is not enabled then one can enable it as follows:

- Run `sudo vi /etc/default/grub`
- Edit the file as follows and save:
  append `systemd.unified_cgroup_hierarchy=1` to `GRUB_CMDLINE_LINUX` line  `GRUB_CMDLINE_LINUX="... systemd.unified_cgroup_hierarchy=1"`
- Run `sudo grub2-mkconfig -o /boot/efi/EFI/openEuler/grub.cfg`
- Run `sudo reboot`

Note that you need docker version 20.10+. Older docker versions do not support cgroups v2.

### Toybox

Before launching the benchmark for the first time run the prepare script.

```bash
scripts/bm-external/cgroups/prepare.sh
```

The script will download [toybox](https://landley.net/toybox/bin/) and create `bm-external/cgroups/rootfs` and `bm-external/cgroups/config.json`.

These are required by the cgroups benchmark.


# Running the benchmark

This benchmark may require `sudo` to run correctly.

Users can run it as follows:

```bash
CSB_BPFTRACE_FILTER='/ comm == "runc" /' ./scripts/run-single.sh config/bm-external/cgroups/runc.json
```

For running the benchmark with the [youki](https://github.com/youki-dev/youki) runtime, please make `youki` executable available in the `$PATH`, and then run:

```bash
CSB_BPFTRACE_FILTER='/ comm=="youki" || comm=="youki:[1:INTER]" || comm=="youki:[2:INIT]" /'  ./scripts/run-single.sh config/bm-external/cgroups/youki.json
```
