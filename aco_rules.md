This project introduces Single-Electric-Vehicle Routing Problem. The vehicle navigates a dynamic urban network, deciding routes and charging stops based on real-time traffic and the vehicle's changing payload weight. Energy consumption depends on how loaded the truck is, and it must choose between charging at dedicated static charging stations or using dynamic wireless electric roads. In short, you're fine-tuning the route, timing, and energy decisions for one vehicle to minimize delivery time.

- The EV has limited battery capacity
- Fixed locations where the vehicle can recharge
- Special road segments that provide dynamic (while-driving) charging
- The vehicle must visit specific customer locations to drop boxes
- Can only move to nodes that are adjacent to the current node

Optimization Objective: Minimize: Total travel time - (Sum of all battery levels / 100)

Primary goal: Minimize total travel time
Secondary goal: Maximize remaining battery (battery levels are slightly favored)
The division by 100 makes battery a minor factor compared to time

Environment is made of roads(edges) and locations(nodes). There are 4 types of node: Depot, Intersections, Charging Station, Customers. Now, we introduce 'electric road boundary' nodes—special markers at the start and end of electric road segments. These act as key checkpoints: the vehicle can gain in-motion energy efficiency between them. Thus, when a route is planned, crossing these boundary nodes signifies entering a zone with different energy rules. Instruct the system that these boundary nodes should be treated as distinct decision points—if the vehicle enters them, it changes energy modeling logic for that segment. In short, you're giving them a special category that modifies energy rules but still fits into the existing node framework. There are 2 types of edges: normal roads and electric roads(that allow vehicle to charge while its driving).

- Program will always have one depot, represented by label D.
- Program can also have 1 to n number of customers, labeled like L1, L2, L3,...Ln.
- Program can also have 1 to n number of Charging stations, labeled as CS1, CS2,....CSn.
- Program can also have Intersections, labeled like 1, 2, 3,...n.
- Electric road boundary nodes: Ns1, Ne1, Ns2, Ne2, …
  Where:
    - Nsx = start of electric road segment x
    - Nex = end of electric road segment x

- Every time EV starts from depot the starting charge is 100% (fully charged at depot)

For each edge we have:
- Distance of edge
- Traffic factor of an edge
- Type: i. normal or ii. electric

We will have a variable called base_speed. That will be considered as base speed at each edge.

5. Summary inputs to consider
    5.1. nodes (Depot, Intersections, Charging Station, Customers, special nodes that shows the starting and ending of electric road like Ns1 to Ne1)
    5.2. edges (including distance and traffic factor for each edge, and type of road: normal or electric)
    5.3. base speed (km)
    5.4. percentage battery level at which we start our journey from.
    5.5. starting node (From which node are we starting our journey, By default its depot)
    5.6. Capacity of battery
    M   = total vehicle mass (kg)
    f   = rolling resistance coefficient (unitless)
    Cx  = aerodynamic drag coefficient (unitless)
    A   = vehicle cross-sectional area (m²)
    m = mass_factor

- Program should take input from a json file. So all program input will be given in a json file. For each example instance we will need a different json file.

note that Charging Station = Static Charging Station = Parked / Plug-in / Static Linear Charging

6. Program
- Overall goal of program is to start journey from current node to deliver packages to all the customers and return to depot, while minimizing arrival time.

Objective: The objective gives higher priority to reducing arrival time and a smaller priority to keeping more battery.

```
cost(R) = sum_arrival_times(R) - 0.01 * total_remaining_battery(R)
```

Where:
- sum_arrival_times(R) : sum of arrival times at each node in the decoded route.
- total_remaining_battery(R) : sum of battery levels measured at arrival to each node.

- Speed of vehicle on each electric road is constant and same for all electric roads. Additionally, traffic will have no impact on them as well.
- In this program each customer will have exactly 1 package.
- Weight of each package is 5kg. This is the package that we will deliver to customer; know that each package will have same weight.

- Do not create two directed edges for normal roads.
- Electric roads are directional (start→end only).

- Calculate the Total_load that vehicle is carrying, by number_of_package * Weight_of_packages.
- Now calculate the actual_speed and Travel_time as mentioned below.
- actual_speed (v0) km/h = base_speed * traffic_factor(for that edge)
- Travel_time(of an edge) = distance (of that edge in km) / actual_speed (at an edge in km/h)
- compute it for every edge on the path and sum the results to get the total energy for the whole path
- Total_travel_time = sum(Travel_time_of_edge)

7. Now we calculate the energy, based on this equation
    -  energy_consumption = E = (1/3600) * [ M * g * ( f * cos(alpha) + sin(alpha) ) + 0.0386 * ( rho * Cx * A * v^2 ) + (M + m) * (dv/dt) ] * d

    - meaning of symbols

        M   = total vehicle mass including payload (kg)
        g   = gravity (9.81 m/s²)
        f   = rolling resistance coefficient (unitless)
        rho   = air density (kg/m³)
        Cx  = aerodynamic drag coefficient (unitless)
        A   = vehicle cross-sectional area (m²)
        v   = vehicle speed (m/s)
        m = mass_factor
        alpha = angle
        d = distance

    if 50 <= v0 <= 80:
        dv_dt = 0.3
    elif 81 <= v0 <= 120:
        dv_dt = 2
    else:
        dv_dt = 0

- note that all value like 50, 80, 81, 120 are in km/h

- the above mentioned equation can help to find the energy consumption between two nodes meaning an edge.
- to find the total energy consumption on a route we need to compute it for every edge on the path and sum the results to get the total energy for the whole path.
    - it should consider the change in speed on each edge except the electric road (based on traffic).
    - it should consider change in weight after delivery.
    Total_energy = sum(Travel_energy)
    - speed of vehicle on each electric road is constant and same for all electric roads. Additionally, traffic will have no impact on them as well.

- the route must start AND end at depot D
- time cost for dropping off a package is 0
- When traversing an electric road time cost for dropping off a package
- Initial node "By default its depot"

• Vehicle speed: vij = 50 km/h
• Total vehicle mass: mij = 1800 kg
• Mass of rolling inertia(aka mass factor): mf = 1.1 kg
• Gravitational acceleration: g = 9.8 m/s2
• Rolling resistance coefficient: f = 0.01
• Air density: ρ = 1.205 kg/m3
• Vehicle cross-sectional area: A = 3.5 m2
• Drag coefficient: Cx = 0.6
• Average road angle: θ = 0.86° degrees
• EV battery capacity: 100 kWh
• Charging station speed: 100 kW
• Average acceleration: dv/dt = 0.3 m/s2
• Battery threshold: 20% of total capacity

# EV Static Charging Model for Static Charging Station

## 1. Variable Definitions

All energy values must use consistent units (recommended: **kWh**).
Charging power should be in **kW**.

* `E_i(t)` → Remaining battery energy at time `t` (kWh)
* `E_bat` → Full battery capacity (kWh)
* `γ` → Mileage anxiety coefficient (0 < γ < 1)
* `E_edge(i→j)` → Energy required to traverse edge (kWh)
* `Ere_i_k` → Remaining energy upon arrival at charging station `CS_k` (kWh)
* `E_ex_i_k` → Energy after charging at `CS_k` (kWh)
* `P` → Charging power (kW)
* `ε` → Charging efficiency (0 < ε ≤ 1)
* `t_c` → Charging time (hours)

note that here Mileage anxiety coefficient = Battery threshold = 20%

## 2. Charging Decision Rule (Equation 4.2)

Before traveling from node `i` to node `j`, charge if:

```
E_i(t) ≤ γ * E_bat
OR
E_i(t) ≤ E_edge(i→j)
```

This means:

* Charge if battery is below safety threshold
* OR if battery cannot reach next segment

## 3. Remaining Energy at Charging Station (Equation 4.3)

When arriving at charging station `CS_k`:

```
Ere_i_k = E_i(tr) - E_edge(i→CS_k)
```

Where:

* `E_i(tr)` is energy before traveling to `CS_k`
* `E_edge(i→CS_k)` is energy required to reach the station

---

## 4. Charging Time Formula (Equation 4.4)

```
t_c = (E_ex_i_k - Ere_i_k) / (P * ε)
```

Conditions:

```
0 ≤ Ere_i_k ≤ E_ex_i_k ≤ E_bat
```

After charging:

```
E_current = E_ex_i_k
total_time += t_c
```


## 5. Charging Policies (Using Static Charging Station)

### Option A — Full Charge Policy

```
E_ex_i_k = E_bat
t_c = (E_bat - Ere_i_k) / (P * ε)
```

Simple and stable.

---

### Option B — Minimum Required Charge

Compute required energy to safely reach next charging station or depot:

```
E_needed_ahead = sum of E_edge until next CS or depot
safety = γ * E_bat
E_ex_i_k = min(E_bat, E_needed_ahead + safety)
t_c = (E_ex_i_k - Ere_i_k) / (P * ε)
```

More efficient, avoids unnecessary full charging.

---

### Charging Policy — Which one to use?

**Recommendation: Implement Option B (Minimum Required Charge) as the primary policy, with Option A (Full Charge) as fallback.**

**Implementation logic:**
- **Primary:** Use Option B to compute `E_needed_ahead` and charge only what's needed plus safety margin
- **Fallback:** If Option B calculation fails (e.g., cannot determine next CS/depot, or computed `E_ex_i_k` is invalid), use Option A (full charge to `E_bat`)
- **Rationale:** Option B is smarter and better for optimization (minimizes charging time), while Option A provides a safe, simple fallback

## 6. Battery Update During Travel

After traversing edge `(i → j)`:

```
E_current = E_current - E_edge(i→j)
total_time += travel_time(i→j)
```

Feasibility condition:

```
If E_current < 0 → Infeasible solution (apply heavy penalty)
```

## 8. Important Implementation Notes

* Use consistent energy units (kWh recommended)
* Clamp battery values within `[0, E_bat]`
* Charging time directly affects total travel time
* Keep charging policy deterministic during route evaluation
* Apply strong penalties for infeasible solutions

* Equation (4.2) → Charging decision
* Equation (4.3) → Remaining energy calculation
* Equation (4.4) → Charging time calculation

Below is the Markdown file content you can paste into a `.md` file. It adds the PIC and DWC (electric road system) charging models and shows exactly how to integrate them into your route simulator alongside the static charging model you already have.

# EV Charging Models — Static + Electric Road System (MD Version)

## 1. Variable / Unit Conventions (use consistently)

* Energies: **kWh**
* Power: **kW**
* Time: **hours**
* Distance / length: **km** (or meters — be consistent)
* Speed: **km/h**
* `E_current`, `E_bat`, `Ere`, `E_ex` → kWh
* `P_chg` → charging power (kW)
* `η_chg` → charging efficiency (0 < η ≤ 1)
* `t_charging` → charging time (hours)
* `L_DWC` → length of dynamic wireless charging section (km)
* `v` → average vehicle speed while on DWC section (km/h)

## 2. PIC (Parked / Plug-in / Static Linear Charging) — Linear Static Model

The common linear static charging model (PIC) updates battery state as a linear function of charging time:

**Equation (7)**
[
\lambda_{R_{k,w}} = \lambda_{i_{k,w}} + R_r \cdot t_{charging}
]

* `\lambda_{i_{k,w}}` — battery state (kWh or SOC in same units) before charging.
* `\lambda_{R_{k,w}}` — battery state after charging.
* `R_r` — effective charging rate (kW). **Clarification: R_r = P * ε**, where:
  - `P` = Charging power (kW) — same as in the static charging model
  - `ε` = Charging efficiency (0 < ε ≤ 1) — same as in the static charging model
  - This makes PIC consistent with the static charging model (Equation 4.4).
* `t_charging` — charging duration (hours).

**Implementation notes**

* Energy added: `E_added = R_r * t_charging` (kWh).
* After charging: `E_current := min(E_bat, E_current + E_added)`.
* Charging time for given `E_target`: `t_charging = (E_target - E_current) / R_r` (hours).
* Clamp `E_target ≤ E_bat` and `E_current ≥ 0`.

## 3. DWC (Dynamic Wireless Charging — on-road charging)

DWC links charging energy to the distance traveled on the charging lane and the time spent on it. Two equivalent perspectives:

**Instantaneous rate view**

* Effective charging power while on ERS: `R_r = P_chg * η_chg` (kW).
* Time spent on ERS section: `t_on = L_DWC / v` (hours).
* Energy gained crossing the section: `E_gain = R_r * t_on`.

**Direct energy formula (paper form)**

**Equation (8)**
[
E_{DWC} = P_{chg} \cdot \eta_{chg} \cdot \frac{L_{DWC}}{v}
]

* `P_chg` — charging power capacity of the DWC infrastructure (kW).
* `η_chg` — charging efficiency.
* `L_DWC` — length of ERS section (km).
* `v` — speed on that section (km/h).
* `E_DWC` (kWh) is the energy added while traversing the charging section.

**Implementation notes**

* When a route edge (or subsegment) is an ERS-enabled segment, compute:

  ```
  t_on = L_DWC / v
  E_gain = P_chg * η_chg * t_on   # same as Eq (8)
  E_current := min(E_bat, E_current + E_gain)
  total_time += t_on   # only if the time spent is not already counted in travel_time
  ```
* Often `t_on` is already included in `travel_time` for that edge; do not double-count travel time. Only add `t_on` separately if your travel_time model excluded ERS dwell time.
* DWC can produce *net positive* energy (reduces net consumption) or simply reduce net drain on that segment.

---

## 4. Integration: Static Charging (Eq. 4.2–4.4) + PIC + DWC

### Core rules summary (use these exactly in simulator)

* **Static station charging** (use Eq. 4.3 & 4.4 style):

  * `Ere = E_before - E_edge_to_CS`
  * Choose `E_ex` (target after charge) per policy (full / minimal / hybrid)
  * `t_charging = (E_ex - Ere) / (P * ε)` or using PIC `t_charging = (E_ex - Ere) / R_r` (same if `R_r = P*ε`)
  * `E_current := E_ex`
* **PIC**: follow Eq (7) directly:

  * `E_after = E_before + R_r * t_charging` (clamped to `E_bat`)
* **DWC**: while traversing ERS section:

  * `E_gain = P_chg * η_chg * (L_DWC / v)` (Eq 8)
  * `E_current := min(E_bat, E_current + E_gain)`

### Conflicts / precedence

* If traversing DWC and also planning a static stop at a charging node located inside the ERS section, decide ordering:

  * Typical: add `E_gain` from DWC during traversal, then compute `Ere` at arrival and evaluate static charging decision (Eq. 4.2).
* Always clamp battery to `[0, E_bat]`.

## 6. Practical Points and Gotchas

* **Units:** be obsessive. Convert Wh ↔ kWh correctly.
* **Double counting time:** travel_time for an ERS edge usually already accounts for time spent on the ERS; only add extra charging time for static charging. DWC energy is obtained during travel, not as extra stop time.
* **Nonlinear charging / power limits:** PIC linear model assumes constant effective power. If you later include tapering curves, replace linear `R_r * t` with an integral over `P(t)`.
* **Look-ahead:** when using minimal-charge policies, compute `E_needed_ahead` until next CS or depot; if next CS is only reachable via ERS that will add energy, include expected `E_gain` from DWC when computing feasibility.

## 7. Quick Reference Equations

* PIC (Eq 7): (\lambda_{R} = \lambda_{i} + R_r \cdot t_{charging})
* DWC (Eq 8): (E_{DWC} = P_{chg} \cdot \eta_{chg} \cdot \dfrac{L_{DWC}}{v})
* Static charging time (Eq 4.4 style): (t_c = \dfrac{E_{ex} - E_{re}}{P \cdot \varepsilon})

8.  Now we have map with nodes and edges, goal which is make delivery to each customer from current node and return to depot, and ability to compute total_travel_time and total_energy for any customer furthermore.

9. Now write code
- consider input as we discussed above
- program will find best path to make deliveries to all the customers and to return to depot with least travel time.

Assumptions and constraints
- Queuing time at Charging Station is 0
- Vehicle payload decreases after each delivery; this reduction in mass is accounted for in the energy calculations.

Values to remember
- battery_threshold = 20%

Clarifications

- Unit of energy is kWh everywhere, only where we need to explain the user like State of charge of total battery, printed it in percentages.

- air_density and angle for each road are following.

    air_density = 1.205
    angle = 0.86


Key Metrics to Track (print in output)
- Total Travel Time: Time to reach destination
- Total Distance: Sum of distances traveled
- Total Energy Depletion: Sum of energy consumed on all edges
- Total Energy Charged at Stations: Sum of all stationary charging
- Total Energy Charged on E-Roads: Sum of all dynamic charging
- Route Sequence: Exact order of nodes visited
- Final Battery Level: Battery percentage when reaching destination
- Boxes Delivered: Confirmation that all boxes were dropped
- Charging Stops: Which stations were used and for how long
- Runtime of program

Also print the following trails for detailed route analysis:

```
SoC Trail: D(100.0%) -> 2(99.3%) -> 4(98.6%) -> L8(98.1%) -> ...
Energy Consumption Trail: D - 0.7 kWh > 2 - 0.6 kWh > 4 - 0.6 kWh > ...
Travel Time Trail: D - 9.80 min > 2 - 4.21 min > 4 - 3.95 min > ...
```

# Ant Colony Optimization (ACO) — Design Specifications

## Overview

Ant Colony Optimization (ACO) is a nature-inspired metaheuristic based on the foraging behavior of ants. Ants deposit pheromone on paths they traverse; shorter/better paths accumulate more pheromone over time, guiding future ants toward better solutions. ACO is well-suited for combinatorial optimization problems like vehicle routing.

**Core Idea:** A colony of artificial ants iteratively constructs solutions (customer visit orders). Each ant builds a tour by probabilistically choosing the next customer to visit based on **pheromone intensity** (learned attractiveness) and **heuristic information** (greedy desirability). After all ants complete their tours, pheromones are updated — good solutions reinforce their trails, while all trails partially evaporate, preventing premature convergence.

## ACO.1 Solution Representation

Each ant constructs a **permutation** of customer nodes (same representation as GA chromosomes).

```
Ant solution = ordered list of customer nodes only
Example: If customers are [L1, L2, L3], an ant might construct [L2, L3, L1]
```

The decoder builds the full route:
  D → (shortest feasible path to L2) → L2 → (shortest feasible path to L3) → L3 → ... → D

Charging station visits and intermediate nodes are NOT part of the ant's decision.
They are determined by the decoder/simulator during route evaluation.
This keeps the construction phase focused on the customer visit order.

## ACO.2 Pheromone Model

### Pheromone Matrix

Maintain a pheromone matrix `τ[i][j]` for all customer pairs (Li, Lj), where `τ[i][j]` represents the desirability of visiting customer Lj immediately after customer Li.

Additionally, maintain:
- `τ[D][j]` — pheromone for visiting customer Lj first (right after depot)
- `τ[i][D]` — pheromone for returning to depot after customer Li (implicitly, the last customer)

### Initialization

All pheromone values initialized uniformly:

```
τ[i][j] = τ_0    for all i, j
```

Where `τ_0` is the initial pheromone level. A common heuristic:

```
τ_0 = 1 / (n_customers * C_nn)
```

Where `C_nn` is the objective value of a nearest-neighbor heuristic solution. If this is not available, use:

```
τ_0 = 1.0
```

## ACO.3 Heuristic Information

The heuristic information `η[i][j]` represents the a priori desirability of visiting customer Lj after Li, without any learned experience. It is based on the shortest-path distance:

```
η[i][j] = 1 / d(Li, Lj)
```

Where `d(Li, Lj)` is the shortest-path distance from customer Li to customer Lj (computed via Dijkstra, same as GA/CW projects).

For the depot-to-customer transitions:
```
η[D][j] = 1 / d(D, Lj)
```

**Note:** If `d(Li, Lj) = 0` (same node — should not happen for distinct customers), set `η[i][j]` to a large value or handle as edge case.

## ACO.4 Solution Construction (Per Ant)

Each ant starts at the depot and constructs a tour by iteratively selecting the next unvisited customer:

```
def construct_solution(ant, pheromone, heuristic, alpha, beta):
    current = D  (depot)
    unvisited = set of all customers
    tour = []

    while unvisited is not empty:
        # Compute transition probabilities for each unvisited customer j
        for each j in unvisited:
            numerator[j] = τ[current][j]^α * η[current][j]^β

        total = sum of all numerators
        probability[j] = numerator[j] / total   for each j in unvisited

        # Select next customer using roulette wheel selection
        next_customer = roulette_wheel_select(probability)

        tour.append(next_customer)
        current = next_customer
        unvisited.remove(next_customer)

    return tour
```

### Transition Probability (Equation — ACO Core)

The probability that an ant at customer `i` moves to unvisited customer `j`:

```
         τ[i][j]^α  *  η[i][j]^β
p(i,j) = ─────────────────────────────
         Σ_k∈unvisited ( τ[i][k]^α * η[i][k]^β )
```

Where:
- `α` (alpha) — pheromone influence exponent. Controls how much pheromone matters. Higher α → more exploitation of learned paths.
- `β` (beta) — heuristic influence exponent. Controls how much the greedy distance heuristic matters. Higher β → greedier, distance-focused decisions.
- The denominator sums over all unvisited customers `k`.

## ACO.5 Pheromone Update

After all ants in a generation complete their tours and are evaluated by the decoder/simulator:

### Step 1: Evaporation

All pheromone values decay:

```
τ[i][j] = (1 - ρ) * τ[i][j]    for all i, j
```

Where `ρ` (rho) is the evaporation rate (0 < ρ < 1). Higher ρ → faster forgetting of old information.

### Step 2: Pheromone Deposit

Each ant deposits pheromone proportional to the quality of its solution:

```
for each ant k:
    Δτ_k = Q / cost_k

    for each consecutive pair (Li, Lj) in ant k's tour:
        τ[Li][Lj] += Δτ_k
```

Where:
- `cost_k` = objective value of ant k's solution (from the decoder/simulator, same cost function as GA: `sum_arrival_times - 0.01 * sum_battery_levels`)
- `Q` = pheromone deposit scaling constant
- `Δτ_k` = amount of pheromone ant k deposits on each edge in its tour. Better solutions (lower cost) deposit more pheromone.

### Step 3: Pheromone Bounds (Optional — Max-Min Ant System variant)

To prevent stagnation, clamp pheromone values:
```
τ[i][j] = max(τ_min, min(τ_max, τ[i][j]))
```

Where:
- `τ_min` — minimum pheromone level (prevents any trail from becoming zero)
- `τ_max` — maximum pheromone level (prevents domination by a single trail)

**Recommendation:** Use pheromone bounds (MMAS variant) for better convergence behavior.

Suggested bounds:
```
τ_max = 1 / (ρ * best_cost)       # updated when a new best solution is found
τ_min = τ_max / (2 * n_customers)  # ensures exploration
```

## ACO.6 Elitist Strategy (Optional but Recommended)

**Best-so-far reinforcement:** In addition to normal pheromone deposits, let the best-so-far solution deposit extra pheromone:

```
for each consecutive pair (Li, Lj) in best_so_far tour:
    τ[Li][Lj] += e * (Q / best_cost)
```

Where `e` is the elitist weight (number of "elite ants"). This accelerates convergence toward the best-known solution.

## ACO.7 Decoder / Simulator Logic

The route evaluation simulator is **identical** to the GA and C&W projects. Once an ant constructs a customer visit order, the decoder:

```
def decode(customer_order, graph, params):
    route = [Depot]
    E_current = initial_battery (kWh)
    total_time = 0
    load = num_customers * package_weight

    for each customer in customer_order:
        # Find shortest path from current_node to customer
        # For each edge on that path:
        #   1. Check charging decision (Eq 4.2) BEFORE traversing
        #   2. If charge needed and CS reachable, detour to nearest CS
        #   3. Traverse edge: update time, energy, handle electric roads
        #   4. If customer reached, deliver package (load -= package_weight)

    # Return to depot from last customer
    # Final: compute objective = sum_arrival_times - 0.01 * sum_battery_levels
```

This is exactly the same decoder that the GA and C&W projects use. All energy consumption equations, charging logic (Eq 4.2–4.4), DWC calculations (Eq 8), and feasibility checks remain unchanged.

## ACO.8 Infeasibility Handling

During the construction and evaluation phase:
- If battery < 0 at any point during simulation → INFEASIBLE solution
- If vehicle cannot reach next node or depot from current position → INFEASIBLE solution
- Penalty: `cost += PENALTY_INFEASIBLE` (large value, e.g., 99999)

Infeasible solutions still contribute (weakly) to pheromones, but their very high cost means they deposit negligible pheromone, effectively discouraging those paths.

## ACO.9 Penalty Constants

```
PENALTY_BATTERY_DEAD = 99999      # battery drops below 0 during route
PENALTY_UNREACHABLE = 99999       # cannot reach next node or depot
```

## ACO.10 Hyperparameters (Sensible Defaults)

```
num_ants: 20                      # number of ants per iteration (colony size)
max_iterations: 500               # maximum number of ACO iterations
alpha: 1.0                        # pheromone influence exponent
beta: 3.0                         # heuristic (distance) influence exponent
rho: 0.1                          # evaporation rate (0 < rho < 1)
Q: 100.0                          # pheromone deposit scaling constant
tau_0: 1.0                        # initial pheromone level (or computed from NN heuristic)
use_elitist: True                 # whether to apply elitist strategy
elitist_weight: 2                 # number of elite ants for best-so-far reinforcement
use_mmas: True                    # whether to use Max-Min Ant System pheromone bounds
random_seed: 42                   # for reproducibility
convergence_check: True           # stop early if no improvement for N iterations
convergence_patience: 50          # iterations without improvement before early stop
```

### Parameter Guidance

- **`alpha` vs `beta`**: α=1, β=3 means the heuristic (distance) has more influence than pheromone initially, encouraging exploration. As pheromone accumulates, learned paths gain importance.
- **`rho`**: 0.1 means 10% evaporation per iteration. Too high → forgets good paths too fast. Too low → converges prematurely.
- **`num_ants`**: Typically set to the number of customers or a fixed value like 20–50. More ants = better exploration per iteration but slower.
- **`Q`**: Scale relative to expected cost values. If typical cost is ~5–10, Q=100 gives deposit values of ~10–20 per edge, which is reasonable.

## ACO.11 Local Search (Post-Construction Improvement — Optional but Recommended)

After each ant constructs a solution (or after each iteration for the best solution), optionally apply local search to improve the customer visit order:

### 2-opt Improvement
```
for i in range(n_customers):
    for j in range(i+2, n_customers):
        new_order = customer_order[:i] + reversed(customer_order[i:j+1]) + customer_order[j+1:]
        if cost(new_order) < cost(current_order):
            current_order = new_order
            improved = True
```

### When to Apply Local Search
- **Option A — All ants:** Apply 2-opt to every ant's solution. Most thorough but expensive.
- **Option B — Best ant only:** Apply 2-opt only to the iteration-best ant. Good trade-off.
- **Option C — Periodic:** Apply 2-opt every N iterations. Balanced approach.

**Recommendation: Apply 2-opt to the iteration-best and global-best solutions at each iteration (Option B).**

### Local Search Parameters
```
local_search: "2opt"              # "2opt", "none"
max_ls_iterations: 500            # maximum 2-opt iterations
ls_improvement_threshold: 1e-6    # stop if improvement less than this
```

## ACO.12 Number of Independent Runs

```
independent_runs: 10
```
Each run uses a different random seed (seed = base_seed + run_index).
Report: best, worst, mean, std of objective across runs.
Also report best solution found across all runs.

## ACO.13 Logging & Outputs

### Per iteration (logged to CSV):
  - iteration_number
  - best_cost (iteration best)
  - worst_cost (iteration worst)
  - average_cost
  - global_best_cost (best seen so far)
  - best_customer_order (iteration best tour)

### Per run (final summary):
  - best_objective (same formula as GA: sum_arrival_times - 0.01 * sum_battery_levels)
  - best_route (full decoded route with all intermediate nodes)
  - total_travel_time (hours)
  - total_distance (km)
  - total_energy_consumed (kWh)
  - total_energy_charged_static (kWh)
  - total_energy_charged_dynamic (kWh)
  - final_battery_level (kWh and %)
  - packages_delivered (count)
  - charging_stops (list of: station_id, time_charged, energy_added)
  - route_sequence (ordered list of all nodes visited)

### Console output format:

```
============================================================
  ANT COLONY OPTIMIZATION — SOLUTION SUMMARY
============================================================
  Objective Value (legacy):         3.930482
  Total Travel Time:          2.2733 hours (136.40 min)
  Total Distance:             87.9400 km
  Total Energy Depletion:     15.6954 kWh
  Total Energy Charged (SC):  0.0000 kWh
  Total Energy Charged (DWC): 1.8326 kWh
  Final Battery Level:        86.1372 kWh (86.1%)
  Boxes Delivered:            10
  Charging Stops:             None

Route Sequence: D -> 2 -> 4 -> L8 -> ... -> D

SoC Trail: D(100.0%) -> 2(99.3%) -> 4(98.6%) -> ...

Energy Consumption Trail: D - 0.7 kWh > 2 - 0.6 kWh > ...

Travel Time Trail: D - 9.80 min > 2 - 4.21 min > ...

  Pheromone convergence:       iteration 312
  Total Runtime:               44.29 seconds
```

### Plots (generated automatically):
  - Convergence curve: global best cost vs. iteration (per run)
  - Box plot: objective distribution across all independent runs
  - Pheromone heatmap (optional): visualization of pheromone matrix at final iteration

## ACO.14 Comparison with GA and C&W

To facilitate comparison between ACO, GA, and C&W solutions on the same instance:
- All three use the **exact same** objective function: `sum_arrival_times - 0.01 * sum_battery_levels`
- All three use the **exact same** decoder/simulator (energy, charging, DWC calculations)
- All three use the **exact same** JSON input format
- All three produce the **exact same** output metrics
- ACO is stochastic (multiple runs, like GA)
- ACO typically converges faster than GA for smaller instances due to constructive heuristic guidance
- ACO's pheromone learning provides a different exploration-exploitation balance vs GA's crossover/mutation

# Test Instances

Use the same JSON instance files as the GA and C&W projects. The ACO algorithm should be tested on the same instances to allow direct comparison.

### Instance 1: Trivial (no charging needed)
```
Nodes: D, L1
Edges: D—L1 (distance=5km, traffic=1.0, type=normal)
Customers: 1
Expected: D → L1 → D, no charging needed
Purpose: Verify basic routing, energy calc, objective calc
```

### Instance 2: Simple with charging
```
Nodes: D, L1, L2, CS1, 1
Edges:
  D—1 (10km, traffic=1.0, normal)
  1—L1 (8km, traffic=0.8, normal)
  1—CS1 (5km, traffic=1.0, normal)
  CS1—L2 (7km, traffic=0.9, normal)
  L2—D (12km, traffic=1.0, normal)
Customers: 2
Purpose: Verify charging station detour logic, weight reduction after delivery
```

### Instance 3: With electric road
```
Nodes: D, L1, L2, CS1, Ns1, Ne1, 1, 2
Edges:
  D—1 (10km, traffic=1.0, normal)
  1—Ns1 (3km, traffic=1.0, normal)
  Ns1—Ne1 (8km, traffic=1.0, electric)
  Ne1—L1 (4km, traffic=0.9, normal)
  1—2 (6km, traffic=0.7, normal)
  2—CS1 (5km, traffic=1.0, normal)
  CS1—L2 (7km, traffic=0.85, normal)
  L2—D (9km, traffic=1.0, normal)
  Ne1—2 (3km, traffic=1.0, normal)
Customers: 2
Purpose: Verify DWC energy gain, electric road speed handling,
         compare route via electric road vs normal road
```

### Instance 4: Stress test (larger)
```
Nodes: D, L1-L5, CS1-CS2, Ns1, Ne1, Ns2, Ne2, 1-5
[Define 15-20 edges with varied traffic factors]
Customers: 5
Purpose: Verify ACO convergence, pheromone learning, solution quality vs GA/CW
```

# JSON Input Format

The exact same JSON format is used for input. Example:

```json
{
    "nodes": [
        {"id": "D",  "type": "depot"},
        {"id": "1",  "type": "intersection"},
        {"id": "L1", "type": "customer"},
        {"id": "L2", "type": "customer"},
        {"id": "CS1","type": "charging_station"},
        {"id": "Ns1","type": "electric_road_start", "segment": 1},
        {"id": "Ne1","type": "electric_road_end",   "segment": 1}
    ],
    "edges": [
        {"from": "D", "to": "1", "distance": 10, "traffic_factor": 1.0, "type": "normal"},
        {"from": "Ns1", "to": "Ne1", "distance": 8, "traffic_factor": 1.0, "type": "electric"}
    ],
    "base_speed": 50,
    "initial_battery_percent": 100,
    "starting_node": "D",
    "battery_capacity": 100,
    "vehicle_mass": 1800,
    "rolling_resistance": 0.01,
    "drag_coefficient": 0.6,
    "cross_sectional_area": 3.5,
    "mass_factor": 1.1,
    "package_weight": 5,
    "charging_power": 100,
    "charging_efficiency": 0.95,
    "dwc_power": 20,
    "dwc_efficiency": 0.85,
    "electric_road_speed": 50,
    "air_density": 1.205,
    "angle": 0.86
}
```

# Project Structure

```
ev-routing-aco/
├── main.py                  # Entry point: runs ACO, handles CLI args
├── config.py                # All constants, hyperparameters, defaults (same physics as GA/CW + ACO params)
├── graph.py                 # Graph representation, shortest path Dijkstra (same as GA/CW project)
├── energy.py                # Energy consumption & charging calculations (same as GA/CW project)
├── simulator.py             # Route decoder: customer_order → full route with metrics (same as GA/CW project)
├── aco.py                   # ACO engine: pheromone init, solution construction, pheromone update, iteration loop
├── local_search.py          # Post-optimization: 2-opt improvement (optional, applied to best solutions)
├── logger.py                # CSV logging per iteration, convergence tracking
├── plotter.py               # Convergence curves, box plots, pheromone heatmap
├── instances/               # Test instance definitions (same JSON files as GA/CW project)
│   ├── instance_1.json
│   ├── instance_2.json
│   ├── instance_3.json
│   └── instance_4.json
├── results/                 # Output directory for logs and plots
└── README.md
```

### Module Responsibilities

- **`config.py`** — Identical physics/vehicle constants to GA/CW project. ACO-specific parameters added: `alpha`, `beta`, `rho`, `Q`, `num_ants`, `tau_0`, `elitist_weight`, `use_mmas`, `tau_min`, `tau_max`.
- **`graph.py`** — Identical to GA/CW project. Graph loading from JSON, Dijkstra shortest path, node queries.
- **`energy.py`** — Identical to GA/CW project. Energy consumption formula (Eq 7), travel time, charging decision (Eq 4.2), static charging time (Eq 4.4), DWC energy gain (Eq 8).
- **`simulator.py`** — Identical to GA/CW project. Takes a customer visit order and decodes it into a full route with all metrics. Same RouteResult dataclass.
- **`aco.py`** — **NEW module.** Core ACO engine. Manages pheromone matrix, constructs solutions for each ant using transition probabilities, performs pheromone evaporation and deposit updates, optionally applies MMAS bounds and elitist strategy.
- **`local_search.py`** — **NEW module.** Implements 2-opt improvement heuristic applied to best ant solutions after construction.
- **`main.py`** — Entry point. Loads instance, runs ACO iterations + optional local search, prints summary in same format as GA/CW project.
- **`logger.py`** — Per-iteration CSV logging (iteration, best/worst/avg cost, global best). Final run summary.
- **`plotter.py`** — Convergence curve (global best vs iteration), box plot across runs, optional pheromone heatmap.
