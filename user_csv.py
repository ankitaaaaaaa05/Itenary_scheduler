# """
# user_csv.py — CSV upload planner interface
# """
# import streamlit as st
# from csv_processor import process_csv, stops_to_plan_data
# from agents import run_planner
# from plan_renderer import render_plan_result


# def render_csv_page():
#     st.title("📤 CSV Upload Planner")
#     st.caption("Upload a CSV file with your delivery stops. Configure vehicle and constraints, then generate.")

#     user = st.session_state.user
#     user_id = user["id"]

#     # Template download
#     template_csv = """name,lat,lng,priority,service_time,weight,delivery_window
# Warehouse A,19.0760,72.8777,5,10,50,08:00-10:00
# Customer B,19.1234,72.9012,3,15,20,10:00-12:00
# Customer C,18.9876,72.8543,2,15,15,12:00-14:00
# Customer D,19.0500,72.8900,4,20,30,14:00-16:00
# Customer E,19.1100,72.9200,1,10,10,09:00-17:00
# """
#     st.download_button(
#         "⬇️ Download CSV Template",
#         data=template_csv,
#         file_name="stops_template.csv",
#         mime="text/csv",
#     )

#     uploaded = st.file_uploader("Upload CSV", type=["csv"])

#     if uploaded:
#         file_bytes = uploaded.read()
#         stops, warnings = process_csv(file_bytes)

#         if warnings:
#             for w in warnings:
#                 st.warning(w)

#         if stops:
#             st.markdown(f"### 📋 Preview — {len(stops)} stops detected")
#             st.dataframe(stops, use_container_width=True)

#             st.markdown("### ⚙️ Route Configuration")
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 start_name = st.text_input("Start Location Name", value="Depot")
#                 start_lat = st.number_input("Start Lat", value=19.0760, format="%.4f")
#                 start_lng = st.number_input("Start Lng", value=72.8777, format="%.4f")
#             with col2:
#                 budget = st.number_input("Budget (₹)", value=5000)
#                 optimize_for = st.selectbox("Optimize For", ["time", "cost"])
#                 avoid_traffic = st.checkbox("Avoid High Traffic")
#             with col3:
#                 start_time = st.text_input("Vehicle Start Time", value="08:00")
#                 end_time = st.text_input("Vehicle End Time", value="20:00")
#                 cost_per_km = st.number_input("Cost/km (₹)", value=10.0)
#                 capacity = st.number_input("Capacity (kg)", value=1000.0)

#             is_modifying = (
#                 st.session_state.current_itin_id is not None
#                 and st.session_state.result is not None
#             )

#             btn_label = "✅ Update Plan from CSV" if is_modifying else "🚀 Generate Plan from CSV"
#             if st.button(btn_label, use_container_width=True):
#                 plan_data = stops_to_plan_data(
#                     stops=stops,
#                     start_location={"name": start_name, "lat": start_lat, "lng": start_lng},
#                     vehicle={
#                         "start_time": start_time,
#                         "end_time": end_time,
#                         "cost_per_km": cost_per_km,
#                         "capacity": capacity,
#                     },
#                     user_constraints={
#                         "budget": budget,
#                         "preferences": {
#                             "optimize_for": optimize_for,
#                             "avoid_high_traffic": avoid_traffic,
#                         },
#                     },
#                 )

#                 with st.spinner("🧠 Processing CSV and generating route..."):
#                     try:
#                         result = run_planner(
#                             user_id=user_id,
#                             input_source="csv",
#                             raw_input=plan_data,
#                             user_message="",
#                             existing_itin_id=st.session_state.current_itin_id if is_modifying else None,
#                             existing_plan=st.session_state.current_plan if is_modifying else None,
#                         )

#                         final_plan = result.get("final_plan")
#                         if final_plan:
#                             st.session_state.current_itin_id = final_plan.get("itinerary_id")
#                             st.session_state.current_plan = final_plan.get("plan_data")
#                             st.session_state.result = result
#                             st.success("✅ Route generated from CSV!")
#                         else:
#                             st.error(f"Error: {result.get('error', 'Unknown')}")
#                     except Exception as e:
#                         st.error(f"System error: {e}")

#                 st.rerun()
#         else:
#             st.error("No valid stops found in CSV. Please check the format.")

#     # Show current result
#     if st.session_state.result:
#         st.markdown("---")
#         render_plan_result(st.session_state.result, user_id)


"""
user_csv.py — CSV upload planner interface
"""
import pandas as pd
import streamlit as st
from csv_processor import process_csv, stops_to_plan_data
from agents import run_planner
from plan_renderer import render_plan_result


def render_csv_page():
    st.title("📤 CSV Upload Planner")
    st.caption("Upload a CSV file with your delivery stops. Configure vehicle and constraints, then generate.")

    user = st.session_state.user
    user_id = user["id"]

    # Template download
    template_csv = """name,lat,lng,priority,service_time,weight,delivery_window
Warehouse A,19.0760,72.8777,5,10,50,08:00-10:00
Customer B,19.1234,72.9012,3,15,20,10:00-12:00
Customer C,18.9876,72.8543,2,15,15,12:00-14:00
Customer D,19.0500,72.8900,4,20,30,14:00-16:00
Customer E,19.1100,72.9200,1,10,10,09:00-17:00
"""
    st.download_button(
        "⬇️ Download CSV Template",
        data=template_csv,
        file_name="stops_template.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        file_bytes = uploaded.read()
        stops, warnings = process_csv(file_bytes)

        if warnings:
            for w in warnings:
                st.warning(w)

        if stops:
            # Normalise to DataFrame regardless of what process_csv returns
            stops_df = pd.DataFrame(stops) if not isinstance(stops, pd.DataFrame) else stops

            st.markdown(f"### 📋 Preview — {len(stops_df)} stops detected")
            st.dataframe(stops_df, use_container_width=True)

            st.markdown("### ⚙️ Route Configuration")

            # Auto-populate start location from first row of the CSV
            first_stop = stops_df.iloc[0] if not stops_df.empty else None
            default_name = str(first_stop["name"]) if first_stop is not None and "name" in stops_df.columns else "Depot"
            default_lat = float(first_stop["lat"])  if first_stop is not None and "lat"  in stops_df.columns else 19.0760
            default_lng = float(first_stop["lng"])  if first_stop is not None and "lng"  in stops_df.columns else 72.8777

            col1, col2, col3 = st.columns(3)
            with col1:
                start_name = st.text_input("Start Location Name", value=default_name)
                start_lat = st.number_input("Start Lat", value=default_lat, format="%.4f")
                start_lng = st.number_input("Start Lng", value=default_lng, format="%.4f")
            with col2:
                budget = st.number_input("Budget (₹)", value=5000)
                optimize_for = st.selectbox("Optimize For", ["time", "cost"])
                avoid_traffic = st.checkbox("Avoid High Traffic")
            with col3:
                start_time = st.text_input("Vehicle Start Time", value="08:00")
                end_time = st.text_input("Vehicle End Time", value="20:00")
                cost_per_km = st.number_input("Cost/km (₹)", value=10.0)
                capacity = st.number_input("Capacity (kg)", value=1000.0)

            is_modifying = (
                st.session_state.current_itin_id is not None
                and st.session_state.result is not None
            )

            btn_label = "✅ Update Plan from CSV" if is_modifying else "🚀 Generate Plan from CSV"
            if st.button(btn_label, use_container_width=True):
                plan_data = stops_to_plan_data(
                    stops=stops,
                    start_location={"name": start_name, "lat": start_lat, "lng": start_lng},
                    vehicle={
                        "start_time": start_time,
                        "end_time": end_time,
                        "cost_per_km": cost_per_km,
                        "capacity": capacity,
                    },
                    user_constraints={
                        "budget": budget,
                        "preferences": {
                            "optimize_for": optimize_for,
                            "avoid_high_traffic": avoid_traffic,
                        },
                    },
                )

                with st.spinner("🧠 Processing CSV and generating route..."):
                    try:
                        result = run_planner(
                            user_id=user_id,
                            input_source="csv",
                            raw_input=plan_data,
                            user_message="",
                            existing_itin_id=st.session_state.current_itin_id if is_modifying else None,
                            existing_plan=st.session_state.current_plan if is_modifying else None,
                        )

                        final_plan = result.get("final_plan")
                        if final_plan:
                            st.session_state.current_itin_id = final_plan.get("itinerary_id")
                            st.session_state.current_plan = final_plan.get("plan_data")
                            st.session_state.result = result
                            st.success("✅ Route generated from CSV!")
                        else:
                            st.error(f"Error: {result.get('error', 'Unknown')}")
                    except Exception as e:
                        st.error(f"System error: {e}")

                st.rerun()
        else:
            st.error("No valid stops found in CSV. Please check the format.")

    # Show current result
    if st.session_state.result:
        st.markdown("---")
        render_plan_result(st.session_state.result, user_id)