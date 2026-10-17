# -*- coding: utf-8 -*-
"""
Fetal Growth Charts View
منحنيات نمو الجنين + معايير WHO
"""
from datetime import date, datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from services.growth import (
    create_measurement, update_measurement, list_measurements,
    delete_measurement, analyze_measurement, get_who_curve,
    get_patient_chart_data, get_patient_summary,
)


# ============================================
# HELPERS
# ============================================

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


def _gest_age_display(week):
    if not week:
        return "—"
    return "أسبوع {}".format(int(week))


# ============================================
# CHART BUILDER
# ============================================

def _build_growth_chart(measure_type, patient_data, title, unit, color="#16A34A"):
    """Build a plotly chart: WHO reference + patient measurements"""

    curve = get_who_curve(measure_type)
    if not curve:
        return None

    fig = go.Figure()

    # Patient data
    weeks_p = patient_data.get("weeks", [])
    values_p = patient_data.get(measure_type, [])

    # Filter out None values
    filtered = [(w, v) for w, v in zip(weeks_p, values_p) if v is not None]
    if filtered:
        p_weeks, p_values = zip(*filtered)

        # Patient line
        fig.add_trace(go.Scatter(
            x=p_weeks, y=p_values,
            mode="lines+markers",
            name="قياسات الحامل",
            line=dict(color=color, width=3),
            marker=dict(size=12, color=color, line=dict(color="white", width=2)),
            hovertemplate="<b>%{x} أسبوع</b><br>القيمة: %{y} " + unit + "<extra></extra>",
        ))

    # WHO reference (P10, P50, P90)
    fig.add_trace(go.Scatter(
        x=curve["weeks"], y=curve["p90"],
        mode="lines", name="P90",
        line=dict(color="#F59E0B", width=2, dash="dash"),
        hovertemplate="P90: %{y} " + unit + "<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=curve["weeks"], y=curve["p50"],
        mode="lines", name="P50 (المتوسط)",
        line=dict(color="#10B981", width=2),
        hovertemplate="P50: %{y} " + unit + "<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=curve["weeks"], y=curve["p10"],
        mode="lines", name="P10",
        line=dict(color="#F59E0B", width=2, dash="dash"),
        fill="tonexty",
        fillcolor="rgba(16,185,129,0.08)",
        hovertemplate="P10: %{y} " + unit + "<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#0F172A"), x=0.5),
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            title="أسابيع الحمل",
            showgrid=True, gridcolor="#F1F5F9",
            range=[10, 42],
        ),
        yaxis=dict(
            title=unit,
            showgrid=True, gridcolor="#F1F5F9",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=10),
        ),
        hovermode="x unified",
    )

    return fig


# ============================================
# TABS
# ============================================

def _render_charts_tab(clinic, user):
    """Charts tab — the main feature"""

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً")
        return

    pmap = {p["id"]: p.get("full_name", "—") for p in patients}

    # Patient selector
    selected_id = st.selectbox(
        "👩 اختر حاملاً",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="growth_chart_patient"
    )

    if not selected_id:
        return

    # Get patient data
    patient_data = get_patient_chart_data(clinic["id"], selected_id)

    if not patient_data.get("weeks"):
        empty_state(
            "📊",
            "لا توجد قياسات",
            "أضف قياسات النمو من تبويب '➕ قياس جديد' لعرض المنحنيات"
        )
        return

    # Summary
    summary = get_patient_summary(clinic["id"], selected_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("📊", summary["total"], "عدد القياسات")
    with c2:
        kpi_card_v2("📅", _gest_age_display(summary.get("first_week")), "أول قياس")
    with c3:
        kpi_card_v2("📅", _gest_age_display(summary.get("last_week")), "آخر قياس")
    with c4:
        latest_analysis = summary.get("latest_analysis") or {}
        diag = latest_analysis.get("diagnosis") or {}
        status = diag.get("status", "unknown")
        status_icon = {"normal": "✅", "iugr": "🚨", "macrosomia": "🟡"}.get(status, "ℹ️")
        kpi_card_v2(status_icon, diag.get("label", "—")[:20], "التشخيص الحالي")

    st.divider()

    # Charts
    section_header_v2("📊", "منحنيات النمو مع معايير WHO")

    # EFW — the most important
    fig = _build_growth_chart("efw", patient_data,
        "⚖️ الوزن المتوقع للجنين (EFW)", "غرام", "#16A34A")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        fig = _build_growth_chart("bpd", patient_data,
            "📏 قطر الرأس (BPD)", "مم", "#0EA5E9")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = _build_growth_chart("hc", patient_data,
            "🧠 محيط الرأس (HC)", "مم", "#8B5CF6")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        fig = _build_growth_chart("ac", patient_data,
            "💚 محيط البطن (AC)", "مم", "#F59E0B")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = _build_growth_chart("fl", patient_data,
            "🦴 طول عظم الفخذ (FL)", "مم", "#EC4899")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Diagnosis details
    latest_analysis = summary.get("latest_analysis") or {}
    diag = latest_analysis.get("diagnosis")
    if diag:
        section_header_v2("⚕️", "التشخيص الطبي", badge="آخر قياس")

        color = diag.get("color", "#10B981")
        st.markdown("""
        <div style="background:white;border:1px solid {color};border-radius:12px;
                    padding:1.25rem 1.5rem;border-right:5px solid {color};">
            <div style="font-size:1.2rem;font-weight:700;color:{color};">
                {label}
            </div>
            <div style="color:#334155;margin-top:0.5rem;font-size:0.95rem;">
                {details}
            </div>
        </div>
        """.format(
            color=color,
            label=diag.get("label", "—"),
            details=diag.get("details", ""),
        ), unsafe_allow_html=True)

        recs = diag.get("recommendations", [])
        if recs:
            st.write("")
            st.markdown("##### 💡 التوصيات")
            for r in recs:
                st.markdown("  - {}".format(r))


def _render_add_tab(clinic, user):
    """Add a new measurement"""

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    st.markdown("#### ➕ إضافة قياس جديد")

    selected_id = st.selectbox(
        "👩 الحامل *",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="growth_add_patient"
    )

    st.markdown("##### 📅 معلومات أساسية")

    c1, c2 = st.columns(2)
    with c1:
        measured_at = st.date_input(
            "تاريخ القياس",
            value=date.today(),
            key="growth_add_date"
        )
    with c2:
        gestational_week = st.number_input(
            "أسابيع الحمل *",
            min_value=8, max_value=42,
            value=20, step=1,
            key="growth_add_week"
        )

    st.markdown("##### 📏 القياسات (املأ ما توفر)")

    c3, c4 = st.columns(2)
    with c3:
        fundal_height = st.number_input(
            "ارتفاع الرحم (سم)",
            min_value=0.0, max_value=60.0,
            value=0.0, step=0.5,
            key="growth_add_fh"
        )
        bpd = st.number_input(
            "قطر الرأس BPD (مم)",
            min_value=0.0, max_value=150.0,
            value=0.0, step=1.0,
            key="growth_add_bpd"
        )
        hc = st.number_input(
            "محيط الرأس HC (مم)",
            min_value=0.0, max_value=450.0,
            value=0.0, step=1.0,
            key="growth_add_hc"
        )

    with c4:
        ac = st.number_input(
            "محيط البطن AC (مم)",
            min_value=0.0, max_value=500.0,
            value=0.0, step=1.0,
            key="growth_add_ac"
        )
        fl = st.number_input(
            "طول عظم الفخذ FL (مم)",
            min_value=0.0, max_value=120.0,
            value=0.0, step=1.0,
            key="growth_add_fl"
        )
        efw = st.number_input(
            "الوزن المتوقع EFW (غرام)",
            min_value=0, max_value=6000,
            value=0, step=50,
            key="growth_add_efw"
        )

    afi = st.number_input(
        "مؤشر السائل الأمنيوسي (AFI)",
        min_value=0.0, max_value=40.0,
        value=0.0, step=0.5,
        key="growth_add_afi"
    )

    notes = st.text_area(
        "ملاحظات",
        placeholder="اختياري...",
        height=68,
        key="growth_add_notes"
    )

    st.write("")

    # === Save button with STRONG debounce (prevents double-click) ===
    import time as _time

    _last_save = st.session_state.get("_growth_last_save_time", 0)
    _now = _time.time()
    _cooldown = 3.0  # seconds

    def _do_save_growth():
        st.session_state["_growth_last_save_time"] = _time.time()
        try:
            create_measurement(
                clinic_id=clinic["id"],
                patient_id=selected_id,
                measured_at=measured_at,
                gestational_week=int(gestational_week),
                fundal_height_cm=fundal_height,
                estimated_fetal_weight_g=efw,
                biparietal_diameter_mm=bpd,
                femur_length_mm=fl,
                abdominal_circumference_mm=ac,
                head_circumference_mm=hc,
                amniotic_fluid_index=afi,
                notes=notes or None,
            )
            st.session_state["_growth_save_result"] = "success"
        except Exception as e:
            st.session_state["_growth_save_result"] = "error:{}".format(str(e)[:200])

    # Show button — disabled if too soon
    _too_soon = (_now - _last_save) < _cooldown
    st.button(
        "💾 حفظ القياس" + (" (انتظر {:.0f}ث)".format(_cooldown - (_now - _last_save)) if _too_soon else ""),
        type="primary",
        use_container_width=True,
        key="growth_save_btn_v2",
        on_click=_do_save_growth,
        disabled=_too_soon,
    )

    # Show result
    if st.session_state.get("_growth_save_result"):
        result = st.session_state["_growth_save_result"]
        if result == "success":
            st.success("✅ تم حفظ القياس بنجاح!")
        elif result.startswith("error:"):
            st.error("❌ " + result[6:])


def _render_table_tab(clinic, user):
    """Table of measurements"""

    patients = _fetch_patients(clinic["id"])
    if not patients:
        return

    pmap = {p["id"]: p.get("full_name", "—") for p in patients}

    selected_id = st.selectbox(
        "👩 الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="growth_table_patient"
    )

    if not selected_id:
        return

    measurements = list_measurements(clinic["id"], selected_id, limit=100)

    if not measurements:
        empty_state("📋", "لا توجد قياسات", "")
        return

    st.caption("📊 {} قياس".format(len(measurements)))

    # Table
    rows = []
    for m in measurements:
        analysis = analyze_measurement(m) or {}
        diag = analysis.get("diagnosis") or {}

        # Convert all values to strings for Arrow compatibility
        rows.append({
            "الأسبوع": str(m.get("gestational_week") or ""),
            "التاريخ": str(m.get("measured_at", ""))[:10],
            "FH (سم)": str(m.get("fundal_height_cm") or ""),
            "BPD (مم)": str(m.get("biparietal_diameter_mm") or ""),
            "HC (مم)": str(m.get("head_circumference_mm") or ""),
            "AC (مم)": str(m.get("abdominal_circumference_mm") or ""),
            "FL (مم)": str(m.get("femur_length_mm") or ""),
            "EFW (غ)": str(m.get("estimated_fetal_weight_g") or ""),
            "التشخيص": str(diag.get("label", ""))[:25],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Delete section
    st.divider()
    with st.expander("🗑️ حذف قياس"):
        idx = st.selectbox(
            "اختر القياس",
            options=range(len(measurements)),
            format_func=lambda i: "أسبوع {} — {}".format(
                measurements[i].get("gestational_week"),
                str(measurements[i].get("measured_at", ""))[:10]),
            key="growth_del_select"
        )
        if st.button("🗑️ حذف", key="growth_del_btn"):
            delete_measurement(clinic["id"], measurements[idx]["id"])
            st.success("🗑️ تم الحذف")


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render — with global patient selector"""
    page_header_v2(
        title="منحنيات نمو الجنين",
        subtitle="متابعة نمو الجنين حسب معايير WHO",
        icon="📊",
    )

    # === GLOBAL PATIENT SELECTOR ===
    patients = _fetch_patients(clinic["id"])

    if not patients:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً من قسم الحوامل")
        return

    pmap = {
        p["id"]: "{} — {}".format(p.get("full_name", "—"), p.get("phone", ""))
        for p in patients
    }

    # Read previously selected patient (or first one)
    saved_id = st.session_state.get("_growth_current_patient")
    if saved_id not in pmap:
        saved_id = list(pmap.keys())[0] if pmap else None

    # Patient selector
    c1, c2 = st.columns([3, 1])
    with c1:
        selected_id = st.selectbox(
            "👩 اختر الحامل",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            index=list(pmap.keys()).index(saved_id) if saved_id in pmap else 0,
            key="growth_global_patient_select",
        )

    with c2:
        # Quick count
        try:
            measurements = list_measurements(clinic["id"], selected_id, limit=1)
            count_resp = __import__("core.db", fromlist=["db"]).db().table(
                "growth_measurements"
            ).select("id", count="exact").eq(
                "clinic_id", clinic["id"]
            ).eq("patient_id", selected_id).execute()
            st.metric("📊 القياسات", count_resp.count or 0)
        except Exception:
            st.metric("📊 القياسات", "—")

    # Save for other tabs
    st.session_state["_growth_current_patient"] = selected_id

    # Selected patient card
    patient = next((p for p in patients if p["id"] == selected_id), {})
    if patient:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#F0FDF4 0%,#DCFCE7 100%);
                    border-radius:12px;padding:0.9rem 1.2rem;
                    border:1px solid #BBF7D0;margin-bottom:1rem;">
            <div style="font-weight:700;color:#0F172A;font-size:1rem;">
                👩 {}
            </div>
            <div style="color:#166534;font-size:0.82rem;margin-top:0.2rem;">
                📞 {} &nbsp;|&nbsp; 📅 EDD: {}
            </div>
        </div>
        """.format(
            patient.get("full_name", "—"),
            patient.get("phone", "—"),
            str(patient.get("edd", "—"))[:10],
        ), unsafe_allow_html=True)

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 المنحنيات",
        "➕ قياس جديد",
        "📋 الجدول",
    ])

    with tab1:
        _render_charts_for(clinic, user, selected_id)
    with tab2:
        _render_add_for(clinic, user, selected_id)
    with tab3:
        _render_table_for(clinic, user, selected_id)


# ============================================
# TAB RENDERERS (using passed patient_id)
# ============================================

def _render_charts_for(clinic, user, patient_id):
    """Charts tab — for selected patient"""
    if not patient_id:
        empty_state("👩", "اختر حاملاً", "")
        return

    patient_data = get_patient_chart_data(clinic["id"], patient_id)

    if not patient_data.get("weeks"):
        empty_state(
            "📊",
            "لا توجد قياسات",
            "أضف قياسات من تبويب '➕ قياس جديد' لعرض المنحنيات"
        )
        return

    summary = get_patient_summary(clinic["id"], patient_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("📊", summary["total"], "عدد القياسات")
    with c2:
        kpi_card_v2("📅", _gest_age_display(summary.get("first_week")), "أول قياس")
    with c3:
        kpi_card_v2("📅", _gest_age_display(summary.get("last_week")), "آخر قياس")
    with c4:
        latest_analysis = summary.get("latest_analysis") or {}
        diag = latest_analysis.get("diagnosis") or {}
        status = diag.get("status", "unknown")
        status_icon = {"normal": "✅", "iugr": "🚨", "macrosomia": "🟡"}.get(status, "ℹ️")
        kpi_card_v2(status_icon, diag.get("label", "—")[:20], "التشخيص")

    st.divider()
    section_header_v2("📊", "المنحنيات مع مرجع WHO")

    fig = _build_growth_chart("efw", patient_data,
        "⚖️ الوزن المتوقع للجنين (EFW)", "غرام", "#16A34A")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = _build_growth_chart("bpd", patient_data, "📏 قطر الرأس (BPD)", "مم", "#0EA5E9")
        if fig: st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = _build_growth_chart("hc", patient_data, "🧠 محيط الرأس (HC)", "مم", "#8B5CF6")
        if fig: st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = _build_growth_chart("ac", patient_data, "💚 محيط البطن (AC)", "مم", "#F59E0B")
        if fig: st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = _build_growth_chart("fl", patient_data, "🦴 طول عظم الفخذ (FL)", "مم", "#EC4899")
        if fig: st.plotly_chart(fig, use_container_width=True)

    # Diagnosis
    latest_analysis = summary.get("latest_analysis") or {}
    diag = latest_analysis.get("diagnosis")
    if diag:
        st.divider()
        section_header_v2("⚕️", "التشخيص الطبي")
        color = diag.get("color", "#10B981")
        st.markdown("""
        <div style="background:white;border:1px solid {color};border-radius:12px;
                    padding:1.25rem 1.5rem;border-right:5px solid {color};">
            <div style="font-size:1.2rem;font-weight:700;color:{color};">
                {label}
            </div>
            <div style="color:#334155;margin-top:0.5rem;font-size:0.95rem;">
                {details}
            </div>
        </div>
        """.format(color=color, label=diag.get("label", ""), details=diag.get("details", "")),
        unsafe_allow_html=True)

        recs = diag.get("recommendations", [])
        if recs:
            st.markdown("##### 💡 التوصيات")
            for r in recs:
                st.markdown("  - {}".format(r))


def _render_add_for(clinic, user, patient_id):
    """Add tab — for selected patient"""
    if not patient_id:
        empty_state("👩", "اختر حاملاً", "")
        return

    st.markdown("#### ➕ إضافة قياس جديد")
    st.caption("👩 الحامل: **{}**".format(
        st.session_state.get("_growth_current_patient", "")))

    st.markdown("##### 📅 معلومات أساسية")

    c1, c2 = st.columns(2)
    with c1:
        measured_at = st.date_input("تاريخ القياس", value=date.today(), key="growth_add_date_v2")
    with c2:
        gestational_week = st.number_input("أسابيع الحمل *", min_value=8, max_value=42,
            value=20, step=1, key="growth_add_week_v2")

    st.markdown("##### 📏 القياسات (املأ ما توفر)")

    c3, c4 = st.columns(2)
    with c3:
        fundal_height = st.number_input("ارتفاع الرحم (سم)", min_value=0.0, max_value=60.0,
            value=0.0, step=0.5, key="growth_add_fh_v2")
        bpd = st.number_input("قطر الرأس BPD (مم)", min_value=0.0, max_value=150.0,
            value=0.0, step=1.0, key="growth_add_bpd_v2")
        hc = st.number_input("محيط الرأس HC (مم)", min_value=0.0, max_value=450.0,
            value=0.0, step=1.0, key="growth_add_hc_v2")

    with c4:
        ac = st.number_input("محيط البطن AC (مم)", min_value=0.0, max_value=500.0,
            value=0.0, step=1.0, key="growth_add_ac_v2")
        fl = st.number_input("طول عظم الفخذ FL (مم)", min_value=0.0, max_value=120.0,
            value=0.0, step=1.0, key="growth_add_fl_v2")
        efw = st.number_input("الوزن المتوقع EFW (غرام)", min_value=0, max_value=6000,
            value=0, step=50, key="growth_add_efw_v2")

    afi = st.number_input("مؤشر السائل الأمنيوسي (AFI)", min_value=0.0, max_value=40.0,
        value=0.0, step=0.5, key="growth_add_afi_v2")

    notes = st.text_area("ملاحظات", placeholder="اختياري...", height=68, key="growth_add_notes_v2")

    st.write("")

    # Debounced save
    import time as _time
    _last = st.session_state.get("_growth_last_save_v2", 0)
    _now = _time.time()
    _cooldown = 3.0
    _too_soon = (_now - _last) < _cooldown

    def _do_save():
        st.session_state["_growth_last_save_v2"] = _time.time()
        try:
            create_measurement(
                clinic_id=clinic["id"],
                patient_id=patient_id,
                measured_at=measured_at,
                gestational_week=int(gestational_week),
                fundal_height_cm=fundal_height,
                estimated_fetal_weight_g=efw,
                biparietal_diameter_mm=bpd,
                femur_length_mm=fl,
                abdominal_circumference_mm=ac,
                head_circumference_mm=hc,
                amniotic_fluid_index=afi,
                notes=notes or None,
            )
            st.session_state["_growth_save_result_v2"] = "success"
        except Exception as e:
            st.session_state["_growth_save_result_v2"] = "error:" + str(e)[:200]

    st.button(
        "💾 حفظ القياس" + (" (انتظر {:.0f}ث)".format(_cooldown - (_now - _last)) if _too_soon else ""),
        type="primary", use_container_width=True,
        key="growth_save_btn_v2", on_click=_do_save,
        disabled=_too_soon,
    )

    if st.session_state.get("_growth_save_result_v2"):
        r = st.session_state["_growth_save_result_v2"]
        if r == "success":
            st.success("✅ تم حفظ القياس بنجاح!")
        elif r.startswith("error:"):
            st.error("❌ " + r[6:])


def _render_table_for(clinic, user, patient_id):
    """Table tab — for selected patient"""
    if not patient_id:
        return

    measurements = list_measurements(clinic["id"], patient_id, limit=100)

    if not measurements:
        empty_state("📋", "لا توجد قياسات", "أضف قياساً من تبويب '➕ قياس جديد'")
        return

    st.caption("📊 {} قياس".format(len(measurements)))

    rows = []
    for m in measurements:
        analysis = analyze_measurement(m) or {}
        diag = analysis.get("diagnosis") or {}
        rows.append({
            "الأسبوع": str(m.get("gestational_week") or ""),
            "التاريخ": str(m.get("measured_at", ""))[:10],
            "FH": str(m.get("fundal_height_cm") or ""),
            "BPD": str(m.get("biparietal_diameter_mm") or ""),
            "HC": str(m.get("head_circumference_mm") or ""),
            "AC": str(m.get("abdominal_circumference_mm") or ""),
            "FL": str(m.get("femur_length_mm") or ""),
            "EFW": str(m.get("estimated_fetal_weight_g") or ""),
            "التشخيص": str(diag.get("label", ""))[:25],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Delete
    st.divider()
    with st.expander("🗑️ حذف قياس"):
        idx = st.selectbox(
            "اختر القياس",
            options=range(len(measurements)),
            format_func=lambda i: "أسبوع {} — {}".format(
                measurements[i].get("gestational_week"),
                str(measurements[i].get("measured_at", ""))[:10]),
            key="growth_del_select_v2"
        )
        if st.button("🗑️ حذف", key="growth_del_btn_v2"):
            delete_measurement(clinic["id"], measurements[idx]["id"])
            st.success("🗑️ تم الحذف")



def quick_add_growth(clinic, user, patient_id):
    """Quick entry from patient view"""
    st.session_state["nav_section"] = "medical"
    st.rerun()
