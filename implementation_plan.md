# ACO-Based Electric Vehicle Routing Problem — Implementation Plan

Build a complete Python project implementing Ant Colony Optimization (ACO) for the Single Electric Vehicle Routing Problem with static/dynamic charging. The project follows the specifications in [aco_rules.md](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/aco_rules.md).

## Proposed Changes

### Core Infrastructure

#### [NEW] [config.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/config.py)

All physics constants and ACO hyperparameters with defaults from the spec:
- Physics: gravity, air density, angle, vehicle mass, drag, cross-section, rolling resistance, mass factor
- Battery: capacity (100 kWh), threshold (20%), charging power (100 kW), efficiency (0.95)
- DWC: power (20 kW), efficiency (0.85), electric road speed (50 km/h)
- Vehicle: base speed (50 km/h), package weight (5 kg)
- ACO: num_ants=20, max_iterations=500, alpha=1.0, beta=3.0, rho=0.1, Q=100, tau_0=1.0, elitist_weight=2, use_mmas=True
- Runs: independent_runs=10, convergence_patience=50
- Local search: 2-opt, max_ls_iterations=500, threshold=1e-6
- Penalties: PENALTY_BATTERY_DEAD=99999, PENALTY_UNREACHABLE=99999

---

#### [NEW] [graph.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/graph.py)

Graph representation and pathfinding:
- `Graph` class: load from JSON, store nodes (with types) and edges (with distance, traffic_factor, type)
- Adjacency model: directed edges for electric roads, undirected for normal roads (stored as two directed edges)
- `dijkstra(source, target)`: shortest path by distance, returns path + total distance
- `get_customers()`, `get_charging_stations()`, `get_depot()` helpers
- `shortest_path_distance_matrix()`: precompute distances between all customer pairs + depot for ACO heuristic info

---

#### [NEW] [energy.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/energy.py)

Energy consumption and charging calculations:
- `compute_energy_consumption(distance, speed_kmh, total_mass, params)`: implements the energy formula from Section 7 with dv/dt speed thresholds
- `compute_travel_time(distance, base_speed, traffic_factor)`: actual_speed = base_speed * traffic_factor; time = distance / actual_speed
- `compute_dwc_energy_gain(distance, speed, dwc_power, dwc_efficiency)`: Equation 8
- `compute_charging_time(energy_needed, power, efficiency)`: Equation 4.4
- `check_charging_needed(current_energy, threshold, battery_cap, energy_for_next_edge)`: Equation 4.2

---

#### [NEW] [simulator.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/simulator.py)

Route decoder — takes a customer visit order and produces a full route with all metrics:
- `RouteResult` dataclass: route_sequence, total_time, total_distance, total_energy_consumed, total_energy_charged_static, total_energy_charged_dynamic, final_battery, packages_delivered, charging_stops, arrival_times, soc_trail, energy_trail, time_trail, objective_value
- `decode_route(customer_order, graph, params)`: main decoder function
  - For each customer in order: find shortest path from current node, traverse edge-by-edge
  - At each edge: check charging decision (Eq 4.2), detour to nearest CS if needed (Option B policy with Option A fallback), compute energy consumption, handle DWC charging on electric roads, update mass after delivery
  - Final leg: return to depot
  - Compute objective: `sum_arrival_times - 0.01 * sum_battery_levels`
- `find_nearest_reachable_cs(current_node, graph, current_energy, params)`: find closest charging station the vehicle can reach

---

### ACO Engine

#### [NEW] [aco.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/aco.py)

Core ACO algorithm:
- `ACOEngine` class:
  - `__init__`: initialize pheromone matrix τ[i][j] for all customer pairs + depot, compute heuristic matrix η[i][j] = 1/d(Li,Lj)
  - `construct_solution(ant_id)`: build tour using transition probability formula with α, β exponents and roulette wheel selection
  - `evaporate_pheromones()`: τ *= (1 - ρ) for all entries
  - `deposit_pheromones(ants_solutions)`: Δτ = Q / cost for each ant; add to edges in tour
  - `apply_mmas_bounds()`: clamp τ to [τ_min, τ_max]
  - `elitist_deposit(best_tour, best_cost)`: extra deposit for best-so-far
  - `run_iteration()`: construct solutions for all ants → evaluate via simulator → update pheromones → apply local search to best → track global best
  - `run(max_iterations)`: main loop with early stopping (convergence_patience)

---

#### [NEW] [local_search.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/local_search.py)

2-opt improvement heuristic:
- `two_opt(customer_order, simulator, graph, params, max_iterations, threshold)`: iteratively try reversing sub-sequences; accept if cost improves; stop when no improvement or max iterations reached
- Applied to iteration-best and global-best solutions per the spec

---

### Support Modules

#### [NEW] [logger.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/logger.py)

- `ACOLogger` class: write per-iteration CSV (iteration, best/worst/avg cost, global best, best tour)
- `log_run_summary(run_id, result)`: final summary for each run
- `log_multi_run_summary(all_results)`: best/worst/mean/std across runs

---

#### [NEW] [plotter.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/plotter.py)

- `plot_convergence(history, output_path)`: global best cost vs. iteration
- `plot_box(run_results, output_path)`: objective distribution across runs
- `plot_pheromone_heatmap(pheromone_matrix, labels, output_path)`: optional pheromone visualization
- Uses `matplotlib`

---

#### [NEW] [main.py](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/main.py)

Entry point:
- CLI: `python main.py --instance instances/instance_1.json [--runs 10] [--seed 42]`
- Load JSON instance → build graph → run ACO for N independent runs → aggregate results
- Print formatted output matching the console format in the spec (objective, times, distances, energy, SoC/energy/time trails)
- Save CSV logs and plots to `results/`

---

### Test Instances

#### [NEW] [instances/instance_1.json](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/instances/instance_1.json)
Trivial: D ↔ L1 (5km), 1 customer, no charging needed.

#### [NEW] [instances/instance_2.json](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/instances/instance_2.json)
Simple with charging: D, L1, L2, CS1, intersection 1. Tests charging detour logic.

#### [NEW] [instances/instance_3.json](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/instances/instance_3.json)
With electric road: adds Ns1, Ne1 electric road segment. Tests DWC energy gain.

#### [NEW] [instances/instance_4.json](file:///c:/Users/ranji/OneDrive/Documents/GitHub/EVRP-BSS-DWC-AC/instances/instance_4.json)
Stress test: 5 customers, 2 charging stations, 2 electric road segments, 5 intersections.

---

## Verification Plan

### Automated Tests

Run each instance and verify correctness:

```bash
# Instance 1 — Trivial (1 customer, no charging)
python main.py --instance instances/instance_1.json --runs 1 --seed 42
# Expect: D → L1 → D, no charging stops, valid energy/time calculations

# Instance 2 — With charging station
python main.py --instance instances/instance_2.json --runs 1 --seed 42
# Expect: visits L1 and L2, may use CS1, charging time reflected in output

# Instance 3 — With electric road
python main.py --instance instances/instance_3.json --runs 1 --seed 42
# Expect: DWC energy gain visible in output when electric road is used

# Instance 4 — Stress test (5 customers)
python main.py --instance instances/instance_4.json --runs 10 --seed 42
# Expect: all 5 customers visited, convergence within 500 iterations,
#          best/worst/mean/std reported, plots generated in results/
```

### Verification Checklist
- [ ] All customers visited and packages delivered in every solution
- [ ] Route starts and ends at depot D
- [ ] Energy never drops below 0 (unless penalized as infeasible)
- [ ] SoC trail, energy consumption trail, and travel time trail print correctly
- [ ] Charging stops are logged with station ID, time, and energy added
- [ ] Convergence curve and box plot are generated in `results/`
- [ ] Multiple runs with different seeds produce varying results
- [ ] Output format matches the spec's console output template
