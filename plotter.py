"""
plotter.py — Convergence curves, box plots, and pheromone heatmap.
Uses matplotlib.
"""

from __future__ import annotations
import os
from typing import List, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def plot_convergence(
    history: List[dict],
    output_path: str,
    run_id: int = 0,
):
    """Plot global_best_cost vs iteration."""
    if not HAS_MPL:
        print("[plotter] matplotlib not available — skipping convergence plot.")
        return

    iterations = [h["iteration"] for h in history]
    global_best = [h["global_best_cost"] for h in history]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(iterations, global_best, linewidth=1.5, color="#2563eb")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Global Best Cost")
    ax.set_title(f"ACO Convergence — Run {run_id}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[plotter] Convergence plot saved: {output_path}")


def plot_box(
    objective_values: List[float],
    output_path: str,
):
    """Box plot of objective values across independent runs."""
    if not HAS_MPL:
        print("[plotter] matplotlib not available — skipping box plot.")
        return

    fig, ax = plt.subplots(figsize=(6, 5))
    bp = ax.boxplot(objective_values, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#93c5fd")
    ax.set_ylabel("Objective Value")
    ax.set_title("ACO — Objective Distribution Across Runs")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[plotter] Box plot saved: {output_path}")


def plot_pheromone_heatmap(
    labels: List[str],
    matrix: List[List[float]],
    output_path: str,
):
    """Heatmap of pheromone matrix at final iteration."""
    if not HAS_MPL:
        print("[plotter] matplotlib not available — skipping pheromone heatmap.")
        return

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("Pheromone Matrix Heatmap")
    fig.colorbar(im, ax=ax, label="Pheromone Level")
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[plotter] Pheromone heatmap saved: {output_path}")
