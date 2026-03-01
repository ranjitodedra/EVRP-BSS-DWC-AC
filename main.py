"""
main.py — Entry point for ACO-based Electric Vehicle Routing.

Usage:
    python main.py --instance instances/instance_1.json [--runs 10] [--seed 42]
"""

from __future__ import annotations
import argparse
import json
import multiprocessing
import os
import time
import traceback
from typing import List

from graph import Graph
from simulator import build_params, decode_route, RouteResult
from aco import ACOEngine
from logger import ACOLogger
from plotter import plot_convergence, plot_box, plot_pheromone_heatmap
import config


# ──────────────────────────────────────────────
# Pretty-print helpers
# ──────────────────────────────────────────────

def format_soc_trail(result: RouteResult, e_bat: float) -> str:
    parts = []
    for node, pct in result.soc_trail:
        parts.append(f"{node}({pct:.1f}%)")
    return " -> ".join(parts)


def format_energy_trail(result: RouteResult) -> str:
    if not result.energy_trail:
        return ""
    parts = [result.energy_trail[0][0]]  # start node
    for src, dst, kwh in result.energy_trail:
        parts.append(f"- {kwh:.1f} kWh > {dst}")
    return " ".join(parts)


def format_time_trail(result: RouteResult) -> str:
    if not result.time_trail:
        return ""
    parts = [result.time_trail[0][0]]  # start node
    for src, dst, mins in result.time_trail:
        parts.append(f"- {mins:.2f} min > {dst}")
    return " ".join(parts)


def print_solution(result: RouteResult, e_bat: float, runtime: float, converged_iter: int = 0):
    print()
    print("=" * 60)
    print("  ANT COLONY OPTIMIZATION — SOLUTION SUMMARY")
    print("=" * 60)
    print(f"  Objective Value (legacy):         {result.objective:.6f}")
    print(f"  Total Travel Time:          {result.total_time:.4f} hours ({result.total_time * 60:.2f} min)")
    print(f"  Total Distance:             {result.total_distance:.4f} km")
    print(f"  Total Energy Depletion:     {result.total_energy_consumed:.4f} kWh")
    print(f"  Total Energy Charged (SC):  {result.total_energy_charged_static:.4f} kWh")
    print(f"  Total Energy Charged (DWC): {result.total_energy_charged_dynamic:.4f} kWh")
    final_pct = (result.final_battery / e_bat) * 100 if e_bat > 0 else 0
    print(f"  Final Battery Level:        {result.final_battery:.4f} kWh ({final_pct:.1f}%)")
    print(f"  Boxes Delivered:            {result.packages_delivered}")

    if result.charging_stops:
        stops_str = ", ".join(
            f"{s.station_id} ({s.time_charged * 60:.1f} min, +{s.energy_added:.1f} kWh)"
            for s in result.charging_stops
        )
        print(f"  Charging Stops:             {stops_str}")
    else:
        print(f"  Charging Stops:             None")

    print()
    print(f"Route Sequence: {' -> '.join(result.route_sequence)}")
    print()
    print(f"SoC Trail: {format_soc_trail(result, e_bat)}")
    print()
    print(f"Energy Consumption Trail: {format_energy_trail(result)}")
    print()
    print(f"Travel Time Trail: {format_time_trail(result)}")
    print()
    if converged_iter > 0:
        print(f"  Pheromone convergence:       iteration {converged_iter}")
    print(f"  Total Runtime:               {runtime:.2f} seconds")
    print()


# ──────────────────────────────────────────────
# Worker function (must be top-level for pickle)
# ──────────────────────────────────────────────

def _run_single(task_args: tuple) -> dict:
    """Execute one independent ACO run inside a worker process.

    Rebuilds Graph and params from the instance file to avoid
    pickling large objects across process boundaries.
    """
    (instance_path, num_ants, max_iter, seed, run_id) = task_args

    try:
        run_start = time.time()

        # Build graph & params fresh inside the worker
        graph = Graph.from_json(instance_path)
        with open(instance_path, "r") as f:
            data = json.load(f)
        params = build_params(data)

        engine = ACOEngine(
            graph, params,
            num_ants=num_ants,
            max_iterations=max_iter,
            seed=seed,
        )
        best_result, history = engine.run()
        run_time = time.time() - run_start

        cost = best_result.objective if best_result else float("inf")

        # Capture pheromone matrix so main process can plot heatmap
        labels, matrix = engine.get_pheromone_matrix()

        return {
            "run_id": run_id,
            "seed": seed,
            "cost": cost,
            "best_result": best_result,
            "history": history,
            "runtime": run_time,
            "pheromone": (labels, matrix),
            "error": None,
        }

    except Exception as exc:
        return {
            "run_id": run_id,
            "seed": seed,
            "cost": float("inf"),
            "best_result": None,
            "history": [],
            "runtime": 0.0,
            "pheromone": None,
            "error": f"Run {run_id} failed: {exc}\n{traceback.format_exc()}",
        }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACO for Electric Vehicle Routing")
    parser.add_argument("--instance", required=True, help="Path to JSON instance file")
    parser.add_argument("--runs", type=int, default=None, help="Number of independent runs")
    parser.add_argument("--seed", type=int, default=None, help="Base random seed")
    parser.add_argument("--ants", type=int, default=None, help="Number of ants per iteration")
    parser.add_argument("--iterations", type=int, default=None, help="Max iterations")
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel workers (default: all cores)")
    args = parser.parse_args()

    # load instance (in main process for initial info display)
    with open(args.instance, "r") as f:
        data = json.load(f)

    graph = Graph.from_json(args.instance)
    params = build_params(data)
    instance_name = os.path.splitext(os.path.basename(args.instance))[0]

    num_runs = args.runs if args.runs is not None else config.INDEPENDENT_RUNS
    base_seed = args.seed if args.seed is not None else config.RANDOM_SEED
    num_ants = args.ants if args.ants is not None else config.NUM_ANTS
    max_iter = args.iterations if args.iterations is not None else config.MAX_ITERATIONS

    # Determine worker count
    if args.workers is not None and args.workers > 0:
        num_workers = args.workers
    elif config.PARALLEL_WORKERS > 0:
        num_workers = config.PARALLEL_WORKERS
    else:
        num_workers = multiprocessing.cpu_count()
    num_workers = min(num_workers, num_runs)

    e_bat = params["battery_capacity"]
    customers = graph.get_customers()
    print(f"\n[ACO] Instance: {instance_name}")
    print(f"[ACO] Customers: {len(customers)} — {customers}")
    print(f"[ACO] Runs: {num_runs}, Ants: {num_ants}, Max Iters: {max_iter}")
    print(f"[ACO] Seed: {base_seed}")
    print(f"[ACO] Parallel workers: {num_workers}")

    logger = ACOLogger(output_dir="results")

    total_start = time.time()

    # ── Build task list for workers ──
    tasks = [
        (args.instance, num_ants, max_iter, base_seed + run - 1, run)
        for run in range(1, num_runs + 1)
    ]

    # ── Dispatch runs in parallel ──
    print(f"\n[ACO] Launching {num_runs} run(s) across {num_workers} worker(s)...")
    with multiprocessing.Pool(processes=num_workers) as pool:
        run_results = pool.map(_run_single, tasks)

    # ── Process results in main process (deterministic order) ──
    all_objectives: List[float] = []
    overall_best_result: RouteResult | None = None
    overall_best_cost = float("inf")
    overall_best_history: List[dict] = []
    overall_best_run = 0
    overall_best_runtime = 0.0
    overall_best_pheromone = None

    for res in sorted(run_results, key=lambda r: r["run_id"]):
        run_id = res["run_id"]
        seed = res["seed"]

        # Report errors
        if res["error"]:
            print(f"\n[ACO] WARNING: {res['error']}")
            continue

        cost = res["cost"]
        best_result = res["best_result"]
        history = res["history"]
        run_time = res["runtime"]

        print(f"\n--- Run {run_id}/{num_runs} (seed={seed}) ---")
        print(f"    Best cost: {cost:.6f}  ({run_time:.2f}s)")

        all_objectives.append(cost)

        # Log
        logger.log_iteration_csv(history, run_id, instance_name)
        if best_result:
            logger.log_run_summary(run_id, best_result, run_time, instance_name)

        # Convergence plot per run
        if not args.no_plot and history:
            plot_convergence(
                history,
                os.path.join("results", f"{instance_name}_run{run_id}_convergence.png"),
                run_id=run_id,
            )

        if cost < overall_best_cost:
            overall_best_cost = cost
            overall_best_result = best_result
            overall_best_history = history
            overall_best_run = run_id
            overall_best_runtime = run_time
            overall_best_pheromone = res["pheromone"]

    total_time_elapsed = time.time() - total_start

    # Pheromone heatmap for best run
    if not args.no_plot and overall_best_pheromone is not None:
        labels, matrix = overall_best_pheromone
        plot_pheromone_heatmap(
            labels, matrix,
            os.path.join("results", f"{instance_name}_best_pheromone.png"),
        )

    # ── final output ──
    if overall_best_result:
        converged_iter = len(overall_best_history)
        print_solution(overall_best_result, e_bat, overall_best_runtime, converged_iter)

    # Multi-run summary
    if num_runs > 1 and len(all_objectives) > 1:
        ACOLogger.print_multi_run_summary(all_objectives)
        if not args.no_plot:
            plot_box(
                all_objectives,
                os.path.join("results", f"{instance_name}_boxplot.png"),
            )

    print(f"[ACO] Total elapsed: {total_time_elapsed:.2f}s across {num_runs} run(s)")
    print(f"[ACO] Logs and plots saved to results/")


if __name__ == "__main__":
    main()
