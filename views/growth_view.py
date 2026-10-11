# -*- coding: utf-8 -*-
"""Fetal growth view with WHO reference curves"""
import time
from datetime import date, datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.growth import (
    create_measurement, list_measurements, delete_measurement,
    get_fundal_height_percentile, get_fetal_weight_percentile,
    get_reference_curve, GrowthError,
)
from services.patients import list_patients_cached, get_patient_summary_cached
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Render growth tab"""
    pid = st.session_state.get("selected_patient_id")

    if not pid:
        st.markdown("### 📈 نمو الجنين")
        st.info("👉 اختر حاملاً من تبويب **👩 الحوامل** أولاً")
        return

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.info("👉 اختر حاملاً من تبويب **👩 الحوامل**")
        return

    st.markdown("### 📈 نمو الجنين — {}".format(p["full_name"]))
    st.caption(p["gestational_display"])

    # Tabs: view / add
    tab_chart, tab_add, tab_table = st.tabs(["📊 المخططات", "➕ قياس جديد", "📋 الجدول"])

    with tab_chart:
        _render_charts(clinic, p)

    with tab_add:
        _render_add(clinic, user, p)

    with tab_table:
        _render_table(clinic, p)


# ============================================
# CHARTS
# ============================================
def _render_charts(clinic, p):
    """Show reference curves + patient measurements"""
    show_cache_status("growth_cache")

    measurements = list_measurements(clinic["id"], p["id"])
    ref = get_reference_curve()

    # ============ FUNDAL HEIGHT CHART ============
    st.markdown("#### 📏 ارتفاع الرحم (Fundal Height)")
    st.caption("مقارنة مع منحنيات WHO (p10 - p50 - p90)")

    fig1 = go.Figure()

    # Reference bands
    fig1.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fh_p90"],
        mode="lines", line=dict(color="#F59E0B", dash="dash", width=1),
        name="P90 (عالية)", hovertemplate="%{x}w: %{y}cm<extra></extra>"
    ))
    fig1.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fh_p10"],
        mode="lines", line=dict(color="#F59E0B", dash="dash", width=1),
        fill="tonexty", fillcolor="rgba(245,158,11,0.1)",
        name="P10 (منخفضة)", hovertemplate="%{x}w: %{y}cm<extra></extra>"
    ))
    fig1.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fh_p50"],
        mode="lines", line=dict(color="#10B981", width=2),
        name="P50 (متوسط)", hovertemplate="%{x}w: %{y}cm<extra></extra>"
    ))

    # Patient data
    if measurements:
        weeks = [m["gestational_week"] for m in measurements if m.get("fundal_height_cm")]
        values = [m["fundal_height_cm"] for m in measurements if m.get("fundal_height_cm")]
        if weeks:
            fig1.add_trace(go.Scatter(
                x=weeks, y=values,
                mode="lines+markers",
                line=dict(color="#0EA5A0", width=3),
                marker=dict(size=12, color="#0EA5A0", line=dict(color="white", width=2)),
                name="قياسات الحامل", hovertemplate="أسبوع %{x}: %{y}cm<extra></extra>"
            ))

    fig1.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis_title="عمر الحمل (أسبوع)",
        yaxis_title="ارتفاع الرحم (سم)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ============ FETAL WEIGHT CHART ============
    st.markdown("#### ⚖️ وزن الجنين التقديري (EFW)")
    st.caption("من منحنيات WHO/INTERGROWTH")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fw_p90"],
        mode="lines", line=dict(color="#F59E0B", dash="dash", width=1),
        name="P90"
    ))
    fig2.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fw_p10"],
        mode="lines", line=dict(color="#F59E0B", dash="dash", width=1),
        fill="tonexty", fillcolor="rgba(245,158,11,0.1)",
        name="P10"
    ))
    fig2.add_trace(go.Scatter(
        x=ref["weeks"], y=ref["fw_p50"],
        mode="lines", line=dict(color="#10B981", width=2),
        name="P50"
    ))

    if measurements:
        w_weeks = [m["gestational_week"] for m in measurements if m.get("estimated_fetal_weight_g")]
        w_vals = [m["estimated_fetal_weight_g"] for m in measurements if m.get("estimated_fetal_weight_g")]
        if w_weeks:
            fig2.add_trace(go.Scatter(
                x=w_weeks, y=w_vals,
                mode="lines+markers",
                line=dict(color="#0EA5A0", width=3),
                marker=dict(size=12, color="#0EA5A0", line=dict(color="white", width=2)),
                name="قياسات الحامل"
            ))

    fig2.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis_title="عمر الحمل (أسبوع)",
        yaxis_title="وزن الجنين (غرام)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ============ LATEST ANALYSIS ============
    if measurements:
        st.divider()
        st.markdown("#### 🔍 آخر تحليل")

        last = measurements[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("عمر الحمل", "{} أسبوع".format(last["gestational_week"]))
        if last.get("fundal_height_cm"):
            c2.metric("ارتفاع الرحم", "{} سم".format(last["fundal_height_cm"]))
        if last.get("estimated_fetal_weight_g"):
            c3.metric("وزن الجنين", "{} غرام".format(last["estimated_fetal_weight_g"]))

        # Percentile analysis
        if last.get("fundal_height_cm"):
            p_info = get_fundal_height_percentile(last["gestational_week"], last["fundal_height_cm"])
            if p_info:
                color = p_info["color"]
                if "high" in p_info["color"].lower() or p_info["percentile"] != "10-90":
                    st.warning("📏 **ارتفاع الرحم**: {} (Deviation: {} سم)".format(
                        p_info["label"], p_info["deviation"]))
                else:
                    st.success("📏 **ارتفاع الرحم**: {} (Deviation: {} سم)".format(
                        p_info["label"], p_info["deviation"]))

        if last.get("estimated_fetal_weight_g"):
            fw = get_fetal_weight_percentile(last["gestational_week"], last["estimated_fetal_weight_g"])
            if fw:
                if fw["percentile"] != "10-90":
                    st.warning("⚖️ **وزن الجنين**: {}".format(fw["label"]))
                else:
                    st.success("⚖️ **وزن الجنين**: {}".format(fw["label"]))

    if not measurements:
        st.info("📭 لا توجد قياسات. أضف قياساً من تبويب **➕ قياس جديد**")


# ============================================
# ADD
# ============================================
def _render_add(clinic, user, p):
    st.markdown("#### ➕ قياس جديد")

    with st.form("new_growth_form"):
        c1, c2 = st.columns(2)
        with c1:
            _gw = p.get("gestational_weeks") or 20
            try:
                _gw = int(_gw)
            except Exception:
                _gw = 20
            # Clamp between min and max
            _gw = max(10, min(42, _gw))
            week = st.number_input(
                "عمر الحمل (أسبوع) *",
                min_value=10, max_value=42,
                value=_gw,
                step=1,
                key="growth_week_input"
            )
        with c2:
            measured_at = st.date_input("تاريخ القياس", value=date.today())

        st.markdown("##### القياسات الأساسية")
        c1, c2 = st.columns(2)
        with c1:
            fundal_height = st.number_input(
                "ارتفاع الرحم (سم)",
                min_value=5.0, max_value=60.0,
                value=20.0, step=0.5,
                help="Fundal height"
            )
        with c2:
            efw = st.number_input(
                "وزن الجنين التقديري (غرام)",
                min_value=100, max_value=6000,
                value=1000, step=50,
                help="Estimated Fetal Weight (EFW)"
            )

        st.markdown("##### قياسات السونار (اختياري)")
        c1, c2, c3 = st.columns(3)
        with c1:
            bpd = st.number_input("BPD (مم)", min_value=0.0, max_value=120.0, value=0.0, step=0.5)
        with c2:
            fl = st.number_input("FL (مم)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
        with c3:
            ac = st.number_input("AC (مم)", min_value=0.0, max_value=400.0, value=0.0, step=1.0)

        afi = st.number_input("AFI (السائل الأمنيوسي، سم)", min_value=0.0, max_value=30.0, value=0.0, step=0.1)
        notes = st.text_area("ملاحظات", height=80)

        submitted = st.form_submit_button("💾 حفظ القياس", use_container_width=True, type="primary")

    if submitted:
        try:
            create_measurement(
                clinic["id"], p["id"],
                gestational_week=week,
                measured_at=measured_at.isoformat(),
                fundal_height_cm=fundal_height if fundal_height > 0 else None,
                estimated_fetal_weight_g=int(efw) if efw > 0 else None,
                biparietal_diameter_mm=bpd if bpd > 0 else None,
                femur_length_mm=fl if fl > 0 else None,
                abdominal_circumference_mm=ac if ac > 0 else None,
                amniotic_fluid_index=afi if afi > 0 else None,
                notes=notes or None,
            )
            clear_all()
            st.success("✅ تم حفظ القياس")
            st.balloons()
            time.sleep(0.8)
            st.rerun()
        except GrowthError as e:
            st.error(str(e))
        except Exception as e:
            st.error("خطأ: {}".format(e))


# ============================================
# TABLE
# ============================================
def _render_table(clinic, p):
    st.markdown("#### 📋 جميع القياسات")

    measurements = list_measurements(clinic["id"], p["id"])

    if not measurements:
        st.info("📭 لا توجد قياسات")
        return

    rows = []
    for m in measurements:
        rows.append({
            "التاريخ": (m.get("measured_at") or "—")[:10],
            "الأسبوع": m.get("gestational_week"),
            "ارتفاع (سم)": m.get("fundal_height_cm") or "—",
            "وزن الجنين (غ)": m.get("estimated_fetal_weight_g") or "—",
            "BPD (مم)": m.get("biparietal_diameter_mm") or "—",
            "FL (مم)": m.get("femur_length_mm") or "—",
            "AFI (سم)": m.get("amniotic_fluid_index") or "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # CSV
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 تحميل CSV", csv,
        "growth_{}.csv".format(p["full_name"].replace(" ", "_")), "text/csv")

    # Delete
    st.divider()
    st.markdown("##### 🗑️ حذف قياس")
    delete_options = {
        m["id"]: "{} — أسبوع {} — {}".format(
            (m.get("measured_at") or "")[:10],
            m.get("gestational_week"),
            m.get("fundal_height_cm") or "—"
        ) for m in measurements
    }
    selected = st.selectbox(
        "اختر القياس",
        options=list(delete_options.keys()),
        format_func=lambda x: delete_options[x],
        key="delete_growth_measurement"
    )
    if st.button("🗑️ حذف هذا القياس", key="del_growth_btn"):
        if st.session_state.get("confirm_growth_del") == selected:
            delete_measurement(clinic["id"], selected)
            clear_all()
            st.session_state["confirm_growth_del"] = None
            st.success("تم الحذف")
            st.rerun()
        else:
            st.session_state["confirm_growth_del"] = selected
            st.warning("اضغط مرة أخرى للتأكيد")


# ============================================
# WIDGET: quick add
# ============================================
def quick_add_growth(clinic, user, patient_id):
    """Button helper for patient detail"""
    if st.button("📈 قياس نمو جديد", key="quick_growth_" + patient_id, use_container_width=True):
        st.session_state["selected_patient_id"] = patient_id
        st.info("👉 اذهب لتبويب **📈 نمو الجنين**")
