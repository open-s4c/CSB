# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import Optional
from config.list import ListConfig
import docker
import docker.errors
import sys
from utils.logger import bm_log, LogType
from utils.platform import get_os, OperatingSystem
from utils.topology import Topology
from config.policy import CoreAssignPolicy, PackGroup


class ContainersConfig(dict):
    MIN_NUM_STEPS: int = 6  # default minimum number of steps to set default container_list
    MAX_NUM_STEPS: int = 10  # default maximum number of steps to set default container_list
    CONFIG_KEY: str = "containers"
    DEFAULT_IMG: dict[OperatingSystem, str] = {
        OperatingSystem.openEuler: "hub.oepkgs.net/openeuler/openeuler",
        OperatingSystem.Ubuntu: "ubuntu:latest",
        OperatingSystem.Unsupported: "ubuntu:latest",
    }

    def __init__(
        self,
        container_list: Optional[ListConfig] = None,
        core_assignment_policy: CoreAssignPolicy = CoreAssignPolicy(),
        core_affinity_offsets: Optional[ListConfig] = None,
        core_count: int = 1,
        name: str = "",
        image: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        ContainersConfig represents the configuration for multiple containers.
        Represented as a JSON object.
        Parameters
        ----------
        container_list: Optional[ListConfig] = dynamically computed.
            Specifies the number of containers to run. When `container_list` is absent in the configuration,
            the default value is dynamically computed based on the number of available CPUs/Cores on the target machine.
        core_assignment_policy: CoreAssignPolicy = {"pack_group":"none", "cpu_order": "asc", "one_cpu_per_core": false}
            Configures the CPU assignment policy, i.e. which CPUs can be assigned to execution units (containers/native processes).
            Note that the policy is overwritten by `core_affinity_offsets`. If the users wish to use this configuration, they
            should make sure not to specify `core_affinity_offsets`.
        core_affinity_offsets: Optional[ListConfig] = core_count * [0, 1, 2, 3, ...]
            Specifies the cores that should be assigned to the containers.
            Note that the assignment of cores happens in ascending order by default.
            This configuration overwrites `core_assignment_policy`.
        core_count: int
            Number of cores to assign to each container.
        name: str
            The base name of the container.
        image: Optional[str] = same as the host OS e.g. ubuntu:latest on Ubuntu.
            The docker image name to use.
        port: Optional[int]
            The starting port number to use for the first container.
            Subsequent containers will use incremented port numbers.
            This configuration is relevant for networking benchmarks.
        -
        """
        super().__init__(
            image=image,
            name=name,
            core_count=core_count,
            port=port,
            core_assignment_policy=core_assignment_policy,
        )
        self.cpus: list[int]
        self.topo = Topology()
        self.core_count = core_count
        self.policy = CoreAssignPolicy.from_dict(core_assignment_policy)
        self.image = image if image is not None else self.DEFAULT_IMG[get_os()]
        self.name = name
        self.port = port
        # needs some of the previous fields to be set
        self.__set_cpus_containers(
            core_affinity_offsets=core_affinity_offsets, container_list=container_list
        )
        self.__ensure_img_exists()

    def __set_cpus_containers(self, core_affinity_offsets, container_list):
        """
        Sets self.container_list and self.cpus

        """
        if core_affinity_offsets is None:
            pre_selected_cpus = None
            # we decide number of available CPUs based on the policy.
            # we use number of cores if the policy requests one CPU per core.
            num_avail_cpus = (
                self.topo.get_core_count()
                if self.policy.one_cpu_per_core
                else self.topo.get_cpu_count()
            )
        else:
            pre_selected_cpus = ListConfig.from_dict(core_affinity_offsets).get_list()
            # if the user wants specific CPUs then we use the count of the specified CPUs.
            num_avail_cpus = len(pre_selected_cpus)

        if container_list is None:
            # if the user did not configure how many containers to run
            # we generate a list from 1 -> max, where max will be the maximum
            # number of containers we can run with without causing oversubscription
            max_num_containers = num_avail_cpus // self.core_count
            bm_log(
                f"""
                   Maximum number of container we can use without causing oversubscription is {max_num_containers}.
                   {self.core_count} CPUs will be used per container.
                   {num_avail_cpus} CPUs are available in total.
            """
            )
            self.container_list = self.__gen_container_list(max_num_containers)
            # at the moment we don't respect the pack group policy when
            # determining max #containers, hence when the policy is set to pack by
            # e.g NUMA this can lead to oversubscription. For the time being
            # we treat it as a misconfiguration.
            if self.policy.pack_group != PackGroup.NO_PACK:
                bm_log(
                    """
                       Expecting "pack_group": "none" in configuration, or
                       absent "core_assignment_policy", when default "container_list"
                       is dynamically computed. CPUs oversubscription might occur.
                       """,
                    LogType.ERROR,
                )
                # we don't need to quit, the run can still be useful if the user
                # does not want to interrupt it, and is ok with oversubscription.
        else:
            self.container_list = ListConfig.from_dict(container_list).get_list()
        # Calculate the maximum number of CPUs needed.
        # max number of containers * cores per container
        max_cpu_count = max(self.container_list) * self.core_count

        self.cpus = self.topo.select(
            count=max_cpu_count, policy=self.policy, pre_selected=pre_selected_cpus
        )

    def __gen_container_list(self, max_num_containers) -> list[int]:
        num_steps = int((self.MIN_NUM_STEPS + self.MAX_NUM_STEPS) / 2)
        if num_steps < 1:
            num_steps = 1
        if max_num_containers < 1:
            max_num_containers = 1
        if max_num_containers < num_steps:
            step = 1
            max = max_num_containers
        else:
            # find the closest number to max_num_containers that is divisible by NUM_STEPS
            # and does not exceed it
            max = (max_num_containers // num_steps) * num_steps
            step = max // num_steps
            if step < 1:
                step = 1
            while (max // step) > self.MAX_NUM_STEPS:
                step = step * 2
            while step > 1 and (max // step) < self.MIN_NUM_STEPS:
                step = step // 2

        # we start range from zero and use max + 1, so that the last value will max
        # Always add 1 and max_num_containers
        default_container_list = list(range(0, max + 1, step))
        assert default_container_list[0] == 0, "unexpected, given the range starts with zero"
        # we remove zero from the list
        default_container_list.remove(0)
        # make sure first element of the list is one
        if default_container_list[0] != 1:
            # insert don't overwrite
            default_container_list.insert(0, 1)
        if default_container_list[-1] != max_num_containers:
            default_container_list.append(max_num_containers)

        return default_container_list

    def get_container_cnt_list(self) -> list[int]:
        return self.container_list

    def get_cpu_pool(self) -> list[int]:
        """
        Returns the list of CPUs that the benchmark is allowed to use.
        """
        # we use set here, because we don't want duplicated items
        # this is only used for collecting information.
        return list(set(self.cpus))

    def get_cpus(self, eu_idx: int) -> str:
        """
        Returns a list, in string format, of the CPUs that should be assigned
        to the given execution unit (identified by its) index.
        """
        first = eu_idx * self.core_count  # first index
        last = first + self.core_count  # last index (exclusive)
        assert last <= len(self.cpus)
        cpus_lst = self.cpus[first:last]
        assert len(cpus_lst) == self.core_count
        cpus_str: str = ",".join(map(str, cpus_lst))
        bm_log(f"Execution Unit#{eu_idx} will be assigned CPUS: {cpus_str}")
        return cpus_str

    def __pull_image(self):
        client = docker.from_env()
        bm_log(f"Docker image {self.image} does not exist. Pulling it now...\n", LogType.INFO)
        try:
            client.images.pull(self.image)
        except Exception as e:
            bm_log(f"Failed to pull image {self.image} with error {str(e)}", LogType.FATAL)
            sys.exit(1)

    def __ensure_img_exists(self):
        client = docker.from_env()
        try:
            client.images.get(self.image)
        except docker.errors.ImageNotFound:
            self.__pull_image()
