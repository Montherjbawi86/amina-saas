# -*- coding: utf-8 -*-
"""Render alerts across the app"""
import streamlit as st


ALERT_COLORS = {
    "critical": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#DC2626"},
    "high": {"bg": "#FEF2F2", "fg": "#991B1B", "border": "#EF4444"},
    "medium": {"bg": "#FFFBEB", "fg": "#92400E", "border": "#F59E0B"},
    "low": {"bg": "#F0FDF4", "fg": "#065F46", "border": "#10B981"},
}


def render_alert_card(alert, compact=False):
    """Render a single alert card"""
    cfg = ALERT_COLORS.get(alert["level"], ALERT_COLORS["low"])

    if compact:
        st.markdown("""
        <div style="background:{bg}; padding:0.5rem 0.75rem; border-radius:8px; border-right:3px solid {border}; margin-bottom:0.4rem; display:flex; align-items:center; gap:0.5rem;">
            <span>{icon}</span>
            <span style="font-weight:600; color:{fg}; font-size:0.85rem;">{title}</span>
            <span style="color:{fg}; font-size:0.8rem; opacity:0.8;">— {msg}</span>
        </div>
        """.format(
            bg=cfg["bg"], border=cfg["border"], fg=cfg["fg"],
            icon=alert["icon"], title=alert["title"], msg=alert["message"]
        ), unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:{bg}; padding:1rem 1.25rem; border-radius:12px; border-right:5px solid {border}; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.4rem;">
                <span style="font-size:1.5rem;">{icon}</span>
                <span style="font-weight:700; color:{fg}; font-size:1rem;">{title}</span>
            </div>
            <div style="color:{fg}; font-size:0.9rem; margin-bottom:0.5rem;">{msg}</div>
            <div style="color:{fg}; font-size:0.85rem; opacity:0.85;">💡 {action}</div>
        </div>
        """.format(
            bg=cfg["bg"], border=cfg["border"], fg=cfg["fg"],
            icon=alert["icon"], title=alert["title"],
            msg=alert["message"], action=alert.get("action", "")
        ), unsafe_allow_html=True)


def render_patient_alerts(patient, visits):
    """Render alerts for a single patient (used in patient detail)"""
    from services.alerts import analyze_patient_alerts

    alerts = analyze_patient_alerts(patient, visits)

    if not alerts:
        st.success("✅ لا توجد تنبيهات طبية حالياً")
        return

    # Count by level
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in alerts:
        counts[a["level"]] = counts.get(a["level"], 0) + 1

    st.markdown("### 🔔 تنبيهات طبية ({})".format(len(alerts)))

    # Summary chips
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if counts["critical"]:
            st.markdown('<div style="background:#DC2626; color:white; padding:0.5rem; border-radius:8px; text-align:center;"><b>🚨 {}</b><br><small>حرج</small></div>'.format(counts["critical"]), unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#F3F4F6; color:#9CA3AF; padding:0.5rem; border-radius:8px; text-align:center;"><b>🚨 0</b><br><small>حرج</small></div>', unsafe_allow_html=True)
    with c2:
        if counts["high"]:
            st.markdown('<div style="background:#EF4444; color:white; padding:0.5rem; border-radius:8px; text-align:center;"><b>🔴 {}</b><br><small>عالي</small></div>'.format(counts["high"]), unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#F3F4F6; color:#9CA3AF; padding:0.5rem; border-radius:8px; text-align:center;"><b>🔴 0</b><br><small>عالي</small></div>', unsafe_allow_html=True)
    with c3:
        if counts["medium"]:
            st.markdown('<div style="background:#F59E0B; color:white; padding:0.5rem; border-radius:8px; text-align:center;"><b>🟡 {}</b><br><small>متوسط</small></div>'.format(counts["medium"]), unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#F3F4F6; color:#9CA3AF; padding:0.5rem; border-radius:8px; text-align:center;"><b>🟡 0</b><br><small>متوسط</small></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div style="background:#F3F4F6; color:#6B7280; padding:0.5rem; border-radius:8px; text-align:center;"><b>📊 {}</b><br><small>إجمالي</small></div>'.format(len(alerts)), unsafe_allow_html=True)

    st.write("")

    # Detailed cards
    for a in alerts:
        render_alert_card(a)


def render_clinic_alerts_dashboard(clinic, patients, visits_by_patient, limit=5):
    """Render alerts summary for dashboard"""
    from services.alerts import get_clinic_alerts, count_alerts_by_level

    all_alerts = get_clinic_alerts(clinic["id"], patients, visits_by_patient)

    if not all_alerts:
        st.success("✅ لا توجد تنبيهات طبية عبر العيادة")
        return

    counts = count_alerts_by_level(all_alerts)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        color = "#DC2626" if counts["critical"] else "#F3F4F6"
        text_color = "white" if counts["critical"] else "#9CA3AF"
        st.markdown('<div style="background:{}; color:{}; padding:1rem; border-radius:12px; text-align:center;"><div style="font-size:2rem; font-weight:800;">{}</div><div style="font-size:0.8rem;">🚨 حرج</div></div>'.format(color, text_color, counts["critical"]), unsafe_allow_html=True)
    with c2:
        color = "#EF4444" if counts["high"] else "#F3F4F6"
        text_color = "white" if counts["high"] else "#9CA3AF"
        st.markdown('<div style="background:{}; color:{}; padding:1rem; border-radius:12px; text-align:center;"><div style="font-size:2rem; font-weight:800;">{}</div><div style="font-size:0.8rem;">🔴 عالي</div></div>'.format(color, text_color, counts["high"]), unsafe_allow_html=True)
    with c3:
        color = "#F59E0B" if counts["medium"] else "#F3F4F6"
        text_color = "white" if counts["medium"] else "#9CA3AF"
        st.markdown('<div style="background:{}; color:{}; padding:1rem; border-radius:12px; text-align:center;"><div style="font-size:2rem; font-weight:800;">{}</div><div style="font-size:0.8rem;">🟡 متوسط</div></div>'.format(color, text_color, counts["medium"]), unsafe_allow_html=True)
    with c4:
        st.markdown('<div style="background:#0EA5A0; color:white; padding:1rem; border-radius:12px; text-align:center;"><div style="font-size:2rem; font-weight:800;">{}</div><div style="font-size:0.8rem;">📊 حوامل</div></div>'.format(len(all_alerts)), unsafe_allow_html=True)

    st.write("")

    # Show patients with alerts
    st.markdown("#### 🚨 حالات تحتاج انتباه")

    for item in all_alerts[:limit]:
        with st.expander("👩 **{}** — {} تنبيه{}".format(
            item["patient_name"],
            len(item["alerts"]),
            "" if len(item["alerts"]) == 1 else "ات"
        ), expanded=True):
            for a in item["alerts"]:
                render_alert_card(a, compact=True)

            if st.button("📋 فتح الملف", key="alert_open_" + item["patient_id"]):
                st.session_state["selected_patient_id"] = item["patient_id"]
                st.session_state["patient_view"] = "detail"
                st.session_state["nav_to_patients"] = True
                st.rerun()


def top_navbar_alert_badge(count):
    """Render alert badge for navbar"""
    if count > 0:
        return '<span style="background:#DC2626; color:white; padding:0.25rem 0.6rem; border-radius:999px; font-size:0.75rem; font-weight:700; margin-right:0.5rem;">🔔 {}</span>'.format(count)
    return ""
