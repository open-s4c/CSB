# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from config.plot import PlotConfig
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame
from utils.logger import LogType, bm_log
import seaborn as sns
import time


class PlotChart:
    def __init__(self, plot: PlotConfig):
        self.fig = plt.figure(dpi=150)

        self.chart = self.fig.add_subplot()
        self.chart.set_title(plot.title)

    def add(
        self,
        plot: PlotConfig,
        df: DataFrame,
        add_points: bool = False,
        **kwargs,
    ):
        args = dict(kwargs)
        # prep hue, we want to generate enough colors
        cnt = df[plot.hue].nunique()
        sorted_gp = sorted(df[plot.hue].unique())
        if isinstance(plot.palette, str):
            palette = sns.color_palette(palette=plot.palette, n_colors=cnt)
        else:
            palette = plot.palette
        sns_plot_fun = getattr(sns, plot.shape)

        if (
            not PlotChart.__col_exists(df, plot.y, plot.title)
            or not PlotChart.__col_exists(df, plot.x, plot.title)
            or not PlotChart.__col_exists(df, plot.hue, plot.title)
        ):
            return

        chart = sns_plot_fun(
            ax=self.chart,
            data=df,
            palette=palette,
            x=plot.x,
            hue=plot.hue,
            hue_order=sorted_gp,
            y=plot.y,
            **args,
        )
        if add_points:
            sns.scatterplot(
                x=plot.x,
                y=plot.y,
                hue=plot.hue,
                markers=plot.hue,
                data=df,
                hue_order=sorted_gp,
                palette=palette,
                ax=chart,
                legend=False,
            )

        # calculate maximum length of x values
        max_len = max(len(str(x)) for x in df[plot.x])
        # rotate the xticks to avoid overlap of string
        if max_len > 10:
            plt.xticks(rotation=90)

        chart.set(xlabel=plot.x_lbl, ylabel=plot.y_lbl)
        chart.grid(True)
        new_ylim = 1.2 * pd.to_numeric(df[plot.y], errors="coerce").dropna().max()
        if np.isfinite(new_ylim):
            chart.set_ylim(0, 1 if new_ylim == 0 else new_ylim)
        else:
            bm_log(
                f"Tried to setup an invalid Y={new_ylim} on `{plot.y_lbl}` axis limit at `{plot.title}` plot!",
                LogType.WARNING,
            )

        plt.legend(
            loc="upper left",
            title=f"{plot.hue_lbl}",
            bbox_to_anchor=(1, 1),
            borderaxespad=0.3,
            fontsize=4.5,
        )

    def save(self, out_fig_name, gen_pdf: bool = False) -> str:

        self.fig.set_size_inches(w=10, h=8)
        self.fig.tight_layout()

        figure_name = f"{out_fig_name}_{time.perf_counter()}"
        self.fig.savefig(f"{figure_name}.png", transparent=False)
        if gen_pdf:
            self.fig.savefig(f"{figure_name}.pdf", transparent=False)
        plt.close()

        return f"{figure_name}.png"

    @staticmethod
    def __col_exists(df: DataFrame, col: str, title: str) -> bool:
        if col not in df.columns:
            bm_log(
                f"cannot find column {col} in the produced data. This plot `{title}` will not be generated!",
                LogType.ERROR,
            )
            return False
        return True

    @staticmethod
    def plot(
        plot: PlotConfig,
        df: DataFrame,
        out_fig_name,
        add_points: bool = False,
        gen_pdf: bool = False,
        **kwargs,
    ) -> str:
        pc = PlotChart(plot)
        pc.add(plot, df, add_points=add_points, **kwargs)
        return pc.save(out_fig_name, gen_pdf)
