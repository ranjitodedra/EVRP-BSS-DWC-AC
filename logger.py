"""
logger.py — CSV logging per iteration and run summaries.
"""

from __future__ import annotations
import csv
import os
from typing import List

from simulator import RouteResult


class ACOLogger:
    """Handles CSV logging for ACO runs."""

    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def log_iteration_csv(
        self,
        history: List[dict],
        run_id: int,
        instance_name: str,
    ):
        """Write per-iteration CSV for one run."""
        filename = os.path.join(
            self.output_dir,
            f"{instance_name}_run{run_id}_iterations.csv",
        )
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "iteration", "best_cost", "worst_cost",
                "average_cost", "global_best_cost", "best_tour",
            ])
            for row in history:
                writer.writerow([
                    row["iteration"],
                    f"{row['best_cost']:.6f}",
                    f"{row['worst_cost']:.6f}",
                    f"{row['average_cost']:.6f}",
                    f"{row['global_best_cost']:.6f}",
                    " -> ".join(row.get("best_tour", [])),
                ])
        return filename

    def log_run_summary(
        self,
        run_id: int,
        result: RouteResult,
        runtime: float,
        instance_name: str,
    ):
        """Append run summary to aggregate CSV."""
        filename = os.path.join(
            self.output_dir,
            f"{instance_name}_run_summaries.csv",
        )
        file_exists = os.path.exists(filename)
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "run_id", "objective", "total_time_h", "total_distance_km",
                    "energy_consumed_kWh", "energy_charged_static_kWh",
                    "energy_charged_dynamic_kWh", "final_battery_kWh",
                    "final_battery_pct", "packages_delivered",
                    "num_charging_stops", "runtime_s", "route",
                ])
            # Battery capacity is the initial battery level (first entry in battery_levels)
            # which should be the full capacity at start
            if result.battery_levels:
                total_bat_kwh = result.battery_levels[0]  # initial battery = full capacity
            else:
                total_bat_kwh = 100.0  # fallback default
            writer.writerow([
                run_id,
                f"{result.objective:.6f}",
                f"{result.total_time:.4f}",
                f"{result.total_distance:.4f}",
                f"{result.total_energy_consumed:.4f}",
                f"{result.total_energy_charged_static:.4f}",
                f"{result.total_energy_charged_dynamic:.4f}",
                f"{result.final_battery:.4f}",
                f"{(result.final_battery / total_bat_kwh) * 100:.1f}",
                result.packages_delivered,
                len(result.charging_stops),
                f"{runtime:.2f}",
                " -> ".join(result.route_sequence),
            ])
        return filename

    @staticmethod
    def print_multi_run_summary(objectives: List[float]):
        """Print best/worst/mean/std across runs."""
        import statistics
        n = len(objectives)
        best = min(objectives)
        worst = max(objectives)
        mean = statistics.mean(objectives)
        std = statistics.stdev(objectives) if n > 1 else 0.0
        print(f"\n{'=' * 60}")
        print(f"  MULTI-RUN SUMMARY ({n} runs)")
        print(f"{'=' * 60}")
        print(f"  Best Objective:   {best:.6f}")
        print(f"  Worst Objective:  {worst:.6f}")
        print(f"  Mean Objective:   {mean:.6f}")
        print(f"  Std Deviation:    {std:.6f}")
        print(f"{'=' * 60}\n")
