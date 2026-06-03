# cgroups v2 Benchmark

## Requirements

Before launching the benchmark for the first time run the prepare script.

```bash
scripts/bm-external/cgroups/prepare.sh
```

The script will download [toybox](https://landley.net/toybox/bin/) and create `bm-external/cgroups/rootfs` and `bm-external/cgroups/config.json`.
These are required by the cgroups benchmark.

# Run the following in this folder

```bash
runc spec
mkdir rootfs
cd rootfs/
wget https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox
chmod +x busybox
mkdir -p bin
ln -s /busybox bin/sh
ln -s /busybox bin/ls
ln -s /busybox bin/echo
ln -s /busybox bin/true
```



# Toybox

[Available binaries](https://landley.net/toybox/bin/)

- https://landley.net/toybox/bin/toybox-aarch64
- https://landley.net/toybox/bin/toybox-x86_64


```bash
mv toybox-aarch64 toybox
chmod +x toybox
mkdir bin
cd bin
for cmd in $(../toybox); do ln -s ../toybox "$cmd"; done
cd ..
cd ..
runc spec  # or runc spec --rootless
sed -i 's/"args": \[[^]*\]/"args": ["\/bin\/sh"]/g' config.json

```

# Edit config
edit the auto-generation `config.json`

- change args to  `"args": ["/bin/true"]`
- change `"terminal": true` to `"terminal": false`
- change `"ociVersion": "1.2.1"` to `"ociVersion": "1.0.2"`

# sanity check

- `sudo runc run cgroups` # or in rootless `runc --root /tmp/runc-rootless run cgroups`
- `crun list`
