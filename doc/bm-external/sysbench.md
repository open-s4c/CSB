# Using Sysbench

Install sysbench dependencies. On openEuler:
```bash
sudo dnf install mariadb-server mariadb-devel mariadb-connector-c postgresql-server postgresql-server-devel libpq libpq-devel autoconf automake libtool pkgconf-pkg-config gcc make
```

Install sysbench from git tree using:
```bash
sudo scripts/bm-external/sysbench/configure.sh
```

To run just one instance in bare metal host, run:
```bash
sudo scripts/bm-external/sysbench/prepare.py
```
