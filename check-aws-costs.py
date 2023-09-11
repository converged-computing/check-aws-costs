#!/usr/bin/env python

# Copyright 2023 Lawrence Livermore National Security, LLC and other
# HPCIC DevTools Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (MIT)

import argparse
import os
import pandas
from datetime import datetime, timedelta
import json

import boto3

# https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetCostAndUsage.html
# We set a dimension, metrics, and granularity, but not a filter

dimension_choices = [
    "AZ",
    "INSTANCE_TYPE",
    "LEGAL_ENTITY_NAME",
    "INVOICING_ENTITY",
    "LINKED_ACCOUNT",
    "OPERATION",
    "PLATFORM",
    "PURCHASE_TYPE",
    "SERVICE",
    "TENANCY",
    "RECORD_TYPE",
    "USAGE_TYPE",
]

granularity_choices = ["DAILY", "MONTHLY", "HOURLY"]
metrics_choices = [
    "AmortizedCost",
    "BlendedCost",
    "NetAmortizedCost",
    "NetUnblendedCost",
    "NormalizedUsageAmount",
    "UnblendedCost",
    "UsageQuantity",
]


# Get a full year of a range between today and tomorrow
today = datetime.now()
tomorrow = today + timedelta(days=1)
start = tomorrow - timedelta(days=365)
here = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Cloud Select Price Exporter",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Save a local cache right here
    parser.add_argument(
        "--data-dir",
        dest="data_dir",
        help="directory for data cache (defaults to $PWD/cache).",
        default=os.path.join(here, "cache"),
    )
    parser.add_argument(
        "-r",
        "--region",
        dest="region",
        help="One or more regions to include",
        default=["us-east-1", "us-east-2", "us-west-1", "us-west-2"],
        action="append",
    )
    parser.add_argument(
        "-g",
        "--granularity",
        help="Granularity (defaults to DAILY)",
        default="DAILY",
        choices=granularity_choices,
    )
    parser.add_argument(
        "-d",
        "--dimension",
        help="Dimension for GroupBy (defaults to SERVICE)",
        default="SERVICE",
        choices=dimension_choices,
    )
    parser.add_argument(
        "-m",
        "--metric",
        help="One or more Metric (defaults to AmortizedCost)",
        default=["AmortizedCost"],
        action="append",
        choices=dimension_choices,
    )
    return parser


def write_json(obj, path):
    """
    Write json to file
    """
    with open(path, "w") as fd:
        fd.write(json.dumps(obj, indent=4))


def get_cost_data(regions, dimension="SERVICE", metrics=None, granularity="DAILY"):
    """
    Get a year of cost data for a list of regions.
    """
    data = {}
    if not metrics:
        metrics = ["AmortizedCost"]

    # Create cost explorer client, across regions we use
    for region in regions:
        print(f"Querying for daily cost by service for {region}")
        data[region] = []
        client = boto3.client("ce", region_name=region)
        response = client.get_cost_and_usage(
            GroupBy=[{"Key": dimension, "Type": "DIMENSION"}],
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": tomorrow.strftime("%Y-%m-%d"),
            },
            Granularity=granularity,
            Metrics=metrics,
        )
        if "ResultsByTime" not in response:
            raise ValueError("Key ResultsByTime missing from response.")

        # Save data to region
        data[region] = response["ResultsByTime"]
    return data


def organize_data(data):
    """
    Organize data into pandas dataframe for easier plotting later
    """
    columns = ["group", "metric", "amount", "unit", "start_date", "end_date"]
    df = pandas.DataFrame(columns=columns)

    idx = 0
    for region, listing in data.items():
        print(f"Adding {region} to the data frame...")
        # keys: ['TimePeriod', 'Total', 'Groups', 'Estimated']
        # Total looks  empty
        for period in listing:
            # This will be the granularity (e.g., daily)
            start = period["TimePeriod"]["Start"]
            ending = period["TimePeriod"]["End"]
            for item in period["Groups"]:
                # Each item has Keys (for service, etc) and metrics
                # This is typically one thing.
                group = "_".join(item["Keys"]).replace(" ", "-").lower()
                for metric, values in item["Metrics"].items():
                    unit = values["Unit"]

                    # Geezers this is a string...
                    amount = float(values["Amount"])
                    df.loc[idx, :] = [group, metric, amount, unit, start, ending]
                    idx += 1
    return df


def announce_save(outfile, result_type=""):
    """
    Announce relative path for results to be saved
    """
    relpath = os.path.relpath(outfile)
    print(f"Saving {result_type} results to {relpath}")


def run():
    """
    Run the cost data extraction.
    """
    parser = get_parser()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # Create output directory
    if not os.path.exists(args.data_dir):
        os.makedirs(args.data_dir)

    # Create organized data by region
    data = get_cost_data(
        args.region,
        dimension=args.dimension,
        metrics=args.metric,
        granularity=args.granularity,
    )

    # Save to data directory
    outfile = os.path.join(
        args.data_dir, "spending-%s.json" % today.strftime("%Y-%m-%d")
    )
    announce_save(outfile, "raw")
    write_json(data, outfile)

    # These are organized into a table
    outfile = os.path.join(
        args.data_dir, "spending-%s.csv" % today.strftime("%Y-%m-%d")
    )
    df = organize_data(data)
    announce_save(outfile, "formatted")
    df.to_csv(outfile)


if __name__ == "__main__":
    run()
