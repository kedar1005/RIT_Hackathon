"""
CitiZen AI — Smart Public Complaint & Issue Detection System
Main entry point and app router.
"""
import os
import sys
import streamlit as st

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── PAGE CONFIG (must be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="CitiZen AI — Smart City Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── IMPORTS ──────────────────────────────────────────────────────────
from utils.data_utils import init_database
try:
    from utils.data_utils import get_active_session, delete_session, cleanup_sessions
except ImportError:
    # Keep the app bootable even if session helpers are temporarily out of sync.
    def get_active_session(session_id):
        return None

    def delete_session(session_id):
        return False

    def cleanup_sessions():
        return None
from utils.ui_utils import inject_global_css, sidebar_logo
from dashboard.landing import show_landing_page
from dashboard.user_dashboard import show_user_dashboard
from dashboard.agent_dashboard import show_agent_dashboard, show_worker_dashboard
from auth.user_auth import show_user_auth
from auth.agent_auth import show_agent_auth, show_worker_auth

# ─── INITIALIZATION ──────────────────────────────────────────────────
# Create necessary directories
os.makedirs(os.path.join(os.path.dirname(__file__), "assets", "uploaded_images"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "db"), exist_ok=True)

# Initialize database
init_database()

# Initialize session state defaults
if 'page' not in st.session_state:
    st.session_state.page = 'landing'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = {}

# ─── SESSION RESTORATION ──────────────────────────────────────────────
# Cleanup old sessions once per run (optional optimization)
if 'cleanup_done' not in st.session_state:
    cleanup_sessions()
    st.session_state.cleanup_done = True

# Check for session in URL
session_id = st.query_params.get("session")
if session_id and not st.session_state.authenticated:
    session_data = get_active_session(session_id)
    if session_data:
        st.session_state.authenticated = True
        st.session_state.user_type = session_data["session_info"]["user_type"]
        st.session_state.current_user = session_data["user_data"]
        # Determine page based on user type
        if st.session_state.user_type == 'citizen':
            st.session_state.page = 'user_auth'
        elif st.session_state.user_type == 'worker':
            st.session_state.page = 'worker_auth'
        else:
            st.session_state.page = 'agent_auth'
        
        # Admin flag
        if st.session_state.user_type == 'agent' and session_data["user_data"].get('agent_id') == 'AGT0001':
            st.session_state.is_admin = True
        else:
            st.session_state.is_admin = False

# ─── INJECT GLOBAL CSS ───────────────────────────────────────────────
inject_global_css()

# ─── SIDEBAR ─────────────────────────────────────────────────────────
sidebar_logo()

if st.session_state.authenticated:
    user = st.session_state.current_user
    user_type = st.session_state.user_type

    # Welcome message
    if user_type == 'citizen':
        st.sidebar.markdown(f"""
        <div style="padding:0.75rem;background:rgba(0,212,255,0.05);
            border:1px solid rgba(0,212,255,0.15);border-radius:8px;margin-bottom:1rem;">
            <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#8B98B8;
                letter-spacing:0.04em;text-transform:uppercase;">CITIZEN</div>
            <div style="font-family:'Sora',sans-serif;font-size:14px;font-weight:600;
                color:#F0F4FF;margin-top:2px;">{user.get('name', 'User')}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                color:#4A5568;margin-top:2px;">{user.get('email', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    elif user_type == 'worker':
        st.sidebar.markdown(f"""
        <div style="padding:0.75rem;background:rgba(0,212,255,0.05);
            border:1px solid rgba(0,212,255,0.15);border-radius:8px;margin-bottom:1rem;">
            <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#8B98B8;
                letter-spacing:0.04em;text-transform:uppercase;">👷 WORKER</div>
            <div style="font-family:'Sora',sans-serif;font-size:14px;font-weight:600;
                color:#F0F4FF;margin-top:2px;">{user.get('name', 'Worker')}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                color:#00D4FF;margin-top:2px;">{user.get('agent_id', '')}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                color:#4A5568;margin-top:2px;">{user.get('department', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f"""
        <div style="padding:0.75rem;background:rgba(124,58,237,0.05);
            border:1px solid rgba(124,58,237,0.15);border-radius:8px;margin-bottom:1rem;">
            <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#8B98B8;
                letter-spacing:0.04em;text-transform:uppercase;">AGENT</div>
            <div style="font-family:'Sora',sans-serif;font-size:14px;font-weight:600;
                color:#F0F4FF;margin-top:2px;">{user.get('name', 'Agent')}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                color:#7C3AED;margin-top:2px;">{user.get('agent_id', '')}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                color:#4A5568;margin-top:2px;">{user.get('department', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Live stats for agents
        try:
            from utils.data_utils import get_complaint_stats
            live_stats = get_complaint_stats()
            pending = live_stats.get('pending', 0)
            high = live_stats.get('urgency_high', 0)

            badge_style = ""
            if pending > 0:
                badge_style = f"""
                <span style="background:#FF4444;color:#fff;font-size:10px;
                    padding:2px 6px;border-radius:10px;margin-left:4px;
                    font-family:'JetBrains Mono',monospace;
                    animation:pulse-red 1.5s infinite;">{pending}</span>
                """

            st.sidebar.markdown(f"""
            <div style="display:none;">
                margin-top:0.5rem;padding-top:0.75rem;">
                <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#8B98B8;
                    margin-bottom:6px;">LIVE STATUS</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#F0F4FF;">
                    Pending {badge_style}
                </div>
                <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#FF4444;
                    margin-top:4px;">
                    🔴 {high} High Urgency
                </div>
            </div>
            """, unsafe_allow_html=True)

            live_status_html = (
                '<div style="padding:0.5rem 0;border-top:1px solid rgba(255,255,255,0.06);'
                'margin-top:0.5rem;padding-top:0.75rem;">'
                '<div style="font-family:\'DM Sans\',sans-serif;font-size:11px;color:#8B98B8;'
                'margin-bottom:6px;">LIVE STATUS</div>'
                f'<div style="font-family:\'DM Sans\',sans-serif;font-size:12px;color:#F0F4FF;">Pending {badge_style}</div>'
                f'<div style="font-family:\'DM Sans\',sans-serif;font-size:12px;color:#FF4444;margin-top:4px;">High Urgency: {high}</div>'
                '</div>'
            )
            st.sidebar.markdown(live_status_html, unsafe_allow_html=True)
        except Exception:
            pass

    # Logout button
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        # Delete session from DB and URL
        sid = st.query_params.get("session")
        if sid:
            delete_session(sid)
            st.query_params.clear()
            
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.current_user = {}
        st.session_state.is_admin = False
        st.session_state.page = 'landing'
        st.rerun()

else:
    # Navigation for unauthenticated users
    st.sidebar.markdown("""
    <div style="padding:0.5rem 0;">
        <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#8B98B8;
            letter-spacing:0.04em;text-transform:uppercase;margin-bottom:8px;">
            NAVIGATION
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.page = 'landing'
        st.rerun()
    if st.sidebar.button("🏛️ Citizen Portal", use_container_width=True):
        st.session_state.page = 'user_auth'
        st.rerun()
    if st.sidebar.button("🛡️ Admin Login", use_container_width=True):
        st.session_state.page = 'agent_auth'
        st.rerun()
    if st.sidebar.button("👷 Worker Login", use_container_width=True):
        st.session_state.page = 'worker_auth'
        st.rerun()


# ─── ROUTING ─────────────────────────────────────────────────────────
page = st.session_state.page

if page == 'landing':
    show_landing_page()

elif page == 'user_auth':
    if st.session_state.authenticated and st.session_state.user_type == 'citizen':
        show_user_dashboard()
    else:
        show_user_auth()

elif page == 'agent_auth':
    if st.session_state.authenticated and st.session_state.user_type == 'agent':
        show_agent_dashboard()
    else:
        show_agent_auth()

elif page == 'worker_auth':
    if st.session_state.authenticated and st.session_state.user_type == 'worker':
        show_worker_dashboard()
    else:
        show_worker_auth()

else:
    show_landing_page()
