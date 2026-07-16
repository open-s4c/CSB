# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import Optional
from typing import TypeAlias

import seaborn as sns


class PlotType(str, Enum):
    """
    Supported types of plots.

    Members
    ----------
    NORMAL: Plots according to the config no post processing of data.
    MEAN: Plots the mean value of execution units' throughput (`y` value specified in plot config) per run.
    MIN_MAX_AVG: Plots min, max optionally with percentile or average time of operations.
    SUCCESS_PERCENT: Experimental, Plots the percentage of successful operations.
    LINEARITY: Calculates and plots the linearity of the benchmark results.
    BPFTRACE_HIST: Exclusive graph for `bpftrace` monitor. To be used with programs that generate histogram data. Use the program name without `.bt` suffix in the plot `y` field. The plot will represent the summary of the collected data over all runs.
    """

    NORMAL = "normal"
    MEAN = "mean"
    MIN_MAX_AVG = "min_max_avg"
    SUCCESS_PERCENT = "success_percent"
    LINEARITY = "linearity"
    BPFTRACE_HIST = "bpftrace_hist"


PlotPalette: TypeAlias = sns.palettes._ColorPalette


class PlotConfig(dict):
    CONFIG_KEY: str = "plots"

    DEFAULT_PLOT: dict[PlotType, str] = {
        PlotType.NORMAL: "lineplot",
        PlotType.MEAN: "lineplot",
        PlotType.MIN_MAX_AVG: "barplot",
        PlotType.BPFTRACE_HIST: "barplot",
        PlotType.SUCCESS_PERCENT: "barplot",
        PlotType.LINEARITY: "lineplot",
    }

    def __init__(
        self,
        x: str = "container_cnt",
        y: str = "throughput_min",
        hue: str = "execution_unit",
        x_lbl: Optional[str] = None,
        y_lbl: Optional[str] = None,
        hue_lbl: Optional[str] = None,
        title: Optional[str] = None,
        shape: Optional[str] = None,
        type: PlotType = PlotType.NORMAL,
        palette: str | PlotPalette = "hls",
    ):
        """
        Plot configuration for benchmark results.
        Represented as a JSON array of objects.

        Parameters
        ----------
        x: str
            The column name to be used for the x-axis.
        y: str
            The column name to be used for the y-axis.
        hue: str
            The column name to be used for the hue/groupby.
        x_lbl: Optional[str] = {x}
            The label for the x-axis. If None, defaults to `{x}`.
        y_lbl: Optional[str] = {y}
            The label for the y-axis. If None, defaults to `{y}`.
        hue_lbl: Optional[str] = {hue}
            The label for the hue/groupby. If None, defaults to `{hue}`.
        title: Optional[str] = {x_lbl} vs. {y_lbl}
            The title of the plot. If None, defaults to `{x_lbl} vs. {y_lbl}`.
        shape: Optional[str]
            The shape/type of the plot (e.g., 'lineplot', 'barplot'). If None, defaults based on `type`.
        type: PlotType
            The type of plot to be created, which determines default shape and other behaviors.
        palette: str
            The color palette to use for the plot.
        -
        """
        super().__init__(
            x=x,
            y=y,
            hue=hue,
            x_lbl=x_lbl,
            y_lbl=y_lbl,
            hue_lbl=hue_lbl,
            title=title,
            shape=shape,
            type=type,
            palette=palette,
        )
        self.x = x
        self.y = y
        self.hue = hue
        self.x_lbl = x_lbl if x_lbl is not None else self.x
        self.y_lbl = y_lbl if y_lbl is not None else self.y
        self.hue_lbl = hue_lbl if hue_lbl is not None else self.hue
        self.title = title if title is not None else f"{self.x_lbl} vs. {self.y_lbl}"
        self.type = type
        self.shape = shape if shape is not None else self.DEFAULT_PLOT[self.type]
        self.palette = palette
        self._fname = f"{self.x}_vs_{self.y}_{PlotType(self.type).value}"

    def set_palette(self, palette: PlotPalette | str):
        self.palette = palette

    @property
    def fname(self):
        return self._fname

    @fname.setter
    def fname(self, value):
        self._fname = value
