#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter

parser = argparse.ArgumentParser()
parser.add_argument("csv", nargs="?", default="results.csv")
parser.add_argument("-o", "--output", default="throughput.pdf")
parser.add_argument("--spdk-only", action="store_true")
parser.add_argument("-t", "--title", required=True)

args = parser.parse_args()

df = pd.read_csv(args.csv)

if args.spdk_only:
    df = df[df["ENGINE"] == "spdk_bdev"]

df["throughput_gbs"] = df["y_BW_TS"] / 1e9

agg = (
    df.groupby(["ENGINE", "TIME"])["throughput_gbs"]
    .agg(["mean", "std"])
    .reset_index()
    .sort_values("TIME")
)

fig, ax = plt.subplots(figsize=(8, 5))

for engine, group in agg.groupby("ENGINE"):
    ax.errorbar(
        group["TIME"],
        group["mean"],
        yerr=group["std"],
        marker="o",
        markersize=3,
        linewidth=1.5,
        capsize=3,
        label=engine,
    )

ax.xaxis.set_major_locator(FixedLocator(range(0, 901, 50)))
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f} s"))
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
ax.set_xlim(0, 900)

ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.1f} GB/s"))
if not args.spdk_only:
    ax.set_ylim(bottom=0)
else:
    ymin = (agg["mean"] - agg["std"]).min()
    ymax = (agg["mean"] + agg["std"]).max()
    margin = (ymax - ymin) * 0.10
    ax.set_ylim(ymin - margin, ymax + margin)

ax.legend(title="ioengine")
ax.grid(True, alpha=0.3)
ax.set_title(args.title)

fig.tight_layout()
fig.savefig(args.output, dpi=300)
print(f"Saved {args.output}")
