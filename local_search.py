"""
local_search.py — 2-opt improvement heuristic for customer visit orders.
"""

from typing import List, Tuple

from simulator import decode_route, RouteResult
from graph import Graph


def two_opt(
    customer_order: List[str],
    graph: Graph,
    params: dict,
    max_iterations: int = 500,
    improvement_threshold: float = 1e-6,
) -> Tuple[List[str], float]:
    """
    Apply 2-opt local search to improve a customer visit order.

    Iteratively reverses sub-sequences of the customer order and accepts
    the change if it reduces the objective value.

    Returns (improved_order, improved_cost).
    """
    n = len(customer_order)
    if n < 3:
        result = decode_route(customer_order, graph, params)
        return list(customer_order), result.objective

    best_order = list(customer_order)
    best_cost = decode_route(best_order, graph, params).objective

    for iteration in range(max_iterations):
        improved = False
        for i in range(n - 1):
            for j in range(i + 2, n):
                # create new order by reversing segment [i, j]
                new_order = (
                    best_order[:i]
                    + list(reversed(best_order[i:j + 1]))
                    + best_order[j + 1:]
                )
                new_cost = decode_route(new_order, graph, params).objective

                if new_cost < best_cost - improvement_threshold:
                    best_order = new_order
                    best_cost = new_cost
                    improved = True
                    break  # restart inner loops
            if improved:
                break

        if not improved:
            break

    return best_order, best_cost
