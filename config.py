"""
config.py — All constants, hyperparameters, and defaults for the
ACO-based Electric Vehicle Routing Problem (EVRP-BSS-DWC).
"""

import math

# ──────────────────────────────────────────────
# Physics / Environment Constants
# ──────────────────────────────────────────────
GRAVITY = 9.81                  # m/s²
AIR_DENSITY = 1.205             # kg/m³
ROAD_ANGLE_DEG = 0.86           # degrees
ROAD_ANGLE_RAD = math.radians(ROAD_ANGLE_DEG)

# ──────────────────────────────────────────────
# Vehicle Parameters (defaults)
# ──────────────────────────────────────────────
VEHICLE_MASS = 1800             # kg (without payload)
ROLLING_RESISTANCE = 0.01       # unitless
DRAG_COEFFICIENT = 0.6          # unitless (Cx)
CROSS_SECTIONAL_AREA = 3.5      # m²
MASS_FACTOR = 1.1               # kg (rolling inertia)
BASE_SPEED = 50                 # km/h
PACKAGE_WEIGHT = 5              # kg per package

# ──────────────────────────────────────────────
# Battery & Charging
# ──────────────────────────────────────────────
BATTERY_CAPACITY = 100          # kWh
BATTERY_THRESHOLD = 0.20        # 20% mileage-anxiety coefficient (γ)
INITIAL_BATTERY_PERCENT = 100   # start fully charged

# Static Charging Station
CHARGING_POWER = 100            # kW (P)
CHARGING_EFFICIENCY = 0.95      # ε

# Dynamic Wireless Charging (DWC)
DWC_POWER = 20                  # kW
DWC_EFFICIENCY = 0.85           # η_chg
ELECTRIC_ROAD_SPEED = 50        # km/h (constant for all electric roads)

# ──────────────────────────────────────────────
# ACO Hyperparameters
# ──────────────────────────────────────────────
NUM_ANTS = 20                   # colony size per iteration
MAX_ITERATIONS = 500            # maximum ACO iterations
ALPHA = 1.0                     # pheromone influence exponent
BETA = 3.0                      # heuristic influence exponent
RHO = 0.1                       # evaporation rate
Q = 100.0                       # pheromone deposit scaling constant
TAU_0 = 1.0                     # initial pheromone level

# Elitist strategy
USE_ELITIST = True
ELITIST_WEIGHT = 2              # number of elite ants

# Max-Min Ant System (MMAS)
USE_MMAS = True

# ──────────────────────────────────────────────
# Independent Runs
# ──────────────────────────────────────────────
INDEPENDENT_RUNS = 10
RANDOM_SEED = 42

# ──────────────────────────────────────────────
# Parallelism
# ──────────────────────────────────────────────
PARALLEL_WORKERS = 0            # 0 = use all available cores (cpu_count())

# ──────────────────────────────────────────────
# Convergence / Early Stopping
# ──────────────────────────────────────────────
CONVERGENCE_CHECK = True
CONVERGENCE_PATIENCE = 50       # iterations w/o improvement → stop

# ──────────────────────────────────────────────
# Local Search (2-opt)
# ──────────────────────────────────────────────
LOCAL_SEARCH = "2opt"           # "2opt" or "none"
MAX_LS_ITERATIONS = 500
LS_IMPROVEMENT_THRESHOLD = 1e-6

# ──────────────────────────────────────────────
# Penalties
# ──────────────────────────────────────────────
PENALTY_BATTERY_DEAD = 99999
PENALTY_UNREACHABLE = 99999
