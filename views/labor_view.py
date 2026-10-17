# -*- coding: utf-8 -*-
"""
Labor View — Partogram + Bishop
واجهة متابعة المخاض + تقييم Bishop
"""
from datetime import datetime, date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from core.save_helper import save_button, mark_result
from services.partogram import (
    get_active_labor, list_active_labors, start_labor, end_labor,
    add_entry, list_entries, get_latest_entry, analyze_labor,
    LABOR_STATUS, AMNIOTIC_FLUID,
)
from services.bishop import calculate_bishop_score, save_bishop_assessment


# ============================================
# HELPERS
# ============================================

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_patients(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id,full_name,phone,lmp,edd")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _format_time(ts):
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return str(ts)[:16]


# ============================================
# TAB 1: ACTIVE LABORS
# ============================================

def _render_active_labors_tab(clinic, user):
    """List all active labors in clinic"""
    labors = list_active_labors(clinic["id"])

    if not labors:
        empty_state(
            "🤰",
            "لا يوجد مخاض نشط",
            "اختر حاملاً من التبويب التالي لبدء مخاض جديد"
        )
        return

    patients = _fetch_patients(clinic["id"])
    pmap = {p["id"]: p.get("full_name", "—") for p in patients}

    st.caption("📊 {} مخاض نشط".format(len(labors)))
    st.write("")

    for labor in labors:
        patient_name = pmap.get(labor["patient_id"], "—")

        # Analyze
        analysis = analyze_labor(clinic["id"], labor["id"])
        duration = analysis.get("duration_hours", 0)
        alerts = analysis.get("alerts", [])
        progress = analysis.get("progress", "no_data")

        # Progress icon
        progress_icon = {
            "normal": "🟢",
            "slow": "🟡",
            "arrest": "🔴",
            "no_data": "⚪",
        }.get(progress, "⚪")

        # Card
        alert_color = "#DC2626" if alerts else "#10B981"

        st.markdown("""
        <div style="background:white;border:2px solid {color};border-radius:14px;
                    padding:1.25rem 1.5rem;margin-bottom:0.75rem;
                    border-right:6px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:700;color:#0F172A;font-size:1.15rem;">
                        🤰 {patient}
                    </div>
                    <div style="color:#64748B;font-size:0.85rem;margin-top:0.3rem;">
                        ⏱️ المدة: {duration} ساعة &nbsp;|&nbsp;
                        📊 {entries} قياس &nbsp;|&nbsp;
                        {progress_icon} {progress_label}
                    </div>
                </div>
            </div>
            {alerts_html}
        </div>
        """.format(
            color=alert_color,
            patient=patient_name,
            duration=duration,
            entries=analysis.get("entries_count", 0),
            progress_icon=progress_icon,
            progress_label={
                "normal": "تقدم طبيعي",
                "slow": "بطيء",
                "arrest": "توقف",
                "no_data": "بدون بيانات",
            }.get(progress, "—"),
            alerts_html="".join([
                '<div style="background:#FEF2F2;border-radius:6px;padding:0.5rem 0.75rem;'
                'margin-top:0.5rem;font-size:0.85rem;color:#991B1B;">{}</div>'.format(a["message"])
                for a in alerts[:3]
            ]),
        ), unsafe_allow_html=True)

        # Actions
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("📋 فتح", key="open_labor_{}".format(labor["id"]),
                         use_container_width=True, type="primary"):
                st.session_state["_labor_view_id"] = labor["id"]
                st.session_state["_labor_view_patient"] = labor["patient_id"]
                st.rerun()
        with c2:
            if st.button("✅ إنهاء", key="end_labor_{}".format(labor["id"]),
                         use_container_width=True):
                end_labor(clinic["id"], labor["id"], status="completed")
                st.success("✅ تم إنهاء المخاض")

        st.write("")


# ============================================
# TAB 2: PARTOGRAM (Detailed view)
# ============================================

def _render_partogram_tab(clinic, user):
    """Detailed partogram view"""

    # Show active labor if selected
    labor_id = st.session_state.get("_labor_view_id")

    if labor_id:
        # Back button
        if st.button("← العودة للقائمة", key="back_from_partogram"):
            st.session_state.pop("_labor_view_id", None)
            st.session_state.pop("_labor_view_patient", None)
            st.rerun()

        _render_partogram_detail(clinic, user, labor_id)
        return

    # Start new labor
    section_header_v2("➕", "بدء مخاض جديد")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    selected_id = st.selectbox(
        "👩 اختر الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="labor_start_patient"
    )

    if st.button("🚀 بدء المخاض", type="primary", use_container_width=True,
                 key="start_labor_btn"):
        try:
            labor = start_labor(clinic["id"], selected_id,
                              doctor_id=user.get("id") if user else None)
            st.session_state["_labor_view_id"] = labor["id"]
            st.session_state["_labor_view_patient"] = selected_id
            st.success("✅ تم بدء المخاض")
        except Exception as e:
            st.error("❌ {}".format(str(e)[:200]))


def _render_partogram_detail(clinic, user, labor_id):
    """Show one labor in detail"""

    # Patient
    patient_id = st.session_state.get("_labor_view_patient")
    patients = _fetch_patients(clinic["id"])
    patient = next((p for p in patients if p["id"] == patient_id), {})

    if not patient:
        st.error("❌ المريضة غير موجودة")
        return

    # Analyze
    analysis = analyze_labor(clinic["id"], labor_id)
    if analysis.get("error"):
        st.error(analysis["error"])
        return

    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#F0FDF4 0%,#DCFCE7 100%);
                border-radius:12px;padding:1rem 1.25rem;
                border:1px solid #BBF7D0;margin-bottom:1rem;">
        <div style="font-weight:700;color:#0F172A;font-size:1.1rem;">
            🤰 {}
        </div>
        <div style="color:#166534;font-size:0.85rem;margin-top:0.3rem;">
            ⏱️ المدة: {} ساعة &nbsp;|&nbsp; 📊 {} قياس
        </div>
    </div>
    """.format(
        patient.get("full_name", "—"),
        analysis.get("duration_hours", 0),
        analysis.get("entries_count", 0),
    ), unsafe_allow_html=True)

    # Alerts
    alerts = analysis.get("alerts", [])
    if alerts:
        for a in alerts:
            color = "#DC2626" if a["level"] == "critical" else "#F59E0B"
            st.markdown("""
            <div style="background:{bg};border:1px solid {color};border-radius:10px;
                        padding:0.75rem 1rem;margin-bottom:0.5rem;
                        border-right:4px solid {color};">
                <div style="font-weight:700;color:{color};">
                    {msg}
                </div>
                <div style="color:#334155;font-size:0.85rem;margin-top:0.25rem;">
                    💡 {rec}
                </div>
            </div>
            """.format(
                bg="#FEF2F2" if a["level"] == "critical" else "#FFFBEB",
                color=color,
                msg=a["message"],
                rec=a["recommendation"],
            ), unsafe_allow_html=True)

    st.divider()

    # Add new entry
    with st.expander("➕ إضافة قياس جديد", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            dilatation = st.number_input(
                "التوسع (سم)",
                min_value=0.0, max_value=10.0,
                value=0.0, step=0.5, key="labor_dil"
            )
            station = st.selectbox(
                "المستوى (Station)",
                options=[-3, -2, -1, 0, 1, 2, 3],
                index=3,
                format_func=lambda x: "{}".format(x),
                key="labor_station"
            )
            effacement = st.number_input(
                "التلاشي (%)",
                min_value=0, max_value=100,
                value=0, step=10, key="labor_eff"
            )
        with c2:
            bp_sys = st.number_input("ضغط انقباضي", min_value=0, max_value=250,
                value=120, step=5, key="labor_sys")
            bp_dia = st.number_input("ضغط انبساطي", min_value=0, max_value=150,
                value=80, step=5, key="labor_dia")
            maternal_pulse = st.number_input("نبض الأم", min_value=0, max_value=200,
                value=80, step=5, key="labor_pulse")
            temperature = st.number_input("الحرارة (°C)", min_value=35.0, max_value=42.0,
                value=37.0, step=0.1, key="labor_temp")
        with c3:
            fhr = st.number_input("نبض الجنين", min_value=0, max_value=250,
                value=140, step=5, key="labor_fhr")
            amniotic = st.selectbox(
                "السائل الأمنيوسي",
                options=list(AMNIOTIC_FLUID.keys()),
                format_func=lambda x: AMNIOTIC_FLUID[x],
                key="labor_amniotic"
            )
            contractions = st.number_input("الانقباضات/10د", min_value=0, max_value=10,
                value=3, step=1, key="labor_contr")
            contr_duration = st.number_input("مدة الانقباضة (ث)", min_value=0, max_value=180,
                value=40, step=5, key="labor_contr_dur")

        notes = st.text_area("ملاحظات", height=68, key="labor_notes")

        if st.button("💾 حفظ القياس", type="primary", use_container_width=True,
                     key="labor_save_entry"):
            try:
                add_entry(clinic["id"], labor_id, {
                    "cervical_dilatation_cm": dilatation if dilatation > 0 else None,
                    "fetal_station": station,
                    "effacement_percent": effacement if effacement > 0 else None,
                    "bp_systolic": bp_sys if bp_sys > 0 else None,
                    "bp_diastolic": bp_dia if bp_dia > 0 else None,
                    "maternal_pulse": maternal_pulse if maternal_pulse > 0 else None,
                    "temperature": temperature if temperature > 0 else None,
                    "fetal_heart_rate": fhr if fhr > 0 else None,
                    "amniotic_fluid": amniotic,
                    "contractions_per_10min": contractions if contractions > 0 else None,
                    "contraction_duration_sec": contr_duration if contr_duration > 0 else None,
                    "notes": notes or None,
                })
                st.success("✅ تم حفظ القياس")
            except Exception as e:
                st.error("❌ {}".format(str(e)[:200]))

    # Entries + chart
    entries = list_entries(clinic["id"], labor_id, limit=100)

    if not entries:
        st.info("📭 لا توجد قياسات بعد")
        return

    st.divider()
    section_header_v2("📊", "منحنى المخاض (Partogram)")

    # Chart
    times = []
    dilations = []
    stations = []
    fhrs = []

    for e in entries:
        t = e.get("recorded_at")
        if not t:
            continue
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            times.append(dt.strftime("%H:%M"))
        except Exception:
            times.append("—")
        dilations.append(e.get("cervical_dilatation_cm"))
        stations.append(e.get("fetal_station"))
        fhrs.append(e.get("fetal_heart_rate"))

    # Dilatation chart
    if times and any(d is not None for d in dilations):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times,
            y=dilations,
            mode="lines+markers",
            name="التوسع (سم)",
            line=dict(color="#16A34A", width=3),
            marker=dict(size=12),
        ))

        # WHO alert line (1 cm/hour)
        fig.update_layout(
            title="📈 منحنى التوسع (Dilatation)",
            xaxis_title="الوقت",
            yaxis_title="التوسع (سم)",
            height=350,
            plot_bgcolor="white",
            yaxis=dict(range=[0, 10]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Table
    with st.expander("📋 الجدول الكامل"):
        rows = []
        for e in entries:
            rows.append({
                "الوقت": _format_time(e.get("recorded_at")),
                "التوسع": e.get("cervical_dilatation_cm") or "—",
                "المستوى": e.get("fetal_station") if e.get("fetal_station") is not None else "—",
                "التلاشي": e.get("effacement_percent") or "—",
                "BP": "{}/{}".format(e.get("bp_systolic", "—"), e.get("bp_diastolic", "—")),
                "نبض الجنين": e.get("fetal_heart_rate") or "—",
                "السائل": AMNIOTIC_FLUID.get(e.get("amniotic_fluid"), "—"),
                "انقباضات": e.get("contractions_per_10min") or "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================
# TAB 3: BISHOP SCORE
# ============================================

def _render_bishop_tab(clinic, user):
    """Bishop Score calculator"""

    section_header_v2("📏", "تقييم Bishop Score")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    selected_id = st.selectbox(
        "👩 اختر الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="bishop_patient"
    )

    st.divider()

    # Inputs
    c1, c2 = st.columns(2)
    with c1:
        dilatation = st.number_input("التوسع (سم)", min_value=0, max_value=10,
            value=2, step=1, key="bishop_dil")
        effacement = st.slider("التلاشي (%)", min_value=0, max_value=100,
            value=50, step=10, key="bishop_eff")
        station = st.selectbox("المستوى (Station)", options=[-3, -2, -1, 0, 1, 2, 3],
            index=3, key="bishop_station")

    with c2:
        consistency = st.selectbox(
            "قوام العنق",
            options=["firm", "medium", "soft"],
            format_func=lambda x: {"firm": "صلب", "medium": "متوسط", "soft": "لين"}[x],
            index=1,
            key="bishop_cons"
        )
        position = st.selectbox(
            "وضعية العنق",
            options=["posterior", "mid", "anterior"],
            format_func=lambda x: {"posterior": "خلفي", "mid": "متوسط", "anterior": "أمامي"}[x],
            index=1,
            key="bishop_pos"
        )

    # Calculate
    result = calculate_bishop_score(dilatation, effacement, station, consistency, position)

    st.divider()

    # Result
    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:16px;
                padding:1.5rem;border-right:8px solid {color};text-align:center;
                margin-bottom:1rem;">
        <div style="font-size:0.9rem;color:#64748B;font-weight:600;">
            Bishop Score
        </div>
        <div style="font-size:3rem;font-weight:900;color:{color};
                    line-height:1;margin:0.5rem 0;">
            {score}
        </div>
        <div style="font-size:1rem;color:#94A3B8;">من 13</div>
        <div style="font-size:1.1rem;font-weight:700;color:{color};margin-top:0.5rem;">
            {label}
        </div>
    </div>
    """.format(
        color=result["color"],
        score=result["score"],
        label=result["label"],
    ), unsafe_allow_html=True)

    # Components
    section_header_v2("📊", "تفصيل النقاط")

    for key, comp in result["components"].items():
        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;
                    padding:0.5rem 0.85rem;margin-bottom:0.3rem;
                    display:flex;justify-content:space-between;">
            <span style="color:#334155;">{label}</span>
            <span style="font-weight:700;color:#0F172A;">{score} / {max}</span>
        </div>
        """.format(
            label=comp["label"],
            score=comp["score"],
            max=comp["max"],
        ), unsafe_allow_html=True)

    # Interpretation
    st.divider()
    section_header_v2("💡", "التفسير")

    st.markdown("""
    <div style="background:#F0FDF4;border-radius:10px;padding:0.75rem 1rem;
                border-right:4px solid #16A34A;">
        {interp}
    </div>
    """.format(interp=result["interpretation"]), unsafe_allow_html=True)

    st.markdown("##### التوصيات")
    for r in result["recommendation"]:
        st.markdown("  - {}".format(r))

    # Save
    st.divider()
    if st.button("💾 حفظ التقييم", type="primary", use_container_width=True,
                 key="bishop_save"):
        try:
            save_bishop_assessment(
                clinic["id"], selected_id, result,
                doctor_id=user.get("id") if user else None
            )
            st.success("✅ تم حفظ التقييم")
        except Exception as e:
            st.error("❌ {}".format(str(e)[:200]))


# ============================================
# MAIN RENDER
# ============================================

@st.fragment
def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="متابعة المخاض",
        subtitle="Partogram + Bishop Score",
        icon="🤰",
    )

    tab1, tab2, tab3 = st.tabs([
        "📋 المخاض النشط",
        "📊 Partogram",
        "📏 Bishop Score",
    ])

    with tab1:
        _render_active_labors_tab(clinic, user)
    with tab2:
        _render_partogram_tab(clinic, user)
    with tab3:
        _render_bishop_tab(clinic, user)
