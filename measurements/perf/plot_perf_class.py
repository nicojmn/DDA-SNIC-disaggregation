import argparse
import pandas as pd
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("input_file")
parser.add_argument("--title", default="Distribution")
parser.add_argument("--min-pct", type=float, default=5.0)
parser.add_argument("-o", "--output", default=None)
args = parser.parse_args()

df = pd.read_csv(args.input_file, sep=";", header=None, names=["label", "value"])

total = df["value"].sum()
pcts = df["value"] / total * 100

colors = plt.cm.tab20.colors  # up to 20 distinct colors; cycle if more categories

fig, ax = plt.subplots(figsize=(10, 2.5))

left = 0
for i, (label, value, pct) in enumerate(zip(df["label"], df["value"], pcts)):
    color = colors[i % len(colors)]
    ax.barh(
        y=0,
        width=value,
        left=left,
        height=0.5,
        color=color,
        edgecolor="white",
        linewidth=0.5,
        label=f"{label} ({pct:.1f}%)",
    )
    if pct >= args.min_pct:
        ax.text(
            left + value / 2,
            0,
            f"{pct:.1f}%",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
        )
    left += value

ax.set_xlim(0, total)
ax.set_yticks([])
ax.spines[["top", "right", "left"]].set_visible(False)
ax.set_title(args.title, fontsize=14, fontweight="bold")

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.25),
    ncol=min(len(df), 5),
    fontsize=9,
    frameon=False,
)

plt.tight_layout()

if args.output:
    plt.savefig(args.output, dpi=150, bbox_inches="tight")
else:
    plt.show()
