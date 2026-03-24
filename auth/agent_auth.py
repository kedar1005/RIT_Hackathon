"""
CitiZen AI — Agent Authentication
Login and registration for resolution agents.
"""
import hashlib
import re
import streamlit as st
from utils.data_utils import add_agent, authenticate_agent
from utils.ui_utils import inject_global_css, hero_header, styled_error, styled_success


DEPARTMENTS = [
    "Roads & Infrastructure",
    "Electricity & Streetlights",
    "Sanitation & Waste",
    "Water Supply",
    "Drainage & Sewerage",
    "Parks & Tree Maintenance",
    "Traffic Management",
    "Public Safety & General"
]


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _validate_agent_id(agent_id):
    """Agent ID must match format AGT followed by 4 digits."""
    return bool(re.match(r'^AGT\d{4}$', agent_id))


def show_agent_auth():
    """Display agent authentication page (Admin Login only, no public registration)."""
    inject_global_css()

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
            st.session_state.page = 'landing'
            st.rerun()

    hero_header(
        "Admin Control Center",
        "Access the administration portal",
        badge_text="🛡️ ADMIN ACCESS"
    )

    st.markdown("""
    <div style="max-width:400px;margin:0 auto;padding:1.5rem;
        background:#111827;border:1px solid rgba(124,58,237,0.2);
        border-radius:16px;">
        <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
            color:#F0F4FF;text-align:center;margin-bottom:1rem;">Admin Login</h3>
    </div>
    """, unsafe_allow_html=True)

    with st.form("agent_login_form", clear_on_submit=False):
        agent_id = st.text_input("Agent ID", placeholder="AGT0001")
        password = st.text_input("Password", type="password",
                                 placeholder="Enter your password")
        submitted = st.form_submit_button("Access Portal →", use_container_width=True)

        if submitted:
            if not agent_id or not password:
                styled_error("Please fill in all fields")
            elif not _validate_agent_id(agent_id):
                styled_error("Agent ID must be in format AGT followed by 4 digits (e.g., AGT0001)")
            else:
                # ─── CONSTANT ADMIN LOGIN ───
                # ID: AGT0001, Password: admin123
                if agent_id.upper() == "AGT0001" and password == "admin123":
                    st.session_state.authenticated = True
                    st.session_state.user_type = 'agent'
                    st.session_state.is_admin = True
                    st.session_state.current_user = {
                        'id': 1, # Placeholder ID for constant admin
                        'name': "System Administrator",
                        'agent_id': "AGT0001",
                        'department': "Administration"
                    }
                    st.session_state.page = 'agent_auth'
                    styled_success("Admin Access Granted. Welcome, System Administrator.")
                    st.rerun()

                # ─── NORMAL AGENT LOGIN (DB) ───
                password_hash = _hash_password(password)
                agent = authenticate_agent(agent_id, password_hash)
                if agent:
                    st.session_state.authenticated = True
                    st.session_state.user_type = 'agent'
                    # Even if logging in via DB, double check ID for admin privileges
                    st.session_state.is_admin = (agent_id.upper() == 'AGT0001')
                    st.session_state.current_user = {
                        'id': agent['id'],
                        'name': agent['name'],
                        'agent_id': agent['agent_id'],
                        'department': agent['department']
                    }
                    st.session_state.page = 'agent_auth'
                    styled_success(f"Access granted. Welcome, {agent['name']}.")
                    st.rerun()
                else:
                    styled_error("Invalid credentials. Access denied.")


def show_worker_auth():
    """Display worker login page. Workers are agents who login to see department-filtered complaints."""
    inject_global_css()

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
            st.session_state.page = 'landing'
            st.rerun()

    hero_header(
        "Worker Portal",
        "Access your department complaint queue",
        badge_text="👷 WORKER ACCESS"
    )

    st.markdown("""
    <div style="max-width:400px;margin:0 auto;padding:1.5rem;
        background:#111827;border:1px solid rgba(0,212,255,0.2);
        border-radius:16px;">
        <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
            color:#F0F4FF;text-align:center;margin-bottom:1rem;">Worker Login</h3>
    </div>
    """, unsafe_allow_html=True)

    with st.form("worker_login_form", clear_on_submit=False):
        agent_id = st.text_input("Agent ID", placeholder="AGT0002")
        password = st.text_input("Password", type="password",
                                 placeholder="Enter your password")
        submitted = st.form_submit_button("Login →", use_container_width=True)

        if submitted:
            if not agent_id or not password:
                styled_error("Please fill in all fields")
            elif not _validate_agent_id(agent_id):
                styled_error("Agent ID must be in format AGT followed by 4 digits (e.g., AGT0002)")
            else:
                password_hash = _hash_password(password)
                agent = authenticate_agent(agent_id, password_hash)
                if agent:
                    st.session_state.authenticated = True
                    st.session_state.user_type = 'worker'
                    st.session_state.is_admin = False
                    st.session_state.current_user = {
                        'id': agent['id'],
                        'name': agent['name'],
                        'agent_id': agent['agent_id'],
                        'department': agent['department']
                    }
                    st.session_state.page = 'worker_auth'
                    styled_success(f"Welcome, {agent['name']}! Department: {agent['department']}")
                    st.rerun()
                else:
                    styled_error("Invalid credentials. Access denied.")
