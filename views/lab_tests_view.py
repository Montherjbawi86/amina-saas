# -*- coding: utf-8 -*-
"""
Lab Tests View
واجهة إدارة التحاليل المخبرية
"""
from datetime import date, timedelta
import streamlit as st

from core.db import db
from core.ui import page_header, spacer
from services.lab_tests import (
    LAB_TEST_TYPES, get_test_label, get_test_info,
    create_lab_test, list_lab_tests, get_lab_test,
    update_lab_test, delete_lab_test, get_patient_lab_summary,
    check_abnormality, get_severity_label,
)


# ============================================
# HELPERS
# ============================================

def _fetch_patients(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id, full_name, phone")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _fetch_patient(clinic_id, patient_id):
    try:
        rows = (
            db().table("patients")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("id", patient_id)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _severity_color(severity):
    return {
        "normal": "#10B981",
        "mild": "#F59E0B",
        "moderate": "#F97316",
        "severe": "#EF4444",
    }.get(severity, "#94A3B8")


def _render_test_card(test, patient_name=""):
    """Render a single lab test as a card"""
    severity = test.get("severity", "normal")
    is_abn = test.get("is_abnormal", False)
    color = _severity_color(severity)
    icon = get_test_info(test.get("test_type", "")) or {}
    icon_str = icon.get("icon", "🧪")

    test_name = test.get("test_name", "—")
    test_date = str(test.get("test_date", ""))[:10]

    badge = ""
    if is_abn:
        badge = '<span style="background:{};color:white;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.7rem;font-weight:700;">⚠️ غير طبيعي — {}</span>'.format(
            color, get_severity_label(severity))
    else:
        badge = '<span style="background:#10B981;color:white;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.7rem;font-weight:700;">✓ طبيعي</span>'

    # Values preview
    values_html = ""
    info = LAB_TEST_TYPES.get(test.get("test_type", ""), {})
    result_value = test.get("result_value") or {}
    fields = info.get("fields", [])

    if fields:
        items = []
        for f in fields[:4]:  # Show max 4 fields
            v = result_value.get(f["key"])
            if v is None or v == "":
                continue
            items.append(
                '<span style="background:#F1F5F9;padding:0.25rem 0.6rem;'
                'border-radius:6px;font-size:0.8rem;margin-right:0.3rem;display:inline-block;margin-bottom:0.3rem;">'
                '<b>{}</b>: {}</span>'.format(f["label"], v)
            )
        values_html = '<div style="margin-top:0.6rem;">{}</div>'.format("".join(items))
        if len(fields) > 4:
            values_html += '<span style="color:#64748B;font-size:0.75rem;">+ {} قيم أخرى</span>'.format(len(fields) - 4)

    patient_html = ""
    if patient_name:
        patient_html = '<div style="color:#0F172A;font-weight:600;font-size:0.9rem;margin-bottom:0.3rem;">👩 {}</div>'.format(patient_name)

    st.markdown("""
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                padding:1rem 1.25rem;margin-bottom:0.75rem;
                border-right:4px solid {color};">
        {patient}
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
            <div style="font-weight:700;color:#0F172A;font-size:1.05rem;">
                {icon} {name}
            </div>
            {badge}
        </div>
        <div style="color:#64748B;font-size:0.8rem;">
            📅 {date} {lab}
        </div>
        {values}
    </div>
    """.format(
        color=color,
        patient=patient_html,
        icon=icon_str,
        name=test_name,
        badge=badge,
        date=test_date,
        lab=" | 🏥 {}".format(test.get("lab_name")) if test.get("lab_name") else "",
        values=values_html,
    ), unsafe_allow_html=True)


# ============================================
# TABS
# ============================================

@st.fragment
def _render_add_tab(clinic, user):
    """Add a new lab test"""
    st.markdown("#### ➕ إضافة تحليل جديد")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        st.warning("⚠️ لا يوجد حوامل")
        st.info("👉 سجّل حاملاً أولاً من قسم **👩 الحوامل**")
        return

    # Step 1: Patient
    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    c1, c2 = st.columns(2)
    with c1:
        selected_id = st.selectbox(
            "الحامل *",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            key="lab_add_patient"
        )

    with c2:
        test_type = st.selectbox(
            "نوع التحليل *",
            options=list(LAB_TEST_TYPES.keys()),
            format_func=lambda x: get_test_label(x),
            key="lab_add_type"
        )

    info = get_test_info(test_type)

    # Step 2: Date + lab info
    c3, c4, c5 = st.columns(3)
    with c3:
        test_date = st.date_input(
            "تاريخ التحليل",
            value=date.today(),
            key="lab_add_date"
        )
    with c4:
        lab_name = st.text_input(
            "اسم المختبر",
            placeholder="مختبر النور",
            key="lab_add_lab"
        )
    with c5:
        visit_id = None  # TODO: link to visit

    # Step 3: Values (dynamic based on type)
    st.markdown("##### 🔬 القيم")

    result_value = {}
    abnormal_fields = []

    for field in info.get("fields", []):
        key = field["key"]
        label = field["label"]
        unit = field.get("unit", "")
        rng = field.get("range", "")
        field_type = field.get("type", "numeric")

        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown("**{}**".format(label))

        with col2:
            if field_type == "text":
                v = st.text_input(
                    "value_{}".format(key),
                    placeholder="مثال: Negative",
                    label_visibility="collapsed",
                    key="lab_add_{}".format(key)
                )
            else:
                v = st.text_input(
                    "value_{}".format(key),
                    placeholder="المعدل: {} {}".format(rng, unit),
                    label_visibility="collapsed",
                    key="lab_add_{}".format(key)
                )

        if v and v.strip():
            result_value[key] = v.strip()

    # Notes
    notes = st.text_area(
        "ملاحظات",
        placeholder="ملاحظات إضافية...",
        height=80,
        key="lab_add_notes"
    )

    # Live preview (abnormality check)
    if result_value:
        is_abn, severity, fields_abn = check_abnormality(test_type, result_value)
        if is_abn:
            st.warning("⚠️ القيم التالية غير طبيعية:")
            for fa in fields_abn:
                st.markdown("  - **{}** = `{}` (المعدل: {}) — {}".format(
                    fa["label"], fa["value"], fa.get("expected", ""),
                    get_severity_label(fa.get("severity", "moderate"))))
        else:
            st.success("✅ كل القيم ضمن المعدل الطبيعي")

    spacer(1)

    # Save button
    def _do_save_lab():
        if not result_value:
            st.session_state["_lab_save_msg"] = "err:أدخل قيمة واحدة على الأقل"
            return
        try:
            create_lab_test(
                clinic_id=clinic["id"],
                patient_id=selected_id,
                test_type=test_type,
                result_value=result_value,
                doctor_id=user.get("id") if user else None,
                test_date=test_date,
                lab_name=lab_name or None,
                notes=notes or None,
            )
            st.session_state["_lab_save_msg"] = "ok"
            st.session_state["_lab_save_patient"] = selected_id
        except Exception as e:
            st.session_state["_lab_save_msg"] = "err:" + str(e)[:200]

    st.button(
        "💾 حفظ التحليل",
        type="primary",
        use_container_width=True,
        key="lab_save_btn_v2",
        on_click=_do_save_lab,
    )

    if st.session_state.get("_lab_save_msg") == "ok":
        st.success("✅ تم حفظ التحليل بنجاح")
        st.session_state.pop("_lab_save_msg", None)
        st.session_state.pop("_lab_save_patient", None)
    elif st.session_state.get("_lab_save_msg", "").startswith("err:"):
        st.error("❌ " + st.session_state["_lab_save_msg"][4:])
        st.session_state.pop("_lab_save_msg", None)


def _render_list_tab(clinic, user):
    """List all lab tests with filters"""
    st.markdown("#### 📋 قائمة التحاليل")

    patients = _fetch_patients(clinic["id"])
    pmap = {"": "الكل"}
    for p in patients:
        pmap[p["id"]] = p.get("full_name", "")

    # Filters
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])

    with c1:
        filter_patient = st.selectbox(
            "الحامل",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            key="lab_list_patient"
        )

    with c2:
        type_options = [""] + list(LAB_TEST_TYPES.keys())
        filter_type = st.selectbox(
            "نوع التحليل",
            options=type_options,
            format_func=lambda x: "الكل" if x == "" else get_test_label(x),
            key="lab_list_type"
        )

    with c3:
        only_abnormal = st.checkbox(
            "🔴 غير الطبيعية فقط",
            value=False,
            key="lab_list_abnormal"
        )

    with c4:
        st.write("")
        st.write("")
        if st.button("🔄 تحديث", use_container_width=True, key="lab_list_refresh"):
            st.rerun()

    # Fetch tests
    tests = list_lab_tests(
        clinic_id=clinic["id"],
        patient_id=filter_patient if filter_patient else None,
        test_type=filter_type if filter_type else None,
        only_abnormal=only_abnormal,
        limit=200,
    )

    # Summary stats
    if tests:
        total = len(tests)
        abnormal_count = sum(1 for t in tests if t.get("is_abnormal"))
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 الإجمالي", total)
        c2.metric("✅ طبيعية", total - abnormal_count)
        c3.metric("⚠️ غير طبيعية", abnormal_count)
        spacer(1)

    if not tests:
        st.info("📭 لا توجد تحاليل بهذه المعايير")
        return

    # Patient name map for cards
    pmap_names = {p["id"]: p.get("full_name", "") for p in patients}

    # Render tests
    for t in tests:
        patient_name = pmap_names.get(t.get("patient_id"), "")
        _render_test_card(t, patient_name)

        # Action buttons per test
        c1, c2, c3, c4 = st.columns([1, 1, 1, 5])
        with c1:
            if st.button("🗑️", key="lab_del_{}".format(t["id"]), help="حذف"):
                if delete_lab_test(clinic["id"], t["id"]):
                    st.success("🗑️ تم الحذف")
        with c2:
            st.write("")  # spacing

        st.markdown("---")


def _render_stats_tab(clinic, user):
    """Statistics"""
    st.markdown("#### 📊 إحصائيات")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        st.info("📭 لا يوجد حوامل")
        return

    pmap = {p["id"]: p.get("full_name", "") for p in patients}

    selected_id = st.selectbox(
        "اختر حاملاً",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="lab_stats_patient"
    )

    if not selected_id:
        return

    summary = get_patient_lab_summary(clinic["id"], selected_id)

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 إجمالي التحاليل", summary["total"])
    c2.metric("✅ طبيعية", summary["normal"])
    c3.metric("⚠️ غير طبيعية", summary["abnormal"])

    if summary["total"] == 0:
        st.info("📭 لا توجد تحاليل لهذه الحامل")
        return

    spacer(1)

    # By type
    if summary.get("by_type"):
        st.markdown("##### 📋 حسب النوع")
        for test_type, data in summary["by_type"].items():
            label = get_test_label(test_type)
            total = data["total"]
            abn = data["abnormal"]
            ratio = (abn / total * 100) if total else 0

            color = "#EF4444" if abn > 0 else "#10B981"
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                        padding:0.75rem 1rem;margin-bottom:0.4rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:600;">{label}</div>
                <div>
                    <span style="background:#F1F5F9;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.85rem;margin-left:0.3rem;">
                        {total} تحليل
                    </span>
                    <span style="background:{color};color:white;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.8rem;font-weight:700;">
                        {abn} غير طبيعي
                    </span>
                </div>
            </div>
            """.format(label=label, total=total, abn=abn, color=color),
            unsafe_allow_html=True)

    if summary.get("latest_date"):
        st.caption("📅 آخر تحليل: {}".format(summary["latest_date"]))


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    page_header(
        "التحاليل المخبرية",
        "إدارة تحاليل الحوامل — 12 نوع مع كشف تلقائي للقيم غير الطبيعية",
        icon="🔬"
    )

    tab_add, tab_list, tab_stats = st.tabs([
        "➕ إضافة تحليل",
        "📋 القائمة",
        "📊 إحصائيات",
    ])

    with tab_add:
        _render_add_tab(clinic, user)

    with tab_list:
        _render_list_tab(clinic, user)

    with tab_stats:
        _render_stats_tab(clinic, user)
