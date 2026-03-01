"""
aco.py — Ant Colony Optimization engine.

Manages pheromone matrix, solution construction via transition probabilities,
pheromone evaporation/deposit, MMAS bounds, and elitist strategy.
"""

from __future__ import annotations
import random
import math
from typing import List, Dict, Optional, Tuple

from graph import Graph
from simulator import decode_route, RouteResult
from local_search import two_opt
from config import (
    NUM_ANTS, MAX_ITERATIONS, ALPHA, BETA, RHO, Q, TAU_0,
    USE_ELITIST, ELITIST_WEIGHT, USE_MMAS,
    CONVERGENCE_CHECK, CONVERGENCE_PATIENCE,
    LOCAL_SEARCH, MAX_LS_ITERATIONS, LS_IMPROVEMENT_THRESHOLD,
)


class ACOEngine:
    """Ant Colony Optimization for EVRP customer-visit-order."""

    def __init__(
        self,
        graph: Graph,
        params: dict,
        *,
        num_ants: int = NUM_ANTS,
        max_iterations: int = MAX_ITERATIONS,
        alpha: float = ALPHA,
        beta: float = BETA,
        rho: float = RHO,
        q: float = Q,
        tau_0: float = TAU_0,
        use_elitist: bool = USE_ELITIST,
        elitist_weight: int = ELITIST_WEIGHT,
        use_mmas: bool = USE_MMAS,
        convergence_check: bool = CONVERGENCE_CHECK,
        convergence_patience: int = CONVERGENCE_PATIENCE,
        local_search: str = LOCAL_SEARCH,
        max_ls_iterations: int = MAX_LS_ITERATIONS,
        ls_threshold: float = LS_IMPROVEMENT_THRESHOLD,
        seed: Optional[int] = None,
    ):
        self.graph = graph
        self.params = params

        self.num_ants = num_ants
        self.max_iterations = max_iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.use_elitist = use_elitist
        self.elitist_weight = elitist_weight
        self.use_mmas = use_mmas
        self.convergence_check = convergence_check
        self.convergence_patience = convergence_patience
        self.local_search = local_search
        self.max_ls_iterations = max_ls_iterations
        self.ls_threshold = ls_threshold

        self.customers: List[str] = graph.get_customers()
        self.depot: str = graph.get_depot()
        self.n = len(self.customers)

        # all nodes for pheromone (depot + customers)
        self.phe_nodes = [self.depot] + self.customers

        if seed is not None:
            random.seed(seed)

        # ── precompute distance matrix & heuristic ──
        self.dist_matrix = graph.distance_matrix(self.phe_nodes)
        self.heuristic: Dict[str, Dict[str, float]] = {}
        for i in self.phe_nodes:
            self.heuristic[i] = {}
            for j in self.phe_nodes:
                d = self.dist_matrix[i][j]
                if d > 0:
                    self.heuristic[i][j] = 1.0 / d
                else:
                    self.heuristic[i][j] = 1e6  # same node or zero distance

        # ── pheromone matrix ──
        self.pheromone: Dict[str, Dict[str, float]] = {}
        for i in self.phe_nodes:
            self.pheromone[i] = {}
            for j in self.phe_nodes:
                self.pheromone[i][j] = tau_0

        # MMAS bounds (set after first solution)
        self.tau_min = tau_0
        self.tau_max = tau_0

        # tracking
        self.global_best_tour: Optional[List[str]] = None
        self.global_best_cost: float = float("inf")
        self.global_best_result: Optional[RouteResult] = None
        self.history: List[dict] = []  # per-iteration stats

    # ──────────────────────────────────────────────
    # Solution Construction
    # ──────────────────────────────────────────────

    def _construct_solution(self) -> List[str]:
        """Build one ant's customer visit order using transition probabilities."""
        current = self.depot
        unvisited = set(self.customers)
        tour: List[str] = []

        while unvisited:
            probs = []
            candidates = list(unvisited)

            for j in candidates:
                tau = self.pheromone[current][j]
                eta = self.heuristic[current][j]
                probs.append((tau ** self.alpha) * (eta ** self.beta))

            total = sum(probs)
            if total <= 0:
                # fallback: uniform random
                next_cust = random.choice(candidates)
            else:
                # roulette wheel selection
                r = random.random() * total
                cumulative = 0.0
                next_cust = candidates[-1]  # default
                for idx, p in enumerate(probs):
                    cumulative += p
                    if cumulative >= r:
                        next_cust = candidates[idx]
                        break

            tour.append(next_cust)
            current = next_cust
            unvisited.remove(next_cust)

        return tour

    # ──────────────────────────────────────────────
    # Pheromone Update
    # ──────────────────────────────────────────────

    def _evaporate(self):
        """Evaporate all pheromone trails: τ *= (1 - ρ)."""
        factor = 1.0 - self.rho
        for i in self.phe_nodes:
            for j in self.phe_nodes:
                self.pheromone[i][j] *= factor

    def _deposit(self, solutions: List[Tuple[List[str], float]]):
        """Deposit pheromone for each ant's solution."""
        for tour, cost in solutions:
            if cost <= 0 or cost >= 99999:
                continue
            delta = self.q / cost
            # depot → first customer
            self.pheromone[self.depot][tour[0]] += delta
            # customer → customer
            for k in range(len(tour) - 1):
                self.pheromone[tour[k]][tour[k + 1]] += delta
            # last customer → depot (implicit)
            self.pheromone[tour[-1]][self.depot] += delta

    def _elitist_deposit(self):
        """Extra pheromone deposit for the global best solution."""
        if self.global_best_tour is None or self.global_best_cost >= 99999:
            return
        delta = self.elitist_weight * (self.q / self.global_best_cost)
        tour = self.global_best_tour
        self.pheromone[self.depot][tour[0]] += delta
        for k in range(len(tour) - 1):
            self.pheromone[tour[k]][tour[k + 1]] += delta
        self.pheromone[tour[-1]][self.depot] += delta

    def _apply_mmas_bounds(self):
        """Clamp pheromone values to [τ_min, τ_max]."""
        if self.global_best_cost < float("inf") and self.global_best_cost > 0:
            self.tau_max = 1.0 / (self.rho * self.global_best_cost)
            self.tau_min = self.tau_max / (2.0 * max(self.n, 1))

        for i in self.phe_nodes:
            for j in self.phe_nodes:
                self.pheromone[i][j] = max(self.tau_min,
                                           min(self.tau_max, self.pheromone[i][j]))

    # ──────────────────────────────────────────────
    # Single Iteration
    # ──────────────────────────────────────────────

    def _run_iteration(self) -> dict:
        """Run one ACO iteration: construct → evaluate → update pheromones."""
        solutions: List[Tuple[List[str], float]] = []
        results: List[RouteResult] = []
        iter_best_tour: Optional[List[str]] = None
        iter_best_cost = float("inf")
        iter_worst_cost = -float("inf")
        iter_best_result: Optional[RouteResult] = None
        cost_sum = 0.0

        for _ in range(self.num_ants):
            tour = self._construct_solution()
            result = decode_route(tour, self.graph, self.params)
            cost = result.objective
            solutions.append((tour, cost))
            results.append(result)

            cost_sum += cost
            if cost < iter_best_cost:
                iter_best_cost = cost
                iter_best_tour = tour
                iter_best_result = result
            if cost > iter_worst_cost:
                iter_worst_cost = cost

        # local search on iteration best
        if self.local_search == "2opt" and iter_best_tour is not None:
            improved_tour, improved_cost = two_opt(
                iter_best_tour, self.graph, self.params,
                self.max_ls_iterations, self.ls_threshold,
            )
            if improved_cost < iter_best_cost:
                iter_best_tour = improved_tour
                iter_best_cost = improved_cost
                iter_best_result = decode_route(improved_tour, self.graph, self.params)
                # update solutions list for pheromone deposit
                solutions.append((improved_tour, improved_cost))

        # update global best
        if iter_best_cost < self.global_best_cost and iter_best_result is not None:
            self.global_best_cost = iter_best_cost
            self.global_best_tour = list(iter_best_tour) if iter_best_tour else None
            self.global_best_result = iter_best_result

        # local search on global best too
        if self.local_search == "2opt" and self.global_best_tour is not None:
            improved_tour, improved_cost = two_opt(
                self.global_best_tour, self.graph, self.params,
                self.max_ls_iterations, self.ls_threshold,
            )
            if improved_cost < self.global_best_cost:
                self.global_best_tour = improved_tour
                self.global_best_cost = improved_cost
                self.global_best_result = decode_route(improved_tour, self.graph, self.params)

        # pheromone update
        self._evaporate()
        self._deposit(solutions)
        if self.use_elitist:
            self._elitist_deposit()
        if self.use_mmas:
            self._apply_mmas_bounds()

        avg_cost = cost_sum / max(self.num_ants, 1)

        stats = {
            "best_cost": iter_best_cost,
            "worst_cost": iter_worst_cost,
            "average_cost": avg_cost,
            "global_best_cost": self.global_best_cost,
            "best_tour": list(iter_best_tour) if iter_best_tour else [],
        }
        return stats

    # ──────────────────────────────────────────────
    # Main loop
    # ──────────────────────────────────────────────

    def run(self) -> Tuple[RouteResult, List[dict]]:
        """
        Run the full ACO for max_iterations (with optional early stopping).
        Returns (best RouteResult, per-iteration history).
        """
        no_improve_count = 0
        prev_best = float("inf")

        for it in range(1, self.max_iterations + 1):
            stats = self._run_iteration()
            stats["iteration"] = it
            self.history.append(stats)

            # convergence check
            if self.convergence_check:
                if self.global_best_cost < prev_best:
                    prev_best = self.global_best_cost
                    no_improve_count = 0
                else:
                    no_improve_count += 1
                if no_improve_count >= self.convergence_patience:
                    break

        # final decode of global best to ensure we have full result
        if self.global_best_tour:
            self.global_best_result = decode_route(
                self.global_best_tour, self.graph, self.params
            )

        return self.global_best_result, self.history

    def get_pheromone_matrix(self) -> Tuple[List[str], List[List[float]]]:
        """Return pheromone matrix as (labels, 2d list) for plotting."""
        labels = self.phe_nodes
        matrix = []
        for i in labels:
            row = [self.pheromone[i][j] for j in labels]
            matrix.append(row)
        return labels, matrix
