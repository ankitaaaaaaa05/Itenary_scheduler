"""
user_chat.py — Chat-based planner interface
"""
import streamlit as st
import json
from agents import run_planner
from plan_renderer import render_plan_result


def render_chat_page():
    st.title("💬 Chat Planner")
    st.caption("Describe your delivery/travel needs in plain language. Modify plans conversationally.")

    user = st.session_state.user
    user_id = user["id"]

    # Display conversation
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            with st.chat_message(role):
                st.markdown(content)

    # Show current plan result
    if st.session_state.result:
        render_plan_result(st.session_state.result, user_id)

    # Input
    st.markdown("---")
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.chat_input(
            "E.g. 'Plan 5 deliveries from Mumbai to nearby locations, budget ₹2000, optimize for time'"
        )
    with col2:
        if st.button("🔄 New Plan", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.current_itin_id = None
            st.session_state.current_plan = None
            st.session_state.result = None
            st.rerun()

    if user_input:
        # Add user message to history display
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("🧠 Planning your route..."):
            try:
                result = run_planner(
                    user_id=user_id,
                    input_source="chat",
                    raw_input={},
                    user_message=user_input,
                    chat_history=st.session_state.chat_history[:-1],  # history before this msg
                    existing_itin_id=st.session_state.current_itin_id,
                    existing_plan=st.session_state.current_plan,
                )

                final_plan = result.get("final_plan")
                if final_plan:
                    st.session_state.current_itin_id = final_plan.get("itinerary_id")
                    st.session_state.current_plan = final_plan.get("plan_data")
                    st.session_state.result = result

                    # Add assistant response to history
                    explanation = final_plan.get("explanation", "Route generated.")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": explanation[:500] + "..." if len(explanation) > 500 else explanation,
                    })
                else:
                    err = result.get("error", "Unknown error")
                    st.error(f"Could not generate plan: {err}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Sorry, I encountered an error: {err}",
                    })

            except Exception as e:
                st.error(f"System error: {e}")

        st.rerun()