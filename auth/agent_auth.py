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
    """Display agent authentication page."""
    inject_global_css()

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
            st.session_state.page = 'landing'
            st.rerun()

    hero_header(
        "Agent Control Center",
        "Access the resolution management portal",
        badge_text="🛡️ AGENT ACCESS"
    )

    tab_login, tab_register = st.tabs(["🔑 Agent Sign In", "📝 Register Agent"])

    with tab_login:
        st.markdown("""
        <div style="max-width:400px;margin:0 auto;padding:1.5rem;
            background:#111827;border:1px solid rgba(124,58,237,0.2);
            border-radius:16px;">
            <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
                color:#F0F4FF;text-align:center;margin-bottom:1rem;">Agent Login</h3>
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
                    password_hash = _hash_password(password)
                    agent = authenticate_agent(agent_id, password_hash)
                    if agent:
                        st.session_state.authenticated = True
                        st.session_state.user_type = 'agent'
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

    with tab_register:
        st.markdown("""
        <div style="max-width:400px;margin:0 auto;padding:1.5rem;
            background:#111827;border:1px solid rgba(124,58,237,0.2);
            border-radius:16px;">
            <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
                color:#F0F4FF;text-align:center;margin-bottom:1rem;">Agent Registration</h3>
        </div>
        """, unsafe_allow_html=True)

        with st.form("agent_register_form", clear_on_submit=False):
            reg_name = st.text_input("Full Name", placeholder="Officer Rahul Mehta")
            reg_agent_id = st.text_input("Agent ID", placeholder="AGT0001")
            reg_department = st.selectbox("Department", DEPARTMENTS)
            reg_password = st.text_input("Create Password", type="password",
                                         placeholder="Min 6 characters")
            reg_confirm = st.text_input("Confirm Password", type="password")
            reg_submitted = st.form_submit_button("Register Agent →",
                                                   use_container_width=True)

            if reg_submitted:
                if not all([reg_name, reg_agent_id, reg_password, reg_confirm]):
                    styled_error("Please fill in all fields")
                elif not _validate_agent_id(reg_agent_id):
                    styled_error("Agent ID must be AGT followed by 4 digits (e.g., AGT0001)")
                elif reg_password != reg_confirm:
                    styled_error("Passwords do not match")
                elif len(reg_password) < 6:
                    styled_error("Password must be at least 6 characters")
                else:
                    password_hash = _hash_password(reg_password)
                    result = add_agent(reg_name, reg_agent_id, password_hash,
                                       reg_department)
                    if result:
                        st.session_state.authenticated = True
                        st.session_state.user_type = 'agent'
                        st.session_state.current_user = {
                            'id': result,
                            'name': reg_name,
                            'agent_id': reg_agent_id,
                            'department': reg_department
                        }
                        st.session_state.page = 'agent_auth'
                        styled_success("Agent registered. Access granted.")
                        st.rerun()
                    else:
                        styled_error("Agent ID already registered.")
