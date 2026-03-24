"""
CitiZen AI — Citizen Authentication
Login and registration for citizens.
"""
import hashlib
import re
import streamlit as st
from utils.data_utils import add_user, authenticate_user
from utils.ui_utils import inject_global_css, hero_header, styled_error, styled_success


def _hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def _validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _validate_password(password):
    """Check password strength: 6+ chars, at least one letter and one number."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""


def show_user_auth():
    """Display citizen authentication page with sign-in and registration."""
    inject_global_css()

    # Back button
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Home"):
            st.session_state.page = 'landing'
            st.rerun()

    hero_header(
        "Citizen Portal",
        "Sign in to report and track civic issues in your city",
        badge_text="🏛️ CITIZEN ACCESS"
    )

    tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Create Account"])

    with tab_login:
        st.markdown("""
        <div style="max-width:400px;margin:0 auto;padding:1.5rem;
            background:#111827;border:1px solid rgba(255,255,255,0.08);
            border-radius:16px;">
            <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
                color:#F0F4FF;text-align:center;margin-bottom:1rem;">Welcome Back</h3>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email Address", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)

            if submitted:
                if not email or not password:
                    styled_error("Please fill in all fields")
                elif not _validate_email(email):
                    styled_error("Please enter a valid email address")
                else:
                    password_hash = _hash_password(password)
                    user = authenticate_user(email, password_hash)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_type = 'citizen'
                        st.session_state.current_user = {
                            'id': user['id'],
                            'name': user['name'],
                            'email': user['email']
                        }
                        st.session_state.page = 'user_auth'
                        styled_success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        styled_error("Invalid email or password. Please try again.")

    with tab_register:
        st.markdown("""
        <div style="max-width:400px;margin:0 auto;padding:1.5rem;
            background:#111827;border:1px solid rgba(255,255,255,0.08);
            border-radius:16px;">
            <h3 style="font-family:'Sora',sans-serif;font-size:18px;font-weight:600;
                color:#F0F4FF;text-align:center;margin-bottom:1rem;">Join CitiZen AI</h3>
        </div>
        """, unsafe_allow_html=True)

        with st.form("register_form", clear_on_submit=False):
            reg_name = st.text_input("Full Name", placeholder="Priya Sharma")
            reg_email = st.text_input("Email", placeholder="priya@example.com")
            reg_password = st.text_input("Create Password", type="password",
                                         placeholder="Min 6 chars, letter + number")
            reg_confirm = st.text_input("Confirm Password", type="password",
                                        placeholder="Repeat your password")
            reg_submitted = st.form_submit_button("Create Account →", use_container_width=True)

            if reg_submitted:
                if not all([reg_name, reg_email, reg_password, reg_confirm]):
                    styled_error("Please fill in all fields")
                elif not _validate_email(reg_email):
                    styled_error("Please enter a valid email address")
                elif reg_password != reg_confirm:
                    styled_error("Passwords do not match")
                else:
                    valid, msg = _validate_password(reg_password)
                    if not valid:
                        styled_error(msg)
                    else:
                        password_hash = _hash_password(reg_password)
                        user_id = add_user(reg_name, reg_email, password_hash)
                        if user_id:
                            st.session_state.authenticated = True
                            st.session_state.user_type = 'citizen'
                            st.session_state.current_user = {
                                'id': user_id,
                                'name': reg_name,
                                'email': reg_email
                            }
                            st.session_state.page = 'user_auth'
                            styled_success("Account created! Welcome to CitiZen AI!")
                            st.rerun()
                        else:
                            styled_error("Email already registered. Please sign in instead.")
