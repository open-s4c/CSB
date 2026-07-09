# CSB Generator

CSB generator found in bm-generator is a tool that extends [syzkaller][] and uses [tmplr][] to auto-generate benchmarks and JSON configuration files
compatible with the CSB framework [bm-runner][].

The generator takes an [strace][] log file as an input.

## Disclaimer
This tool is currently experimental and still in the prototype phase.

At the moment, users are expected to run benchmark generation scripts on the target machine, where the benchmarks
will be run and analyzed.

## Requirements

### Install golang

[syzkaller][] requires golang of version 1.25.x to be installed.

Critically, on Ubuntu 22.04, `apt install golang-go` uses version 18.1 which *does not* work.

You can install [golang][] as follows:
```bash
cd bm-generator/helper/
./install_go.sh
```

Make sure to add the golang binary directory to your PATH environment variable and re-login to your terminal session.
Put the following line into `$HOME/.bashrc`
```bash
export PATH=$PATH:/usr/local/go/bin
```

If installation fails, use the following instructions:

1. Verify if golang is installed with the correct version
```bash
go version
# result should be "go version go1.25.x ..."
```
2. If the version is incorrect *and* go is installed, then uninstall it with
  ```bash
  sudo apt remove golang-go
  ```
  - Check that has worked with
  ```bash
  ls /usr/local/go
  ```
  - If the directory is not empty, then uninstall it with:
  ```bash
  rm -rf /usr/local/go
  ```
3. Download golong from the official website:
```bash
wget https://go.dev/dl/go1.25.5.linux-amd64.tar.gz
```
  - Note: make sure that the file downloaded match your architecture (i.e., amd64 for x86-64 and arm64 for Arm).
4. Decompress file and place it in executables directory
```bash
tar -C /usr/local -xzf go1.25.5.linux-amd64.tar.gz
```
5. Add directory into PATH environment variable by adding the following line into `$HOME/.bashrc`
```bash
export PATH=$PATH:/usr/local/go/bin
```
  - Note: this change is only applied by closing and then reopening the terminal
6. Check that the correct golang was installed with
```bash
go version
# result should be "go version go1.25.x ..."
```

For more details, you can check the go installation website:
https://go.dev/doc/install


## Generating Benchmarks

The pipeline for generating benchmarks is implemented in
the following scripts within `bm-generator/`:

|Script|Description|
|---|---|
|`00_init.sh`| Checks and possibly updates/installs golang as well as cloning the syzkaller repository. |
|`01_build.sh`| Builds the syzkaller tools necessary to automatically generate test cases from strace logs. |
|`02_parse.sh`| Parses an strace log file into the [syzlang][] internal representation of syzkaller. It outputs one [syzlang][] program for each strace log file. Output is stored in `deserialized/0/program_<id1>.prog` |
|`03_extract.sh`| Analyzes all `deserialized/*/*.prog` [syzlang][] programs. For each input program, a dependency graph for all syscalls is computed. It outputs one [syzlang][] program per dependency graph into `extracted/min_<id2>.prog` |
|`04_prepare.sh`| Processes all `extracted/*.prog` [syzlang][] programs. Each input program is converted into a C header containing a function calling all dependent syscalls from the input [syzlang][] program. Output is stored in `../bench/targets/gen-ws/syz/min_<id3>.h` |
|`05_generate.sh`| Uses [tmplr][] to generate [bm-runner][] compatible headers and JSON configuration for all generated `../bench/targets/gen-ws/syz/min_<id3>.h` files. Output is stored as `../bench/targets/gen-ws/min_<id3>.h` header and `../../config/gen-ws/fg_min_<id3>.json`. |
|`06_select.sh`| Runs all the auto-generated benchmarks for a short duration, performs pairwise comparison of the flamegraphs of the benchmark execution, and prints a list of benchmarks that are different enough from each other. |

The only script that takes an argument is `02_parse.sh`, which needs a path to an strace log file generated as described below.
```bash
./02_parse.sh </path/to/strace.log>
```

### Collect strace

Use the following [strace][] command to collect `strace.log`.

_Note: replace `<app-binary>` with the name of your binary/application including all necessary arguments._

_Note: strace must be previously installed using the command `dnf install strace`._

```bash
./scripts/collect_strace.sh strace.log <app-binary>
```

Alternatively:

```bash
strace -o strace.log -a 1 -s 65500 -v -xx -f -Xraw --raw=wait4 <app-binary>
```

The scripts should be run in the same order they are enumerated:

```bash
cd bm-generator/
./00_init.sh
./01_build.sh
./02_parse.sh strace.log
./03_extract.sh
./04_prepare.sh
./05_generate.sh
./06_select.sh
```

Generator scripts intentionally fail on non-empty output directories. This is a
guard against accidentally mixing generated benchmark sets; remove or rename the
existing output directory before regenerating unless intentionally debugging the
generator.

## CSB syzkaller fork

The CSB syzkaller fork extends upstream syzkaller primarily in these areas:

- `tools/syz-trace2syz/`: strace parsing and `.prog` serialization. Notable
  flags include `-deserialize`, `-nocorpus`, `-topCalls`, `-splitThreads`, and
  `-argLength`.
- `prog/`: serialization/deserialization and CSB-specific annotations such as
  strace TIDs, return values, clone/resource annotations, and dependency
  minimization helpers.
- `tools/syz-extraction/`: dependency minimization, poll filtering,
  deterministic TID iteration, and minimum call count filtering.
- `tools/syz-prog2c/` and `pkg/csource/`: C/CSB header generation, path, socket
  and file sanitization, file descriptor lifecycle handling, shared buffers,
  metadata, and CSB config output.
- `executor/` and `sys/linux/sys.txt*`: runtime helpers and syscall
  descriptions when needed.

Build the syzkaller tools from the nested repository:

```bash
cd deps/syzkaller
make trace2syz prog2c extraction
```

Focused tests for syzkaller-side CSB changes:

```bash
cd deps/syzkaller
go test ./tools/syz-trace2syz/parser ./tools/syz-trace2syz/proggen
go test ./prog ./pkg/csource
go test ./tools/syz-extraction ./tools/syz-prog2c ./tools/syz-trace2syz
```

## Deduplicating the set of autogenerated microbenchmarks:

The benchmarks generated by bm-generator may contain redundancy: for example, system call sequences that differ only in a file name in the same directory will be considered to be different, even though their effect on the system is the same.

To filter out such benchmarks, we introduce a pipeline based on flamegraph difference calculation:
- For each benchmark, the flamegraph is recorded and post-processed (see details below).
- Each of the collapsed stacks of the flamegraph is passed to `diffolded.pl` to calculate the difference of flamegraphs, and the maximum detected difference for a single stack (in either diff direction) is reported.
- Benchmarks which differ from each other by less than a certain threshold, are considered to be the same, and only of them is kept, while others are ignored.

Before passing the stacks to the `difffolded.pl` the flamegraph is postprocessed: in particular, the userspace stacks are dropped from the flamegraph, and only kernel stacks are kept.
Futhermore, the name of the benchmark application is replaced with a generic one: this allows side-stepping `difffolded.pl` limitation that permits calculation of the diff only for the applications with the same name.
This directly allows comparing the postprocessed flamegraphs of the autogenerated microbenchmarks with each other as well as with the postprocessed flamegraph of the original application.

To run the benchmarks selection pipeline after generation of the microbenchmarks, you can run:
```bash
./06_select.sh
```
Alternatively, you can use the manual workflow outlined below.

### Manual workflow

To perform the deduplication, CSB provides a set of scripts in the `CSB/scripts/fg-diff` directory, driven by `./CSB/scripts/fg-diff/select-benchmarks.sh` script.
The operation workflow looks like the following:
```
$ cd CSB # this is important; the script will not work from a different directory
$ ./scripts/fg-diff/select-benchmarks.sh ./config/min_mysql_*.json
```
The last command takes as arguments the list of JSON config files of the microbenchmarks to execute for inclusion into the comparison.
In case no config files are provided, no new benchmarks are executed and only the results already present in the `results` directory are taken into account.

The output of the script is a list of benchmark names that are distinct from each other, according to the flamegraph difference criterion.

## Excluded syscalls for bm-generator

The following list of syscalls is parsed by bm-generator, but excluded from [syzlang][] program generation.

|Syscall|Reason|
|---|---|
|execve|Replaces actual benchmark program|
|arch_prctl|Unsafe to set process properties|
|wait, wait4, clone, futex|Multithreaded tests are not supported|
|mmap, msync, mremap, mprotect, madvise, munmap | Might interfere with mmap'ed memory for test |
|rt_sig* |Sigset cannot be evaluated, yet|
|rt_sigaction|Function pointers are not recovered by strace|
|set_robust_list, set_tid_address|Glibc issued calls mostly uninteresting|
|io_setup, io_getevents, io_* |AOI syscalls are paired by resources passed in memory pointers (io_ctx), not supported yet.|
|write|Supported, but if used on file descriptor 1 or 2 (stdout, stderr) these are dropped to avoid output parsing issues|
|read|Supported, but if used on file descriptor 0 (stdin) these are dropped to avoid blocking|


## Generating JSON files

Users can generate JSON files for any group of generated benchmark headers.
The generator reads input headers from:
`bench/targets/<group>/syz/*.h` and writes the generated JSON files to `config/<group>/`

By default, `<group>` is `gen-ws`. To generate JSON files for another group,
set the environment variable `CSB_RESULTS_GROUP` before running the CMake build target.

For example, to generate JSON files for headers in `bench/targets/my-group/syz/`:

```bash
cd csb
export CSB_RESULTS_GROUP=my-group
cmake -S. -B build -DCSB_BM_GENERATOR=ON
cmake --build build --target bm_single.json.in
```
Note that `bm_single.json.in` is a template that exists under `bm-generator/templates/`.
Users can also create their own templates and generate for them, provided that
the template name matches `*single*.json.in`

[strace]: https://github.com/strace/strace
[tmplr]: https://github.com/open-s4c/tmplr
[syzkaller]: https://github.com/open-s4c/syzkaller/tree/s4c/
[bm-runner]: doc/bm-runner.md
[golang]: https://go.dev/doc/install
[syzlang]: https://github.com/google/syzkaller/blob/master/docs/syscall_descriptions_syntax.md
