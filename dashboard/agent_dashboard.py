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
    get_complaint_stats, get_complaints_with_coords, get_available_cities_with_coords,
    export_complaints_csv, get_model_versions, get_all_corrections,
    get_agent_leaderboard, get_daily_trend, add_agent,
    get_tickets_for_admin, get_unread_count_admin, mark_tickets_read_admin,
    get_tickets_by_department, get_unread_count_worker, mark_tickets_read_worker,
    get_all_workers, warn_worker, unblock_worker, get_departments_without_active_workers,
    is_worker_blocked
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

    # Build tab list — add 'Add Agents' and 'Inbox' only for admin
    unread_admin = get_unread_count_admin()
    inbox_label = f"📥 Inbox ({unread_admin})" if unread_admin > 0 else "📥 Inbox"
    tab_labels = [
        "📋 Active Queue",
        "🗺️ City Intelligence Map",
        "🧠 AI Intelligence Center",
        "📊 Analytics & Reports",
        inbox_label
    ]
    if st.session_state.get('is_admin', False):
        tab_labels.append("➕ Add Agents")

    tabs = st.tabs(tab_labels)
    tab_queue = tabs[0]
    tab_map = tabs[1]
    tab_ai = tabs[2]
    tab_analytics = tabs[3]
    tab_inbox = tabs[4]
    tab_add_agents = tabs[5] if st.session_state.get('is_admin', False) else None

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

        city_options = ["All"] + get_available_cities_with_coords()
        default_end = datetime.now().date()
        default_start = default_end.replace(day=1)

        map_filter_col1, map_filter_col2, map_filter_col3 = st.columns([1.2, 1, 1])
        with map_filter_col1:
            selected_city = st.selectbox("City", city_options, key="map_city_filter")
        with map_filter_col2:
            date_from = st.date_input("From Date", value=default_start, key="map_date_from")
        with map_filter_col3:
            date_to = st.date_input("To Date", value=default_end, key="map_date_to")

        if date_from > date_to:
            styled_error("Map filter error: 'From Date' cannot be after 'To Date'.")
            map_complaints = []
        else:
            map_complaints = get_complaints_with_coords(
                city_filter=selected_city,
                date_from=date_from,
                date_to=date_to
            )

        if not map_complaints:
            empty_state("No geotagged complaints found for the selected city/date filters.",
                        icon="🗺️")
            styled_info("Try a different city or widen the date range.")
        else:
            styled_info(
                f"Showing {len(map_complaints)} mapped complaints for "
                f"{selected_city if selected_city != 'All' else 'all cities'} "
                f"from {date_from} to {date_to}."
            )
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

                st_folium(m, width=None, height=500)

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

            except ImportError as ie:
                styled_warning(f"Missing library: {ie}. Run: pip install folium streamlit-folium")
            except Exception as e:
                styled_error(f"Map error: {str(e)[:200]}")

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

    # ═══════════════════════════════════════════════════════════════════
    # TAB 5: ADD AGENTS + WORKER MANAGEMENT (ADMIN ONLY)
    # ═══════════════════════════════════════════════════════════════════
    if tab_add_agents is not None:
        with tab_add_agents:
            section_header("Manage Workers",
                           "Register new agents and manage warnings / blocks",
                           accent="purple")

            # ── REGISTER NEW AGENT ──
            with st.expander("➕ Register New Agent", expanded=True):
                st.markdown("""
                <p style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                    margin-bottom:8px;">Fill in agent details and assign a department</p>
                """, unsafe_allow_html=True)

                with st.form("admin_register_agent_form", clear_on_submit=True):
                    from auth.agent_auth import DEPARTMENTS, _hash_password, _validate_agent_id

                    reg_name = st.text_input("Full Name", placeholder="Officer Rahul Mehta")
                    reg_agent_id = st.text_input("Agent ID", placeholder="AGT0002")
                    reg_department = st.selectbox("Assign Department", DEPARTMENTS)
                    reg_password = st.text_input("Create Password", type="password",
                                                 placeholder="Min 6 characters")
                    reg_confirm = st.text_input("Confirm Password", type="password")
                    reg_submitted = st.form_submit_button("Register Agent →",
                                                           use_container_width=True)

                    if reg_submitted:
                        if not all([reg_name, reg_agent_id, reg_password, reg_confirm]):
                            styled_error("Please fill in all fields")
                        elif not _validate_agent_id(reg_agent_id):
                            styled_error("Agent ID must be AGT followed by 4 digits (e.g., AGT0002)")
                        elif reg_password != reg_confirm:
                            styled_error("Passwords do not match")
                        elif len(reg_password) < 6:
                            styled_error("Password must be at least 6 characters")
                        else:
                            password_hash = _hash_password(reg_password)
                            result = add_agent(reg_name, reg_agent_id, password_hash, reg_department)
                            if result:
                                styled_success(f"Agent {reg_agent_id} ({reg_department}) registered successfully!")
                            else:
                                styled_error("Agent ID already registered.")

            # ── WORKER WARNING & BLOCK MANAGEMENT ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-family:'Sora',sans-serif;font-size:15px;font-weight:600;
                color:#F0F4FF;margin-bottom:12px;">⚠️ Worker Warning & Block Management</div>
            """, unsafe_allow_html=True)

            all_workers = get_all_workers()
            if not all_workers:
                st.info("No workers registered yet.")
            else:
                for w in all_workers:
                    is_blocked = bool(w.get('is_blocked', 0))
                    warn_count = int(w.get('warning_count', 0) or 0)
                    status_color = "#FF4444" if is_blocked else "#39FF14"
                    status_label = "🔴 Blocked" if is_blocked else "🟢 Active"

                    wk_col1, wk_col2, wk_col3, wk_col4 = st.columns([3, 2, 2, 2])
                    with wk_col1:
                        st.markdown(f"""
                        <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#F0F4FF;">
                            <strong>{w['name']}</strong>
                            <span style="font-size:11px;color:#8B98B8;"> — {w['agent_id']}</span><br>
                            <span style="font-size:11px;color:#4A5568;">{w['department']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with wk_col2:
                        st.markdown(f"""
                        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;
                            color:{status_color};padding-top:8px;">{status_label}</div>
                        """, unsafe_allow_html=True)
                    with wk_col3:
                        warn_color = "#FF4444" if warn_count >= 2 else "#F59E0B" if warn_count == 1 else "#8B98B8"
                        st.markdown(f"""
                        <div style="font-family:'DM Sans',sans-serif;font-size:12px;
                            color:{warn_color};padding-top:8px;">⚠️ {warn_count}/3 warnings</div>
                        """, unsafe_allow_html=True)
                    with wk_col4:
                        if is_blocked:
                            if st.button("🔓 Unblock", key=f"unblock_{w['agent_id']}"):
                                unblock_worker(w['agent_id'])
                                styled_success(f"{w['name']} unblocked and warnings reset.")
                                st.rerun()
                        else:
                            if st.button("⚠️ Warn", key=f"warn_{w['agent_id']}"):
                                new_count, now_blocked = warn_worker(w['agent_id'])
                                if now_blocked:
                                    styled_warning(f"⛔ {w['name']} has been automatically BLOCKED after {new_count} warnings.")
                                elif new_count is not None:
                                    styled_warning(f"Warning {new_count}/3 issued to {w['name']}.")
                                st.rerun()
                    st.markdown("<hr style='border-color:rgba(255,255,255,0.05);margin:6px 0;'>",
                                unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════
    # TAB 6: INBOX (ALL USERS — ADMIN VIEW)
    # ═══════════════════════════════════════════════════════════════════
    with tab_inbox:
        section_header("📥 Inbox — Citizen Tickets",
                       "Messages raised by citizens about their complaints",
                       accent="cyan")

        tickets = get_tickets_for_admin()
        mark_tickets_read_admin()  # Mark all as read when inbox is opened

        # ── Department health alerts ──
        empty_depts = get_departments_without_active_workers()
        for dept in empty_depts:
            st.markdown(f"""
            <div style="background:rgba(255,68,68,0.08);border:1px solid rgba(255,68,68,0.3);
                border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.5rem;
                display:flex;align-items:center;gap:10px;">
                <span style="font-size:1.2rem;">⚠️</span>
                <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#FF8585;">
                    <strong>No active workers</strong> in <strong>{dept}</strong>.
                    Please create a new worker or unblock an existing worker.
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not tickets:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#8B98B8;
                font-family:'DM Sans',sans-serif;">
                📭 No tickets yet. Inbox is empty.
            </div>
            """, unsafe_allow_html=True)
        else:
            for t in tickets:
                status_color = "#39FF14" if t['status'] == 'Closed' else "#00D4FF"
                st.markdown(f"""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    border-radius:12px;padding:1rem;margin-bottom:0.75rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span style="font-family:'Sora',sans-serif;font-size:13px;font-weight:600;
                            color:#F0F4FF;">🎫 Ticket #{t['id']} — Complaint #CMP-{t['complaint_id']:04d}</span>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                            color:{status_color};border:1px solid {status_color};
                            padding:2px 8px;border-radius:20px;">{t['status']}</span>
                    </div>
                    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                        margin-bottom:6px;">
                        🏷️ Dept: <strong style="color:#F0F4FF;">{t.get('department','—')}</strong>
                        &nbsp;&nbsp;👤 User ID: <strong style="color:#F0F4FF;">{t['user_id']}</strong>
                        &nbsp;&nbsp;🕒 <strong style="color:#4A5568;">{str(t.get('created_at',''))[:16]}</strong>
                    </div>
                    <div style="font-family:'Inter',sans-serif;font-size:13px;color:#C1C8E4;
                        background:rgba(0,212,255,0.05);border-left:3px solid #00D4FF;
                        padding:8px 12px;border-radius:4px;">
                        {t['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def show_worker_dashboard():
    """Display worker dashboard — department-filtered complaint queue only."""
    inject_global_css()

    worker = st.session_state.get('current_user', {})
    worker_id = worker.get('agent_id', 'AGT0000')
    worker_dept = worker.get('department', '')

    if not worker_dept:
        styled_warning("No department assigned to your account. Contact your admin.")
        return

    # ── Block check: if blocked, show message and stop ──
    if is_worker_blocked(worker_id):
        st.markdown("""
        <div style="background:rgba(255,68,68,0.08);border:1px solid rgba(255,68,68,0.3);
            border-radius:12px;padding:2rem;text-align:center;margin-top:2rem;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">⛔</div>
            <div style="font-family:'Sora',sans-serif;font-size:18px;font-weight:700;
                color:#FF4444;margin-bottom:0.5rem;">Account Temporarily Blocked</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#8B98B8;">
                Your account has been temporarily blocked by admin after receiving 3 warnings.<br>
                Please contact your administrator to resolve this.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Build worker tabs with unread notification badge
    unread_worker = get_unread_count_worker(worker_dept)
    inbox_label_w = f"📥 Inbox ({unread_worker})" if unread_worker > 0 else "📥 Inbox"
    w_tab_queue, w_tab_inbox = st.tabs([f"📋 {worker_dept} — Complaint Queue", inbox_label_w])

    # ── WORKER TAB 1: COMPLAINT QUEUE ──
    with w_tab_queue:
        section_header(
            f"📋 {worker_dept} — Complaint Queue",
            f"Showing complaints assigned to your department: {worker_dept}",
            accent="cyan"
        )

    # Filters
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        status_f = st.selectbox("Status", ["All", "Pending", "In Progress", "Resolved"],
                                key="wq_status")
    with f_col2:
        urgency_f = st.selectbox("Urgency", ["All", "High", "Medium", "Low"],
                                 key="wq_urg")
    with f_col3:
        search_f = st.text_input("🔍 Search", key="wq_search",
                                 placeholder="Search complaints...")

    # Fetch department-filtered complaints
    complaints = search_complaints(
        term=search_f if search_f else None,
        status_filter=status_f,
        urgency_filter=urgency_f,
        department_filter=worker_dept.strip()
    )

    # Summary stats
    total = len(complaints)
    pending = len([c for c in complaints if c['status'] == 'Pending'])
    high = len([c for c in complaints if c.get('ai_urgency') == 'High'])
    resolved = len([c for c in complaints if c['status'] == 'Resolved'])

    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        stat_card("Total", str(total), color="cyan", icon="📋")
    with s_col2:
        stat_card("Pending", str(pending), color="amber", icon="⏳")
    with s_col3:
        stat_card("High Urgency", str(high), color="red", icon="🔴")
    with s_col4:
        stat_card("Resolved", str(resolved), color="green", icon="✅")

    st.markdown("<br>", unsafe_allow_html=True)

    if not complaints:
        empty_state(f"No complaints in {worker_dept} department", icon="📭")
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
                        if st.button("▶️ Start Work", key=f"w_start_{c['id']}"):
                            if update_complaint_status(c['id'], "In Progress",
                                                      worker_id, "Worker started work"):
                                styled_success("Status → In Progress")
                                st.rerun()

                with act_col2:
                    if c['status'] in ['Pending', 'In Progress']:
                        if st.button("✅ Mark Resolved", key=f"w_resolve_{c['id']}"):
                            notes = st.session_state.get(f"w_resolve_notes_{c['id']}", "")
                            if update_complaint_status(c['id'], "Resolved",
                                                      worker_id, notes or "Issue resolved"):
                                styled_success("Status → Resolved")
                                st.rerun()

                with act_col3:
                    if c['status'] == 'In Progress':
                        if st.button("⏸️ Pause", key=f"w_pause_{c['id']}"):
                            if update_complaint_status(c['id'], "Pending",
                                                      worker_id, "Paused by worker"):
                                styled_info("Status → Pending")
                                st.rerun()

                # Resolution notes
                if c['status'] in ['Pending', 'In Progress']:
                    st.text_input("Resolution notes", key=f"w_resolve_notes_{c['id']}",
                                  placeholder="Add notes about the resolution...")

    # ── WORKER TAB 2: INBOX ──
    with w_tab_inbox:
        section_header("📥 Inbox — Your Department's Tickets",
                       f"Messages from citizens in: {worker_dept}",
                       accent="cyan")

        w_tickets = get_tickets_by_department(worker_dept)
        mark_tickets_read_worker(worker_dept)  # Mark as read on open

        if not w_tickets:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#8B98B8;
                font-family:'DM Sans',sans-serif;">
                📭 No tickets for your department yet.
            </div>
            """, unsafe_allow_html=True)
        else:
            for t in w_tickets:
                status_color = "#39FF14" if t['status'] == 'Closed' else "#00D4FF"
                st.markdown(f"""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    border-radius:12px;padding:1rem;margin-bottom:0.75rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span style="font-family:'Sora',sans-serif;font-size:13px;font-weight:600;
                            color:#F0F4FF;">🎫 Ticket #{t['id']} — Complaint #CMP-{t['complaint_id']:04d}</span>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                            color:{status_color};border:1px solid {status_color};
                            padding:2px 8px;border-radius:20px;">{t['status']}</span>
                    </div>
                    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#8B98B8;
                        margin-bottom:6px;">
                        👤 User ID: <strong style="color:#F0F4FF;">{t['user_id']}</strong>
                        &nbsp;&nbsp;🕒 <strong style="color:#4A5568;">{str(t.get('created_at',''))[:16]}</strong>
                    </div>
                    <div style="font-family:'Inter',sans-serif;font-size:13px;color:#C1C8E4;
                        background:rgba(0,212,255,0.05);border-left:3px solid #00D4FF;
                        padding:8px 12px;border-radius:4px;">
                        {t['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
