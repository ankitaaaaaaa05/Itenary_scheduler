"""
routing.py — VRP + Time Windows + Traffic-Aware routing logic
"""
import json
import math
from datetime import datetime, timedelta
from geopy.distance import geodesic


# ---------- Traffic factors ----------

TRAFFIC_PROFILES = [
    {"start": 9, "end": 11, "factor": 1.5, "label": "heavy", "color": "red"},
    {"start": 17, "end": 19, "factor": 1.6, "label": "heavy", "color": "red"},
    {"start": 11, "end": 17, "factor": 1.2, "label": "medium", "color": "orange"},
    {"start": 6,  "end": 9,  "factor": 1.1, "label": "light", "color": "yellow"},
    {"start": 19, "end": 22, "factor": 1.1, "label": "light", "color": "yellow"},
]


def get_traffic_factor(hour: float) -> tuple[float, str, str]:
    for p in TRAFFIC_PROFILES:
        if p["start"] <= hour < p["end"]:
            return p["factor"], p["label"], p["color"]
    return 1.0, "low", "green"


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    try:
        return geodesic((lat1, lng1), (lat2, lng2)).km
    except Exception:
        # Fallback manual calculation
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        return R * 2 * math.asin(math.sqrt(a))


def time_str_to_minutes(t: str) -> int:
    """Convert 'HH:MM' to minutes from midnight."""
    if not t:
        return 0
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def minutes_to_time_str(m: int) -> str:
    h = int(m) // 60
    mi = int(m) % 60
    return f"{h:02d}:{mi:02d}"


def nearest_neighbor_route(stops: list[dict], start: dict) -> list[dict]:
    """Simple nearest-neighbor heuristic for VRP."""
    remaining = stops.copy()
    route = []
    current = start

    while remaining:
        nearest = min(
            remaining,
            key=lambda s: haversine_km(
                current.get("lat", 0), current.get("lng", 0),
                s.get("lat", 0), s.get("lng", 0)
            )
        )
        route.append(nearest)
        current = nearest
        remaining.remove(nearest)

    return route


def priority_sort(stops: list[dict]) -> list[dict]:
    """Sort stops by priority (higher = earlier)."""
    return sorted(stops, key=lambda s: -int(s.get("priority", 1)))


def compute_route(plan_data: dict) -> dict:
    """
    Main routing function.
    Returns a route result with timings, distances, costs, alerts.
    """
    start = plan_data.get("start_location", {})
    stops = plan_data.get("stops", [])
    vehicle = plan_data.get("vehicle", {})
    constraints = plan_data.get("user_constraints", {})

    if not stops:
        return {"error": "No stops provided"}

    optimize_for = constraints.get("optimize_for", "time")
    avoid_traffic = constraints.get("avoid_high_traffic", False)
    cost_per_km = float(vehicle.get("cost_per_km", 10))
    capacity = float(vehicle.get("capacity", 1000))

    # Sort + route
    if optimize_for == "cost":
        ordered_stops = nearest_neighbor_route(stops, start)
    else:
        # Priority + nearest neighbor hybrid
        high_priority = [s for s in stops if int(s.get("priority", 1)) >= 3]
        low_priority = [s for s in stops if int(s.get("priority", 1)) < 3]
        ordered_stops = priority_sort(high_priority) + nearest_neighbor_route(low_priority, start if not high_priority else high_priority[-1])

    # Start time
    start_time_str = vehicle.get("start_time", "08:00")
    current_time_min = time_str_to_minutes(start_time_str)
    end_time_min = time_str_to_minutes(vehicle.get("end_time", "20:00"))
    budget = float(constraints.get("budget", 99999))
    deadline_str = constraints.get("deadline", "")

    route_segments = []
    total_distance = 0.0
    total_cost = 0.0
    total_time = 0.0
    alerts = []
    current_load = 0.0

    prev_loc = start

    for stop in ordered_stops:
        dist_km = haversine_km(
            prev_loc.get("lat", 0), prev_loc.get("lng", 0),
            stop.get("lat", 0), stop.get("lng", 0)
        )
        hour = current_time_min / 60
        traffic_factor, traffic_label, traffic_color = get_traffic_factor(hour)

        if avoid_traffic and traffic_factor > 1.3:
            # Wait until traffic clears
            for h_offset in range(1, 5):
                new_hour = hour + h_offset
                new_factor, new_label, _ = get_traffic_factor(new_hour)
                if new_factor <= 1.3:
                    wait_min = h_offset * 60
                    current_time_min += wait_min
                    hour = new_hour
                    traffic_factor, traffic_label, traffic_color = get_traffic_factor(hour)
                    break

        # Speed assumption: 40 km/h base urban speed
        base_speed_kmh = 40
        travel_time_min = (dist_km / base_speed_kmh) * 60 * traffic_factor
        travel_cost = dist_km * cost_per_km

        arrival_time_min = current_time_min + travel_time_min
        arrival_str = minutes_to_time_str(arrival_time_min)

        # Check delivery window
        dw = stop.get("delivery_window", "")
        window_alert = None
        wait_time = 0
        if dw and "-" in str(dw):
            parts = str(dw).split("-")
            win_start = time_str_to_minutes(parts[0].strip())
            win_end = time_str_to_minutes(parts[1].strip())
            if arrival_time_min < win_start:
                wait_time = win_start - arrival_time_min
                arrival_time_min = win_start
                arrival_str = minutes_to_time_str(arrival_time_min)
            elif arrival_time_min > win_end:
                window_alert = f"Missed delivery window at {stop.get('name', 'stop')} (arrived {arrival_str}, window ended {minutes_to_time_str(win_end)})"
                alerts.append(window_alert)

        service_time = float(stop.get("service_time_min", 15))
        departure_time_min = arrival_time_min + service_time
        departure_str = minutes_to_time_str(departure_time_min)

        # Capacity check
        pkg_weight = float(stop.get("package_weight", 0))
        current_load += pkg_weight
        if current_load > capacity:
            alerts.append(f"Capacity overflow at {stop.get('name', 'stop')} (load: {current_load:.1f} kg, capacity: {capacity} kg)")

        # Budget check
        total_cost += travel_cost
        if total_cost > budget:
            alerts.append(f"Budget exceeded after {stop.get('name', 'stop')} (cost: ₹{total_cost:.0f}, budget: ₹{budget:.0f})")

        route_segments.append({
            "stop_id": stop.get("id", ""),
            "name": stop.get("name", "Unknown"),
            "lat": stop.get("lat"),
            "lng": stop.get("lng"),
            "arrival_time": arrival_str,
            "departure_time": departure_str,
            "wait_time_min": round(wait_time, 1),
            "service_time_min": service_time,
            "travel_time_min": round(travel_time_min, 1),
            "distance_km": round(dist_km, 2),
            "traffic_factor": traffic_factor,
            "traffic_label": traffic_label,
            "traffic_color": traffic_color,
            "cost": round(travel_cost, 2),
            "priority": stop.get("priority", 1),
            "package_weight": pkg_weight,
            "delivery_window": dw,
            "alert": window_alert,
        })

        total_distance += dist_km
        total_time += travel_time_min + service_time + wait_time
        current_time_min = departure_time_min
        prev_loc = stop

    # End time check
    if current_time_min > end_time_min:
        alerts.append(f"Route exceeds vehicle end time (ends at {minutes_to_time_str(current_time_min)}, limit {vehicle.get('end_time', '20:00')})")

    return {
        "start": start,
        "route": route_segments,
        "summary": {
            "total_distance_km": round(total_distance, 2),
            "total_time_min": round(total_time, 1),
            "total_cost": round(total_cost, 2),
            "total_stops": len(route_segments),
            "start_time": start_time_str,
            "end_time": minutes_to_time_str(current_time_min),
            "optimize_for": optimize_for,
        },
        "alerts": alerts,
    }