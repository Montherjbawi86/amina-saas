# -*- coding: utf-8 -*-
"""
Preeclampsia Screening View
واجهة فحص ما قبل تسمم الحمل
"""
from datetime import date, datetime
import streamlit as st

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from services.preeclampsia import (
    evaluate_preeclampsia, get_preeclampsia_data,
    get_severity_meta,
)


# ============================================
# HELPERS
# ============================================

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


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="فحص ما قبل تسمم الحمل",
        subtitle="Preeclampsia Screening — تقييم شامل",
        icon="🚨",
    )

    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    saved_id = st.session_state.get("_pe_current_patient")
    if saved_id not in pmap:
        saved_id = list(pmap.keys())[0]

    selected_id = st.selectbox(
        "👩 اختر الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        index=list(pmap.keys()).index(saved_id) if saved_id in pmap else 0,
        key="pe_patient_select"
    )
    st.session_state["_pe_current_patient"] = selected_id

    patient = next((p for p in patients if p["id"] == selected_id), None)
    if not patient:
        return

    week = _get_week(patient)

    # Auto-fetch latest data
    auto_data = get_preeclampsia_data(clinic["id"], selected_id)

    # If no auto data found → manual entry
    use_auto = auto_data.get("systolic") is not None

    st.divider()

    # === Quick facts ===
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card_v2("📅", "أسبوع {}".format(week) if week else "—", "عمر الحمل")
    with c2:
        if auto_data.get("systolic"):
            kpi_card_v2("💓", "{}/{}".format(auto_data["systolic"], auto_data["diastolic"]), "آخر ضغط")
        else:
            kpi_card_v2("💓", "—", "آخر ضغط")
    with c3:
        kpi_card_v2("💧", auto_data.get("proteinuria") or "—", "بروتين البول")

    st.divider()

    # === Input section ===
    section_header_v2("📝", "بيانات الفحص")

    with st.expander("أدخل / عدّل البيانات", expanded=not use_auto):
        c1, c2 = st.columns(2)
        with c1:
            systolic = st.number_input(
                "ضغط الدم الانقباضي (Systolic)",
                min_value=50, max_value=250,
                value=int(auto_data.get("systolic") or 120),
                step=1,
                key="pe_systolic"
            )
        with c2:
            diastolic = st.number_input(
                "ضغط الدم الانبساطي (Diastolic)",
                min_value=30, max_value=150,
                value=int(auto_data.get("diastolic") or 80),
                step=1,
                key="pe_diastolic"
            )

        c3, c4 = st.columns(2)
        with c3:
            proteinuria = st.selectbox(
                "بروتين البول",
                options=["NEG", "+", "++", "+++", "++++"],
                format_func=lambda x: {
                    "NEG": "سلبي",
                    "+": "+ (خفيف)",
                    "++": "++ (متوسط)",
                    "+++": "+++ (شديد)",
                    "++++": "++++ (شديد جداً)",
                }[x],
                index=0 if not auto_data.get("proteinuria") else
                      (["NEG", "+", "++", "+++", "++++"].index(auto_data["proteinuria"])
                       if auto_data["proteinuria"] in ["NEG", "+", "++", "+++", "++++"] else 0),
                key="pe_proteinuria"
            )
        with c4:
            platelets = st.number_input(
                "الصفائح الدموية (/μL)",
                min_value=10000, max_value=600000,
                value=int(auto_data.get("platelets") or 250000),
                step=10000,
                key="pe_platelets"
            )

        c5, c6 = st.columns(2)
        with c5:
            liver_enzymes = st.number_input(
                "إنزيمات الكبد (×الطبيعي)",
                min_value=0.5, max_value=5.0,
                value=float(auto_data.get("liver_enzymes") or 1.0),
                step=0.1,
                key="pe_liver"
            )
        with c6:
            creatinine = st.number_input(
                "كرياتينين (mg/dL)",
                min_value=0.3, max_value=3.0,
                value=float(auto_data.get("creatinine") or 0.8),
                step=0.1,
                key="pe_creat"
            )

        st.markdown("##### الأعراض")
        symptoms = []
        c7, c8 = st.columns(2)
        with c7:
            if st.checkbox("صداع شديد", key="pe_headache"):
                symptoms.append("headache")
            if st.checkbox("اضطرابات بصرية (فلاشات)", key="pe_visual"):
                symptoms.append("visual")
        with c8:
            if st.checkbox("ألم شرسوفي", key="pe_epigastric"):
                symptoms.append("epigastric")
            if st.checkbox("تورم مفاجئ", key="pe_edema"):
                symptoms.append("edema")

    # === Evaluate ===
    result = evaluate_preeclampsia(
        systolic, diastolic,
        proteinuria=proteinuria,
        platelets=platelets,
        liver_enzymes=liver_enzymes,
        creatinine=creatinine,
        symptoms=symptoms,
    )

    st.divider()

    # === Result card ===
    color = result["color"]
    level = result["level"]

    # Urgent banner
    if result["urgent"]:
        st.markdown("""
        <div style="background:#DC2626;color:white;padding:1rem 1.25rem;
                    border-radius:12px;margin-bottom:1rem;text-align:center;
                    font-weight:700;font-size:1.1rem;animation: blink 1s infinite;">
            🚨 حالة طارئة — يحتاج تدخل فوري
        </div>
        <style>
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        </style>
        """, unsafe_allow_html=True)

    # Main result
    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:16px;
                padding:1.5rem;border-right:8px solid {color};margin-bottom:1rem;">
        <div style="text-align:center;">
            <div style="font-size:0.9rem;color:#64748B;font-weight:600;">
                التصنيف
            </div>
            <div style="font-size:1.75rem;font-weight:900;color:{color};
                        margin:0.5rem 0;">
                {label}
            </div>
            <div style="font-size:0.85rem;color:#94A3B8;">
                درجة الشدة: {score} / 100
            </div>
        </div>
    </div>
    """.format(
        color=color,
        label=result["label"],
        score=result["score"],
    ), unsafe_allow_html=True)

    # === Criteria met ===
    section_header_v2("📋", "المعايير المستوفاة", badge="{}".format(len(result["criteria_met"])))

    if not result["criteria_met"]:
        st.success("✅ لا توجد معايير خطورة مستوفاة")
    else:
        for c in result["criteria_met"]:
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;
                        border-radius:8px;padding:0.5rem 0.85rem;
                        margin-bottom:0.3rem;">
                {c}
            </div>
            """.format(c=c), unsafe_allow_html=True)

    # === Recommendations ===
    st.divider()
    section_header_v2("💡", "التوصيات")

    for r in result["recommendation"]:
        st.markdown("  - {}".format(r))

    # === Interpretation Guide ===
    st.divider()
    with st.expander("ℹ️ تفسير النتائج"):
        st.markdown("""
        ### 🚨 مستويات التسمم:

        **🟢 لا يوجد (None)**
        - ضغط < 140/90
        - لا بروتين في البول
        - متابعة روتينية

        **🟡 ارتفاع ضغط حمل (Gestational HTN)**
        - ضغط ≥ 140/90
        - **لا يوجد** بروتين
        - متابعة أسبوعية

        **🟠 تسمم حمل خفيف (Mild Preeclampsia)**
        - ضغط ≥ 140/90
        - **+ بروتين البول**
        - مراقبة أسبوعية

        **🔴 تسمم حمل شديد (Severe)**
        - ضغط ≥ 160/110
        - بروتين +++ أو أكثر
        - أو أعراض شديدة
        - **حالة طارئة**

        **🚨 HELLP Syndrome**
        - Hemolysis + Elevated Liver + Low Platelets
        - **أخطر مضاعفات التسمم**
        - يحتاج ولادة فورية

        ### ⚠️ العلامات الحمراء:
        - صداع مستمر
        - اضطرابات بصرية
        - ألم في الشرسوف
        - تورم مفاجئ في الوجه/اليدين
        """)
