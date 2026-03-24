"""
CitiZen AI — Citizen Dashboard
Three tabs: Submit Complaint, My Complaints, Help & Guidelines.
"""
import os
import streamlit as st
from datetime import datetime
from PIL import Image

from utils.ui_utils import (
    inject_global_css, section_header, stat_card, complaint_card,
    ai_prediction_result, styled_success, styled_error, styled_warning,
    styled_info, empty_state
)
from utils.data_utils import (
    add_complaint, get_user_complaints, get_complaint_by_id,
    check_duplicate, add_feedback
)
from utils.geo_utils import (
    extract_gps_from_image, geocode_address, get_image_hash,
    get_image_hash_from_bytes
)
from ml.model import predict_full, CATEGORIES
from ml.image_model import dual_predict

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "uploaded_images")

CATEGORY_OPTIONS = [
    "🛣️ Roads & Potholes",
    "💡 Streetlight & Electricity",
    "🗑️ Garbage & Waste Management",
    "💧 Water Supply Issues",
    "🌊 Drainage & Water Logging",
    "🌳 Tree Fall & Maintenance",
    "🚗 Traffic & Parking",
    "🛡️ Public Safety & Others"
]

URGENCY_OPTIONS = ["Low", "Medium", "High"]


def _clean_category(cat_with_emoji):
    """Strip emoji prefix from category string."""
    parts = cat_with_emoji.split(" ", 1)
    return parts[1] if len(parts) > 1 else cat_with_emoji


def show_user_dashboard():
    """Display the citizen portal with 3 tabs."""
    inject_global_css()

    user = st.session_state.get('current_user', {})
    user_id = user.get('id', 1)

    tab_submit, tab_my, tab_help = st.tabs([
        "📝 Submit Complaint",
        "📋 My Complaints",
        "❓ Help & Guidelines"
    ])

    # ─── TAB 1: SUBMIT COMPLAINT ──────────────────────────────────────
    with tab_submit:
        section_header("Report a Civic Issue",
                       "Upload a photo and describe the problem for AI analysis",
                       accent="cyan")

        with st.form("complaint_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                category_sel = st.selectbox("Issue Category", CATEGORY_OPTIONS)
                user_urgency = st.selectbox("Your Perceived Urgency", URGENCY_OPTIONS,
                                            index=1)
                address = st.text_input("📍 Address / Location",
                                        placeholder="e.g., MG Road, near City Hospital")
            with col2:
                landmark = st.text_input("🏢 Nearest Landmark (optional)",
                                         placeholder="e.g., opposite SBI Bank")
                description = st.text_area(
                    "📝 Describe the Issue",
                    placeholder="Provide details: what's the problem, how severe, any hazards...",
                    height=120
                )

            st.markdown("---")
            st.markdown("""
            <p style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;
                margin-bottom:8px;">📸 Upload a photo of the issue (optional but recommended)</p>
            """, unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Upload Photo",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed"
            )

            camera_input = st.camera_input("Or take a photo with your camera")

            submitted = st.form_submit_button("🔍 Submit & Analyze with AI →",
                                              use_container_width=True)

        if submitted:
            category = _clean_category(category_sel)

            if not description or len(description.strip()) < 10:
                styled_error("Please provide a detailed description (at least 10 characters)")
            elif not address:
                styled_error("Please provide an address or location")
            else:
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                image_path = None
                image_hash = None
                lat, lon = None, None

                # Handle image
                img_source = uploaded_file or camera_input
                if img_source:
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"complaint_{user_id}_{timestamp}.jpg"
                        image_path = os.path.join(UPLOAD_DIR, filename)

                        img_bytes = img_source.getvalue()
                        with open(image_path, "wb") as f:
                            f.write(img_bytes)

                        image_hash = get_image_hash_from_bytes(img_bytes)

                        # Check for duplicates
                        if image_hash and check_duplicate(image_hash):
                            styled_warning("⚠️ Duplicate detected! A similar complaint with the same photo already exists. Submitting anyway for review.")

                        # Extract GPS from EXIF
                        exif_lat, exif_lon = extract_gps_from_image(image_path)
                        if exif_lat and exif_lon:
                            lat, lon = exif_lat, exif_lon
                            styled_info(f"📍 GPS auto-detected from photo: {lat:.4f}, {lon:.4f}")
                    except Exception as e:
                        styled_warning(f"Image processing note: {str(e)[:80]}")

                # Geocode address if no GPS from image
                if lat is None and address:
                    try:
                        geo_lat, geo_lon = geocode_address(address)
                        if geo_lat and geo_lon:
                            lat, lon = geo_lat, geo_lon
                    except Exception:
                        pass

                # AI Prediction
                with st.spinner("🧠 AI analyzing your complaint..."):
                    try:
                        result = dual_predict(description, category, image_path)
                    except Exception:
                        result = predict_full(description, category)

                # Show AI result
                ai_prediction_result(
                    category=result.get('category', category),
                    urgency=result.get('urgency', 'Medium'),
                    confidence=result.get('confidence', 0.7),
                    resolution_time=result.get('resolution_time', '2 days'),
                    method=result.get('method', 'text')
                )

                # Map category to worker department
                CATEGORY_TO_DEPT = {
                    "Roads & Potholes": "Roads & Infrastructure",
                    "Streetlight & Electricity": "Electricity & Streetlights",
                    "Garbage & Waste Management": "Sanitation & Waste",
                    "Water Supply Issues": "Water Supply",
                    "Drainage & Water Logging": "Drainage & Sewerage",
                    "Tree Fall & Maintenance": "Parks & Tree Maintenance",
                    "Traffic & Parking": "Traffic Management",
                    "Public Safety & Others": "Public Safety & General"
                }
                dept = CATEGORY_TO_DEPT.get(result.get('category', category), "Public Safety & General")

                # Save to database
                try:
                    complaint_id = add_complaint(
                        user_id=user_id,
                        category=result.get('category', category),
                        description=description,
                        address=address,
                        landmark=landmark,
                        image_path=image_path,
                        image_hash=image_hash,
                        lat=lat,
                        lon=lon,
                        ai_urgency=result.get('urgency', 'Medium'),
                        user_urgency=user_urgency,
                        ai_confidence=result.get('confidence', 0.0),
                        ai_method=result.get('method', 'text'),
                        estimated_resolution=result.get('resolution_time', ''),
                        department=dept
                    )

                    if complaint_id:
                        styled_success(
                            f"Complaint submitted! Your tracking ID: #CMP-{complaint_id:04d}")
                    else:
                        styled_error("Failed to save complaint. Please try again.")
                except Exception as e:
                    styled_error(f"Database error: {str(e)[:80]}")

    # ─── TAB 2: MY COMPLAINTS ──────────────────────────────────────────
    with tab_my:
        section_header("My Complaints", "Track the status of your submitted issues")

        complaints = get_user_complaints(user_id)

        if not complaints:
            empty_state("No complaints yet. Your city looks great! 🌆", icon="🎉")
        else:
            # Filters
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                status_filter = st.selectbox("Status Filter",
                                             ["All", "Pending", "In Progress", "Resolved"],
                                             key="my_status_filter")
            with filter_col2:
                urgency_filter = st.selectbox("Urgency Filter",
                                              ["All", "High", "Medium", "Low"],
                                              key="my_urgency_filter")
            with filter_col3:
                search_term = st.text_input("🔍 Search", placeholder="Search your complaints...",
                                            key="my_search")

            # Apply filters
            filtered = complaints
            if status_filter != "All":
                filtered = [c for c in filtered if c['status'] == status_filter]
            if urgency_filter != "All":
                filtered = [c for c in filtered if c['ai_urgency'] == urgency_filter]
            if search_term:
                term = search_term.lower()
                filtered = [c for c in filtered if
                            term in c.get('description', '').lower() or
                            term in c.get('category', '').lower() or
                            term in c.get('address', '').lower()]

            # Stats row
            s_col1, s_col2, s_col3, s_col4 = st.columns(4)
            with s_col1:
                stat_card("Total Filed", str(len(complaints)), color="cyan", icon="📋")
            with s_col2:
                pending = len([c for c in complaints if c['status'] == 'Pending'])
                stat_card("Pending", str(pending), color="amber", icon="⏳")
            with s_col3:
                in_prog = len([c for c in complaints if c['status'] == 'In Progress'])
                stat_card("In Progress", str(in_prog), color="cyan", icon="🔄")
            with s_col4:
                resolved = len([c for c in complaints if c['status'] == 'Resolved'])
                stat_card("Resolved", str(resolved), color="green", icon="✅")

            st.markdown("<br>", unsafe_allow_html=True)

            # Complaint list
            for c in filtered:
                complaint_card(
                    complaint_id=c['id'],
                    category=c['category'],
                    description=c['description'],
                    urgency=c['ai_urgency'],
                    status=c['status'],
                    address=c.get('address', 'N/A'),
                    created_at=c.get('created_at', '')
                )

                # Expandable details
                with st.expander(f"View details — #CMP-{c['id']:04d}"):
                    detail = get_complaint_by_id(c['id'])
                    if detail:
                        d_col1, d_col2 = st.columns(2)
                        with d_col1:
                            st.markdown(f"""
                            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;">
                                <strong style="color:#F0F4FF;">AI Confidence:</strong>
                                {detail.get('ai_confidence', 0)*100:.0f}%<br>
                                <strong style="color:#F0F4FF;">Method:</strong>
                                {detail.get('ai_method', 'text').upper()}<br>
                                <strong style="color:#F0F4FF;">Est. Resolution:</strong>
                                {detail.get('estimated_resolution', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)
                        with d_col2:
                            if detail.get('lat') and detail.get('lon'):
                                st.markdown(f"""
                                <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;">
                                    <strong style="color:#F0F4FF;">GPS:</strong>
                                    {detail['lat']:.4f}, {detail['lon']:.4f}<br>
                                    <strong style="color:#F0F4FF;">Landmark:</strong>
                                    {detail.get('landmark', 'N/A')}<br>
                                    <strong style="color:#F0F4FF;">Agent:</strong>
                                    {detail.get('assigned_agent', 'Not assigned')}
                                </div>
                                """, unsafe_allow_html=True)

                        # Status history timeline
                        history = detail.get('history', [])
                        if history:
                            st.markdown("""
                            <div style="margin-top:12px;padding-top:12px;
                                border-top:1px solid rgba(255,255,255,0.06);">
                                <span style="font-family:'Sora',sans-serif;font-size:12px;
                                    font-weight:600;color:#F0F4FF;">Status Timeline</span>
                            </div>
                            """, unsafe_allow_html=True)
                            for h in history:
                                color = {"Pending": "#8B98B8", "In Progress": "#00D4FF",
                                         "Resolved": "#39FF14"}.get(h['new_status'], "#8B98B8")
                                st.markdown(f"""
                                <div style="display:flex;align-items:flex-start;gap:10px;
                                    padding:6px 0;border-left:2px solid {color};
                                    padding-left:12px;margin-left:4px;">
                                    <div>
                                        <span style="font-family:'DM Sans',sans-serif;
                                            font-size:12px;color:{color};font-weight:500;">
                                            {h['new_status']}</span>
                                        <span style="font-family:'JetBrains Mono',monospace;
                                            font-size:10px;color:#4A5568;margin-left:8px;">
                                            {str(h.get('changed_at', ''))[:16]}</span>
                                        <br>
                                        <span style="font-family:'DM Sans',sans-serif;
                                            font-size:11px;color:#8B98B8;">
                                            {h.get('change_reason', '')}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                        # Feedback for resolved complaints
                        if c['status'] == 'Resolved':
                            st.markdown("---")
                            st.markdown("""
                            <span style="font-family:'Sora',sans-serif;font-size:13px;
                                font-weight:600;color:#39FF14;">Rate this resolution</span>
                            """, unsafe_allow_html=True)
                            rating = st.slider(
                                "Rating", 1, 5, 4,
                                key=f"rating_{c['id']}"
                            )
                            comment = st.text_input(
                                "Comment (optional)",
                                key=f"comment_{c['id']}"
                            )
                            if st.button("Submit Feedback", key=f"fb_{c['id']}"):
                                if add_feedback(c['id'], user_id, rating, comment):
                                    styled_success("Thank you for your feedback!")
                                else:
                                    styled_error("Could not save feedback")

    # ─── TAB 3: HELP & GUIDELINES ──────────────────────────────────────
    with tab_help:
        section_header("Help & Guidelines",
                       "Everything you need to know about using CitiZen AI")

        # Types of issues
        st.markdown("""
        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
            border-radius:12px;padding:1.5rem;margin-bottom:1rem;">
            <h4 style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                color:#00D4FF;margin:0 0 12px;">📋 What Issues Can You Report?</h4>
            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;line-height:1.8;">
                • <strong style="color:#F0F4FF;">Roads & Potholes</strong> — Potholes, broken roads, missing manhole covers<br>
                • <strong style="color:#F0F4FF;">Streetlight & Electricity</strong> — Broken lights, exposed wires, pole damage<br>
                • <strong style="color:#F0F4FF;">Garbage & Waste</strong> — Overflowing bins, illegal dumping, missed collection<br>
                • <strong style="color:#F0F4FF;">Water Supply</strong> — Pipe bursts, no water, contamination<br>
                • <strong style="color:#F0F4FF;">Drainage</strong> — Blocked drains, waterlogging, sewage overflow<br>
                • <strong style="color:#F0F4FF;">Tree Maintenance</strong> — Fallen trees, dangerous branches, uprooting<br>
                • <strong style="color:#F0F4FF;">Traffic & Parking</strong> — Signal faults, illegal parking, missing signs<br>
                • <strong style="color:#F0F4FF;">Public Safety</strong> — Stray animals, unsafe structures, fire hazards
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#111827;border:1px solid rgba(124,58,237,0.2);
            border-radius:12px;padding:1.5rem;margin-bottom:1rem;">
            <h4 style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                color:#7C3AED;margin:0 0 12px;">🧠 How Does AI Analysis Work?</h4>
            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;line-height:1.8;">
                CitiZen AI uses a <strong style="color:#F0F4FF;">dual-model system</strong>:<br><br>
                <strong style="color:#00D4FF;">Text AI (NLP)</strong> — Analyzes your description using
                TF-IDF vectorization + Random Forest classifier trained on 135+ complaint patterns.<br><br>
                <strong style="color:#7C3AED;">Image AI (CNN)</strong> — MobileNetV3 deep learning model
                analyzes uploaded photos to detect issue type from visual patterns.<br><br>
                Both models work together. If the image model has high confidence (>70%),
                its prediction takes priority. Emergency keywords like "fire", "flood",
                or "collapse" automatically override to HIGH urgency.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#111827;border:1px solid rgba(57,255,20,0.15);
            border-radius:12px;padding:1.5rem;margin-bottom:1rem;">
            <h4 style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                color:#39FF14;margin:0 0 12px;">📸 Tips for Better Photos</h4>
            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;line-height:1.8;">
                • Take photos in daylight for best AI accuracy<br>
                • Show the full extent of the problem (zoom out)<br>
                • Include nearby landmarks for context<br>
                • Keep GPS enabled on your phone for automatic location tagging<br>
                • Avoid blurry photos — hold your phone steady
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#111827;border:1px solid rgba(255,184,0,0.2);
            border-radius:12px;padding:1.5rem;">
            <h4 style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                color:#FFB800;margin:0 0 12px;">⏱️ Expected Resolution Times</h4>
            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;line-height:1.8;">
                <strong style="color:#FF4444;">HIGH urgency:</strong> 2-6 hours (safety-critical issues)<br>
                <strong style="color:#FFB800;">MEDIUM urgency:</strong> 1-4 days (inconvenience issues)<br>
                <strong style="color:#39FF14;">LOW urgency:</strong> 3-7 days (maintenance requests)
            </div>
        </div>
        """, unsafe_allow_html=True)
