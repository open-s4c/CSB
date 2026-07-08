# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from dominate import document
from dominate.tags import style, table, tr, td, div, img, h1, h2, a, iframe, br
import datetime
import base64
import re
from benchkit.benchmark import PathType


class Report:
    def __init__(self, title: str, add_title_date: bool = True):
        self.doc = document(title=title)
        if add_title_date:
            self.doc.add(h1(f"Title: {title}"))
            self.doc.add(
                h2(f"Datetime: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S.%f')}")
            )
        self.__add_css_style()

    def add_chapter(self, chapter_title: str):
        self.doc.add(br())
        self.doc.add(h2(chapter_title))

    def add_table(self, data: dict[str, str]):
        tbl = table()
        for k, v in data.items():
            row = tr()
            row.add(td(k))
            row.add(td(v))
            tbl.add(row)
        self.doc.add(tbl)

    def embed_plots(self, plot_lists: list[list[str]], show_path: bool = True):
        tbl = table()
        for list in plot_lists:
            row = tr()
            tbl.add(row)
            for plot_path in list:
                img_div = (
                    self.embed_svg(plot_path)
                    if plot_path.endswith(".svg")
                    else self.embed_img(plot_path)
                )
                cell = div()
                cell.add(a(img_div, href=plot_path))
                if show_path:
                    cell.add(a(plot_path, href=plot_path, _class="png_title"))
                row.add(td(cell))
        # append the plots/graphs table to the given document
        self.doc.add(tbl)

    def __add_css_style(self):
        self.doc.add(
            style(
                """table {
                    width: 100%;
                    background-color: #FFFFFF;
                    border-collapse: collapse;
                    border-width: 2px;
                    border-color: #7ea8f8;
                    border-style: solid;
                    color: #000000;
                }
                td,  th {
                    border-width: 2px;
                    border-color: #7ea8f8;
                    border-style: solid;
                    padding: 5px;
                }
                thead {
                    background-color: #7ea8f8;
                }
                h1, h2 {
                    text-align: center;
                    font-color: blue;
                }
                .png_title {
                    font-size: 14px;
                    font-style: italic;
                }
                """
            )
        )

    def save(self, report_file_name: PathType):
        with open(report_file_name, "w") as f:
            f.write(self.doc.render())

    @staticmethod
    def embed_img(path: PathType) -> div:
        data_uri = base64.b64encode(open(path, "rb").read()).decode("utf-8")
        img_tag = f"data:image/png;base64,{data_uri}"
        return div(img(src=img_tag))

    @staticmethod
    def embed_svg(path: PathType) -> div:
        with open(path, "r") as file:
            svg_content = file.read()
        # extract height from svg content
        height = re.search(r'height="([^"]+)"', svg_content)
        h = height.group(1) if height else "1200"
        # Note that we put each svg into an iframe to avoid all types of conflicts
        # on IDs, styles, global variable names etc.
        # The content of iframe will be rendered as a separate html document
        return div(iframe(srcdoc=svg_content, width="100%", height=f"{h}px"))
