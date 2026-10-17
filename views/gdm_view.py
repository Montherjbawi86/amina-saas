# -*- coding: utf-8 -*-
"""
GDM Screening View
واجهة سكري الحمل
"""
from datetime import date, datetime
import streamlit as st

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from services.gdm import (
    evaluate_ogtt, evaluate_glucose_log, get_ogtt_data,
    get_severity_meta, GDM_CRITERIA,
)


@st.cache_data(ttl=60, show_spinner=False)
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


def _get_week(patient):
    lmp = patient.get("lmp")
    if not lmp:
        return None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        else:
            lmp_d = lmp
        days = (date.today() - lmp_d).days
        return days // 7 if days >= 0 else None
    except Exception:
        return None


def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="سكري الحمل",
        subtitle="Gestational Diabetes (GDM) — تشخيص ومتابعة",
        icon="🩸",
    )

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    saved_id = st.session_state.get("_gdm_current_patient")
    if saved_id not in pmap:
        saved_id = list(pmap.keys())[0]

    selected_id = st.selectbox(
        "👩 اختر الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        index=list(pmap.keys()).index(saved_id) if saved_id in pmap else 0,
        key="gdm_patient_select"
    )
    st.session_state["_gdm_current_patient"] = selected_id

    patient = next((p for p in patients if p["id"] == selected_id), None)
    if not patient:
        return

    week = _get_week(patient)
    auto_data = get_ogtt_data(clinic["id"], selected_id)

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 OGTT",
        "📈 متابعة السكر",
        "ℹ️ المعلومات",
    ])

    with tab1:
        _render_ogtt_tab(clinic, user, patient, week, auto_data)

    with tab2:
        _render_monitoring_tab(clinic, user, patient)

    with tab3:
        _render_help_tab()


def _render_ogtt_tab(clinic, user, patient, week, auto_data):
    """OGTT evaluation"""

    section_header_v2("🩸", "فحص تحمل السكر (75g OGTT)")
    st.caption("IADPSG / WHO 2013 criteria — يُجرى بين 24-28 أسبوع")

    if auto_data.get("fasting") or auto_data.get("1h") or auto_data.get("2h"):
        st.info("📋 آخر OGTT: {}".format(auto_data.get("date", "—")[:10]))

    st.markdown("##### أدخل القيم")

    c1, c2, c3 = st.columns(3)
    with c1:
        fasting = st.number_input(
            "الصيام (mg/dL)",
            min_value=40, max_value=300,
            value=int(auto_data.get("fasting") or 85),
            step=1,
            key="gdm_fasting",
            help="الحد الطبيعي: < 92"
        )
    with c2:
        h1 = st.number_input(
            "بعد ساعة (mg/dL)",
            min_value=40, max_value=400,
            value=int(auto_data.get("1h") or 140),
            step=1,
            key="gdm_1h",
            help="الحد الطبيعي: < 180"
        )
    with c3:
        h2 = st.number_input(
            "بعد ساعتين (mg/dL)",
            min_value=40, max_value=400,
            value=int(auto_data.get("2h") or 120),
            step=1,
            key="gdm_2h",
            help="الحد الطبيعي: < 153"
        )

    # Evaluate
    result = evaluate_ogtt(fasting, h1, h2)

    st.divider()

    # Result banner
    if result["urgent"]:
        st.markdown("""
        <div style="background:#DC2626;color:white;padding:1rem 1.25rem;
                    border-radius:12px;margin-bottom:1rem;text-align:center;
                    font-weight:700;font-size:1.1rem;">
            🚨 سكري صريح — يحتاج تحويل فوري
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:16px;
                padding:1.5rem;border-right:8px solid {color};margin-bottom:1rem;
                text-align:center;">
        <div style="font-size:0.9rem;color:#64748B;font-weight:600;">
            التصنيف
        </div>
        <div style="font-size:1.75rem;font-weight:900;color:{color};
                    margin:0.5rem 0;">
            {label}
        </div>
        <div style="font-size:0.85rem;color:#94A3B8;">
            {abnormal} قيمة غير طبيعية
        </div>
    </div>
    """.format(
        color=result["color"],
        label=result["label"],
        abnormal=result["abnormal_count"],
    ), unsafe_allow_html=True)

    # Criteria met
    if result["criteria_met"]:
        st.markdown("##### 🔍 القيم غير الطبيعية")
        for c in result["criteria_met"]:
            st.markdown("""
            <div style="background:#FEF2F2;border:1px solid #FECACA;
                        border-radius:8px;padding:0.5rem 0.85rem;
                        margin-bottom:0.3rem;">
                {c}
            </div>
            """.format(c=c), unsafe_allow_html=True)

    # Recommendations
    st.divider()
    section_header_v2("💡", "التوصيات")
    for r in result["recommendation"]:
        st.markdown("  - {}".format(r))

    # Save button
    st.divider()
    if st.button("💾 حفظ النتائج في قاعدة البيانات", type="primary",
                 use_container_width=True, key="gdm_save_btn"):
        try:
            db().table("lab_tests").insert({
                "clinic_id": clinic["id"],
                "patient_id": patient["id"],
                "test_type": "glucose",
                "test_name": "OGTT 75g",
                "test_date": str(date.today()),
                "result_value": {
                    "fasting": fasting,
                    "h1": h1,
                    "h2": h2,
                },
                "is_abnormal": result["abnormal_count"] >= 2,
                "severity": "severe" if result["urgent"] else
                            ("moderate" if result["abnormal_count"] >= 2 else "normal"),
                "status": "completed",
            }).execute()
            st.success("✅ تم حفظ نتائج OGTT")
        except Exception as e:
            st.error("❌ {}".format(str(e)[:200]))


def _render_monitoring_tab(clinic, user, patient):
    """Home glucose monitoring"""

    section_header_v2("📈", "متابعة السكر اليومية")
    st.caption("القياسات المنزلية — 4 مرات يومياً (صيام + بعد الوجبات)")

    st.markdown("##### 🎯 الأهداف (ADIPS)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("🌅", "< 95", "صيام")
    with c2:
        kpi_card_v2("🍳", "< 140", "بعد الفطور")
    with c3:
        kpi_card_v2("🍽️", "< 140", "بعد الغداء")
    with c4:
        kpi_card_v2("🍲", "< 140", "بعد العشاء")

    st.divider()

    # Add reading
    with st.expander("➕ إضافة قراءة جديدة", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            reading_date = st.date_input("التاريخ", value=date.today(), key="gdm_reading_date")
            fasting = st.number_input("صيام (mg/dL)", min_value=40, max_value=300,
                value=90, step=1, key="gdm_reading_fasting")
        with c2:
            post_bf = st.number_input("بعد الفطور (mg/dL)", min_value=40, max_value=400,
                value=130, step=1, key="gdm_reading_bf")
            post_lunch = st.number_input("بعد الغداء (mg/dL)", min_value=40, max_value=400,
                value=130, step=1, key="gdm_reading_lunch")

        post_dinner = st.number_input("بعد العشاء (mg/dL)", min_value=40, max_value=400,
            value=130, step=1, key="gdm_reading_dinner")

        if st.button("💾 حفظ القراءة", key="gdm_save_reading"):
            try:
                db().table("lab_tests").insert({
                    "clinic_id": clinic["id"],
                    "patient_id": patient["id"],
                    "test_type": "glucose_monitor",
                    "test_name": "Glucose Log",
                    "test_date": str(reading_date),
                    "result_value": {
                        "fasting": fasting,
                        "post_breakfast": post_bf,
                        "post_lunch": post_lunch,
                        "post_dinner": post_dinner,
                    },
                    "status": "completed",
                }).execute()
                st.success("✅ تم الحفظ")
                st.rerun()
            except Exception as e:
                st.error("❌ {}".format(str(e)[:200]))

    # Fetch readings
    try:
        readings = (
            db().table("lab_tests").select("*")
            .eq("clinic_id", clinic["id"])
            .eq("patient_id", patient["id"])
            .eq("test_type", "glucose_monitor")
            .order("test_date", desc=True)
            .limit(14)
            .execute()
            .data or []
        )
    except Exception:
        readings = []

    if not readings:
        st.info("📭 لا توجد قراءات مسجلة بعد")
        return

    # Evaluate
    parsed = []
    for r in readings:
        rv = r.get("result_value") or {}
        if isinstance(rv, dict):
            parsed.append({
                "date": r.get("test_date"),
                "fasting": rv.get("fasting"),
                "post_breakfast": rv.get("post_breakfast"),
                "post_lunch": rv.get("post_lunch"),
                "post_dinner": rv.get("post_dinner"),
            })

    eval_result = evaluate_glucose_log(parsed)
    if not eval_result:
        return

    st.divider()
    section_header_v2("📊", "التحليل")

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card_v2("📋", eval_result["total"], "إجمالي القراءات")
    with c2:
        kpi_card_v2("✅", "{}%".format(eval_result["controlled_pct"]), "السيطرة")
    with c3:
        kpi_card_v2("⚠️", eval_result["out_of_range_count"], "خارج النطاق")

    # Result banner
    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:16px;
                padding:1.25rem;border-right:8px solid {color};margin:1rem 0;
                text-align:center;">
        <div style="font-size:1.4rem;font-weight:900;color:{color};">
            {label}
        </div>
        {note}
    </div>
    """.format(
        color=eval_result["color"],
        label=eval_result["label"],
        note='<div style="font-size:0.85rem;color:#64748B;margin-top:0.5rem;">قد يحتاج بدء أنسولين</div>' if eval_result["needs_insulin"] else "",
    ), unsafe_allow_html=True)

    # Out of range details
    if eval_result["out_of_range"]:
        st.markdown("##### ⚠️ القراءات خارج النطاق")
        for o in eval_result["out_of_range"][:10]:
            st.markdown("""
            <div style="background:#FEF2F2;border:1px solid #FECACA;
                        border-radius:6px;padding:0.4rem 0.75rem;
                        margin-bottom:0.25rem;font-size:0.85rem;">
                📅 {date} — {type}: <b>{value}</b> mg/dL (الحد: {threshold})
            </div>
            """.format(
                date=str(o.get("date", ""))[:10],
                type={
                    "fasting": "صيام",
                    "post_breakfast": "بعد الفطور",
                    "post_lunch": "بعد الغداء",
                    "post_dinner": "بعد العشاء",
                }.get(o.get("type"), o.get("type")),
                value=o.get("value"),
                threshold=o.get("threshold"),
            ), unsafe_allow_html=True)


def _render_help_tab():
    """Help and education"""
    section_header_v2("📚", "معلومات عن سكري الحمل")

    st.markdown("""
    ### 🩸 ما هو سكري الحمل؟

    سكري الحمل (GDM) هو ارتفاع سكر الدم **أول مرة** أثناء الحمل، عادةً بين **24-28 أسبوع**.

    ### 📊 عوامل الخطورة:
    - العمر > 35
    - السمنة (BMI > 30)
    - تاريخ عائلي لسكري
    - GDM في حمل سابق
    - ولادة سابقة بطفل > 4 كغ
    - متلازمة المبيض المتعدد الكيسات

    ### 🧪 التشخيص (OGTT 75g):

    | القيمة | الطبيعي | GDM |
    |--------|---------|-----|
    | صيام | < 92 | ≥ 92 |
    | 1 ساعة | < 180 | ≥ 180 |
    | 2 ساعة | < 153 | ≥ 153 |

    **قيمة واحدة غير طبيعية = GDM** (IADPSG)

    ### ⚠️ مضاعفات بدون علاج:
    - **للأم:** تسمم حمل، ولادة قيصرية، سكري بعد الولادة
    - **للجنين:** ضخامة (macrosomia)، هبوط سكر بعد الولادة، مشاكل تنفس

    ### 💊 العلاج:

    **1. النظام الغذائي (80%):**
    - 30 kcal/kg/day
    - 3 وجبات + 2-3 وجبات خفيفة
    - تقليل السكريات البسيطة
    - زيادة الألياف

    **2. الرياضة:**
    - 30 دقيقة يومياً
    - مشي، سباحة

    **3. الأنسولين (20%):**
    - إذا فشل النظام الغذائي
    - بعد أسبوعين من المتابعة

    ### 🎯 أهداف السكر:
    - **صيام:** < 95 mg/dL
    - **بعد ساعة:** < 140 mg/dL
    - **بعد ساعتين:** < 120 mg/dL

    ### 🍼 بعد الولادة:
    - إيقاف الأنسولين عادةً
    - إعادة OGTT بعد 6-12 أسبوع
    - خطر 50% للإصابة بسكري نوع 2 لاحقاً
    """)
