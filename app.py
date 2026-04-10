"""
app.py — Main Streamlit entry point
AI Travel & Logistics Planner
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from database import init_db, login_user, signup_user

# Init DB on startup
init_db()

st.set_page_config(
    page_title="AI Travel & Logistics Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Session state defaults ----------
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_itin_id" not in st.session_state:
    st.session_state.current_itin_id = None
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "result" not in st.session_state:
    st.session_state.result = None


def render_auth():
    """Render login/signup page."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🗺️ AI Travel & Logistics Planner")
        st.markdown("---")

        tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Signup"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                if submitted:
                    user = login_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.page = "app"
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Username", key="su_user")
                new_pass = st.text_input("Password", type="password", key="su_pass")
                role = st.selectbox("Role", ["user", "admin"])
                admin_key = ""
                if role == "admin":
                    admin_key = st.text_input("Admin Secret Key", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                if submitted:
                    ok, msg = signup_user(new_user, new_pass, role, admin_key)
                    if ok:
                        st.success(msg + " Please login.")
                    else:
                        st.error(msg)


def render_sidebar():
    """Sidebar navigation for logged-in users."""
    with st.sidebar:
        user = st.session_state.user
        st.markdown(f"### 👤 {user['username']}")
        st.markdown(f"**Role:** {user['role'].title()}")
        st.markdown("---")

        if user["role"] == "user":
            st.session_state.page = st.radio(
                "Navigate",
                ["💬 Chat Planner", "📋 Form Planner", "📤 CSV Upload", "📊 My Plans"],
                key="nav_user",
            )
        else:
            st.session_state.page = st.radio(
                "Navigate",
                ["📊 Admin Dashboard"],
                key="nav_admin",
            )

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["user", "chat_history", "current_itin_id", "current_plan", "result"]:
                st.session_state[key] = None if key == "user" else ([] if key == "chat_history" else None)
            st.session_state.page = "login"
            st.rerun()


def main():
    # Route by auth state
    if not st.session_state.user:
        render_auth()
        return

    render_sidebar()
    page = st.session_state.get("page", "login")

    if st.session_state.user["role"] == "admin":
        from admin_dashboard import render_admin_dashboard
        render_admin_dashboard()
        return

    # User pages
    if page == "💬 Chat Planner":
        from user_chat import render_chat_page
        render_chat_page()
    elif page == "📋 Form Planner":
        from user_form import render_form_page
        render_form_page()
    elif page == "📤 CSV Upload":
        from user_csv import render_csv_page
        render_csv_page()
    elif page == "📊 My Plans":
        from user_plans import render_plans_page
        render_plans_page()
    else:
        from user_chat import render_chat_page
        render_chat_page()


if __name__ == "__main__":
    main()