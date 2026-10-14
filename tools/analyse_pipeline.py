#!/usr/bin/env python3
"""Script to analyse data_run_performance.csv pipeline log

Generated with the help of Mistral Medium 3.5 via opencode
"""

import argparse
import os

import pandas as pd
import plotly.express as px


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Analyze pipeline performance data")
    parser.add_argument(
        "--unit",
        choices=["seconds", "minutes", "hours"],
        default="seconds",
        help="Time unit for output (default: seconds)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output PNG file path (default: shows interactive plot)",
    )
    args = parser.parse_args()

    # Conversion factors
    unit_factors = {"seconds": 1, "minutes": 1 / 60, "hours": 1 / 3600}

    # Load the CSV file
    df = pd.read_csv(
        "data_run_performance.csv",
        header=None,
        names=["timestamp", "run_id", "stage", "duration"],
    )

    # Convert duration to desired unit
    factor = unit_factors[args.unit]
    df["duration"] = df["duration"] * factor

    # Define pipeline stage labels and ordering
    pipeline_stages = [
        ("PREPARING_FOR_RUN", "Preparing for Run"),
        ("RUNNING_DATAGETTER", "Running Data Getter"),
        (
            "LOADING_DATA_INTO_DATASTORE",
            "Loading Data into Datastore<br>and generating quality data",
        ),
        ("PREPARING_TO_MAKE_GRANTNAV_PACKAGE", "Preparing GrantNav Package"),
        (
            "CREATING_GRANTNAV_DATAPACKAGE_FILES",
            "Creating GrantNav<br>Data Package Files",
        ),
        ("BUILDING_GRANTNAV_DATAPACKAGE", "Building GrantNav<br>Data Package"),
        ("CREATE_MONITORING_SNAPSHOT", "Creating Monitoring Snapshot"),
    ]

    # Create mapping from stage code to display label
    stage_labels = {code: label for code, label in pipeline_stages}

    # Identify complete runs (those with all expected stages)
    expected_stages = set(code for code, label in pipeline_stages)

    # Group by run_id and check which runs have all stages
    run_stages = df.groupby("run_id")["stage"].apply(set)
    complete_runs = run_stages[run_stages == expected_stages].index

    # Filter to only complete runs
    complete_df = df[df["run_id"].isin(complete_runs)]

    # Add display labels to the dataframe
    complete_df["stage_label"] = complete_df["stage"].map(stage_labels)

    # Calculate statistics for each stage in the defined order
    stage_order = [code for code, label in pipeline_stages]
    stats = (
        complete_df.groupby("stage")["duration"]
        .agg(
            [
                "mean",
                "median",
                "std",
                "min",
                "max",
                "count",
                lambda x: x.quantile(0.25),
                lambda x: x.quantile(0.75),
            ]
        )
        .reset_index()
    )
    stats.columns = [
        "stage",
        "mean",
        "median",
        "std",
        "min",
        "max",
        "count",
        "q1",
        "q3",
    ]
    stats["label"] = stats["stage"].map(stage_labels)
    stats = stats.sort_values(
        by="stage", key=lambda x: x.map(lambda s: stage_order.index(s))
    )

    # Print the statistics table
    unit_label = args.unit.capitalize() if args.unit != "seconds" else "Seconds"
    print(
        f"Duration Statistics for Each Pipeline Stage (Complete Runs Only) - {unit_label}:"
    )
    print("=" * 80)
    print(stats[["label", "median", "q1", "q3", "min", "max"]].to_string(index=False))
    print()

    # Create box plot
    fig = px.box(
        complete_df,
        x="stage_label",
        y="duration",
        title=f"Pipeline Stage Duration Distribution (Complete Runs) - {unit_label}",
        labels={"stage_label": "Pipeline Stage", "duration": f"Duration ({args.unit})"},
        category_orders={"stage_label": [label for code, label in pipeline_stages]},
    )

    fig.update_layout(
        xaxis_title="Pipeline Stage",
        yaxis_title=f"Duration ({args.unit})",
        xaxis_tickangle=-45,
        height=600,
    )

    if args.output:
        fig.write_image(args.output)
        print(f"\nGraph saved to: {os.path.abspath(args.output)}")
    else:
        fig.show()

    # Generate markdown table for Google Docs
    markdown_table = "# Pipeline Performance Statistics (Complete Runs Only)\n\n"
    markdown_table += f"## Duration Statistics by Stage ({unit_label})\n\n"
    markdown_table += "| Pipeline Stage | Median | Q1 | Q3 | Min | Max |\n"
    markdown_table += "|----------------|--------|----|----|-----|-----|\n"

    for _, row in stats.iterrows():
        # Clean label for markdown (remove HTML line breaks)
        clean_label = row["label"].replace("<br>", " ").strip()
        markdown_table += f"| {clean_label} | {row['median']:.2f} | {row['q1']:.2f} | {row['q3']:.2f} | {row['min']:.2f} | {row['max']:.2f} |\n"

    markdown_table += f"\n*Data based on {len(complete_runs)} complete pipeline runs*"

    # Save markdown to file
    md_filename = "pipeline_stats_table.md"
    with open(md_filename, "w") as f:
        f.write(markdown_table)
    print(f"\nMarkdown table saved to: {os.path.abspath(md_filename)}")


if __name__ == "__main__":
    main()
