# """
# user_form.py — Form-based planner interface
# """
# import streamlit as st
# from agents import run_planner
# from plan_renderer import render_plan_result


# def render_form_page():
#     st.title("📋 Form Planner")
#     st.caption("Enter detailed route information using the structured form below.")

#     user = st.session_state.user
#     user_id = user["id"]

#     # Check if modifying existing plan
#     is_modifying = (
#         st.session_state.current_itin_id is not None
#         and st.session_state.current_plan is not None
#         and st.session_state.result is not None
#     )

#     if is_modifying:
#         st.info(f"✏️ Modifying existing plan #{st.session_state.current_itin_id}. Submit to update.")
#         if st.button("🆕 Create New Plan Instead"):
#             st.session_state.current_itin_id = None
#             st.session_state.current_plan = None
#             st.session_state.result = None
#             st.rerun()

#     with st.form("planner_form"):
#         st.markdown("### 📌 Route Constraints")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             date = st.date_input("Date")
#         with col2:
#             budget = st.number_input("Budget (₹)", min_value=0, value=5000, step=100)
#         with col3:
#             deadline = st.text_input("Deadline (HH:MM)", value="20:00")

#         col4, col5, col6 = st.columns(3)
#         with col4:
#             avoid_traffic = st.checkbox("Avoid High Traffic")
#         with col5:
#             avoid_tolls = st.checkbox("Avoid Tolls")
#         with col6:
#             optimize_for = st.selectbox("Optimize For", ["time", "cost"])

#         st.markdown("### 🏁 Start Location")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             start_name = st.text_input("Location Name", value="Mumbai Central")
#         with col2:
#             start_lat = st.number_input("Latitude", value=18.9696, format="%.4f")
#         with col3:
#             start_lng = st.number_input("Longitude", value=72.8194, format="%.4f")

#         st.markdown("### 🚛 Vehicle")
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             start_time = st.text_input("Start Time", value="08:00")
#         with col2:
#             end_time = st.text_input("End Time", value="20:00")
#         with col3:
#             cost_per_km = st.number_input("Cost/km (₹)", value=10.0)
#         with col4:
#             capacity = st.number_input("Capacity (kg)", value=1000.0)

#         st.markdown("### 📍 Stops")
#         st.caption("Add delivery stops below. Use the + button to add more.")

#         num_stops = st.number_input("Number of Stops", min_value=1, max_value=20, value=3, step=1)

#         stops = []
#         for i in range(int(num_stops)):
#             with st.expander(f"Stop {i+1}", expanded=(i == 0)):
#                 c1, c2, c3 = st.columns(3)
#                 with c1:
#                     sname = st.text_input("Name", key=f"sname_{i}", value=f"Stop {i+1}")
#                 with c2:
#                     slat = st.number_input("Latitude", key=f"slat_{i}", value=18.9 + i * 0.05, format="%.4f")
#                 with c3:
#                     slng = st.number_input("Longitude", key=f"slng_{i}", value=72.8 + i * 0.04, format="%.4f")

#                 c4, c5, c6, c7 = st.columns(4)
#                 with c4:
#                     sprio = st.selectbox("Priority", [1, 2, 3, 4, 5], index=1, key=f"sprio_{i}")
#                 with c5:
#                     ssvc = st.number_input("Service Time (min)", min_value=1, value=15, key=f"ssvc_{i}")
#                 with c6:
#                     swt = st.number_input("Package Weight (kg)", min_value=0.0, value=10.0, key=f"swt_{i}")
#                 with c7:
#                     sdw = st.text_input("Delivery Window", value="09:00-17:00", key=f"sdw_{i}")

#                 stops.append({
#                     "id": f"s{i+1}",
#                     "name": sname,
#                     "lat": slat,
#                     "lng": slng,
#                     "priority": sprio,
#                     "service_time_min": ssvc,
#                     "package_weight": swt,
#                     "delivery_window": sdw,
#                 })

#         submitted = st.form_submit_button(
#             "✅ Update Plan" if is_modifying else "🚀 Generate Plan",
#             use_container_width=True
#         )

#     if submitted:
#         plan_data = {
#             "user_constraints": {
#                 "date": str(date),
#                 "budget": budget,
#                 "deadline": deadline,
#                 "preferences": {
#                     "avoid_high_traffic": avoid_traffic,
#                     "avoid_tolls": avoid_tolls,
#                     "optimize_for": optimize_for,
#                 },
#             },
#             "start_location": {
#                 "name": start_name,
#                 "lat": start_lat,
#                 "lng": start_lng,
#             },
#             "vehicle": {
#                 "start_time": start_time,
#                 "end_time": end_time,
#                 "cost_per_km": cost_per_km,
#                 "capacity": capacity,
#             },
#             "stops": stops,
#         }

#         with st.spinner("🧠 Generating optimized route..."):
#             try:
#                 result = run_planner(
#                     user_id=user_id,
#                     input_source="form",
#                     raw_input=plan_data,
#                     user_message="",
#                     existing_itin_id=st.session_state.current_itin_id if is_modifying else None,
#                     existing_plan=st.session_state.current_plan if is_modifying else None,
#                 )

#                 final_plan = result.get("final_plan")
#                 if final_plan:
#                     st.session_state.current_itin_id = final_plan.get("itinerary_id")
#                     st.session_state.current_plan = final_plan.get("plan_data")
#                     st.session_state.result = result
#                     st.success("✅ Plan generated!")
#                 else:
#                     st.error(f"Error: {result.get('error', 'Unknown')}")

#             except Exception as e:
#                 st.error(f"System error: {e}")

#         st.rerun()

#     # Show result
#     if st.session_state.result:
#         st.markdown("---")
#         render_plan_result(st.session_state.result, user_id)



"""
user_form.py — Form-based planner interface
Geocoding via Nominatim (OpenStreetMap) — no API key needed.
"""
import streamlit as st
from agents import run_planner
from plan_renderer import render_plan_result
from geocoder import render_location_picker, geocode


# ── helpers ──────────────────────────────────────────────────────────────────

def _init_stop_geo(i: int):
    """Ensure session state keys exist for stop i."""
    for suffix, default in [("_addr", ""), ("_lat", 0.0), ("_lng", 0.0), ("_name", "")]:
        k = f"stop_{i}{suffix}"
        if k not in st.session_state:
            st.session_state[k] = default


def _render_stop_geocoder(i: int):
    """
    Inline geocoder for a stop (outside st.form so buttons can trigger reruns).
    Returns current {name, lat, lng} from session state.
    """
    _init_stop_geo(i)

    addr_key = f"stop_{i}_addr"
    lat_key  = f"stop_{i}_lat"
    lng_key  = f"stop_{i}_lng"
    name_key = f"stop_{i}_name"

    col_txt, col_btn = st.columns([4, 1])
    with col_txt:
        addr_val = st.text_input(
            "Address / Place name",
            value=st.session_state[addr_key],
            key=f"stop_{i}_input",
            placeholder="e.g. Dadar Station, Mumbai",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("🔍", key=f"stop_{i}_geo_btn", help="Search location", use_container_width=True):
            if addr_val.strip():
                with st.spinner("Searching..."):
                    res = geocode(addr_val)
                if res:
                    hits = res["all_results"]
                    if len(hits) > 1:
                        st.session_state[f"stop_{i}_hits"] = hits
                        st.session_state[addr_key] = addr_val
                    else:
                        st.session_state[addr_key]  = addr_val
                        st.session_state[lat_key]   = res["lat"]
                        st.session_state[lng_key]   = res["lng"]
                        st.session_state[name_key]  = res["display_name"]
                        if f"stop_{i}_hits" in st.session_state:
                            del st.session_state[f"stop_{i}_hits"]
                    st.rerun()
                else:
                    st.warning(f"No result for '{addr_val}'. Try a more specific name.")
            else:
                st.warning("Enter an address first.")

    # Multi-result disambiguation picker
    hits_key = f"stop_{i}_hits"
    if hits_key in st.session_state:
        options = [h["display_name"] for h in st.session_state[hits_key]]
        chosen  = st.selectbox("Multiple results — select one:", options, key=f"stop_{i}_pick")
        if st.button("✅ Confirm selection", key=f"stop_{i}_confirm"):
            idx = options.index(chosen)
            h   = st.session_state[hits_key][idx]
            st.session_state[lat_key]  = h["lat"]
            st.session_state[lng_key]  = h["lng"]
            st.session_state[name_key] = h["display_name"]
            del st.session_state[hits_key]
            st.rerun()

    # Resolved badge
    if st.session_state[lat_key] != 0.0:
        st.caption(
            f"📍 {st.session_state[name_key][:70]}  "
            f"| `{st.session_state[lat_key]:.5f}, {st.session_state[lng_key]:.5f}`"
        )
    else:
        st.caption("⚠️ Not resolved yet — click 🔍 to search.")

    return {
        "name": st.session_state[name_key] or addr_val or f"Stop {i+1}",
        "lat":  st.session_state[lat_key],
        "lng":  st.session_state[lng_key],
    }


# ── main page ─────────────────────────────────────────────────────────────────

def render_form_page():
    st.title("📋 Form Planner")
    st.caption(
        "Type any place name or address — coordinates are resolved automatically "
        "via **OpenStreetMap / Nominatim** (free, no API key required)."
    )

    user    = st.session_state.user
    user_id = user["id"]

    # ── Modification banner ──────────────────────────────────────────────────
    is_modifying = (
        st.session_state.current_itin_id is not None
        and st.session_state.current_plan  is not None
        and st.session_state.result        is not None
    )
    if is_modifying:
        st.info(f"✏️ Modifying existing plan #{st.session_state.current_itin_id}. Submit to update.")
        if st.button("🆕 Create New Plan Instead"):
            st.session_state.current_itin_id = None
            st.session_state.current_plan    = None
            st.session_state.result          = None
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION A — geocoding widgets (must be OUTSIDE st.form so Search
    #             buttons can trigger st.rerun() mid-interaction)
    # ════════════════════════════════════════════════════════════════════════

    st.markdown("### 🏁 Start Location")
    start_loc = render_location_picker(
        label="Start Location",
        key_prefix="start",
        default_address="Mumbai Central, Mumbai",
    )

    st.markdown("### 📍 Delivery Stops")
    num_stops = st.number_input(
        "Number of Stops", min_value=1, max_value=20, value=3, step=1, key="num_stops_input"
    )

    stop_geos = []
    for i in range(int(num_stops)):
        with st.expander(f"Stop {i+1} — Location Search", expanded=(i == 0)):
            geo = _render_stop_geocoder(i)
            stop_geos.append(geo)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION B — all non-geocoding fields inside st.form
    # ════════════════════════════════════════════════════════════════════════
    with st.form("planner_form"):

        st.markdown("### 📌 Route Constraints")
        col1, col2, col3 = st.columns(3)
        with col1:
            date         = st.date_input("Date")
        with col2:
            budget       = st.number_input("Budget (₹)", min_value=0, value=5000, step=100)
        with col3:
            deadline     = st.text_input("Deadline (HH:MM)", value="20:00")

        col4, col5, col6 = st.columns(3)
        with col4:
            avoid_traffic = st.checkbox("Avoid High Traffic")
        with col5:
            avoid_tolls   = st.checkbox("Avoid Tolls")
        with col6:
            optimize_for  = st.selectbox("Optimize For", ["time", "cost"])

        st.markdown("### 🚛 Vehicle")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_time  = st.text_input("Start Time",  value="08:00")
        with col2:
            end_time    = st.text_input("End Time",    value="20:00")
        with col3:
            cost_per_km = st.number_input("Cost/km (₹)", value=10.0)
        with col4:
            capacity    = st.number_input("Capacity (kg)", value=1000.0)

        st.markdown("### ⚙️ Stop Details")
        st.caption("Set priority, timing and weight for each stop.")

        stop_extras = []
        for i in range(int(num_stops)):
            resolved_name = stop_geos[i]["name"][:50] if stop_geos else f"Stop {i+1}"
            st.markdown(f"**Stop {i+1}** — _{resolved_name}_")
            c4, c5, c6, c7 = st.columns(4)
            with c4:
                sprio = st.selectbox("Priority (1=low, 5=high)", [1,2,3,4,5], index=1, key=f"sprio_{i}")
            with c5:
                ssvc  = st.number_input("Service Time (min)", min_value=1, value=15, key=f"ssvc_{i}")
            with c6:
                swt   = st.number_input("Package Weight (kg)", min_value=0.0, value=10.0, key=f"swt_{i}")
            with c7:
                sdw   = st.text_input("Delivery Window", value="09:00-17:00", key=f"sdw_{i}")
            stop_extras.append({
                "priority":         sprio,
                "service_time_min": ssvc,
                "package_weight":   swt,
                "delivery_window":  sdw,
            })

        submitted = st.form_submit_button(
            "✅ Update Plan" if is_modifying else "🚀 Generate Plan",
            use_container_width=True,
        )

    # ════════════════════════════════════════════════════════════════════════
    # On submit — validate then run planner
    # ════════════════════════════════════════════════════════════════════════
    if submitted:
        # Validate start location resolved
        if start_loc["lat"] == 0.0 and start_loc["lng"] == 0.0:
            st.error(
                "⚠️ Start location not resolved. "
                "Please type an address above and click 🔍 Search before submitting."
            )
            st.stop()

        # Warn about unresolved stops
        unresolved = [
            f"Stop {i+1}" for i, g in enumerate(stop_geos)
            if g["lat"] == 0.0 and g["lng"] == 0.0
        ]
        if unresolved:
            st.warning(
                f"⚠️ Unresolved coordinates for: {', '.join(unresolved)}. "
                "These stops default to (0, 0). Search them for accurate routing."
            )

        # Merge geo + extras into full stops list
        stops = [
            {
                "id":               f"s{i+1}",
                "name":             geo["name"],
                "lat":              geo["lat"],
                "lng":              geo["lng"],
                "priority":         extra["priority"],
                "service_time_min": extra["service_time_min"],
                "package_weight":   extra["package_weight"],
                "delivery_window":  extra["delivery_window"],
            }
            for i, (geo, extra) in enumerate(zip(stop_geos, stop_extras))
        ]

        plan_data = {
            "user_constraints": {
                "date":     str(date),
                "budget":   budget,
                "deadline": deadline,
                "preferences": {
                    "avoid_high_traffic": avoid_traffic,
                    "avoid_tolls":        avoid_tolls,
                    "optimize_for":       optimize_for,
                },
            },
            "start_location": start_loc,
            "vehicle": {
                "start_time":  start_time,
                "end_time":    end_time,
                "cost_per_km": cost_per_km,
                "capacity":    capacity,
            },
            "stops": stops,
        }

        with st.spinner("🧠 Generating optimized route..."):
            try:
                result = run_planner(
                    user_id      = user_id,
                    input_source = "form",
                    raw_input    = plan_data,
                    user_message = "",
                    existing_itin_id = st.session_state.current_itin_id if is_modifying else None,
                    existing_plan    = st.session_state.current_plan    if is_modifying else None,
                )

                final_plan = result.get("final_plan")
                if final_plan:
                    st.session_state.current_itin_id = final_plan.get("itinerary_id")
                    st.session_state.current_plan    = final_plan.get("plan_data")
                    st.session_state.result          = result
                    st.success("✅ Plan generated!")
                else:
                    st.error(f"Error: {result.get('error', 'Unknown')}")

            except Exception as e:
                st.error(f"System error: {e}")

        st.rerun()

    # ── Display result ────────────────────────────────────────────────────────
    if st.session_state.result:
        st.markdown("---")
        render_plan_result(st.session_state.result, user_id)