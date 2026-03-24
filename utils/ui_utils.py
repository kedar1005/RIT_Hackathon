"""
CitiZen AI — Reusable Styled UI Components
All visual components inject beautiful styled HTML via st.markdown()
"""
import streamlit as st


def inject_global_css():
    """Inject all global styles, fonts, animations"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-primary: #0A0E1A;
        --bg-card: #111827;
        --bg-elevated: #1C2333;
        --accent-cyan: #00D4FF;
        --accent-green: #39FF14;
        --accent-red: #FF4444;
        --accent-amber: #FFB800;
        --accent-purple: #7C3AED;
        --text-primary: #F0F4FF;
        --text-secondary: #8B98B8;
        --text-tertiary: #4A5568;
        --border: rgba(255,255,255,0.08);
        --glow-cyan: 0 0 20px rgba(0,212,255,0.3);
        --glow-red: 0 0 20px rgba(255,68,68,0.4);
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif !important;
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }

    /* Background grid pattern */
    .main > div {
        background-image:
            linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        background-color: var(--bg-primary);
    }

    /* Streamlit overrides */
    .stApp { background-color: var(--bg-primary) !important; }
    .stSidebar, section[data-testid="stSidebar"] {
        background-color: #080C16 !important;
        border-right: 1px solid var(--border);
    }
    .stButton > button {
        background: transparent !important;
        border: 1px solid var(--accent-cyan) !important;
        color: var(--accent-cyan) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.02em;
    }
    .stButton > button:hover {
        background: rgba(0,212,255,0.1) !important;
        box-shadow: 0 0 20px rgba(0,212,255,0.3) !important;
        transform: translateY(-1px) !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background-color: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 0 2px rgba(0,212,255,0.15) !important;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-card);
        border-radius: 10px;
        padding: 4px;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary) !important;
        font-family: 'DM Sans', sans-serif !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent-cyan) !important;
        background: var(--bg-elevated) !important;
        border-bottom-color: transparent !important;
    }

    /* DataFrames */
    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.3); border-radius: 3px; }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: rgba(10,14,26,0.8) !important;
        backdrop-filter: blur(10px);
    }

    /* Animations */
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,68,68,0.4); }
        50% { box-shadow: 0 0 0 8px rgba(255,68,68,0); }
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes glow-pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    @keyframes border-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-6px); }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-30px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes countUp {
        from { opacity: 0; transform: scale(0.5); }
        to { opacity: 1; transform: scale(1); }
    }

    .animate-fadeInUp { animation: fadeInUp 0.5s ease forwards; }
    .animate-fadeInUp-delay-1 { animation: fadeInUp 0.5s ease 0.1s forwards; opacity: 0; }
    .animate-fadeInUp-delay-2 { animation: fadeInUp 0.5s ease 0.2s forwards; opacity: 0; }
    .animate-fadeInUp-delay-3 { animation: fadeInUp 0.5s ease 0.3s forwards; opacity: 0; }
    .animate-fadeInUp-delay-4 { animation: fadeInUp 0.5s ease 0.4s forwards; opacity: 0; }
    .animate-float { animation: float 3s ease-in-out infinite; }
    .animate-slideInLeft { animation: slideInLeft 0.5s ease forwards; }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: var(--bg-card) !important;
        border: 1px dashed rgba(0,212,255,0.3) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Radio buttons */
    .stRadio > div {
        gap: 0.5rem !important;
    }
    .stRadio > div > label {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        color: var(--text-secondary) !important;
    }

    /* Selectbox */
    .stSelectbox [data-baseweb="select"] {
        background: var(--bg-elevated) !important;
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--accent-purple), var(--accent-cyan)) !important;
    }
    </style>
    """, unsafe_allow_html=True)


def hero_header(title, subtitle, badge_text=None):
    """Animated hero section with glowing title"""
    badge_html = ""
    if badge_text:
        badge_html = f'''<span style="background:rgba(0,212,255,0.15);
            border:1px solid rgba(0,212,255,0.3);color:#00D4FF;padding:4px 12px;
            border-radius:20px;font-size:12px;font-weight:500;letter-spacing:0.08em;
            font-family:'DM Sans',sans-serif;display:inline-block;margin-bottom:16px;">
            {badge_text}</span><br>'''
    st.markdown(f"""
    <div class="animate-fadeInUp" style="text-align:center;padding:3rem 1rem 2rem;">
        {badge_html}
        <h1 style="font-family:'Sora',sans-serif;font-size:clamp(2rem,5vw,3.5rem);font-weight:800;
            background:linear-gradient(135deg,#F0F4FF 0%,#00D4FF 50%,#7C3AED 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;margin:0 0 1rem;line-height:1.1;">
            {title}
        </h1>
        <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:1.1rem;
            max-width:600px;margin:0 auto;line-height:1.7;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)


def stat_card(label, value, delta=None, color="cyan", icon=""):
    """Metric card with glow effect"""
    colors = {
        "cyan": ("#00D4FF", "rgba(0,212,255,0.1)", "rgba(0,212,255,0.2)"),
        "green": ("#39FF14", "rgba(57,255,20,0.1)", "rgba(57,255,20,0.2)"),
        "red": ("#FF4444", "rgba(255,68,68,0.1)", "rgba(255,68,68,0.2)"),
        "amber": ("#FFB800", "rgba(255,184,0,0.1)", "rgba(255,184,0,0.2)"),
        "purple": ("#7C3AED", "rgba(124,58,237,0.1)", "rgba(124,58,237,0.2)"),
    }
    c, bg, border_c = colors.get(color, colors["cyan"])
    delta_html = ""
    if delta:
        delta_html = f'<span style="font-size:11px;color:{c};margin-top:4px;display:block;">{delta}</span>'
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border_c};border-radius:12px;
        padding:1.25rem;transition:all 0.2s ease;">
        <div style="font-size:11px;color:#8B98B8;font-weight:500;letter-spacing:0.06em;
            text-transform:uppercase;margin-bottom:8px;font-family:'DM Sans',sans-serif;">
            {icon} {label}
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:500;
            color:{c};line-height:1;">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def urgency_badge(urgency):
    """Color-coded urgency badge with glow"""
    config = {
        "High": ("#FF4444", "rgba(255,68,68,0.15)", "CRITICAL",
                 "animation:pulse-red 1.5s infinite;"),
        "Medium": ("#FFB800", "rgba(255,184,0,0.15)", "MODERATE", ""),
        "Low": ("#39FF14", "rgba(57,255,20,0.15)", "ROUTINE", ""),
        "CRITICAL": ("#FF4444", "rgba(255,68,68,0.25)", "CRITICAL",
                     "animation:pulse-red 1s infinite;"),
    }
    c, bg, label, anim = config.get(urgency, config["Low"])
    return f"""<span style="background:{bg};border:1px solid {c};color:{c};
        padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;
        letter-spacing:0.08em;font-family:'JetBrains Mono',monospace;{anim}
        display:inline-block;">
        {label}</span>"""


def status_badge(status):
    """Color-coded status badge"""
    config = {
        "Pending": ("#8B98B8", "rgba(139,152,184,0.1)"),
        "In Progress": ("#00D4FF", "rgba(0,212,255,0.1)"),
        "Resolved": ("#39FF14", "rgba(57,255,20,0.1)"),
        "CRITICAL": ("#FF4444", "rgba(255,68,68,0.2)"),
    }
    c, bg = config.get(status, config["Pending"])
    return f"""<span style="background:{bg};border:1px solid {c}40;color:{c};
        padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500;
        font-family:'DM Sans',sans-serif;display:inline-block;">{status}</span>"""


def complaint_card(complaint_id, category, description, urgency, status,
                   address, created_at, show_actions=False, agent_id=None):
    """Full complaint card with all styling"""
    urg_badge = urgency_badge(urgency)
    stat_badge = status_badge(status)
    border_color = {
        "High": "rgba(255,68,68,0.3)",
        "Medium": "rgba(255,184,0,0.2)",
        "Low": "rgba(57,255,20,0.15)"
    }.get(urgency, "rgba(255,255,255,0.08)")

    desc_display = description[:180] + ('...' if len(description) > 180 else '')
    addr_display = address[:50] + ('...' if len(str(address)) > 50 else '') if address else 'N/A'
    time_display = str(created_at)[:16] if created_at else ''

    st.markdown(f"""
    <div style="background:#111827;border:1px solid {border_color};border-radius:12px;
        padding:1.25rem;margin-bottom:0.75rem;transition:all 0.2s ease;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
            margin-bottom:0.75rem;flex-wrap:wrap;gap:8px;">
            <div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:11px;
                    color:#8B98B8;">#CMP-{complaint_id:04d}</span>
                <h4 style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                    color:#F0F4FF;margin:4px 0 0;">{category}</h4>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;">
                {urg_badge} {stat_badge}
            </div>
        </div>
        <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:13px;
            line-height:1.6;margin:0 0 0.75rem;
            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
            overflow:hidden;">
            {desc_display}
        </p>
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;">
            <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
                📍 {addr_display}
            </span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#4A5568;">
                {time_display}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def ai_prediction_result(category, urgency, confidence, resolution_time,
                         method="text"):
    """Dramatic AI prediction result display"""
    urg_color = {"High": "#FF4444", "Medium": "#FFB800", "Low": "#39FF14"}.get(urgency, "#00D4FF")
    method_label = "Image AI + Text AI" if method == "dual" else "Text AI" if method == "text" else "Image AI"
    conf_pct = confidence * 100 if confidence <= 1 else confidence
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(124,58,237,0.1),rgba(0,212,255,0.05));
        border:1px solid rgba(124,58,237,0.3);border-radius:16px;padding:1.5rem;
        margin:1rem 0;position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;right:0;width:120px;height:120px;
            background:radial-gradient(circle,rgba(124,58,237,0.15),transparent);
            border-radius:50%;transform:translate(30%,-30%);"></div>
        <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;
            color:#7C3AED;font-family:'DM Sans',sans-serif;margin-bottom:0.75rem;">
            ◆ AI ANALYSIS COMPLETE — {method_label}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">
            <div>
                <div style="font-size:11px;color:#8B98B8;margin-bottom:4px;
                    font-family:'DM Sans',sans-serif;">DETECTED ISSUE</div>
                <div style="font-family:'Sora',sans-serif;font-size:16px;font-weight:600;
                    color:#F0F4FF;">{category}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#8B98B8;margin-bottom:4px;
                    font-family:'DM Sans',sans-serif;">URGENCY LEVEL</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                    font-weight:600;color:{urg_color};">{urgency.upper()}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#8B98B8;margin-bottom:4px;
                    font-family:'DM Sans',sans-serif;">AI CONFIDENCE</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                    font-weight:600;color:#00D4FF;">{conf_pct:.0f}%</div>
            </div>
        </div>
        <div style="margin-top:1rem;padding-top:1rem;
            border-top:1px solid rgba(255,255,255,0.06);">
            <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;">
                Estimated resolution:
                <span style="color:#00D4FF;font-weight:500;">{resolution_time}</span>
            </span>
        </div>
        <div style="margin-top:0.75rem;background:rgba(255,255,255,0.05);
            border-radius:4px;height:4px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#7C3AED,#00D4FF);
                height:100%;width:{conf_pct:.0f}%;border-radius:4px;
                transition:width 1s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title, subtitle=None, accent="cyan"):
    """Section divider with accent line"""
    colors = {"cyan": "#00D4FF", "purple": "#7C3AED", "green": "#39FF14", "red": "#FF4444"}
    c = colors.get(accent, "#00D4FF")
    sub = ""
    if subtitle:
        sub = f'<p style="font-family:\'DM Sans\',sans-serif;color:#8B98B8;font-size:13px;margin:4px 0 0;">{subtitle}</p>'
    st.markdown(f"""
    <div style="margin:1.5rem 0 1rem;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:3px;height:24px;background:{c};border-radius:2px;
                box-shadow:0 0 10px {c}80;"></div>
            <div>
                <h3 style="font-family:'Sora',sans-serif;font-size:16px;font-weight:600;
                    color:#F0F4FF;margin:0;">{title}</h3>
                {sub}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def sidebar_logo():
    """Styled sidebar header"""
    st.sidebar.markdown("""
    <div style="padding:1rem 0 1.5rem;text-align:center;
        border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:1rem;">
        <div style="font-family:'Sora',sans-serif;font-size:22px;font-weight:800;
            background:linear-gradient(135deg,#00D4FF,#7C3AED);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;">CitiZen AI</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#4A5568;
            letter-spacing:0.06em;margin-top:2px;">SMART CITY PLATFORM</div>
    </div>
    """, unsafe_allow_html=True)


def styled_success(message):
    """Beautiful success message"""
    st.markdown(f"""
    <div style="background:rgba(57,255,20,0.08);border:1px solid rgba(57,255,20,0.25);
        border-radius:12px;padding:1rem 1.25rem;margin:0.5rem 0;
        display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">✅</span>
        <span style="font-family:'DM Sans',sans-serif;color:#39FF14;font-size:14px;
            font-weight:500;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def styled_error(message):
    """Beautiful error message"""
    st.markdown(f"""
    <div style="background:rgba(255,68,68,0.08);border:1px solid rgba(255,68,68,0.25);
        border-radius:12px;padding:1rem 1.25rem;margin:0.5rem 0;
        display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">⚠️</span>
        <span style="font-family:'DM Sans',sans-serif;color:#FF4444;font-size:14px;
            font-weight:500;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def styled_warning(message):
    """Beautiful warning message"""
    st.markdown(f"""
    <div style="background:rgba(255,184,0,0.08);border:1px solid rgba(255,184,0,0.25);
        border-radius:12px;padding:1rem 1.25rem;margin:0.5rem 0;
        display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">🔔</span>
        <span style="font-family:'DM Sans',sans-serif;color:#FFB800;font-size:14px;
            font-weight:500;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def styled_info(message):
    """Beautiful info message"""
    st.markdown(f"""
    <div style="background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);
        border-radius:12px;padding:1rem 1.25rem;margin:0.5rem 0;
        display:flex;align-items:center;gap:10px;">
        <span style="font-size:20px;">ℹ️</span>
        <span style="font-family:'DM Sans',sans-serif;color:#00D4FF;font-size:14px;
            font-weight:500;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def loading_shimmer(height=60):
    """Loading skeleton shimmer animation"""
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#1C2333 25%,#2A3347 50%,#1C2333 75%);
        background-size:200% 100%;animation:shimmer 1.5s infinite;
        border-radius:8px;height:{height}px;margin:8px 0;"></div>
    """, unsafe_allow_html=True)


def empty_state(message, icon="🔍"):
    """Empty state illustration"""
    st.markdown(f"""
    <div style="text-align:center;padding:3rem 1rem;">
        <div style="font-size:48px;margin-bottom:16px;animation:float 3s ease-in-out infinite;">
            {icon}
        </div>
        <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:15px;
            max-width:400px;margin:0 auto;">{message}</p>
    </div>
    """, unsafe_allow_html=True)
