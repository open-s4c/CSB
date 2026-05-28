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

# Edit config
edit the auto-generation `config.json`

- change args to  `"args": ["/bin/true"]`
- change `"terminal": true` to `"terminal": false`
- change `"ociVersion": "1.2.1"` to `"ociVersion": "1.0.2"`

# sanity check

- `sudo crun run cgroups`
- `crun list`
