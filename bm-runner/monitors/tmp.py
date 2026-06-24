import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
from utils.logger import bm_log, LogType
_UNITS = {
    "": 1,
    "K": 1024,
    "M": 1024 ** 2,
    "G": 1024 ** 3,
}

_HEADER_RE = re.compile(r"^@(?P<name>\w+)\[(?P<keys>.*)\]:")
_BUCKET_RE = re.compile(
    r"\[\s*(?P<low>\d+(?:\.\d+)?)(?P<low_unit>[KMG]?)\s*,\s*"
    r"(?P<high>\d+(?:\.\d+)?)(?P<high_unit>[KMG]?)\s*\)\s+"
    r"(?P<count>\d+)"
)


def _scaled_number(value: str, unit: str) -> int:
    return int(float(value) * _UNITS[unit])


def plot_perf_hist_for_comm(filename: str, comm: str, plot_file: Path):
    rows = []
    current = None

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            header = _HEADER_RE.match(line)
            if header:
                keys = [k.strip() for k in header.group("keys").split(",")]
                current = {
                    "hist_name": header.group("name"),
                    "pid": keys[0] if len(keys) > 0 else None,
                    "comm": keys[1] if len(keys) > 1 else None,
                }
                continue

            bucket = _BUCKET_RE.search(line)
            if not bucket or current is None:
                continue

            if current["comm"] != comm:
                continue

            low = _scaled_number(bucket.group("low"), bucket.group("low_unit"))
            high = _scaled_number(bucket.group("high"), bucket.group("high_unit"))
            count = int(bucket.group("count"))

            rows.append({
                **current,
                "low": low,
                "high": high,
                "midpoint": (low + high) / 2,
                "count": count,
                "bucket": f"[{low}, {high})",
            })

    if not rows:
        raise ValueError(f"No histogram buckets found for comm={comm!r}")

    df = pd.DataFrame(rows)

    ax = sns.lineplot(
        data=df,
        x="midpoint",
        y="count",
        hue="pid",
        marker="o",
    )

    ax.set_xscale("log", base=2)
    ax.set_xlabel("Bucket midpoint")
    ax.set_ylabel("Count")
    ax.set_title(f"Histogram buckets for comm={comm}")

    plt.tight_layout()
    plt.savefig(plot_file, transparent=False)

    bm_log(filename, LogType.FATAL)
    bm_log(plot_file, LogType.FATAL)
    print(df)
    return df
