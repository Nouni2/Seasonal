# -*- coding: utf-8 -*-
"""
Validation History Plotter
==========================

This script parses multiple validation report files and visualizes the
evolution of engine accuracy using horizontal grouped bar charts.

It expects the following files in the same directory as the script:
    - validation_report.txt   (Newest/Current run)
    - validation_report1.txt  (Previous run)
    - validation_report2.txt  (Oldest run)

For each report, it compares:
    - Max Az Error
    - Max Alt Error
    - Max LST Error

The visualization uses a dark theme and horizontal orientation to
distinctly separate scenarios and highlight regression/improvements.

-------------------------------------------------------------------------------
SEASONAL: VALIDATION & VERIFICATION PROTOCOL TOLERANCES
-------------------------------------------------------------------------------
Based on the Acceptance Criteria:
  - Azimuth       : 1.0 arcsec  (~0.000277 deg)
  - Altitude (Geom): 1.0 arcsec  (~0.000277 deg)
  - Altitude (App) : 5.0 arcsec  (~0.001389 deg)
  - LST           : 0.1 seconds (~0.000417 deg)
-------------------------------------------------------------------------------
"""

import os
import re
from typing import Dict, List, Tuple

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Error: matplotlib and numpy are required.")
    print("pip install matplotlib numpy")
    exit(1)


# Type alias for report data: scenario_name -> metric_name -> value
ReportData = Dict[str, Dict[str, float]]


def parse_validation_report(path: str) -> ReportData:
    """
    Parses a single validation report file into structured metric data.
    """
    data: ReportData = {}
    current_scenario: str | None = None

    # Matches: "Max Az Error      : 0.000496° (Limit 0.0003°)"
    # Updated regex to be slightly more robust for floats
    az_pattern = re.compile(r"Max Az Error\s*:\s*([0-9.eE+-]+)")
    alt_pattern = re.compile(r"Max Alt Error\s*:\s*([0-9.eE+-]+)")
    lst_pattern = re.compile(r"Max LST Error\s*:\s*([0-9.eE+-]+)")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("=== Validating:"):
                parts = stripped.split("Validating:")
                if len(parts) < 2:
                    continue
                right = parts[1]
                scenario = right.split("===")[0].strip()
                current_scenario = scenario
                if current_scenario not in data:
                    data[current_scenario] = {}
                continue

            if current_scenario is None:
                continue

            az_match = az_pattern.search(stripped)
            if az_match:
                data[current_scenario]["Max Az Error"] = float(az_match.group(1))
                continue

            alt_match = alt_pattern.search(stripped)
            if alt_match:
                data[current_scenario]["Max Alt Error"] = float(alt_match.group(1))
                continue

            lst_match = lst_pattern.search(stripped)
            if lst_match:
                data[current_scenario]["Max LST Error"] = float(lst_match.group(1))
                continue

    return data


def load_all_reports(base_dir: str) -> List[Tuple[str, ReportData]]:
    """
    Loads all validation_report*.txt files in historical order.
    """
    # Candidates list: (Legend Label, Filename)
    # We load them in order so the bars appear consistently (Old -> New)
    candidates: List[Tuple[str, str]] = [
        ("Run -2 (Oldest)", os.path.join(base_dir, "validation_report2.txt")),
        ("Run -1", os.path.join(base_dir, "validation_report1.txt")),
        ("Current Run", os.path.join(base_dir, "validation_report.txt")),
    ]

    reports: List[Tuple[str, ReportData]] = []

    for label, path in candidates:
        if os.path.exists(path):
            print(f"Loading report: {path}")
            parsed = parse_validation_report(path)
            reports.append((label, parsed))
        else:
            print(f"Skipping missing report: {path}")

    return reports


def collect_scenarios(reports: List[Tuple[str, ReportData]]) -> List[str]:
    """
    Builds a sorted list of all scenario names present in any of the reports.
    """
    scenario_set = set()
    for _, data in reports:
        scenario_set.update(data.keys())
    return sorted(scenario_set)


def plot_validation_history(reports: List[Tuple[str, ReportData]]) -> None:
    """
    Plots the evolution of max errors using horizontal grouped bar charts
    in a dark mode theme.
    """
    if not reports:
        print("No validation reports found to plot.")
        return

    scenarios = collect_scenarios(reports)
    if not scenarios:
        print("No scenarios found in the reports.")
        return

    # --- THEME SETUP ---
    # Attempting to use a dark background for high contrast
    plt.style.use('dark_background')
    
    # Neon/Bright colors that pop on dark background
    # v2 (Oldest) = Magenta, v1 = Cyan, Current = Bright Yellow
    colors = ['#FF00FF', '#00FFFF', '#FFFF00', '#00FF00'] 

    # Layout: 1 Row, 3 Columns (Az, Alt, LST side by side)
    fig, axes = plt.subplots(1, 3, figsize=(20, 10), sharey=True)
    ax_az, ax_alt, ax_lst = axes

    # Metrics config
    metrics_info = [
        (ax_az, "Max Az Error"),
        (ax_alt, "Max Alt Error"),
        (ax_lst, "Max LST Error")
    ]
    
    # Tolerance Definitions (degrees)
    # 1 arcsec = 1/3600 deg
    # 5 arcsec = 5/3600 deg
    # 0.1 sec LST = 0.1 * (15/3600) deg
    TOL_1_ARCSEC = 1.0 / 3600.0
    TOL_5_ARCSEC = 5.0 / 3600.0
    TOL_LST = 0.1 * 15.0 / 3600.0

    tolerance_map = {
        "Max Az Error": [("Limit: 1\"", TOL_1_ARCSEC)],
        "Max Alt Error": [("Geom: 1\"", TOL_1_ARCSEC), ("App: 5\"", TOL_5_ARCSEC)],
        "Max LST Error": [("Limit: 0.1s", TOL_LST)]
    }

    # Bar Configuration
    y_pos = np.arange(len(scenarios))
    num_reports = len(reports)
    total_bar_height = 0.8
    single_bar_height = total_bar_height / num_reports

    # Iterate over axes/metrics
    for ax, metric_key in metrics_info:
        
        # Plot bars for each report version
        for i, (version_label, data) in enumerate(reports):
            values = []
            for scen in scenarios:
                val = data.get(scen, {}).get(metric_key, 0.0)
                values.append(val)
            
            # Calculate vertical offset for grouped bars
            # Center the group on the y tick
            offset = (i - (num_reports - 1) / 2) * single_bar_height
            
            bars = ax.barh(
                y_pos + offset, 
                values, 
                height=single_bar_height, 
                label=version_label, 
                color=colors[i % len(colors)],
                alpha=0.9,
                edgecolor='black',
                linewidth=0.5
            )

        # Plot Tolerance Lines
        if metric_key in tolerance_map:
            for label, threshold in tolerance_map[metric_key]:
                ax.axvline(x=threshold, color='#FF4444', linestyle='--', linewidth=1.5, alpha=0.9, zorder=10)
                # Annotate the line at the top
                # Using blended transform to place text at X=threshold, Y=axes_coordinate(1.01)
                trans = ax.get_xaxis_transform()
                ax.text(threshold, 1.01, label, color='#FF4444', 
                        transform=trans, ha='center', va='bottom', 
                        fontsize=9, fontweight='bold', rotation=0)

        # Styling
        ax.set_title(metric_key, fontsize=14, fontweight='bold', color='white', pad=25)
        ax.set_xscale('log')  # Use log scale for x-axis
        ax.set_xlabel("Error (deg) [Log Scale]", fontsize=10, color='gray')
        
        # Grid settings for log scale
        ax.grid(True, axis='x', which='both', linestyle=':', alpha=0.3, color='gray')
        
        # Invert Y axis so first scenario is at the top
        if ax == ax_az:
            ax.invert_yaxis()

    # Y-Axis Labels (Scenarios) - Only needed on the first plot due to sharey
    ax_az.set_yticks(y_pos)
    ax_az.set_yticklabels(scenarios, fontsize=10, color='#DDDDDD')
    
    # Legend
    # Place legend on the last plot or distinct location
    ax_lst.legend(title="Engine Version", loc='lower right', frameon=True, facecolor='#222222', edgecolor='gray')

    plt.tight_layout()
    
    # Add a main title to the figure
    fig.suptitle("Engine Validation History: Error Evolution", fontsize=16, y=0.98, color='white')
    
    # Adjust layout to make room for suptitle
    plt.subplots_adjust(top=0.90)

    plt.show()


def main() -> None:
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    
    print(f"Scanning for reports in: {script_dir}")
    reports = load_all_reports(script_dir)
    plot_validation_history(reports)


if __name__ == "__main__":
    main()