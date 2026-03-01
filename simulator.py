"""
simulator.py — Route decoder: takes a customer-visit-order (permutation)
and produces a full route with all metrics (time, energy, charging, trails).

This module is algorithm-agnostic; ACO, GA, and C&W can all call
``decode_route()`` with different customer orderings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

from graph import Graph, Edge
from energy import (
    compute_actual_speed,
    compute_travel_time,
    compute_energy_consumption,
    compute_dwc_energy_gain,
    check_charging_needed,
    compute_charging_time,
    compute_charge_target_option_a,
    compute_charge_target_option_b,
)
from config import (
    BATTERY_CAPACITY, BATTERY_THRESHOLD, INITIAL_BATTERY_PERCENT,
    PACKAGE_WEIGHT, ELECTRIC_ROAD_SPEED, PENALTY_BATTERY_DEAD,
    PENALTY_UNREACHABLE, BASE_SPEED, VEHICLE_MASS,
)


# ──────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────

@dataclass
class ChargingStop:
    station_id: str
    time_charged: float   # hours
    energy_added: float   # kWh


@dataclass
class RouteResult:
    route_sequence: List[str] = field(default_factory=list)
    total_time: float = 0.0               # hours
    total_distance: float = 0.0           # km
    total_energy_consumed: float = 0.0    # kWh
    total_energy_charged_static: float = 0.0  # kWh
    total_energy_charged_dynamic: float = 0.0  # kWh
    final_battery: float = 0.0            # kWh
    packages_delivered: int = 0
    charging_stops: List[ChargingStop] = field(default_factory=list)

    # per-node trails
    soc_trail: List[Tuple[str, float]] = field(default_factory=list)        # (node, %)
    energy_trail: List[Tuple[str, str, float]] = field(default_factory=list)  # (from, to, kWh)
    time_trail: List[Tuple[str, str, float]] = field(default_factory=list)    # (from, to, minutes)

    # for objective
    arrival_times: List[float] = field(default_factory=list)    # cumulative time at each node (hours)
    battery_levels: List[float] = field(default_factory=list)    # kWh at each node

    objective: float = float("inf")
    is_feasible: bool = True


# ──────────────────────────────────────────────
# Helper: build params dict from JSON data
# ──────────────────────────────────────────────

def build_params(data: dict) -> dict:
    """
    Merge JSON instance parameters with defaults.
    Returns a flat dict usable by energy.py functions.
    """
    import math, config
    return {
        "base_speed": data.get("base_speed", BASE_SPEED),
        "vehicle_mass": data.get("vehicle_mass", VEHICLE_MASS),
        "rolling_resistance": data.get("rolling_resistance", config.ROLLING_RESISTANCE),
        "drag_coefficient": data.get("drag_coefficient", config.DRAG_COEFFICIENT),
        "cross_sectional_area": data.get("cross_sectional_area", config.CROSS_SECTIONAL_AREA),
        "mass_factor": data.get("mass_factor", config.MASS_FACTOR),
        "gravity": config.GRAVITY,
        "air_density": data.get("air_density", config.AIR_DENSITY),
        "road_angle_rad": math.radians(data.get("angle", config.ROAD_ANGLE_DEG)),
        "battery_capacity": data.get("battery_capacity", BATTERY_CAPACITY),
        "battery_threshold": data.get("battery_threshold", BATTERY_THRESHOLD) if data.get("battery_threshold", BATTERY_THRESHOLD) <= 1 else data.get("battery_threshold", BATTERY_THRESHOLD) / 100,
        "initial_battery_percent": data.get("initial_battery_percent", INITIAL_BATTERY_PERCENT),
        "package_weight": data.get("package_weight", PACKAGE_WEIGHT),
        "charging_power": data.get("charging_power", config.CHARGING_POWER),
        "charging_efficiency": data.get("charging_efficiency", config.CHARGING_EFFICIENCY),
        "dwc_power": data.get("dwc_power", config.DWC_POWER),
        "dwc_efficiency": data.get("dwc_efficiency", config.DWC_EFFICIENCY),
        "electric_road_speed": data.get("electric_road_speed", ELECTRIC_ROAD_SPEED),
    }


# ──────────────────────────────────────────────
# Nearest reachable charging station
# ──────────────────────────────────────────────

def _find_nearest_cs(
    current_node: str,
    graph: Graph,
    current_energy: float,
    params: dict,
    load_kg: float,
) -> Optional[Tuple[str, List[Edge], float]]:
    """
    Find the nearest charging station reachable from current_node
    given current energy and load.
    Returns (cs_id, edges_to_cs, energy_to_reach_cs) or None.
    """
    stations = graph.get_charging_stations()
    best = None
    for cs in stations:
        edges, dist = graph.shortest_path_edges(current_node, cs)
        if not edges:
            continue
        # compute energy cost to reach CS
        e_cost = 0.0
        for edge in edges:
            if edge.type == "electric":
                v = params["electric_road_speed"]
            else:
                v = compute_actual_speed(params["base_speed"], edge.traffic_factor)
            total_mass = params["vehicle_mass"] + load_kg
            e_cost += compute_energy_consumption(edge.distance, v, total_mass, params)
            # subtract DWC gain on electric roads
            if edge.type == "electric":
                e_cost -= compute_dwc_energy_gain(edge.distance, v, params)
        if e_cost > current_energy:
            continue  # can't reach this CS
        if best is None or dist < best[2]:
            best = (cs, edges, e_cost)
    return best


# ──────────────────────────────────────────────
# Compute energy needed ahead (for Option B)
# ──────────────────────────────────────────────

def _energy_needed_ahead(
    current_node: str,
    remaining_customers: List[str],
    depot: str,
    graph: Graph,
    params: dict,
    load_kg: float,
) -> float:
    """
    Estimate energy needed to reach next CS or depot from the current
    planned path.  Used by Option B charging policy.
    Simple estimate: energy from current_node → next customer → depot
    """
    if not remaining_customers:
        # just need to get back to depot
        edges, _ = graph.shortest_path_edges(current_node, depot)
        if not edges:
            return params["battery_capacity"]  # force full charge
        total = 0.0
        for e in edges:
            v = params["electric_road_speed"] if e.type == "electric" else compute_actual_speed(params["base_speed"], e.traffic_factor)
            total += compute_energy_consumption(e.distance, v, params["vehicle_mass"] + load_kg, params)
            if e.type == "electric":
                total -= compute_dwc_energy_gain(e.distance, v, params)
        return max(total, 0.0)

    # energy to next customer + customer to depot (rough)
    next_cust = remaining_customers[0]
    total = 0.0
    for src, dst in [(current_node, next_cust), (next_cust, depot)]:
        edges, _ = graph.shortest_path_edges(src, dst)
        if not edges:
            return params["battery_capacity"]
        for e in edges:
            v = params["electric_road_speed"] if e.type == "electric" else compute_actual_speed(params["base_speed"], e.traffic_factor)
            total += compute_energy_consumption(e.distance, v, params["vehicle_mass"] + load_kg, params)
            if e.type == "electric":
                total -= compute_dwc_energy_gain(e.distance, v, params)
    return max(total, 0.0)


# ──────────────────────────────────────────────
# Main route decoder
# ──────────────────────────────────────────────

def decode_route(
    customer_order: List[str],
    graph: Graph,
    params: dict,
) -> RouteResult:
    """
    Decode a customer visit order into a full route with metrics.

    Parameters
    ----------
    customer_order : list of customer node IDs in visit order
    graph          : loaded Graph
    params         : parameter dict (from build_params)

    Returns
    -------
    RouteResult with all fields populated.
    """
    result = RouteResult()
    depot = graph.get_depot()

    e_bat = params["battery_capacity"]
    e_current = e_bat * (params["initial_battery_percent"] / 100.0)
    total_time = 0.0
    total_distance = 0.0
    total_energy_consumed = 0.0
    total_energy_charged_static = 0.0
    total_energy_charged_dynamic = 0.0
    num_customers = len(customer_order)
    load_kg = num_customers * params["package_weight"]
    packages_delivered = 0
    is_feasible = True

    current_node = depot
    route_seq = [depot]

    result.soc_trail.append((depot, (e_current / e_bat) * 100))
    result.arrival_times.append(total_time)
    result.battery_levels.append(e_current)

    # visit each customer in order, then return to depot
    destinations = list(customer_order) + [depot]
    remaining_customers = list(customer_order)

    for dest in destinations:
        # find shortest path from current_node to dest
        path_edges, path_dist = graph.shortest_path_edges(current_node, dest)

        if not path_edges:
            # unreachable
            result.objective = PENALTY_UNREACHABLE
            result.is_feasible = False
            result.route_sequence = route_seq
            result.total_time = total_time
            result.total_distance = total_distance
            result.total_energy_consumed = total_energy_consumed
            result.total_energy_charged_static = total_energy_charged_static
            result.total_energy_charged_dynamic = total_energy_charged_dynamic
            result.final_battery = e_current
            result.packages_delivered = packages_delivered
            return result

        # traverse each edge on the path
        for edge in path_edges:
            # determine speed
            if edge.type == "electric":
                actual_speed = params["electric_road_speed"]
            else:
                actual_speed = compute_actual_speed(params["base_speed"], edge.traffic_factor)

            total_mass = params["vehicle_mass"] + load_kg

            # energy cost for this edge
            e_edge = compute_energy_consumption(edge.distance, actual_speed, total_mass, params)

            # check charging decision BEFORE traversing (Eq 4.2)
            if check_charging_needed(e_current, e_edge, params):
                # try to detour to nearest CS
                cs_info = _find_nearest_cs(current_node, graph, e_current, params, load_kg)
                if cs_info is not None:
                    cs_id, cs_edges, e_cost_to_cs = cs_info

                    # traverse edges to CS
                    for cs_edge in cs_edges:
                        if cs_edge.type == "electric":
                            cs_speed = params["electric_road_speed"]
                        else:
                            cs_speed = compute_actual_speed(params["base_speed"], cs_edge.traffic_factor)

                        cs_mass = params["vehicle_mass"] + load_kg
                        cs_e_edge = compute_energy_consumption(cs_edge.distance, cs_speed, cs_mass, params)
                        cs_t_edge = compute_travel_time(cs_edge.distance, cs_speed)

                        # DWC gain on electric road
                        dwc_gain = 0.0
                        if cs_edge.type == "electric":
                            dwc_gain = compute_dwc_energy_gain(cs_edge.distance, cs_speed, params)
                            total_energy_charged_dynamic += dwc_gain

                        e_current -= cs_e_edge
                        e_current += dwc_gain
                        e_current = min(e_current, e_bat)
                        total_energy_consumed += cs_e_edge
                        total_time += cs_t_edge
                        total_distance += cs_edge.distance

                        if e_current < 0:
                            is_feasible = False

                        # record intermediate node
                        if cs_edge.dst != current_node:
                            route_seq.append(cs_edge.dst)
                            result.soc_trail.append((cs_edge.dst, (max(e_current, 0) / e_bat) * 100))
                            result.energy_trail.append((cs_edge.src, cs_edge.dst, cs_e_edge))
                            result.time_trail.append((cs_edge.src, cs_edge.dst, cs_t_edge * 60))
                            result.arrival_times.append(total_time)
                            result.battery_levels.append(max(e_current, 0))

                    # now at CS — charge
                    e_remaining = max(e_current, 0)

                    # Option B (primary)
                    e_ahead = _energy_needed_ahead(
                        cs_id, remaining_customers, depot, graph, params, load_kg
                    )
                    e_target = compute_charge_target_option_b(e_remaining, e_ahead, params)

                    # Fallback to Option A if target invalid
                    if e_target <= e_remaining or e_target > e_bat:
                        e_target = compute_charge_target_option_a(params)

                    t_charge = compute_charging_time(e_remaining, e_target, params)
                    energy_added = e_target - e_remaining

                    e_current = e_target
                    total_time += t_charge
                    total_energy_charged_static += energy_added

                    result.charging_stops.append(ChargingStop(cs_id, t_charge, energy_added))

                    current_node = cs_id

                    # need to re-find path to original destination
                    path_edges_new, _ = graph.shortest_path_edges(current_node, dest)
                    if not path_edges_new:
                        result.objective = PENALTY_UNREACHABLE
                        result.is_feasible = False
                        result.route_sequence = route_seq
                        result.total_time = total_time
                        result.total_distance = total_distance
                        result.total_energy_consumed = total_energy_consumed
                        result.total_energy_charged_static = total_energy_charged_static
                        result.total_energy_charged_dynamic = total_energy_charged_dynamic
                        result.final_battery = e_current
                        result.packages_delivered = packages_delivered
                        return result

                    # re-traverse from CS to destination
                    for new_edge in path_edges_new:
                        if new_edge.type == "electric":
                            ns = params["electric_road_speed"]
                        else:
                            ns = compute_actual_speed(params["base_speed"], new_edge.traffic_factor)

                        nm = params["vehicle_mass"] + load_kg
                        ne = compute_energy_consumption(new_edge.distance, ns, nm, params)
                        nt = compute_travel_time(new_edge.distance, ns)

                        dwc_g = 0.0
                        if new_edge.type == "electric":
                            dwc_g = compute_dwc_energy_gain(new_edge.distance, ns, params)
                            total_energy_charged_dynamic += dwc_g

                        e_current -= ne
                        e_current += dwc_g
                        e_current = min(e_current, e_bat)
                        total_energy_consumed += ne
                        total_time += nt
                        total_distance += new_edge.distance

                        if e_current < 0:
                            is_feasible = False

                        route_seq.append(new_edge.dst)
                        result.soc_trail.append((new_edge.dst, (max(e_current, 0) / e_bat) * 100))
                        result.energy_trail.append((new_edge.src, new_edge.dst, ne))
                        result.time_trail.append((new_edge.src, new_edge.dst, nt * 60))
                        result.arrival_times.append(total_time)
                        result.battery_levels.append(max(e_current, 0))

                    current_node = dest
                    # deliver if customer
                    if dest in customer_order:
                        packages_delivered += 1
                        load_kg -= params["package_weight"]
                        load_kg = max(load_kg, 0)
                        if dest in remaining_customers:
                            remaining_customers.remove(dest)
                    continue  # move to next destination
                # else: no CS reachable → continue and hope for the best (will be penalised)

            # normal traversal (no charging detour)
            t_edge = compute_travel_time(edge.distance, actual_speed)

            # DWC gain
            dwc_gain = 0.0
            if edge.type == "electric":
                dwc_gain = compute_dwc_energy_gain(edge.distance, actual_speed, params)
                total_energy_charged_dynamic += dwc_gain

            e_current -= e_edge
            e_current += dwc_gain
            e_current = min(e_current, e_bat)
            total_energy_consumed += e_edge
            total_time += t_edge
            total_distance += edge.distance

            if e_current < 0:
                is_feasible = False

            route_seq.append(edge.dst)
            result.soc_trail.append((edge.dst, (max(e_current, 0) / e_bat) * 100))
            result.energy_trail.append((edge.src, edge.dst, e_edge))
            result.time_trail.append((edge.src, edge.dst, t_edge * 60))
            result.arrival_times.append(total_time)
            result.battery_levels.append(max(e_current, 0))

            current_node = edge.dst

        # after reaching destination
        if dest in customer_order:
            packages_delivered += 1
            load_kg -= params["package_weight"]
            load_kg = max(load_kg, 0)
            if dest in remaining_customers:
                remaining_customers.remove(dest)

    # ── compute objective ────────────────────
    result.route_sequence = route_seq
    result.total_time = total_time
    result.total_distance = total_distance
    result.total_energy_consumed = total_energy_consumed
    result.total_energy_charged_static = total_energy_charged_static
    result.total_energy_charged_dynamic = total_energy_charged_dynamic
    result.final_battery = max(e_current, 0)
    result.packages_delivered = packages_delivered

    if not is_feasible:
        result.is_feasible = False
        result.objective = PENALTY_BATTERY_DEAD
    else:
        sum_at = sum(result.arrival_times)
        sum_bl = sum(result.battery_levels)
        result.objective = sum_at - 0.01 * sum_bl

    return result
