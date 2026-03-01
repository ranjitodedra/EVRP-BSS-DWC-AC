"""
energy.py — Energy consumption, travel-time, and charging calculations.

Equations from the spec:
  - Section 7:  energy_consumption formula
  - Eq 4.2:    charging decision
  - Eq 4.4:    static charging time
  - Eq 8:      DWC energy gain
"""

import math
from config import (
    GRAVITY, AIR_DENSITY, ROAD_ANGLE_RAD,
    ROLLING_RESISTANCE, DRAG_COEFFICIENT, CROSS_SECTIONAL_AREA,
    MASS_FACTOR, BATTERY_CAPACITY, BATTERY_THRESHOLD,
    CHARGING_POWER, CHARGING_EFFICIENCY,
    DWC_POWER, DWC_EFFICIENCY, ELECTRIC_ROAD_SPEED,
)


# ──────────────────────────────────────────────
# Travel Time
# ──────────────────────────────────────────────

def compute_actual_speed(base_speed: float, traffic_factor: float) -> float:
    """Actual speed on an edge (km/h)."""
    return base_speed * traffic_factor


def compute_travel_time(distance_km: float, actual_speed_kmh: float) -> float:
    """
    Travel time in hours for a single edge.
    distance_km : edge distance (km)
    actual_speed_kmh : v0 = base_speed * traffic_factor (km/h)
    """
    if actual_speed_kmh <= 0:
        return float("inf")
    return distance_km / actual_speed_kmh


# ──────────────────────────────────────────────
# Energy Consumption (Section 7)
# ──────────────────────────────────────────────

def _get_dv_dt(speed_kmh: float) -> float:
    """Acceleration term (dv/dt) based on speed range (km/h)."""
    if 50 <= speed_kmh <= 80:
        return 0.3
    elif 81 <= speed_kmh <= 120:
        return 2.0
    else:
        return 0.0


def compute_energy_consumption(
    distance_km: float,
    speed_kmh: float,
    total_mass_kg: float,
    params: dict,
) -> float:
    """
    Energy consumed traversing one edge (kWh).

    Formula (per spec Section 7):
      E = (1/3600) * [ M*g*(f*cos(α)+sin(α)) + 0.0386*(ρ*Cx*A*v²)
                        + (M+m)*(dv/dt) ] * d

    d is in km → converted to metres inside.
    v is in km/h → converted to m/s for the v² term.
    """
    g = params.get("gravity", GRAVITY)
    f = params.get("rolling_resistance", ROLLING_RESISTANCE)
    rho = params.get("air_density", AIR_DENSITY)
    Cx = params.get("drag_coefficient", DRAG_COEFFICIENT)
    A = params.get("cross_sectional_area", CROSS_SECTIONAL_AREA)
    m = params.get("mass_factor", MASS_FACTOR)
    alpha = params.get("road_angle_rad", ROAD_ANGLE_RAD)

    M = total_mass_kg
    v_ms = speed_kmh / 3.6          # convert km/h → m/s
    d_m = distance_km * 1000        # convert km → m
    dv_dt = _get_dv_dt(speed_kmh)

    term1 = M * g * (f * math.cos(alpha) + math.sin(alpha))
    term2 = 0.0386 * (rho * Cx * A * v_ms ** 2)
    term3 = (M + m) * dv_dt

    energy_joules_per_m = term1 + term2 + term3
    energy_kwh = (1 / 3600) * energy_joules_per_m * d_m  # Wh → kWh (the 1/3600 accounts for J→kWh with d in m)

    # The formula gives result in kWh when d is in m and the
    # outer factor is 1/3600 (since 1 kWh = 3.6e6 J, and we have
    # force*distance = energy in Joules, divided by 3600 → Wh,
    # but we want kWh so divide by 1000 additionally).
    energy_kwh = energy_kwh / 1000.0

    return max(energy_kwh, 0.0)


# ──────────────────────────────────────────────
# DWC Energy Gain (Equation 8)
# ──────────────────────────────────────────────

def compute_dwc_energy_gain(
    distance_km: float,
    speed_kmh: float,
    params: dict,
) -> float:
    """
    Energy gained from Dynamic Wireless Charging (kWh).
    E_DWC = P_chg * η_chg * (L_DWC / v)
    where L_DWC in km, v in km/h → result in kWh (power * hours).
    """
    p_chg = params.get("dwc_power", DWC_POWER)
    eta = params.get("dwc_efficiency", DWC_EFFICIENCY)
    v = speed_kmh if speed_kmh > 0 else 1.0
    t_on = distance_km / v  # hours
    return p_chg * eta * t_on


# ──────────────────────────────────────────────
# Static Charging (Eq 4.2, 4.3, 4.4)
# ──────────────────────────────────────────────

def check_charging_needed(
    current_energy_kwh: float,
    energy_for_next_edge_kwh: float,
    params: dict,
) -> bool:
    """
    Eq 4.2 — Charge if:
      E_i(t) ≤ γ * E_bat   OR   E_i(t) ≤ E_edge(i→j)
    """
    e_bat = params.get("battery_capacity", BATTERY_CAPACITY)
    gamma = params.get("battery_threshold", BATTERY_THRESHOLD)

    if current_energy_kwh <= gamma * e_bat:
        return True
    if current_energy_kwh <= energy_for_next_edge_kwh:
        return True
    return False


def compute_charging_time(
    energy_before: float,
    energy_target: float,
    params: dict,
) -> float:
    """
    Eq 4.4 — t_c = (E_ex - E_re) / (P * ε)
    Returns charging time in hours.
    """
    P = params.get("charging_power", CHARGING_POWER)
    eps = params.get("charging_efficiency", CHARGING_EFFICIENCY)
    delta = energy_target - energy_before
    if delta <= 0:
        return 0.0
    return delta / (P * eps)


def compute_charge_target_option_b(
    energy_remaining: float,
    energy_needed_ahead: float,
    params: dict,
) -> float:
    """
    Option B — Minimum Required Charge.
    E_ex = min(E_bat, E_needed_ahead + γ * E_bat)
    """
    e_bat = params.get("battery_capacity", BATTERY_CAPACITY)
    gamma = params.get("battery_threshold", BATTERY_THRESHOLD)
    target = energy_needed_ahead + gamma * e_bat
    return min(e_bat, target)


def compute_charge_target_option_a(params: dict) -> float:
    """Option A — Full Charge. E_ex = E_bat."""
    return params.get("battery_capacity", BATTERY_CAPACITY)
