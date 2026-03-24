"""
CitiZen AI — Animated Landing Page
Stunning hero section, features grid, how-it-works, and role selection.
"""
import streamlit as st
from utils.ui_utils import inject_global_css


def show_landing_page():
    """Display the animated landing page."""
    inject_global_css()

    # ─── HERO SECTION ──────────────────────────────────────────────────
    st.markdown("""
    <style>
        @keyframes particle-float {
            0%, 100% { transform: translateY(0) translateX(0); opacity: 0.4; }
            25% { transform: translateY(-20px) translateX(10px); opacity: 0.7; }
            50% { transform: translateY(-40px) translateX(-5px); opacity: 0.5; }
            75% { transform: translateY(-20px) translateX(15px); opacity: 0.6; }
        }
        .hero-bg {
            position: relative;
            padding: 4rem 1rem 2rem;
            text-align: center;
            overflow: hidden;
        }
        .hero-bg::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background:
                radial-gradient(circle at 20% 50%, rgba(0,212,255,0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 50%, rgba(124,58,237,0.08) 0%, transparent 50%);
            z-index: 0;
        }
        .hero-particles {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            z-index: 0;
        }
        .particle {
            position: absolute;
            width: 3px; height: 3px;
            background: #00D4FF;
            border-radius: 50%;
            animation: particle-float 6s ease-in-out infinite;
        }
        .particle:nth-child(1) { top: 20%; left: 15%; animation-delay: 0s; }
        .particle:nth-child(2) { top: 60%; left: 25%; animation-delay: 1s; background: #7C3AED; }
        .particle:nth-child(3) { top: 30%; left: 70%; animation-delay: 2s; }
        .particle:nth-child(4) { top: 70%; left: 80%; animation-delay: 3s; background: #39FF14; }
        .particle:nth-child(5) { top: 40%; left: 45%; animation-delay: 4s; background: #7C3AED; }
        .particle:nth-child(6) { top: 80%; left: 55%; animation-delay: 1.5s; }
        .particle:nth-child(7) { top: 15%; left: 85%; animation-delay: 2.5s; background: #FFB800; }
        .particle:nth-child(8) { top: 55%; left: 10%; animation-delay: 3.5s; }
    </style>

    <div class="hero-bg">
        <div class="hero-particles">
            <div class="particle"></div><div class="particle"></div>
            <div class="particle"></div><div class="particle"></div>
            <div class="particle"></div><div class="particle"></div>
            <div class="particle"></div><div class="particle"></div>
        </div>
        <div style="position:relative;z-index:1;">
            <div class="animate-fadeInUp" style="margin-bottom:16px;">
                <span style="background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.25);
                    color:#00D4FF;padding:6px 16px;border-radius:20px;font-size:11px;
                    font-weight:600;letter-spacing:0.1em;font-family:'DM Sans',sans-serif;">
                    🏆 RIT HACKATHON 2K26 — MCA TRACK
                </span>
            </div>
            <h1 class="animate-fadeInUp-delay-1" style="font-family:'Sora',sans-serif;
                font-size:clamp(2.5rem,6vw,4.5rem);font-weight:800;margin:24px 0 16px;
                line-height:1.05;
                background:linear-gradient(135deg,#F0F4FF 0%,#00D4FF 40%,#7C3AED 100%);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;">
                CitiZen AI
            </h1>
            <p class="animate-fadeInUp-delay-2" style="font-family:'DM Sans',sans-serif;
                color:#8B98B8;font-size:1.15rem;max-width:560px;margin:0 auto 2rem;
                line-height:1.7;">
                AI-Powered Smart City Complaint Intelligence Platform —
                Report. Detect. Resolve. Faster.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CTA Buttons
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        if st.button("🏛️ Report an Issue", use_container_width=True, key="hero_citizen"):
            st.session_state.page = 'user_auth'
            st.rerun()

    # ─── STAT STRIP ───────────────────────────────────────────────────
    st.markdown("""
    <div class="animate-fadeInUp-delay-3" style="display:flex;justify-content:center;
        gap:24px;flex-wrap:wrap;padding:1.5rem 0 2rem;margin-top:0.5rem;">
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;
            letter-spacing:0.04em;">8 Issue Categories</span>
        <span style="color:#1C2333;">•</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            AI-Powered Detection</span>
        <span style="color:#1C2333;">•</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            Real-Time Mapping</span>
        <span style="color:#1C2333;">•</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            Self-Learning Model</span>
        <span style="color:#1C2333;">•</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            GPS Auto-Detection</span>
        <span style="color:#1C2333;">•</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            Duplicate Prevention</span>
    </div>
    """, unsafe_allow_html=True)

    # ─── FEATURES GRID ────────────────────────────────────────────────
    st.markdown("""
    <div style="margin:1rem 0 0.5rem;">
        <h2 style="font-family:'Sora',sans-serif;font-size:22px;font-weight:700;
            color:#F0F4FF;text-align:center;margin-bottom:0.5rem;">
            Powered by Intelligence
        </h2>
        <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:14px;
            text-align:center;margin-bottom:2rem;">
            Six cutting-edge capabilities in one platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    features = [
        ("#00D4FF", "🧠", "Dual AI Engine",
         "CNN image analysis + NLP text classification working together for accurate issue detection"),
        ("#7C3AED", "📈", "Self-Learning Model",
         "Model improves with every agent correction — accuracy rises automatically over time"),
        ("#39FF14", "🗺️", "Real-Time Map",
         "Live heatmap visualizing city-wide complaint density with color-coded urgency markers"),
        ("#FFB800", "⚡", "Smart Priority",
         "Emergency keyword override + ML-based scoring — critical issues surface instantly"),
        ("#FF4444", "🛡️", "Duplicate Shield",
         "MD5 image hashing prevents repeated submissions — keeps the queue clean"),
        ("#00D4FF", "📍", "GPS Auto-Tag",
         "Automatic EXIF GPS extraction from photos + Nominatim address geocoding"),
    ]

    for row_start in range(0, 6, 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            idx = row_start + i
            if idx < len(features):
                border_color, icon, title, desc = features[idx]
                with col:
                    st.markdown(f"""
                    <div class="animate-fadeInUp-delay-{i+1}" style="
                        background:rgba(17,24,39,0.6);
                        backdrop-filter:blur(12px);
                        border:1px solid rgba(255,255,255,0.06);
                        border-top:2px solid {border_color};
                        border-radius:12px;padding:1.5rem;
                        min-height:180px;margin-bottom:1rem;
                        transition:all 0.2s ease;">
                        <div style="font-size:28px;margin-bottom:12px;">{icon}</div>
                        <h4 style="font-family:'Sora',sans-serif;font-size:15px;
                            font-weight:600;color:#F0F4FF;margin:0 0 8px;">
                            {title}
                        </h4>
                        <p style="font-family:'DM Sans',sans-serif;font-size:13px;
                            color:#8B98B8;line-height:1.6;margin:0;">
                            {desc}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

    # ─── HOW IT WORKS ──────────────────────────────────────────────────
    st.markdown("""
    <div style="margin:3rem 0 1rem;">
        <h2 style="font-family:'Sora',sans-serif;font-size:22px;font-weight:700;
            color:#F0F4FF;text-align:center;margin-bottom:0.5rem;">
            How It Works
        </h2>
        <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:14px;
            text-align:center;margin-bottom:2rem;">
            From report to resolution in four intelligent steps
        </p>
    </div>
    """, unsafe_allow_html=True)

    steps = [
        ("01", "📸", "Upload Photo", "Snap or upload a photo of the issue", "#00D4FF"),
        ("02", "🧠", "AI Analyzes", "Dual-model classifies category & urgency", "#7C3AED"),
        ("03", "📡", "Auto-Routes", "Smart queue prioritizes and assigns agent", "#FFB800"),
        ("04", "✅", "Track Resolution", "Real-time status updates until resolved", "#39FF14"),
    ]

    step_cols = st.columns(4)
    for i, col in enumerate(step_cols):
        num, icon, title, desc, color = steps[i]
        with col:
            st.markdown(f"""
            <div class="animate-fadeInUp-delay-{i+1}" style="text-align:center;padding:1rem 0.5rem;">
                <div style="width:48px;height:48px;border-radius:50%;
                    background:rgba({','.join(str(int(color.lstrip('#')[j:j+2], 16)) for j in (0,2,4))},0.15);
                    border:1px solid {color}40;display:flex;align-items:center;
                    justify-content:center;margin:0 auto 12px;font-size:22px;">
                    {icon}
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                    color:{color};letter-spacing:0.1em;margin-bottom:4px;">STEP {num}</div>
                <h4 style="font-family:'Sora',sans-serif;font-size:14px;font-weight:600;
                    color:#F0F4FF;margin:0 0 6px;">{title}</h4>
                <p style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    line-height:1.5;margin:0;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # ─── ROLE SELECTION (Citizen Focus) ────────────────────────────────
    st.markdown("""
    <div style="margin:3rem 0 1rem;">
        <h2 style="font-family:'Sora',sans-serif;font-size:22px;font-weight:700;
            color:#F0F4FF;text-align:center;margin-bottom:2rem;">
            Join the Smart City Movement
        </h2>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div style="background:rgba(17,24,39,0.6);backdrop-filter:blur(12px);
            border:1px solid rgba(0,212,255,0.2);border-radius:16px;padding:2rem;
            text-align:center;transition:all 0.2s ease;max-width:600px;margin:0 auto 1.5rem;">
            <div style="font-size:48px;margin-bottom:16px;">🏛️</div>
            <h3 style="font-family:'Sora',sans-serif;font-size:20px;font-weight:700;
                color:#00D4FF;margin:0 0 12px;">I'm a Citizen</h3>
            <p style="font-family:'DM Sans',sans-serif;color:#8B98B8;font-size:13px;
                line-height:1.6;margin:0 0 16px;">
                Report civic issues in your neighbourhood — potholes, garbage,
                broken lights, water problems, and more.
            </p>
            <ul style="text-align:left;list-style:none;padding:0;margin:0 0 16px;max-width:320px;margin-left:auto;margin-right:auto;">
                <li style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    padding:4px 0;">✦ AI-powered issue classification</li>
                <li style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    padding:4px 0;">✦ Photo upload with GPS detection</li>
                <li style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    padding:4px 0;">✦ Real-time status tracking</li>
                <li style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    padding:4px 0;">✦ Rate resolution quality</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        c_col1, c_col2, c_col3 = st.columns([1.2, 1, 1.2])
        with c_col2:
            if st.button("Report Issues →", use_container_width=True, key="role_citizen"):
                st.session_state.page = 'user_auth'
                st.rerun()

    # ─── FOOTER ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:3rem 0 1rem;border-top:1px solid rgba(255,255,255,0.05);
        margin-top:3rem;">
        <p style="font-family:'DM Sans',sans-serif;font-size:12px;color:#4A5568;">
            Built for RIT Hackathon 2K26 • CitiZen AI • Powered by ML & Computer Vision
        </p>
    </div>
    """, unsafe_allow_html=True)
