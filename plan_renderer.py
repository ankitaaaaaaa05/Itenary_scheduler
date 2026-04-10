"""
plan_renderer.py — Shared UI components for displaying plan results
"""
import streamlit as st
import json
from streamlit_folium import st_folium
import folium
from database import update_itinerary_status, log_action
from csv_processor import route_to_csv


def render_plan_result(result: dict, user_id: int):
    """Render the full plan result: explanation, route table, map, actions."""
    if not result:
        return

    final_plan = result.get("final_plan") or result
    route_result = final_plan.get("route_result", {})
    explanation = final_plan.get("explanation", "")
    itin_id = final_plan.get("itinerary_id")
    status = final_plan.get("status", "generated")
    error = result.get("error")

    if error:
        st.error(f"⚠️ Error: {error}")

    # Status badge
    status_colors = {
        "generated": "🔵",
        "accepted": "🟢",
        "modified": "🟡",
        "rejected": "🔴",
    }
    st.markdown(f"**Plan Status:** {status_colors.get(status, '⚪')} {status.title()}")
    if itin_id:
        st.caption(f"Itinerary ID: #{itin_id}")

    # Explanation
    if explanation:
        with st.expander("💡 AI Explanation", expanded=True):
            st.markdown(explanation)

    # Summary metrics
    summary = route_result.get("summary", {})
    if summary:
        st.markdown("### 📊 Route Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📏 Distance", f"{summary.get('total_distance_km', 0)} km")
        c2.metric("⏱️ Total Time", f"{summary.get('total_time_min', 0):.0f} min")
        c3.metric("💰 Total Cost", f"₹{summary.get('total_cost', 0):.0f}")
        c4.metric("📍 Stops", summary.get("total_stops", 0))

    # Alerts
    alerts = route_result.get("alerts", [])
    if alerts:
        st.warning("⚠️ **Route Alerts:**")
        for alert in alerts:
            st.warning(f"• {alert}")

    # Route table
    route = route_result.get("route", [])
    if route:
        st.markdown("### 🗺️ Optimized Route")
        rows = []
        for i, seg in enumerate(route):
            traffic_emoji = {"low": "🟢", "light": "🟡", "medium": "🟠", "heavy": "🔴"}.get(
                seg.get("traffic_label", "low"), "⚪"
            )
            rows.append({
                "Order": i + 1,
                "Stop": seg.get("name", ""),
                "Arrival": seg.get("arrival_time", ""),
                "Departure": seg.get("departure_time", ""),
                "Wait (min)": seg.get("wait_time_min", 0),
                "Dist (km)": seg.get("distance_km", 0),
                "Traffic": f"{traffic_emoji} {seg.get('traffic_label', '')}",
                "Cost (₹)": seg.get("cost", 0),
                "Priority": "⭐" * int(seg.get("priority", 1)),
            })
        st.dataframe(rows, use_container_width=True)

    # Map
    map_html = final_plan.get("map_html", "")
    if map_html:
        st.markdown("### 🗺️ Live Map with Traffic")
        st.components.v1.html(map_html, height=500, scrolling=True)

    # Download CSV
    if route:
        csv_data = route_to_csv(route_result)
        st.download_button(
            "⬇️ Download Route CSV",
            data=csv_data,
            file_name=f"route_plan_{itin_id or 'new'}.csv",
            mime="text/csv",
        )

    # Accept / Reject buttons
    if itin_id and status in ("generated", "modified"):
        st.markdown("### ✅ Plan Decision")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Accept Plan", key=f"accept_{itin_id}", use_container_width=True):
                update_itinerary_status(itin_id, "accepted")
                log_action(user_id, "accept_plan", f"itin_id={itin_id}")
                st.success("Plan accepted! ✅")
                st.session_state.current_plan = None  # Reset so next is new
                st.rerun()
        with col2:
            if st.button("❌ Reject Plan", key=f"reject_{itin_id}", use_container_width=True):
                update_itinerary_status(itin_id, "rejected")
                log_action(user_id, "reject_plan", f"itin_id={itin_id}")
                st.warning("Plan rejected.")
                st.session_state.current_itin_id = None
                st.session_state.current_plan = None
                st.session_state.result = None
                st.rerun()