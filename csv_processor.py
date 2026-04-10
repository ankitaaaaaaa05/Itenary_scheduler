"""
csv_processor.py — CSV upload handling with auto-column detection
"""
import pandas as pd
import json
import io
from typing import Tuple

# Column aliases
COL_ALIASES = {
    "name": ["name", "stop_name", "location", "place", "destination", "address"],
    "lat": ["lat", "latitude", "y", "lat_coord"],
    "lng": ["lng", "lon", "longitude", "x", "lng_coord", "long"],
    "priority": ["priority", "prio", "importance", "urgency"],
    "service_time_min": ["service_time", "service_time_min", "dwell", "dwell_time", "stop_time"],
    "package_weight": ["weight", "package_weight", "load", "kg", "mass"],
    "delivery_window": ["delivery_window", "window", "time_window", "slot", "schedule"],
}


def detect_column(df: pd.DataFrame, target: str) -> str | None:
    """Find the actual column name in df matching target aliases."""
    aliases = COL_ALIASES.get(target, [target])
    for alias in aliases:
        for col in df.columns:
            if col.strip().lower() == alias.lower():
                return col
    return None


def process_csv(file_bytes: bytes) -> Tuple[list[dict], list[str]]:
    """
    Parse uploaded CSV bytes into a list of stop dicts.
    Returns (stops, warnings).
    """
    warnings = []
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        return [], [f"Failed to read CSV: {e}"]

    # Drop fully empty rows
    df = df.dropna(how="all")

    # Drop duplicate rows
    original_len = len(df)
    df = df.drop_duplicates()
    if len(df) < original_len:
        warnings.append(f"Removed {original_len - len(df)} duplicate rows.")

    stops = []
    for idx, row in df.iterrows():
        stop = {"id": f"s{idx + 1}"}

        # Name
        name_col = detect_column(df, "name")
        stop["name"] = str(row[name_col]).strip() if name_col else f"Stop {idx+1}"

        # Lat
        lat_col = detect_column(df, "lat")
        try:
            stop["lat"] = float(row[lat_col]) if lat_col else 0.0
        except (ValueError, TypeError):
            stop["lat"] = 0.0
            warnings.append(f"Row {idx+1}: Invalid latitude, defaulting to 0.")

        # Lng
        lng_col = detect_column(df, "lng")
        try:
            stop["lng"] = float(row[lng_col]) if lng_col else 0.0
        except (ValueError, TypeError):
            stop["lng"] = 0.0
            warnings.append(f"Row {idx+1}: Invalid longitude, defaulting to 0.")

        # Priority
        prio_col = detect_column(df, "priority")
        try:
            stop["priority"] = int(row[prio_col]) if prio_col else 2
            stop["priority"] = max(1, min(5, stop["priority"]))
        except (ValueError, TypeError):
            stop["priority"] = 2

        # Service time
        svc_col = detect_column(df, "service_time_min")
        try:
            stop["service_time_min"] = float(row[svc_col]) if svc_col else 15
        except (ValueError, TypeError):
            stop["service_time_min"] = 15

        # Package weight
        wt_col = detect_column(df, "package_weight")
        try:
            stop["package_weight"] = float(row[wt_col]) if wt_col else 0
        except (ValueError, TypeError):
            stop["package_weight"] = 0

        # Delivery window
        dw_col = detect_column(df, "delivery_window")
        stop["delivery_window"] = str(row[dw_col]).strip() if dw_col and pd.notna(row[dw_col]) else ""

        stops.append(stop)

    if not stops:
        warnings.append("No valid stops found in CSV.")

    return stops, warnings


def stops_to_plan_data(stops: list[dict], start_location: dict, vehicle: dict, user_constraints: dict) -> dict:
    """Combine CSV stops with form-provided metadata into full plan_data."""
    return {
        "start_location": start_location,
        "vehicle": vehicle,
        "user_constraints": user_constraints,
        "stops": stops,
    }


def route_to_csv(route_result: dict) -> str:
    """Convert a route result to downloadable CSV string."""
    rows = []
    for i, seg in enumerate(route_result.get("route", [])):
        rows.append({
            "order": i + 1,
            "name": seg.get("name", ""),
            "lat": seg.get("lat", ""),
            "lng": seg.get("lng", ""),
            "arrival_time": seg.get("arrival_time", ""),
            "departure_time": seg.get("departure_time", ""),
            "wait_time_min": seg.get("wait_time_min", 0),
            "service_time_min": seg.get("service_time_min", 0),
            "travel_time_min": seg.get("travel_time_min", 0),
            "distance_km": seg.get("distance_km", 0),
            "traffic_label": seg.get("traffic_label", ""),
            "cost": seg.get("cost", 0),
            "priority": seg.get("priority", 1),
            "package_weight": seg.get("package_weight", 0),
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)