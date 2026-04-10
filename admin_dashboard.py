"""
admin_dashboard.py — Admin analytics dashboard
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database import get_admin_stats, get_conn


def render_admin_dashboard():
    st.title("👨‍💼 Admin Dashboard")
    st.caption("System-wide analytics and monitoring.")

    stats = get_admin_stats()

    # --- KPI Cards ---
    st.markdown("### 📊 Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👤 Total Users", stats["total_users"])
    c2.metric("📋 Total Plans", stats["total_plans"])
    c3.metric("✅ Accepted", stats["plans_accepted"])
    c4.metric("📈 Acceptance Rate", f"{stats['acceptance_rate']}%")
    c5.metric("🔵 Generated", stats["plans_generated"])

    st.markdown("---")

    col1, col2 = st.columns(2)

    # --- Plan Status Distribution ---
    with col1:
        st.markdown("#### Plan Status Distribution")
        status_data = {
            "Status": ["Generated", "Accepted", "Modified", "Rejected"],
            "Count": [
                stats["plans_generated"],
                stats["plans_accepted"],
                stats["plans_modified"],
                stats["plans_rejected"],
            ],
        }
        fig_status = px.pie(
            status_data,
            names="Status",
            values="Count",
            color="Status",
            color_discrete_map={
                "Generated": "#3b82f6",
                "Accepted": "#22c55e",
                "Modified": "#eab308",
                "Rejected": "#ef4444",
            },
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # --- Input Source Distribution ---
    with col2:
        st.markdown("#### Input Source Usage")
        src = stats.get("by_source", {})
        if src:
            fig_src = px.bar(
                x=list(src.keys()),
                y=list(src.values()),
                labels={"x": "Source", "y": "Count"},
                color=list(src.keys()),
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig_src, use_container_width=True)
        else:
            st.info("No input source data yet.")

    st.markdown("---")

    # --- Plans per Day ---
    st.markdown("#### 📅 Plans Per Day (Last 30 Days)")
    daily = stats.get("plans_per_day", [])
    if daily:
        df_daily = pd.DataFrame(daily)
        fig_daily = px.line(
            df_daily,
            x="day",
            y="count",
            markers=True,
            labels={"day": "Date", "count": "Plans"},
        )
        fig_daily.update_traces(line_color="#6366f1", fill="tozeroy")
        st.plotly_chart(fig_daily, use_container_width=True)
    else:
        st.info("No daily data yet.")

    st.markdown("---")

    # --- Plans per User ---
    st.markdown("#### 👤 Plans per User")
    ppu = stats.get("plans_per_user", [])
    if ppu:
        df_ppu = pd.DataFrame(ppu)
        fig_ppu = px.bar(
            df_ppu,
            x="username",
            y="count",
            labels={"username": "User", "count": "Plans"},
            color="count",
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig_ppu, use_container_width=True)
    else:
        st.info("No user data yet.")

    st.markdown("---")

    # --- Recent Activity Log ---
    st.markdown("#### 📝 Recent Activity Log")
    conn = get_conn()
    logs = conn.execute("""
        SELECT l.id, u.username, l.action, l.detail, l.timestamp
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.timestamp DESC LIMIT 50
    """).fetchall()
    conn.close()

    if logs:
        log_data = [dict(r) for r in logs]
        df_logs = pd.DataFrame(log_data)
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No activity logged yet.")

    st.markdown("---")

    # --- All Users Table ---
    st.markdown("#### 👥 All Users")
    conn = get_conn()
    users = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    if users:
        st.dataframe([dict(u) for u in users], use_container_width=True)

    # --- All Itineraries ---
    st.markdown("#### 📋 All Itineraries")
    conn = get_conn()
    itins = conn.execute("""
        SELECT i.id, u.username, i.input_source, i.status, i.timestamp
        FROM itineraries i
        LEFT JOIN users u ON i.user_id = u.id
        ORDER BY i.timestamp DESC LIMIT 100
    """).fetchall()
    conn.close()
    if itins:
        st.dataframe([dict(i) for i in itins], use_container_width=True)
    else:
        st.info("No itineraries yet.")

    # Auto-refresh
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()