"""
CitiZen AI — Agent Control Center Dashboard
Four tabs: Active Queue, City Map, AI Intelligence, Analytics & Reports.
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime

from utils.ui_utils import (
    inject_global_css, section_header, stat_card, complaint_card,
    styled_success, styled_error, styled_warning, styled_info, empty_state
)
from utils.data_utils import (
    get_all_complaints, search_complaints, update_complaint_status,
    add_correction, get_correction_count_since_last_training,
    get_complaint_stats, get_complaints_with_coords,
    export_complaints_csv, get_model_versions, get_all_corrections,
    get_agent_leaderboard, get_daily_trend
)
from ml.model import CATEGORIES, check_and_retrain
from ml.model_tracker import (
    get_accuracy_chart, get_category_distribution_chart,
    get_urgency_donut, get_daily_trend_chart,
    get_resolution_by_category_chart, get_agent_leaderboard_chart
)

URGENCY_LEVELS = ["Low", "Medium", "High"]


def show_agent_dashboard():
    """Display the agent control center with 4 tabs."""
    inject_global_css()

    agent = st.session_state.get('current_user', {})
    agent_id = agent.get('agent_id', 'AGT0000')

    tab_queue, tab_map, tab_ai, tab_analytics = st.tabs([
        "📋 Active Queue",
        "🗺️ City Intelligence Map",
        "🧠 AI Intelligence Center",
        "📊 Analytics & Reports"
    ])

    # ═══════════════════════════════════════════════════════════════════
    # TAB 1: ACTIVE QUEUE
    # ═══════════════════════════════════════════════════════════════════
    with tab_queue:
        section_header("Complaint Intelligence Queue",
                       "AI-sorted by urgency and submission time",
                       accent="cyan")

        # Filters
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            status_f = st.selectbox("Status", ["All", "Pending", "In Progress", "Resolved"],
                                    key="aq_status")
        with f_col2:
            category_f = st.selectbox("Category", ["All"] + CATEGORIES, key="aq_cat")
        with f_col3:
            urgency_f = st.selectbox("Urgency", ["All", "High", "Medium", "Low"],
                                     key="aq_urg")
        with f_col4:
            search_f = st.text_input("🔍 Search", key="aq_search",
                                     placeholder="Search complaints...")

        # Fetch complaints
        complaints = search_complaints(
            term=search_f if search_f else None,
            status_filter=status_f,
            urgency_filter=urgency_f,
            category_filter=category_f
        )

        # Summary stats
        stats = get_complaint_stats()
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        with s_col1:
            active = stats.get('total', 0) - stats.get('resolved', 0)
            stat_card("Total Active", str(active), color="cyan", icon="📋")
        with s_col2:
            stat_card("High Urgency", str(stats.get('urgency_high', 0)),
                      color="red", icon="🔴")
        with s_col3:
            stat_card("In Progress", str(stats.get('in_progress', 0)),
                      color="amber", icon="🔄")
        with s_col4:
            stat_card("Resolved Today", str(stats.get('resolved_today', 0)),
                      color="green", icon="✅")

        st.markdown("<br>", unsafe_allow_html=True)

        if not complaints:
            empty_state("No complaints match your filters", icon="📭")
        else:
            for c in complaints:
                complaint_card(
                    complaint_id=c['id'],
                    category=c['category'],
                    description=c['description'],
                    urgency=c['ai_urgency'],
                    status=c['status'],
                    address=c.get('address', 'N/A'),
                    created_at=c.get('created_at', '')
                )

                with st.expander(f"Actions — #CMP-{c['id']:04d}"):
                    act_col1, act_col2, act_col3 = st.columns(3)

                    with act_col1:
                        if c['status'] == 'Pending':
                            if st.button("▶️ Start Work", key=f"start_{c['id']}"):
                                if update_complaint_status(c['id'], "In Progress",
                                                          agent_id, "Agent started work"):
                                    styled_success("Status → In Progress")
                                    st.rerun()

                    with act_col2:
                        if c['status'] in ['Pending', 'In Progress']:
                            if st.button("✅ Mark Resolved", key=f"resolve_{c['id']}"):
                                notes = st.session_state.get(f"resolve_notes_{c['id']}", "")
                                if update_complaint_status(c['id'], "Resolved",
                                                          agent_id, notes or "Issue resolved"):
                                    styled_success("Status → Resolved")
                                    st.rerun()

                    with act_col3:
                        if c['status'] == 'In Progress':
                            if st.button("⏸️ Pause", key=f"pause_{c['id']}"):
                                if update_complaint_status(c['id'], "Pending",
                                                          agent_id, "Paused by agent"):
                                    styled_info("Status → Pending")
                                    st.rerun()

                    # Resolution notes
                    if c['status'] in ['Pending', 'In Progress']:
                        st.text_input("Resolution notes", key=f"resolve_notes_{c['id']}",
                                      placeholder="Add notes about the resolution...")

                    # AI Correction section
                    st.markdown("---")
                    st.markdown(f"""
                    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;">
                        AI predicted: <strong style="color:#7C3AED;">{c['category']}</strong>
                        with <strong style="color:#00D4FF;">{c.get('ai_confidence', 0)*100:.0f}%</strong> confidence
                    </div>
                    """, unsafe_allow_html=True)

                    was_wrong = st.checkbox("⚠️ AI prediction was wrong",
                                            key=f"wrong_{c['id']}")
                    if was_wrong:
                        corr_col1, corr_col2 = st.columns(2)
                        with corr_col1:
                            correct_cat = st.selectbox(
                                "Correct category",
                                CATEGORIES,
                                key=f"corr_cat_{c['id']}"
                            )
                        with corr_col2:
                            correct_urg = st.selectbox(
                                "Correct urgency",
                                URGENCY_LEVELS,
                                key=f"corr_urg_{c['id']}"
                            )

                        if st.button("Submit Correction", key=f"submit_corr_{c['id']}"):
                            try:
                                success = add_correction(
                                    complaint_id=c['id'],
                                    original_prediction=c['category'],
                                    corrected_label=correct_cat,
                                    original_urgency=c['ai_urgency'],
                                    corrected_urgency=correct_urg,
                                    corrected_by=agent_id,
                                    image_path=c.get('image_path'),
                                    description=c.get('description'),
                                    category=correct_cat
                                )
                                if success:
                                    styled_success("Correction recorded! AI will learn from this.")

                                    # Check if retrain needed
                                    count = get_correction_count_since_last_training()
                                    if count >= 15:
                                        with st.spinner("🧠 Retraining model..."):
                                            result = check_and_retrain()
                                        if result.get('retrained'):
                                            styled_success(
                                                f"Model retrained! v{result['version']} — "
                                                f"Accuracy: {result['new_accuracy']*100:.1f}%")
                                    else:
                                        styled_info(
                                            f"{count}/15 corrections until next retraining")
                                else:
                                    styled_error("Failed to save correction")
                            except Exception as e:
                                styled_error(f"Error: {str(e)[:80]}")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 2: CITY INTELLIGENCE MAP
    # ═══════════════════════════════════════════════════════════════════
    with tab_map:
        section_header("Live Complaint Heatmap",
                       "Real-time geographic distribution of complaints",
                       accent="green")

        map_complaints = get_complaints_with_coords()

        if not map_complaints:
            empty_state("No geotagged complaints yet. Submit complaints with GPS-enabled photos!",
                        icon="🗺️")
            styled_info("Complaints with GPS coordinates or geocoded addresses will appear on the map.")
        else:
            view_mode = st.radio("View Mode", ["📍 Markers", "🔥 Heatmap"],
                                 horizontal=True, key="map_view")

            try:
                import folium
                from folium.plugins import MarkerCluster, HeatMap
                from streamlit_folium import st_folium

                # Center map on average coordinates
                avg_lat = sum(c['lat'] for c in map_complaints) / len(map_complaints)
                avg_lon = sum(c['lon'] for c in map_complaints) / len(map_complaints)

                m = folium.Map(
                    location=[avg_lat, avg_lon],
                    zoom_start=12,
                    tiles='CartoDB dark_matter'
                )

                if "Markers" in view_mode:
                    marker_cluster = MarkerCluster().add_to(m)

                    urgency_colors = {
                        'High': 'red',
                        'Medium': 'orange',
                        'Low': 'green'
                    }

                    for c in map_complaints:
                        color = urgency_colors.get(c['ai_urgency'], 'blue')
                        popup_html = f"""
                        <div style="font-family:sans-serif;min-width:200px;">
                            <strong style="color:#333;">#{c['id']:04d} — {c['category']}</strong><br>
                            <span style="color:#666;font-size:12px;">{c['description'][:100]}...</span><br>
                            <span style="color:{{'High':'red','Medium':'orange','Low':'green'}}.get(c['ai_urgency'],'blue');">
                                ● {c['ai_urgency']} Urgency</span><br>
                            <span style="font-size:11px;color:#999;">{c.get('address', 'N/A')}</span>
                        </div>
                        """
                        folium.Marker(
                            location=[c['lat'], c['lon']],
                            popup=folium.Popup(popup_html, max_width=300),
                            tooltip=f"#{c['id']:04d} - {c['category']}",
                            icon=folium.Icon(color=color, icon='info-sign')
                        ).add_to(marker_cluster)
                else:
                    # Heatmap view
                    heat_data = [[c['lat'], c['lon'],
                                  {'High': 3, 'Medium': 2, 'Low': 1}.get(c['ai_urgency'], 1)]
                                 for c in map_complaints]
                    HeatMap(
                        heat_data,
                        radius=20,
                        blur=15,
                        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 1: 'red'}
                    ).add_to(m)

                st_folium(m, use_container_width=True, height=500)

                # Map legend
                st.markdown("""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px;padding:1rem;margin-top:0.5rem;">
                    <span style="font-family:'Sora',sans-serif;font-size:12px;
                        font-weight:600;color:#F0F4FF;">Map Legend</span>
                    <div style="display:flex;gap:20px;margin-top:8px;">
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;">
                            🔴 <span style="color:#FF4444;">High Urgency</span></span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;">
                            🟠 <span style="color:#FFB800;">Medium Urgency</span></span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;">
                            🟢 <span style="color:#39FF14;">Low Urgency</span></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            except ImportError:
                styled_warning("Folium or streamlit-folium not installed. Run: pip install folium streamlit-folium")
            except Exception as e:
                styled_error(f"Map error: {str(e)[:100]}")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3: AI INTELLIGENCE CENTER
    # ═══════════════════════════════════════════════════════════════════
    with tab_ai:
        section_header("Model Performance",
                       "Self-learning system analytics — improves with every correction",
                       accent="purple")

        # Top stats
        versions = get_model_versions()
        corrections = get_all_corrections()
        stats = get_complaint_stats()
        correction_count = get_correction_count_since_last_training()

        ai_col1, ai_col2, ai_col3, ai_col4 = st.columns(4)
        with ai_col1:
            latest_acc = versions[-1]['accuracy'] * 100 if versions else 74.0
            stat_card("Current Accuracy", f"{latest_acc:.0f}%",
                      color="green", icon="🎯")
        with ai_col2:
            stat_card("Total Predictions", str(stats.get('total', 0)),
                      color="cyan", icon="🔮")
        with ai_col3:
            stat_card("Corrections", str(len(corrections)),
                      color="purple", icon="✏️")
        with ai_col4:
            current_v = versions[-1]['version_num'] if versions else 1
            stat_card("Model Version", f"v{current_v}",
                      color="amber", icon="📦")

        st.markdown("<br>", unsafe_allow_html=True)

        # Accuracy chart
        try:
            fig = get_accuracy_chart()
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            styled_warning(f"Chart error: {str(e)[:60]}")

        # Retrain status
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Retrain Status", accent="purple")

        progress = min(correction_count / 15.0, 1.0)
        st.markdown(f"""
        <div style="background:#111827;border:1px solid rgba(124,58,237,0.2);
            border-radius:12px;padding:1.25rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;
                margin-bottom:10px;">
                <span style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;">
                    {correction_count} corrections since last training. Retrains at 15.
                </span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                    color:#7C3AED;">{correction_count}/15</span>
            </div>
            <div style="background:rgba(255,255,255,0.05);border-radius:4px;height:6px;
                overflow:hidden;">
                <div style="background:linear-gradient(90deg,#7C3AED,#00D4FF);
                    height:100%;width:{progress*100:.0f}%;border-radius:4px;
                    transition:width 0.5s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if correction_count >= 15:
            st.markdown("""
            <div style="margin-top:8px;">
                <span style="font-family:'DM Sans',sans-serif;font-size:13px;
                    color:#39FF14;animation:glow-pulse 1.5s infinite;">
                    ✨ Ready to retrain! Click below to improve the model.
                </span>
            </div>
            """, unsafe_allow_html=True)

        retrain_col1, retrain_col2 = st.columns(2)
        with retrain_col1:
            if st.button("🔄 Manual Retrain", key="manual_retrain"):
                with st.spinner("🧠 Retraining model... This may take a few seconds."):
                    result = check_and_retrain()
                if result.get('retrained'):
                    styled_success(
                        f"Model retrained! New version: v{result['version']} — "
                        f"Accuracy: {result['new_accuracy']*100:.1f}%")
                    st.rerun()
                elif result.get('error'):
                    styled_error(f"Retrain failed: {result['error'][:80]}")
                else:
                    styled_info(
                        f"Not enough corrections yet ({result.get('correction_count', 0)}/15)")

        # Correction analysis
        if corrections:
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Correction Analysis", accent="purple")

            # Corrections by category
            corr_cats = {}
            for c in corrections:
                cat = c.get('corrected_label', 'Unknown')
                corr_cats[cat] = corr_cats.get(cat, 0) + 1

            corr_df = pd.DataFrame([
                {"category": k, "count": v} for k, v in corr_cats.items()
            ])

            if len(corr_df) > 0:
                try:
                    fig = get_category_distribution_chart(corr_df.to_dict('records'))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

            # Recent corrections table
            st.markdown("""
            <div style="margin:1rem 0 0.5rem;">
                <span style="font-family:'Sora',sans-serif;font-size:13px;font-weight:600;
                    color:#F0F4FF;">Recent Corrections</span>
            </div>
            """, unsafe_allow_html=True)

            recent = corrections[:10]
            for corr in recent:
                st.markdown(f"""
                <div style="background:rgba(124,58,237,0.05);border:1px solid rgba(124,58,237,0.15);
                    border-radius:8px;padding:10px 14px;margin-bottom:6px;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                    <div>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;
                            color:#8B98B8;">#CMP-{corr.get('complaint_id', 0):04d}</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#FF4444;margin-left:8px;">
                            {corr.get('original_prediction', '?')}</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#8B98B8;margin:0 4px;">→</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#39FF14;">
                            {corr.get('corrected_label', '?')}</span>
                    </div>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                        color:#4A5568;">{str(corr.get('corrected_at', ''))[:16]}</span>
                </div>
                """, unsafe_allow_html=True)

        # Model versions table
        if versions:
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("Model Version History", accent="cyan")

            for v in reversed(versions):
                acc_color = "#39FF14" if v['accuracy'] >= 0.8 else "#FFB800" if v['accuracy'] >= 0.6 else "#FF4444"
                st.markdown(f"""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                    border-radius:8px;padding:10px 14px;margin-bottom:6px;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                    <div>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:13px;
                            font-weight:600;color:#00D4FF;">v{v['version_num']}</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#8B98B8;margin-left:12px;">
                            {v['total_samples']} samples</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#8B98B8;margin-left:8px;">•</span>
                        <span style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:#8B98B8;margin-left:8px;">
                            {v.get('correction_samples', 0)} corrections</span>
                    </div>
                    <div>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:14px;
                            font-weight:600;color:{acc_color};">
                            {v['accuracy']*100:.1f}%</span>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                            color:#4A5568;margin-left:12px;">
                            {str(v.get('trained_at', ''))[:16]}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════
    # TAB 4: ANALYTICS & REPORTS
    # ═══════════════════════════════════════════════════════════════════
    with tab_analytics:
        section_header("Performance Analytics",
                       "Comprehensive data insights across all complaints",
                       accent="cyan")

        stats = get_complaint_stats()

        # KPI row
        k_col1, k_col2, k_col3, k_col4 = st.columns(4)
        with k_col1:
            stat_card("Total Complaints", str(stats.get('total', 0)),
                      color="cyan", icon="📊")
        with k_col2:
            stat_card("Resolved", str(stats.get('resolved', 0)),
                      color="green", icon="✅")
        with k_col3:
            stat_card("Pending", str(stats.get('pending', 0)),
                      color="amber", icon="⏳")
        with k_col4:
            avg_hrs = stats.get('avg_resolution_hours', 0)
            if avg_hrs > 24:
                avg_display = f"{avg_hrs/24:.1f}d"
            else:
                avg_display = f"{avg_hrs:.0f}h"
            stat_card("Avg Resolution", avg_display,
                      color="purple", icon="⏱️")

        st.markdown("<br>", unsafe_allow_html=True)

        # Charts row 1
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            section_header("Complaints by Category", accent="cyan")
            by_cat = stats.get('by_category', [])
            if by_cat:
                try:
                    fig = get_category_distribution_chart(by_cat)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    styled_info("Not enough data for category chart")
            else:
                styled_info("No complaint data yet")

        with chart_col2:
            section_header("Urgency Distribution", accent="red")
            high = stats.get('urgency_high', 0)
            medium = stats.get('urgency_medium', 0)
            low = stats.get('urgency_low', 0)
            try:
                fig = get_urgency_donut(high, medium, low)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                styled_info("Not enough data for urgency chart")

        # Charts row 2
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            section_header("Daily Trend (30 days)", accent="cyan")
            daily = get_daily_trend(30)
            if daily:
                try:
                    fig = get_daily_trend_chart(daily)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    styled_info("Not enough data for trend chart")
            else:
                styled_info("No daily trend data yet")

        with chart_col4:
            section_header("Agent Leaderboard", accent="green")
            agents = get_agent_leaderboard()
            if agents:
                try:
                    fig = get_agent_leaderboard_chart(agents)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    styled_info("Not enough data for leaderboard")
            else:
                styled_info("No agent data yet")

        # Export section
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Export Data", accent="cyan")

        exp_col1, exp_col2, exp_col3 = st.columns(3)
        with exp_col1:
            exp_status = st.selectbox("Status", ["All", "Pending", "In Progress", "Resolved"],
                                      key="exp_status")
        with exp_col2:
            exp_cat = st.selectbox("Category", ["All"] + CATEGORIES, key="exp_cat")
        with exp_col3:
            exp_urg = st.selectbox("Urgency", ["All", "High", "Medium", "Low"],
                                   key="exp_urg")

        if st.button("📥 Export as CSV", key="export_csv"):
            try:
                df = export_complaints_csv(
                    status_filter=exp_status if exp_status != "All" else None,
                    category_filter=exp_cat if exp_cat != "All" else None,
                    urgency_filter=exp_urg if exp_urg != "All" else None
                )
                if len(df) > 0:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV File",
                        data=csv,
                        file_name=f"citizen_ai_complaints_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                    styled_success(f"Export ready! {len(df)} records.")
                else:
                    styled_info("No complaints match the selected filters")
            except Exception as e:
                styled_error(f"Export error: {str(e)[:80]}")
