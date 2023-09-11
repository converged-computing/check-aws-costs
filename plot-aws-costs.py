#!/usr/bin/env python

# Copyright 2023 Lawrence Livermore National Security, LLC and other
# HPCIC DevTools Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (MIT)

import argparse
import os
import random
from datetime import datetime

import matplotlib.pyplot as plt
import pandas
import seaborn as sns
from matplotlib import colormaps as cm

# set seaborn style
sns.set_theme()

# Get a full year of a range between today and tomorrow
today = datetime.now()
here = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Cloud Select Price Exporter",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Save a local cache right here
    parser.add_argument(
        "--csv",
        help="csv data frame file to plot (defaults to $PWD/cache/spending-latest.csv).",
        default=os.path.join(here, "cache", "spending-latest.csv"),
    )
    parser.add_argument(
        "--outdir",
        help="Output directory for images (defaults to $PWD/img)",
        default=os.path.join(here, "img"),
    )

    return parser


def to_date(datestr):
    """
    Convert a datestring in YYYY-MM-DD to a datetime time
    """
    return datetime.strptime(datestr, "%Y-%m-%d").date()


def run():
    """
    Run the cost data extraction.
    """
    parser = get_parser()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # Create output directory
    if not os.path.exists(args.csv):
        raise ValueError(f"CSV file {args.csv} does not exist.")

    # Read in data, index column is 0
    df = pandas.read_csv(args.csv, index_col=0)

    # Determine which groups to skip (if sum for region is < $5)
    # Note that it looks like some of these are actual NEGATIVE which is weird
    keepers = set()
    for group in df.group.unique():
        subset = df[df.group == group]

        # Is the total under $5?
        if subset.amount.sum() < 5:
            print(f"Skipping {group} - total across regions is < $5")
            continue
        keepers.add(group)

    # Total plots are the number of groups by metrics (each plot has all regions)
    total_plots = 2 * len(keepers) * len(df.metric.unique())

    # Make some nice colors
    colors = [list(x) for x in cm["Paired"].colors]
    random.shuffle(colors)
    region_colors = {}
    for i, region in enumerate(df.region.unique()):
        region_colors[region] = colors[i]

    # Convert dates to datetime.date
    # I'm not sure if these are actually different, they look the same lol
    # df['start'] = df['start_date'].map(lambda x:to_date(x))
    # df['end'] = df['end_date'].map(lambda x:to_date(x))
    df["start"] = pandas.to_datetime(df["start_date"]).dt.strftime("%Y-%m-%d")
    df["end"] = pandas.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")

    # Stack dem pancakes
    fig, axs = plt.subplots(nrows=total_plots, figsize=(12, total_plots * 3))

    # Date specific output directory (when generated)
    outdir = os.path.join(args.outdir, today.strftime("%Y-%m-%d"))
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # We assume these are the same
    if len(df.unit.unique()) > 1:
        raise ValueError("Trying to compare different units.")
    unit = df.unit.unique()[0]

    # Plot by group, line plots (by region and for all)
    idx = 0
    for group in df.group.unique():
        if group not in keepers:
            continue
        subset = df[df.group == group]
        by_region = subset[subset.region != "all"]
        all_regions = subset[subset.region == "all"]
        groups = {"for all regions": all_regions, "by region": by_region}
        for k, v in groups.items():
            ax = axs[idx]
            ax.tick_params("x", labelrotation=90)
            plot = sns.lineplot(
                x="start",
                y="amount",
                markers=True,
                data=v,
                palette=region_colors,
                hue="region",
                ax=ax,
            )
            plot.set_title(f"AWS cost group {group} {k}")
            plot.set_ylabel(f"Amount ({unit})")
            idx += 1

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "aws-spending-by-region.pdf"))
    plt.close()

    # TODO Generate stacked area, one per group
    # TODO: an accumulative view


if __name__ == "__main__":
    run()
