#!/usr/bin/env python3
"""
csv_analyzer.py — Interactive CSV statistics analyzer for benchmark results.

Analyzes one selected numeric column, grouped by ENGINE and SIZE when present.
Supports raw CSV and LaTeX export.

Selecting y_IOPS analyzes the IOPS values already present in the CSV.
No IOPS values are derived from bandwidth.
"""

import os

import numpy as np
import pandas as pd
import questionary
from questionary import Style


custom_style = Style(
    [
        ("qmark", "fg:#00c8c8 bold"),
        ("question", "bold"),
        ("pointer", "fg:#00c8c8 bold"),
        ("highlighted", "fg:#00c8c8 bold"),
        ("selected", "fg:#27ae60"),
    ]
)


STATS_FUNCS = {
    "count": lambda g, v: g[v].count(),
    "mean": lambda g, v: g[v].mean(),
    "variance": lambda g, v: g[v].var(),
    "std_dev": lambda g, v: g[v].std(),
    "min": lambda g, v: g[v].min(),
    "median": lambda g, v: g[v].median(),
    "max": lambda g, v: g[v].max(),
    "sum": lambda g, v: g[v].sum(),
    "cv_%": lambda g, v: g[v].std() / g[v].mean() * 100,
}

VALUE_STATS = {"mean", "std_dev", "min", "median", "max", "sum"}
DEFAULT_STATS = ["mean", "std_dev", "min", "median", "max"]


# ---------------- Unit helpers ----------------


def human_bytes(n):
    """Format a throughput value using SI units."""
    if n is None or pd.isna(n):
        return "n/a"

    sign = "-" if n < 0 else ""
    n = abs(float(n))

    for unit in ["B/s", "kB/s", "MB/s", "GB/s", "TB/s"]:
        if n < 1000 or unit == "TB/s":
            return f"{sign}{n:,.2f} {unit}"
        n /= 1000


def human_iops(n):
    """Format an IOPS value using SI suffixes."""
    if n is None or pd.isna(n):
        return "n/a"

    n = float(n)

    for unit in ["", "k", "M", "G"]:
        if abs(n) < 1000 or unit == "G":
            return f"{n:,.2f} {unit}IOPS"
        n /= 1000


def format_value(value, value_is_iops):
    if value_is_iops:
        return human_iops(value)
    return human_bytes(value)


# ---------------- Display formatting ----------------


def format_for_display(result, value_is_iops=False):
    """Format numeric results as human-readable strings for display."""
    disp = result.copy()

    for col in disp.columns:
        if col in VALUE_STATS:
            disp[col] = disp[col].apply(
                lambda value: format_value(value, value_is_iops)
            )
        elif col == "variance":
            unit = "IOPS²" if value_is_iops else "(B/s)²"
            disp[col] = disp[col].apply(
                lambda value: "n/a" if pd.isna(value) else f"{value:.3e} {unit}"
            )
        elif col == "cv_%":
            disp[col] = disp[col].apply(
                lambda value: "n/a" if pd.isna(value) else f"{value:.2f} %"
            )

    return disp


# ---------------- LaTeX export ----------------


def escape_latex(value):
    """Escape LaTeX special characters used by the CSV column values."""
    return (
        str(value)
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def format_latex_value(name, value, value_is_iops=False):
    """Format one statistic for LaTeX output."""
    if value is None or pd.isna(value):
        return "n/a"

    if name in VALUE_STATS:
        return format_value(value, value_is_iops).replace(" ", "")

    if name == "variance":
        return f"{value:.3e}"

    if name == "cv_%":
        return f"{value:.2f}\\%"

    return str(value)


def to_latex(result, group_cols, value_is_iops=False):
    """
    Generate LaTeX table rows for insertion between \\toprule and \\bottomrule.

    A \\midrule is inserted whenever the first grouping column changes.
    """
    lines = []
    previous_group = object()
    first_group_col = group_cols[0] if group_cols else None
    flat = result.reset_index()

    for _, row in flat.iterrows():
        first_group = row[first_group_col] if first_group_col else None

        if first_group != previous_group:
            if lines:
                lines.append("\\midrule")
            previous_group = first_group

        cells = [escape_latex(row[col]) for col in group_cols]
        cells.extend(
            format_latex_value(col, row[col], value_is_iops)
            for col in result.columns
        )

        if group_cols:
            cells[0] = f"\\textbf{{{cells[0]}}}"

        lines.append(" & ".join(cells) + " \\\\")

    return "\n".join(lines)


# ---------------- File browser ----------------


def browse_csv(start_dir="."):
    cwd = os.path.abspath(start_dir)

    while True:
        entries = sorted(os.listdir(cwd))
        directories = [
            f"[D] {entry}"
            for entry in entries
            if os.path.isdir(os.path.join(cwd, entry))
        ]
        csv_files = [
            f"    {entry}"
            for entry in entries
            if entry.lower().endswith(".csv")
        ]

        choices = [".. (up)"] + directories + csv_files + ["✖ Cancel"]

        selection = questionary.select(
            f"Select CSV file  ({cwd})",
            choices=choices,
            style=custom_style,
        ).ask()

        if selection is None or selection == "✖ Cancel":
            return None

        if selection == ".. (up)":
            cwd = os.path.dirname(cwd)
        elif selection.startswith("[D] "):
            cwd = os.path.join(cwd, selection[4:])
        else:
            return os.path.join(cwd, selection.strip())


# ---------------- Main program ----------------


def main():
    # 1) Select the CSV file.
    path = browse_csv()

    if not path:
        print("Cancelled.")
        return

    df = pd.read_csv(path)
    print(f"\nLoaded {len(df)} rows from {path}")

    # 2) Select exactly one existing value column.
    numeric_cols = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]

    if not numeric_cols:
        print("Error: the CSV contains no numeric columns.")
        return

    if "y_IOPS" in numeric_cols:
        default_value_col = "y_IOPS"
    elif "y_BANDWIDTH" in numeric_cols:
        default_value_col = "y_BANDWIDTH"
    else:
        default_value_col = numeric_cols[0]

    value_col = questionary.select(
        "Value column:",
        choices=numeric_cols,
        default=default_value_col,
        style=custom_style,
    ).ask()

    if not value_col:
        print("Cancelled.")
        return

    value_is_iops = value_col.lower() == "y_iops"
    metric_label = "IOPS" if value_is_iops else value_col

    print(f"Analyzing existing column: {value_col}")

    # 3) Select grouping columns.
    group_cols = [
        col for col in ("ENGINE", "SIZE")
        if col in df.columns
    ]

    if not group_cols:
        group_candidates = [
            col for col in df.columns
            if col != value_col
        ]

        if not group_candidates:
            print("Error: no column is available for grouping.")
            return

        selected_group = questionary.select(
            "Group by column:",
            choices=group_candidates,
            style=custom_style,
        ).ask()

        if not selected_group:
            print("Cancelled.")
            return

        group_cols = [selected_group]

    print(f"Grouping by: {group_cols}")

    # 4) Select one or more statistics.
    chosen = questionary.checkbox(
        "Select statistics (space = toggle, enter = confirm):",
        choices=[
            questionary.Choice(
                name,
                checked=name in DEFAULT_STATS,
            )
            for name in STATS_FUNCS
        ],
        validate=lambda answer: (
            "Select at least one statistic!" if not answer else True
        ),
        style=custom_style,
    ).ask()

    if not chosen:
        print("Cancelled.")
        return

    # 5) Compute statistics only for the selected existing column.
    grouped = df.groupby(group_cols)
    result = pd.DataFrame(
        {
            name: STATS_FUNCS[name](grouped, value_col)
            for name in chosen
        }
    )

    # 6) Display only the selected metric.
    print("\n" + "=" * 70)
    print(f"{metric_label} statistics by {group_cols}:")
    print(
        format_for_display(
            result,
            value_is_iops=value_is_iops,
        ).to_string()
    )
    print("=" * 70)

    # 7) Build a per-engine summary for the same selected metric.
    engine_summary = None

    if "ENGINE" in df.columns:
        engine_groups = df.groupby("ENGINE")[value_col]

        engine_summary = pd.DataFrame(
            {
                "runs": engine_groups.count(),
                f"mean_{value_col}": engine_groups.mean(),
                f"std_{value_col}": engine_groups.std(),
            }
        )

        display_summary = engine_summary.copy()

        for col in display_summary.columns:
            if col.startswith("mean_") or col.startswith("std_"):
                display_summary[col] = display_summary[col].apply(
                    lambda value: format_value(value, value_is_iops)
                )

        print(f"\nPer-engine {metric_label} summary:")
        print(display_summary.to_string())

    # 8) Optionally save the results.
    save = questionary.confirm(
        "Save results?",
        default=False,
        style=custom_style,
    ).ask()

    if not save:
        return

    export_format = questionary.select(
        "Format:",
        choices=[
            "Statistics CSV (raw)",
            "LaTeX table rows",
            "Both statistics CSV and LaTeX",
            "Engine summary CSV",
        ],
        style=custom_style,
    ).ask()

    if not export_format:
        return

    if export_format in (
        "Statistics CSV (raw)",
        "Both statistics CSV and LaTeX",
    ):
        output = questionary.text(
            "CSV output file:",
            default="stats_output.csv",
            style=custom_style,
        ).ask()

        if output:
            result.to_csv(output)
            print(f"Saved -> {output}")

    if export_format in (
        "LaTeX table rows",
        "Both statistics CSV and LaTeX",
    ):
        output = questionary.text(
            "LaTeX output file:",
            default="stats_output.tex",
            style=custom_style,
        ).ask()

        if output:
            body = to_latex(
                result,
                group_cols,
                value_is_iops=value_is_iops,
            )

            with open(output, "w", encoding="utf-8") as file:
                file.write(body + "\n")

            print(f"Saved -> {output}")
            print(
                "\n--- LaTeX table rows "
                "(paste between \\toprule and \\bottomrule) ---"
            )
            print(body)

    if export_format == "Engine summary CSV":
        if engine_summary is None:
            print("No ENGINE column -> engine summary not available.")
            return

        output = questionary.text(
            "Output file:",
            default="engine_summary.csv",
            style=custom_style,
        ).ask()

        if output:
            engine_summary.to_csv(output)
            print(f"Saved -> {output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")