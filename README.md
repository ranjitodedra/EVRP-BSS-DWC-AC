# ACO-Based Electric Vehicle Routing (EVRP-BSS-DWC)

Ant Colony Optimization solver for the Single Electric Vehicle Routing Problem with Battery Swap Stations (static charging) and Dynamic Wireless Charging (electric roads).

python main.py --instance instances/instance_1.json --runs 10 --seed 42 --workers 8


## Quick Start

```bash
python main.py --instance instances/instance_1.json --runs 1 --seed 42
```

## Full Run (10 independent runs)

```bash
python main.py --instance instances/instance_4.json --runs 10 --seed 42
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--instance` | *required* | Path to JSON instance file |
| `--runs` | 10 | Number of independent runs |
| `--seed` | 42 | Base random seed |
| `--ants` | 20 | Number of ants per iteration |
| `--iterations` | 500 | Maximum iterations |
| `--no-plot` | false | Skip plot generation |

## Project Structure

```
├── main.py          # Entry point & CLI
├── config.py        # Constants & ACO hyperparameters
├── graph.py         # Graph representation & Dijkstra
├── energy.py        # Energy consumption & charging formulas
├── simulator.py     # Route decoder (customer order → full route)
├── aco.py           # ACO engine (pheromone, construction, update)
├── local_search.py  # 2-opt improvement heuristic
├── logger.py        # CSV logging
├── plotter.py       # Convergence curves, box plots, heatmaps
├── instances/       # JSON test instances
│   ├── instance_1.json  (1 customer, trivial)
│   ├── instance_2.json  (2 customers, charging station)
│   ├── instance_3.json  (2 customers, electric road)
│   └── instance_4.json  (5 customers, stress test)
└── results/         # Output logs & plots
```

## Dependencies

- Python 3.8+
- `matplotlib` (for plots — optional, program runs without it)

## Algorithm

The ACO solver uses Max-Min Ant System (MMAS) with elitist strategy and 2-opt local search. Key parameters (configurable in `config.py`):

- **Colony size:** 20 ants per iteration
- **α = 1.0** (pheromone influence), **β = 3.0** (heuristic influence)
- **ρ = 0.1** (evaporation rate)
- **Early stopping:** 50 iterations without improvement
- **Objective:** `sum_arrival_times - 0.01 * sum_battery_levels`

## Output

Console output includes: objective value, travel time, distance, energy metrics, SoC/energy/time trails, charging stops, and runtime. CSV logs and convergence/box plots are saved to `results/`.
