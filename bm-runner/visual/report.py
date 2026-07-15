# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from dominate import document
from dominate.tags import style, table, tr, td, div, img, h1, h2, a, iframe, br
import datetime
import base64
import re
from benchkit.benchmark import PathType
from bm_utils import get_path_rel_to_csb


class Report:
    CSS_STYLE = """
        table {
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
        a, img {
            width: 100%;
        }
        a {
            white-space: normal;
            overflow-wrap: break-word;
            word-break: break-word;
        }

    """

    def __init__(self, title: str, add_title_date: bool = True, css_style=CSS_STYLE):
        self.doc = document(title=title)
        if add_title_date:
            self.doc.add(h1(f"Title: {title}"))
            self.doc.add(
                h2(f"Datetime: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S.%f')}")
            )
        self.__add_css_style(css_style)

    def add_line(self, text):
        self.doc.add(br(text))

    def add_chapter(self, name: str, level=1):
        match level:
            case 1:
                self.doc.add(h1(name))

            # Currently, only two levels are supported
            case _:
                self.doc.add(h2(name))

    def add_table(self, data: dict[str, str]):
        tbl = table()
        for k, v in data.items():
            row = tr()
            row.add(td(k))
            row.add(td(v))
            tbl.add(row)
        self.doc.add(tbl)

    def embed_plots(self, plot_lists: list[list[str]], show_path: bool = True):
        """
        Parameters
        ---
        plot_lists : list[list[str]]
            a list of lists. Each list is added to the table as a row, and each element is a cell.
        """
        if len(plot_lists) == 0:
            return
        tbl = table()
        num_cols = max(map(len, plot_lists))
        width = 100 / num_cols
        for list in plot_lists:
            row = tr()
            tbl.add(row)
            for plot_path in list:
                if not plot_path:
                    row.add(td("", width=f"{width}%"))
                    continue

                img_div = (
                    self.embed_svg(plot_path)
                    if plot_path.endswith(".svg")
                    else self.embed_img(plot_path)
                )
                cell = div()
                cell.add(a(img_div, href=plot_path))
                if show_path:
                    relative_path = get_path_rel_to_csb(plot_path)
                    cell.add(a(relative_path, href=str(plot_path)))
                row.add(td(cell, width=f"{width}%"))
        # append the plots/graphs table to the given document
        self.doc.add(tbl)

    def __add_css_style(self, css_style):
        self.doc.add(style(css_style))

    def save(self, report_file_name: PathType):
        with open(report_file_name, "w") as f:
            f.write(self.doc.render())

    @staticmethod
    def embed_img(path: PathType) -> img:
        data_uri = base64.b64encode(open(path, "rb").read()).decode("utf-8")
        img_tag = f"data:image/png;base64,{data_uri}"
        return img(src=img_tag)

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
