"""
map_generator.py — Folium map with traffic simulation, markers, and route
"""
import folium
import json
from routing import get_traffic_factor


TRAFFIC_COLORS = {
    "low": "#22c55e",      # green
    "light": "#eab308",    # yellow
    "medium": "#f97316",   # orange
    "heavy": "#ef4444",    # red
}


def generate_map(route_result: dict) -> folium.Map:
    """
    Generate a Folium map from a route result dict.
    Returns a folium.Map object.
    """
    start = route_result.get("start", {})
    route = route_result.get("route", [])
    summary = route_result.get("summary", {})
    alerts = route_result.get("alerts", [])

    # Center map on start
    start_lat = float(start.get("lat", 20.5937))
    start_lng = float(start.get("lng", 78.9629))

    m = folium.Map(
        location=[start_lat, start_lng],
        zoom_start=12,
        tiles="OpenStreetMap",
    )

    # Start marker
    folium.Marker(
        location=[start_lat, start_lng],
        popup=folium.Popup(
            f"""<b>🏁 START</b><br>{start.get('name', 'Start')}<br>
            Departure: {summary.get('start_time', '')}<br>
            <small>Lat: {start_lat:.4f}, Lng: {start_lng:.4f}</small>""",
            max_width=250
        ),
        tooltip="Start Location",
        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
    ).add_to(m)

    # Route path + stop markers
    route_coords = [[start_lat, start_lng]]

    for i, seg in enumerate(route):
        lat = float(seg.get("lat") or 0)
        lng = float(seg.get("lng") or 0)
        if lat == 0 and lng == 0:
            continue

        route_coords.append([lat, lng])
        color = TRAFFIC_COLORS.get(seg.get("traffic_label", "low"), "green")

        # Priority icon
        priority = int(seg.get("priority", 1))
        icon_color = "red" if priority >= 4 else "orange" if priority == 3 else "green"
        icon_name = "star" if priority >= 4 else "map-marker"

        alert_html = ""
        if seg.get("alert"):
            alert_html = f'<br>⚠️ <span style="color:red">{seg["alert"]}</span>'

        popup_html = f"""
        <div style="min-width:200px">
            <b>📍 Stop {i+1}: {seg.get('name', '')}</b><br>
            <b>Arrival:</b> {seg.get('arrival_time', '')}<br>
            <b>Departure:</b> {seg.get('departure_time', '')}<br>
            <b>Wait:</b> {seg.get('wait_time_min', 0)} min<br>
            <b>Service:</b> {seg.get('service_time_min', 0)} min<br>
            <b>Priority:</b> {'⭐' * priority}<br>
            <b>Package:</b> {seg.get('package_weight', 0)} kg<br>
            <b>Distance:</b> {seg.get('distance_km', 0)} km<br>
            <b>Travel time:</b> {seg.get('travel_time_min', 0):.1f} min<br>
            <b>Traffic:</b> <span style="color:{color}">● {seg.get('traffic_label', '')}</span>
            ({seg.get('traffic_factor', 1.0):.1f}x)<br>
            <b>Cost:</b> ₹{seg.get('cost', 0):.0f}<br>
            <b>Window:</b> {seg.get('delivery_window', 'Any')}{alert_html}
        </div>
        """

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"Stop {i+1}: {seg.get('name', '')}",
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
        ).add_to(m)

        # Draw segment line with traffic color
        if len(route_coords) >= 2:
            folium.PolyLine(
                locations=route_coords[-2:],
                color=color,
                weight=4,
                opacity=0.8,
                tooltip=f"{seg.get('traffic_label', '')} traffic ({seg.get('traffic_factor', 1.0):.1f}x)",
            ).add_to(m)

    # Summary box
    alerts_html = ""
    if alerts:
        alerts_html = "<br><b>⚠️ Alerts:</b><ul>" + "".join(f"<li>{a}</li>" for a in alerts) + "</ul>"

    summary_html = f"""
    <div style="font-size:13px; min-width:240px">
        <b>📊 Route Summary</b><br>
        Total Distance: <b>{summary.get('total_distance_km', 0)} km</b><br>
        Total Time: <b>{summary.get('total_time_min', 0):.0f} min</b><br>
        Total Cost: <b>₹{summary.get('total_cost', 0):.0f}</b><br>
        Stops: <b>{summary.get('total_stops', 0)}</b><br>
        Start: {summary.get('start_time', '')} → End: {summary.get('end_time', '')}
        {alerts_html}
    </div>
    """

    # Add summary as a floating div via HTML
    legend_html = f"""
    <div style="position: fixed; bottom: 30px; left: 30px; z-index:9999;
         background:white; border:2px solid #ccc; border-radius:8px;
         padding:12px; font-size:13px; max-width:280px; box-shadow:3px 3px 8px rgba(0,0,0,.2)">
        {summary_html}
        <br><b>Traffic Legend:</b><br>
        <span style="color:#22c55e">●</span> Low (1.0x) &nbsp;
        <span style="color:#eab308">●</span> Light (1.1x)<br>
        <span style="color:#f97316">●</span> Medium (1.2x) &nbsp;
        <span style="color:#ef4444">●</span> Heavy (1.5-1.6x)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Fit bounds
    if len(route_coords) > 1:
        m.fit_bounds(route_coords)

    return m


def map_to_html(route_result: dict) -> str:
    """Generate map and return as HTML string."""
    m = generate_map(route_result)
    return m._repr_html_()