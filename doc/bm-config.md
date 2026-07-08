# Overall Configuration
 The overall configuration of a benchmark combines the setups of distinct components, such as application details and networking.  Only some components need to specified, as displayed below.  More information on each component is detailed in their own documentations.  If an object contains duplicate keys, the last one is used.  
|Type|Optional|JSON Representation|
|---|---|---|
|[BenchmarkConfig](#benchmarkconfig)|:white_check_mark:|`{...}`|
|[Application](#application)|:x:|`[...]`|
|[ContainersConfig](#containersconfig)|:white_check_mark:|`{...}`|
|[Plugin](#plugin)|:white_check_mark:|`[...]`|
|[PlotConfig](#plotconfig)|:white_check_mark:|`[...]`|
|[NicsConfig](#nicsconfig)|:white_check_mark:|`{...}`|

## BenchmarkConfig
General configuration for benchmarks, as well as a collection of system-level metrics (specified under monitors). Represented as one JSON object. 
<br/>***JSON key: "benchmark_config"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|duration|int|:white_check_mark:|`3`|    Duration of the benchmark in seconds.     JSON example: `"repeat": 3` |
|repeat|int|:white_check_mark:|`1`|    Number of times the benchmark should be repeated.     JSON example: `"repeat": 1` |
|initial_size|list[int]|:white_check_mark:|`[0]`|    The initial size parameter that should be passed     to the benchmark initialization.     JSON example: `"initial_size" : [1, 1000]` |
|noise|list[int]|:white_check_mark:|`[0]`|    How many `nop` operations to run between real     operations.     JSON example: `"noise" : [0, 1000]` |
|exec_env|dict[[ExecutionType](#executiontype), list[str]]|:white_check_mark:|`{"native":[], "container":[]}`|    Dictates in which environments the benchmark is executed, and which     extra arguments are used. Note that currently the arguments are     only considered in case of `bwrap`.     JSON example: `"exec_env" : {"native":[], "container":[], "bwrap":["--die-with-parent"]}` |
|monitors|dict[[MonitorType](#monitortype), list[str]]|:white_check_mark:|`{}`|    Monitors to run in the background. |
|threads|[ListConfig](#listconfig)|:white_check_mark:|`{"values": [[1]]}`|    Determines number of threads to run target benchmarks with.     If not provided all applications will be run with 1 thread. |

## Application
An application is either a builtin benchmark binary from the `bench` directory, or an external application/benchmark binary. This configuration defines an array of applications, each with their own setup. If this array has more than one application. each container will run an application from the array in a round robin fashion. Represented as a JSON array of objects.  
<br/>***JSON key: "applications"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|name|str|:x:||    The name of the application/benchmark binary. |
|operations|list[int]|:white_check_mark:|`[]`|    A list of integers representing the distribution of operations.     The sum of all values in the list must be equal to 1024.     Each index represents a specific operation as defined by the benchmark/application.     This is only relevant for builtin benchmarks. |
|path|Path|:white_check_mark:||    Specifies the relative path where the benchmark binary/script exists. This is     relevant to running external benchmarks that do not exist system wide under e.g. in `/usr/bin`.     Note that the path here should be relative to CSB (project) dir, which is mounted as     `/home` dir in the containers. When running an external benchmark, place its parent folder under     the project directory e.g. `CSB/bm-external/will-it-scale`, then specify `path` as     `bm-external/will-it-scale`. |
|args|str|:white_check_mark:|`-t={threads} -n={noise} -d={duration} -s={initial_size}`|    A string that represents the command line arguments of the application.     It can contain place holders for dynamic values. Available place holders:     are `{threads}`, `{noise}`, `{duration}`, `{index}`, `{initial_size}` and `{host_ip}`.     They are replaced at runtime with the actual values: number of threads, number of nop instructions following an operation,     duration of the benchmark in seconds, the index of the execution unit in the current benchmarking run, initial size of the data structure, and the host IP where CSB is running respectively.     If any of the above is relevant for the external application they can be used in the args     string. Otherwise they can be omitted. |
|adapter|[Adapter](#adapter)|:white_check_mark:|`{}`|    An adapter object.     This is only relevant for external applications/benchmarks. |
|cd|bool|:white_check_mark:|`false`|    When set to `true`, it changes the current directory to the given `path`, and     then runs the binary/script with the given `name`. When set to `false` and `path`     is given, the binary is run from the project directory as `path/name`. Use this     configuration with caution! This configuration is useful when running external     benchmarks that require to be run from their own directory, because they use     relative paths like unix bench. |

## ContainersConfig
ContainersConfig represents the configuration for multiple containers. Note that the same configuration (excluding image) parameters are used in native runs, where processes run on bare metal instead of inside containers. Represented as a JSON object. 
<br/>***JSON key: "containers"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|container_list|[ListConfig](#listconfig)|:white_check_mark:|`dynamically computed.`|    Specifies the number of containers/processes to run. When `container_list` is absent in the configuration,     the default value is dynamically computed based on the number of available CPUs/Cores on the target machine. |
|core_assignment_policy|[CoreAssignPolicy](#coreassignpolicy)|:white_check_mark:|`{"pack_group":"none", "cpu_order": "asc", "one_cpu_per_core": false}`|    Configures the CPU assignment policy, i.e. which CPUs can be assigned to execution units (containers/native processes).     Note that the policy is overwritten by `core_affinity_offsets`. If the users wish to use this configuration, they     should make sure not to specify `core_affinity_offsets`. |
|core_affinity_offsets|[ListConfig](#listconfig)|:white_check_mark:|`core_count * [0, 1, 2, 3, ...]`|    Specifies the cores that should be assigned to the containers.     Note that the assignment of cores happens in ascending order by default.     This configuration overwrites `core_assignment_policy`. |
|core_count|int|:white_check_mark:|`1`|    Number of cores to assign to each container. |
|name|str|:white_check_mark:||    The base name of the container. |
|image|str|:white_check_mark:|`same as the host OS e.g. ubuntu:latest on Ubuntu.`|    The docker image name to use. |
|port|int|:white_check_mark:||    The starting port number to use for the first container.     Subsequent containers will use incremented port numbers.     This configuration is relevant for networking benchmarks. |

## Plugin
Plugins are a flexible way to inject additional scripts/processes to be executed at different stages of the benchmark execution. A good example would be to start a client to communicate with a server benchmark before the server starts accepting connections. Represented as a JSON array of objects. 
<br/>***JSON key: "plugins"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|name|str|:x:||    Name of the script/process to be executed. |
|exec_time|[ExecutionTime](#executiontime)|:x:||    When to execute the script/process (pre, post, cleanup, with). |
|path|Path|:white_check_mark:||    Path to the script/process. It will look under scripts/plugins     or if it is available system wide. |
|args|list[str]|:white_check_mark:|`[]`|    List of arguments to be passed to the script/process.     It can include one place holder: `{homedir}`.     This is replaced at runtime with the path of the build directory of the CSB project. |
|force_stop|bool|:white_check_mark:|`False`|    Whether to forcefully stop the process if it is still running during cleanup. |

## PlotConfig
Plot configuration for benchmark results. Represented as a JSON array of objects.  
<br/>***JSON key: "plots"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|x|str|:white_check_mark:|`container_cnt`|    The column name to be used for the x-axis. |
|y|str|:white_check_mark:|`throughput_min`|    The column name to be used for the y-axis. |
|hue|str|:white_check_mark:|`execution_unit`|    The column name to be used for the hue/groupby. |
|x_lbl|str|:white_check_mark:|`{x}`|    The label for the x-axis. If None, defaults to `{x}`. |
|y_lbl|str|:white_check_mark:|`{y}`|    The label for the y-axis. If None, defaults to `{y}`. |
|hue_lbl|str|:white_check_mark:|`{hue}`|    The label for the hue/groupby. If None, defaults to `{hue}`. |
|title|str|:white_check_mark:|`{x_lbl} vs. {y_lbl}`|    The title of the plot. If None, defaults to `{x_lbl} vs. {y_lbl}`. |
|shape|str|:white_check_mark:||    The shape/type of the plot (e.g., 'lineplot', 'barplot'). If None, defaults based on `type`. |
|type|[PlotType](#plottype)|:white_check_mark:|`normal`|    The type of plot to be created, which determines default shape and other behaviors. |
|palette|UnionType[str, _ColorPalette]|:white_check_mark:|`hls`|    The color palette to use for the plot. |

## NicsConfig
NicsConfig configures the assignment of Network Interface Cards (NICs) or their Virtual Functions (VFs) to containers. Represented as a JSON object. 
<br/>***JSON key: "nics"***
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|nic_format|str|:x:||    A formatting string to get a NIC name for a containers. It supports a single formatting     argument `{i}` -- the index of the container in a benchmarking run. |
|ips|[ListConfig](#listconfig)|:x:||    Specifies the list of IP addresses that are assigned to a container sequentially in each     run. |
|netmask|int|:x:||    The IPv4 netmask to specify along with the IP address. |
|core_affinity_offsets|[ListConfig](#listconfig)|:white_check_mark:||    Specifies the cores that should be assigned to handle the NIC/VF IRQs.     Note that the assignment of cores will happen in ascending order. |
# Types

## Adapter
Adapters are used to transform the output of an external benchmark into the format understood by the framework: a line of `<key>=<val>;` pairs e.g. `throughput=1000;latency=20;`. If an adapter is used the output of the benchmark is piped to the adapter script. See scripts/adapters for examples.  
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|name|str|:x:||    Adapter script filename. |
|path|Path|:white_check_mark:||    The dir where the script exists. Required if it does not exist     system wide, or under script/adapters. |

## ListConfig

|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|values|list[Union[list[int], [RangeConfig](#rangeconfig)]]|:x:||    list of values each value an be either a list of integers, or `RangeConfig`     object.     JSON example `"values": [ [5, 6], {"min": 1, "step": 1, "max": 3 }, [12] ]}` |
|str_format|str|:white_check_mark:||    A formatting string. Used to convert the values into string.     JSON example: `"str_format": "127.0.0.{i}"`     with this string the values `i` is replaced by an integer from values     and the list become:     `["127.0.0.1", "127.0.0.2", "127.0.0.3", "127.0.0.5", "127.0.0.6", "127.0.0.12"]` |

## RangeConfig

|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|min|int|:x:||    start value     JSON example: `"min": 1` |
|max|int|:x:||    end value     JSON example: `"max": 5` |
|step|int|:x:||    increment step     JSON example: `"step": 2`     with min = 1, and max = 5, this becomes a list = `[1, 3, 5]` |

## CoreAssignPolicy
CPU/Core assignment policy for execution units, i.e. containers and native processes.  
|Field|Type|Optional|Default|Description|
|---|---|---|---|---|
|pack_group|[PackGroup](#packgroup)|:white_check_mark:|`none`|    Specifies the policy of CPU selection, whether in the same NUMA, same Package,     can cross packages, or distant. |
|cpu_order|[CpuOrder](#cpuorder)|:white_check_mark:|`asc`|    Specifies the assignment order, whether ascending to starting for CPU lowest index,     or descending starting from the highest CPU index.     This configuration is ignored if pack_group is distant. |
|one_cpu_per_core|bool|:white_check_mark:|`False`|    Whether to use only one CPU from each Core. This is relevant to hyper-threading     when multiple CPUs share the same core. When set to true, from each core only     the first CPU is considered. |
## MonitorType
Monitors are used to monitor performance. They can be used to analyze the behavior of the benchmarks.  <br/>Supported values:
- `"mpstat"`:  Runs mpstat and generates related graphs.
- `"perf"`:  Runs perf and generates flame-graphs.
- `"iostat"`:  Runs iostat -x and generates block-device graphs.
- `"redis_benchmark"`:  parses the output of redis_benchmark.
- `"sar_net"`:  monitors network traffic.
- `"perf_stat"`:  Runs perf stat.
- `"perf_lock"`:  Runs perf lock, and perf lock contention if supported. Lock-contention output is generated when the kernel exposes the required `perf lock` trace-points. Running `perf_lock` together with `perf` monitor can corrupt the `perf` monitor results.
- `"bpftrace"`:  Runs [bpftrace](https://bpftrace.org/docs/release_025/stdlib) with the given programs. Users may list programs from scripts/bpftrace. Giving multiple programs as arguments, will result in launching multiple instances of bpftrace.
## PlotType
Supported types of plots.  <br/>Supported values:
- `"normal"`:  Plots according to the config no post processing of data.
- `"mean"`:  Plots the mean value of execution units' throughput (`y` value specified in plot config) per run.
- `"min_max_avg"`:  Plots min, max optionally with percentile or average time of operations.
- `"histogram"`:  Experimental, Plots the distribution of operations.
- `"success_percent"`:  Experimental, Plots the percentage of successful operations.
- `"linearity"`:  Calculates and plots the linearity of the benchmark results.
- `"bpftrace_hist"`:  Exclusive graph for `bpftrace` monitor. To be used with programs that generate histogram data. Use the program name without `.bt` suffix in the plot `y` field. The plot will represent the summary of the collected data over all runs.
## ExecutionTime
Execution time of the plugin script/process.  <br/>Supported values:
- `"pre"`:  The script/process will be launched before the start signal.
- `"post"`:  The script/process will be launched after the start signal.
- `"cleanup"`:  The script/process will be called after the benchmark is finished or interrupted.
- `"with"`:  The script/process will be called at the same time as the benchmark as a wrapper. The order of the JSON array of objects indicates the order in which plugins are wrapped. For example, a plugins' array of `[{name: foo}, {name: bar}]` executed the command `foo bar <application>`.
## ExecutionType
Execution environment of the benchmarks.  <br/>Supported values:
- `"native"`:  Launches the benchmark(s) directly on the host OS.
- `"container"`:  Launches the benchmark(s) inside a container.
- `"bwrap"`:  Launches the benchmark(s) with bubblewrap.
## CpuOrder
Supported CPU orders.  <br/>Supported values:
- `"asc"`:  Assign CPUs in ascending order.
- `"desc"`:  Assign CPUs in descending order.
## PackGroup
Supported groups for packing.  <br/>Supported values:
- `"package"`:  Use CPUs that belong to package/socket zero only.
- `"numa"`:  Use CPUs that belong to NUMA/Node zero only.
- `"distant"`:  [Experimental-feature] Use CPUs at the maximum possible distant from each other.
- `"none"`:  CPUs crossing NUMA and package domains can be chosen.
## Environment Variables
CSB bm-runner has universal configuration that can overwrite default behavior and JSON config values. These are set via environment variables, and are read at runtime.  <br/>Supported values:
- `"CSB_NO_CLEAN_BENCH"`:  When set to `true`, it disables the cleaning of the build folder of builtin benchmarks.
- `"CSB_ANALYZE"`:  When set to `false`, it disables the analysis monitors.
- `"CSB_NO_BUILD_BENCH"`:  when set to `true`, it skips building *all* builtin benchmarks.
- `"CSB_PIN_MONITORS"`:  When set to `true`, all monitors will be pinned to a specific CPU.
- `"CSB_RESULTS_GROUP"`:  when set to <dir-name>, bm-runner dumps all results under results/<dir-name>.
- `"CSB_ARM_SPE"`:  when set to `true`, it checks of availability of arm_spe perf event and captures these events.
- `"CSB_BPFTRACE_FILTER"`:  can be used to overwrite the default filter of bpftrace `/ comm == "<comm>" /`. Note that `<comm>` is replaced by the first 15chars of the benchmark application name.
