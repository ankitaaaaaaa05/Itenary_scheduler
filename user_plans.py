"""
user_plans.py — View and manage past itineraries
"""
import streamlit as st
import json
from database import get_user_itineraries, update_itinerary_status, log_action
from plan_renderer import render_plan_result


def render_plans_page():
    st.title("📊 My Plans")

    user = st.session_state.user
    user_id = user["id"]

    itineraries = get_user_itineraries(user_id)

    if not itineraries:
        st.info("No plans yet. Create one using Chat, Form, or CSV upload!")
        return

    status_emoji = {
        "generated": "🔵",
        "accepted": "🟢",
        "modified": "🟡",
        "rejected": "🔴",
    }

    for itin in itineraries:
        itin_id = itin["id"]
        status = itin["status"]
        source = itin.get("input_source", "form")
        timestamp = itin.get("timestamp", "")[:16]

        label = f"{status_emoji.get(status, '⚪')} Plan #{itin_id} | {source.upper()} | {status.title()} | {timestamp}"

        with st.expander(label):
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📂 Load & Modify", key=f"load_{itin_id}"):
                    # Load this plan into session for modification
                    plan_data = {}
                    try:
                        raw = json.loads(itin.get("generated_plan", "{}"))
                        plan_data = raw.get("plan", {})
                    except Exception:
                        pass

                    st.session_state.current_itin_id = itin_id
                    st.session_state.current_plan = plan_data

                    # Build minimal result for display
                    try:
                        full = json.loads(itin.get("generated_plan", "{}"))
                        from map_generator import map_to_html
                        map_html = ""
                        if full.get("route"):
                            map_html = map_to_html(full["route"])
                        st.session_state.result = {
                            "final_plan": {
                                "itinerary_id": itin_id,
                                "plan_data": full.get("plan", {}),
                                "route_result": full.get("route", {}),
                                "explanation": "Loaded from saved plans.",
                                "map_html": map_html,
                                "status": status,
                            }
                        }
                    except Exception:
                        st.session_state.result = None

                    log_action(user_id, "load_plan", f"itin_id={itin_id}")
                    st.success(f"Plan #{itin_id} loaded. Go to Form or Chat to modify.")
                    st.rerun()

            with col2:
                if status == "generated" or status == "modified":
                    if st.button("✅ Accept", key=f"acc_{itin_id}"):
                        update_itinerary_status(itin_id, "accepted")
                        log_action(user_id, "accept_plan", f"itin_id={itin_id}")
                        st.success("Accepted!")
                        st.rerun()

            with col3:
                if status not in ("rejected",):
                    if st.button("❌ Reject", key=f"rej_{itin_id}"):
                        update_itinerary_status(itin_id, "rejected")
                        log_action(user_id, "reject_plan", f"itin_id={itin_id}")
                        st.warning("Rejected.")
                        st.rerun()

            # Show raw route summary
            try:
                plan_json = json.loads(itin.get("generated_plan", "{}"))
                route_result = plan_json.get("route", {})
                summary = route_result.get("summary", {})
                if summary:
                    st.markdown(
                        f"**{summary.get('total_stops', 0)} stops** | "
                        f"**{summary.get('total_distance_km', 0)} km** | "
                        f"**{summary.get('total_time_min', 0):.0f} min** | "
                        f"**₹{summary.get('total_cost', 0):.0f}**"
                    )
            except Exception:
                pass