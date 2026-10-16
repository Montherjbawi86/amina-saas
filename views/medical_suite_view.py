# -*- coding: utf-8 -*-
"""
Medical Suite View
واجهة الرعاية الطبية المتقدمة — 4 ميزات
"""
from datetime import date, datetime
import streamlit as st

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from services.medical_suite import (
    calculate_risk_score, get_risk_level_meta,
    get_antenatal_plan, get_anemia_thresholds, classify_anemia,
    get_patient_medical_summary, calculate_age,
)
from services.drug_interactions_db import (
    check_interactions, get_severity_label, get_severity_color,
    get_severity_icon, COMMON_DRUGS, DRUG_CATEGORIES,
    search_drugs, check_pregnancy_warning,
)


# ============================================
# HELPERS
# ============================================

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_patients(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id,full_name,phone,date_of_birth,gravida,para,risk_level,lmp,edd,blood_type")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_visits(clinic_id, patient_id):
    try:
        return (
            db().table("visits")
            .select("visit_date,bp_systolic,bp_diastolic,fetal_heart_rate,gestational_age_weeks,weight_kg")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .order("visit_date", desc=True)
            .limit(10)
            .execute()
            .data or []
        )
    except Exception:
        return []


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_prescriptions(clinic_id, patient_id):
    try:
        return (
            db().table("prescriptions")
            .select("id,issued_at,diagnosis,medications")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .order("issued_at", desc=True)
            .limit(10)
            .execute()
            .data or []
        )
    except Exception:
        return []


def _get_current_week(patient):
    """Calculate current gestational week"""
    lmp = patient.get("lmp")
    if not lmp:
        return None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        else:
            lmp_d = lmp
        days = (date.today() - lmp_d).days
        if days < 0:
            return None
        return days // 7
    except Exception:
        return None


# ============================================
# TAB 1: RISK SCORE
# ============================================

def _render_risk_tab(clinic, user, patient):
    """Risk Score Calculator"""

    visits = _fetch_visits(clinic["id"], patient["id"])
    risk = calculate_risk_score(patient, visits)
    if not risk:
        empty_state("📊", "لا يمكن حساب المخاطر", "بيانات ناقصة")
        return

    meta = get_risk_level_meta(risk["level"])

    # Big score card
    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:16px;
                padding:1.5rem;text-align:center;border-right:8px solid {color};
                margin-bottom:1rem;">
        <div style="font-size:0.85rem;color:#64748B;font-weight:600;">
            درجة المخاطر
        </div>
        <div style="font-size:3rem;font-weight:900;color:{color};
                    line-height:1;margin:0.5rem 0;">
            {score}
        </div>
        <div style="font-size:1.1rem;font-weight:700;color:{color};">
            {label}
        </div>
        <div style="font-size:0.8rem;color:#94A3B8;margin-top:0.5rem;">
            من 100 — كلما ارتفعت، زادت المخاطر
        </div>
    </div>
    """.format(color=meta["color"], score=risk["score"], label=meta["label"]),
    unsafe_allow_html=True)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        age = risk.get("age")
        kpi_card_v2("👤", str(age) if age else "—", "العمر")
    with c2:
        kpi_card_v2("🤰", "{}/{}".format(patient.get("gravida", 0), patient.get("para", 0)), "G/P")
    with c3:
        kpi_card_v2("🩸", patient.get("blood_type") or "—", "فصيلة الدم")
    with c4:
        week = _get_current_week(patient)
        kpi_card_v2("📅", "أسبوع {}".format(week) if week else "—", "الحمل")

    st.divider()

    # Factors
    section_header_v2("🔍", "عوامل المخاطر", badge="{}".format(len(risk["factors"])))

    if not risk["factors"]:
        st.success("✅ لا توجد عوامل مخاطر محددة")
    else:
        for f in risk["factors"]:
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                        padding:0.7rem 1rem;margin-bottom:0.4rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:600;color:#0F172A;font-size:0.9rem;">
                        ⚠️ {name}
                    </div>
                    {note}
                </div>
                <div style="background:{color};color:white;padding:0.25rem 0.65rem;
                            border-radius:999px;font-size:0.78rem;font-weight:700;">
                    +{points}
                </div>
            </div>
            """.format(
                name=f["name"],
                note='<div style="color:#64748B;font-size:0.78rem;margin-top:0.15rem;">{}</div>'.format(f["note"]) if f.get("note") else "",
                color=meta["color"],
                points=f["points"],
            ), unsafe_allow_html=True)

    # Recommendations
    st.divider()
    section_header_v2("💡", "التوصيات")

    for r in risk["recommendations"]:
        st.markdown("  - {}".format(r))


# ============================================
# TAB 2: ANTENATAL CARE PLAN
# ============================================

def _render_care_plan_tab(clinic, user, patient):
    """WHO Antenatal Care Plan"""

    plan = get_antenatal_plan(patient)
    if not plan:
        empty_state(
            "📅",
            "لا يمكن إنشاء الخطة",
            "يحتاج LMP أو EDD — أضفه من صفحة الحامل"
        )
        return

    # Info card
    st.markdown("""
    <div style="background:linear-gradient(135deg,#F0FDF4 0%,#DCFCE7 100%);
                border-radius:12px;padding:1rem 1.25rem;
                border:1px solid #BBF7D0;margin-bottom:1rem;">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
            <div>
                <div style="color:#166534;font-size:0.78rem;font-weight:600;">LMP</div>
                <div style="font-weight:700;color:#0F172A;">{lmp}</div>
            </div>
            <div>
                <div style="color:#166534;font-size:0.78rem;font-weight:600;">EDD</div>
                <div style="font-weight:700;color:#0F172A;">{edd}</div>
            </div>
            <div>
                <div style="color:#166534;font-size:0.78rem;font-weight:600;">الأسبوع الحالي</div>
                <div style="font-weight:700;color:#16A34A;">أسبوع {week}</div>
            </div>
            <div>
                <div style="color:#166534;font-size:0.78rem;font-weight:600;">الزيارات</div>
                <div style="font-weight:700;color:#0F172A;">{total}</div>
            </div>
        </div>
    </div>
    """.format(
        lmp=plan["lmp"].strftime("%Y-%m-%d"),
        edd=plan["edd"].strftime("%Y-%m-%d"),
        week=plan["current_week"],
        total=len(plan["visits"]),
    ), unsafe_allow_html=True)

    # Progress
    done = sum(1 for v in plan["visits"] if v["status"] == "past")
    current = sum(1 for v in plan["visits"] if v["status"] == "current")
    upcoming = sum(1 for v in plan["visits"] if v["status"] == "upcoming")

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card_v2("✅", done, "مكتملة")
    with c2:
        kpi_card_v2("🔵", current, "حالية")
    with c3:
        kpi_card_v2("⏳", upcoming, "قادمة")

    st.divider()

    # Visits
    section_header_v2("📅", "الزيارات (WHO 2016)")

    for v in plan["visits"]:
        status = v["status"]
        if status == "past":
            color = "#10B981"
            icon = "✅"
            status_label = "مكتملة"
        elif status == "current":
            color = "#0EA5E9"
            icon = "🔵"
            status_label = "الحالية"
        else:
            color = "#F59E0B"
            icon = "⏳"
            status_label = "قادمة"

        with st.expander(
            "{} الزيارة {}: {} (أسبوع {}) — {}".format(
                icon, v["visit_num"], v["title"],
                v["target_week"], status_label
            ),
            expanded=(status == "current")
        ):
            c1, c2 = st.columns([1, 2])

            with c1:
                st.markdown("**📅 التاريخ المتوقع**")
                st.write(v["target_date"].strftime("%Y-%m-%d"))
                st.markdown("**📊 الفحوصات**")
                for t in v["tests"]:
                    st.markdown("  - {}".format(t))

            with c2:
                st.markdown("**⚕️ الإجراءات**")
                for a in v["actions"]:
                    st.markdown("  - {}".format(a))


# ============================================
# TAB 3: DRUG INTERACTIONS
# ============================================

def _render_interactions_tab(clinic, user, patient):
    """Drug Interactions checker"""

    section_header_v2("💊", "فحص تفاعلات الأدوية")

    # Current medications from latest prescription
    prescriptions = _fetch_prescriptions(clinic["id"], patient["id"])

    current_meds = []
    if prescriptions:
        latest = prescriptions[0]
        meds = latest.get("medications") or []
        if isinstance(meds, list):
            for m in meds:
                if isinstance(m, dict) and m.get("name"):
                    current_meds.append(m)

    # === Current medications ===
    st.markdown("##### 💊 الأدوية الحالية (من آخر وصفة)")

    if not current_meds:
        st.info("📭 لا توجد وصفات حديثة لهذه الحامل")
    else:
        for m in current_meds:
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;
                        border-radius:8px;padding:0.5rem 0.85rem;
                        margin-bottom:0.3rem;border-right:3px solid #16A34A;">
                <span style="font-weight:600;">💊 {name}</span>
                <span style="color:#64748B;font-size:0.85rem;margin-right:0.5rem;">
                    {dose}
                </span>
            </div>
            """.format(
                name=m.get("name", "—"),
                dose=m.get("dose") or "",
            ), unsafe_allow_html=True)

    st.divider()

    # === Check interactions ===
    st.markdown("##### 🔍 فحص التفاعلات")

    if current_meds:
        interactions = check_interactions(current_meds)

        if not interactions:
            st.success("✅ لا توجد تفاعلات معروفة بين الأدوية الحالية")
        else:
            st.warning("⚠️ تم العثور على **{}** تفاعل".format(len(interactions)))

            for inter in interactions:
                sev = inter["severity"]
                color = get_severity_color(sev)
                icon = get_severity_icon(sev)
                label = get_severity_label(sev)

                st.markdown("""
                <div style="background:white;border:1px solid {color};
                            border-radius:10px;padding:0.85rem 1rem;
                            margin-bottom:0.5rem;border-right:4px solid {color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-weight:700;color:#0F172A;">
                            {icon} {drug1} + {drug2}
                        </div>
                        <div style="background:{color};color:white;padding:0.2rem 0.6rem;
                                    border-radius:6px;font-size:0.72rem;font-weight:700;">
                            {label}
                        </div>
                    </div>
                    <div style="color:#334155;font-size:0.85rem;margin-top:0.5rem;">
                        {desc}
                    </div>
                    <div style="background:#F0FDF4;border-radius:6px;padding:0.5rem 0.75rem;
                                margin-top:0.5rem;font-size:0.82rem;color:#166534;
                                border-right:3px solid #16A34A;">
                        💡 {rec}
                    </div>
                </div>
                """.format(
                    color=color,
                    icon=icon,
                    drug1=inter["drug1"],
                    drug2=inter["drug2"],
                    label=label,
                    desc=inter["description"],
                    rec=inter["recommendation"],
                ), unsafe_allow_html=True)

    st.divider()

    # === Test medications manually ===
    st.markdown("##### 🧪 فحص أدوية مخصصة")
    st.caption("اكتب أسماء الأدوية مفصولة بفواصل للفحص")

    test_input = st.text_area(
        "أسماء الأدوية",
        placeholder="حديد، كالسيوم، فيتامين D",
        height=68,
        key="drug_test_input"
    )

    if st.button("🔍 فحص", key="drug_test_btn", type="primary"):
        if not test_input.strip():
            st.warning("أدخل اسم دواء واحد على الأقل")
        else:
            names = [n.strip() for n in test_input.split(",") if n.strip()]
            test_meds = [{"name": n} for n in names]
            results = check_interactions(test_meds)

            if not results:
                st.success("✅ لا توجد تفاعلات معروفة")
            else:
                st.warning("⚠️ {} تفاعل".format(len(results)))
                for r in results:
                    st.markdown("**{} {}** — {}".format(
                        get_severity_icon(r["severity"]),
                        get_severity_label(r["severity"]),
                        r["description"],
                    ))
                    st.caption("💡 {}".format(r["recommendation"]))


# ============================================
# TAB 4: ANEMIA SCREENING
# ============================================

def _render_anemia_tab(clinic, user, patient):
    """Anemia Screening"""

    section_header_v2("🩸", "فحص فقر الدم (Anemia)")

    # Thresholds
    thresholds = get_anemia_thresholds()

    st.markdown("##### 📋 معايير WHO")
    cols = st.columns(3)
    for i, (key, info) in enumerate(thresholds.items()):
        with cols[i]:
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                        padding:0.75rem;text-align:center;">
                <div style="color:#64748B;font-size:0.78rem;">{label}</div>
                <div style="font-weight:700;color:#16A34A;font-size:1.3rem;margin-top:0.3rem;">
                    &lt; {hb}
                </div>
                <div style="color:#94A3B8;font-size:0.7rem;">g/dL</div>
            </div>
            """.format(label=info["label"], hb=info["hb"]), unsafe_allow_html=True)

    st.divider()

    # Latest CBC
    try:
        labs = db().table("lab_tests").select("*").eq(
            "clinic_id", clinic["id"]
        ).eq("patient_id", patient["id"]).eq(
            "test_type", "cbc"
        ).order("test_date", desc=True).limit(5).execute().data or []
    except Exception:
        labs = []

    if not labs:
        empty_state(
            "🩸",
            "لا توجد تحاليل CBC",
            "أضف تحليل CBC من قسم 'التحاليل المخبرية'"
        )
        return

    st.markdown("##### 🩸 آخر تحاليل CBC")

    week = _get_current_week(patient) or 0

    for lab in labs[:3]:
        rv = lab.get("result_value") or {}
        hb = rv.get("hgb") if isinstance(rv, dict) else None

        if not hb:
            continue

        try:
            hb = float(hb)
        except Exception:
            continue

        result = classify_anemia(hb, week)
        if not result:
            continue

        test_date = str(lab.get("test_date", ""))[:10]

        st.markdown("""
        <div style="background:white;border:1px solid {color};border-radius:12px;
                    padding:1rem 1.25rem;margin-bottom:0.5rem;
                    border-right:5px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:700;color:#0F172A;font-size:1rem;">
                        Hb: <span style="color:{color};">{hb} g/dL</span>
                    </div>
                    <div style="color:#64748B;font-size:0.8rem;margin-top:0.2rem;">
                        📅 {date} &nbsp;|&nbsp; 🤰 أسبوع {week}
                    </div>
                </div>
                <div style="background:{color};color:white;padding:0.3rem 0.7rem;
                            border-radius:999px;font-size:0.75rem;font-weight:700;">
                    {severity}
                </div>
            </div>
            <div style="color:#334155;font-size:0.85rem;margin-top:0.5rem;
                        background:#F8FAFC;padding:0.5rem 0.75rem;border-radius:6px;">
                💡 {rec}
            </div>
        </div>
        """.format(
            color=result["color"],
            hb=hb,
            date=test_date,
            week=week,
            severity=result["severity"],
            rec=result["recommendation"],
        ), unsafe_allow_html=True)


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="الرعاية الطبية المتقدمة",
        subtitle="مخاطر + خطة زيارات + تفاعلات أدوية + فقر الدم",
        icon="🏥",
    )

    # Global patient selector
    patients = _fetch_patients(clinic["id"])
    if not patients:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً")
        return

    pmap = {
        p["id"]: "{} — {}".format(p.get("full_name", "—"), p.get("phone", ""))
        for p in patients
    }

    saved_id = st.session_state.get("_medical_current_patient")
    if saved_id not in pmap:
        saved_id = list(pmap.keys())[0]

    selected_id = st.selectbox(
        "👩 اختر الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        index=list(pmap.keys()).index(saved_id) if saved_id in pmap else 0,
        key="medical_patient_select",
    )
    st.session_state["_medical_current_patient"] = selected_id

    patient = next((p for p in patients if p["id"] == selected_id), None)
    if not patient:
        return

    st.divider()

    # 4 tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 المخاطر",
        "📅 خطة الزيارات",
        "💊 تفاعلات الأدوية",
        "🩸 فقر الدم",
    ])

    with tab1:
        _render_risk_tab(clinic, user, patient)
    with tab2:
        _render_care_plan_tab(clinic, user, patient)
    with tab3:
        _render_interactions_tab(clinic, user, patient)
    with tab4:
        _render_anemia_tab(clinic, user, patient)
