# -*- coding: utf-8 -*-
"""Vaccinations view"""
import time
from datetime import date, timedelta
import streamlit as st

from services.vaccinations import (
    create_vaccination, list_vaccinations_cached, delete_vaccination,
    update_vaccination, mark_given, auto_schedule_defaults,
    get_status_color, get_status_label, VaccinationError,
)
from services.patients import list_patients_cached, get_patient_summary_cached
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Render vaccinations tab"""
    view = st.session_state.get("vacc_view", "list")
    if view == "list":
        _render_list(clinic, user)
    elif view == "new":
        _render_new(clinic, user)


# ============================================
# LIST
# ============================================
def _render_list(clinic, user):
    st.markdown("### 💉 التحصينات")

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        patients = list_patients_cached(clinic["id"])
        patient_options = {"all": "كل الحوامل"} if patients else {}
        for p in patients:
            patient_options[p["id"]] = p["full_name"]

        selected_pid = st.selectbox(
            "تصفية حسب الحامل",
            options=list(patient_options.keys()),
            format_func=lambda x: patient_options[x],
            key="vacc_patient_filter"
        )
    with c2:
        status_filter = st.selectbox(
            "الحالة",
            ["all", "pending", "given", "missed", "skipped"],
            format_func=lambda x: {
                "all": "الكل",
                "pending": "⏳ منتظرة",
                "given": "✅ تم إعطاؤها",
                "missed": "❌ فائتة",
                "skipped": "⏭️ متجاوزة",
            }[x],
            key="vacc_status_filter"
        )
    with c3:
        st.write("")
        if st.button("➕ تحصين", use_container_width=True, type="primary", key="new_vacc_btn"):
            st.session_state["vacc_view"] = "new"
            st.rerun()

    show_cache_status("vacc_cache")
    st.divider()

    with st.spinner("جاري التحميل..."):
        vaccs = list_vaccinations_cached(
            clinic["id"],
            patient_id=None if selected_pid == "all" else selected_pid
        )

    # Apply status filter manually
    if status_filter != "all":
        vaccs = [v for v in vaccs if v.get("status") == status_filter]

    if not vaccs:
        st.info("📭 لا توجد تحصينات")
        return

    patients_map = {p["id"]: p for p in patients}

    # Summary counts
    counts = {"pending": 0, "given": 0, "missed": 0, "skipped": 0}
    for v in vaccs:
        counts[v.get("status", "pending")] = counts.get(v.get("status", "pending"), 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi("⏳ منتظرة", counts["pending"], "#F59E0B")
    with c2:
        _kpi("✅ تم", counts["given"], "#10B981")
    with c3:
        _kpi("❌ فائتة", counts["missed"], "#EF4444")
    with c4:
        _kpi("⏭️ متجاوزة", counts["skipped"], "#6B7280")

    st.divider()
    st.markdown("**العدد: {}**".format(len(vaccs)))

    # Group by status
    for status_group in ["pending", "given", "missed", "skipped"]:
        items = [v for v in vaccs if v.get("status", "pending") == status_group]
        if not items:
            continue

        st.markdown("#### {}".format(get_status_label(status_group)))

        for v in items:
            p = patients_map.get(v["patient_id"], {})
            name = p.get("full_name", "—")
            color = get_status_color(v.get("status", "pending"))

            scheduled = v.get("scheduled_for") or "—"
            given = v.get("given_at") or "—"

            st.markdown("""
            <div style="background:white; border-radius:10px; padding:0.75rem 1rem; margin-bottom:0.4rem; border-right:4px solid {color}; box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-weight:700; color:#1F2937;">💉 {vaccine} <span style="color:#6B7280; font-weight:400; font-size:0.85rem;">(جرعة {dose})</span></div>
                <div style="font-size:0.85rem; color:#6B7280; margin-top:0.35rem;">
                    👩 {name} &nbsp;|&nbsp; 📅 مجدول: {scheduled} &nbsp;|&nbsp; 💉 أُعطي: {given}
                </div>
            </div>
            """.format(
                color=color,
                vaccine=v.get("vaccine_name", "—"),
                dose=v.get("dose_number", 1),
                name=name,
                scheduled=scheduled[:10] if scheduled else "—",
                given=given[:10] if given else "—"
            ), unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
            with c1:
                if v.get("status") != "given":
                    if st.button("✅ أُعطي", key="given_" + v["id"], use_container_width=True):
                        mark_given(clinic["id"], v["id"])
                        clear_all()
                        st.success("تم")
                        st.rerun()
            with c2:
                if v.get("status") == "pending":
                    if st.button("❌ فائت", key="miss_" + v["id"], use_container_width=True):
                        update_vaccination(clinic["id"], v["id"], status="missed")
                        clear_all()
                        st.rerun()
            with c3:
                if st.button("🗑️ حذف", key="del_" + v["id"], use_container_width=True):
                    if st.session_state.get("confirm_vacc_del") == v["id"]:
                        delete_vaccination(clinic["id"], v["id"])
                        clear_all()
                        st.session_state["confirm_vacc_del"] = None
                        st.rerun()
                    else:
                        st.session_state["confirm_vacc_del"] = v["id"]
                        st.warning("اضغط مرة أخرى")
            st.write("")


# ============================================
# NEW
# ============================================
def _render_new(clinic, user):
    st.markdown("### ➕ تحصين جديد")

    if st.button("⬅️ رجوع للقائمة", key="back_vacc_list"):
        st.session_state["vacc_view"] = "list"
        st.rerun()

    patients = list_patients_cached(clinic["id"])
    if not patients:
        st.warning("⚠️ لا توجد حوامل")
        return

    patient_map = {p["id"]: "{} — {}".format(p["full_name"], p["phone"]) for p in patients}
    preselected = st.session_state.get("selected_patient_id")
    default_idx = 0
    if preselected and preselected in patient_map:
        default_idx = list(patient_map.keys()).index(preselected)

    with st.form("new_vacc_form"):
        pid = st.selectbox(
            "الحامل *",
            options=list(patient_map.keys()),
            format_func=lambda x: patient_map[x],
            index=default_idx,
            key="new_vacc_patient"
        )

        c1, c2 = st.columns([3, 1])
        with c1:
            vaccine_name = st.text_input("اسم التحصين *", placeholder="مثال: Tdap")
        with c2:
            dose = st.number_input("الجرعة", min_value=1, max_value=10, value=1)

        c1, c2 = st.columns(2)
        with c1:
            scheduled = st.date_input("مجدول لتاريخ", value=date.today())
        with c2:
            status = st.selectbox(
                "الحالة",
                ["pending", "given"],
                format_func=lambda x: {"pending": "⏳ منتظرة", "given": "✅ تم إعطاؤها"}[x]
            )

        given_at = None
        if status == "given":
            given_at = st.date_input("تاريخ الإعطاء", value=date.today())

        batch = st.text_input("رقم الدفعة (Batch)", placeholder="اختياري")
        site = st.text_input("موضع الإعطاء", placeholder="مثال: ذراع أيسر")
        notes = st.text_area("ملاحظات", height=80)

        submitted = st.form_submit_button("💾 حفظ", use_container_width=True, type="primary")

    if submitted:
        if not vaccine_name:
            st.error("اسم التحصين مطلوب")
        else:
            try:
                create_vaccination(
                    clinic["id"], pid, vaccine_name,
                    dose_number=dose,
                    scheduled_for=scheduled.isoformat(),
                    status=status,
                    given_at=given_at.isoformat() if given_at else None,
                    batch_number=batch or None,
                    site=site or None,
                    notes=notes or None,
                    doctor_id=user["id"],
                )
                clear_all()
                st.success("✅ تم الحفظ")
                st.session_state["vacc_view"] = "list"
                time.sleep(0.8)
                st.rerun()
            except VaccinationError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))

    st.divider()
    st.markdown("### ⚡ توليد جدول تلقائي")
    st.caption("ينشئ جدول تحصينات قياسي حسب EDD للحامل المختارة")

    # Auto schedule section
    with st.form("auto_schedule_form"):
        patient_for_auto = st.selectbox(
            "الحامل",
            options=list(patient_map.keys()),
            format_func=lambda x: patient_map[x],
            key="auto_vacc_patient"
        )
        submitted_auto = st.form_submit_button("⚡ توليد الجدول", use_container_width=True)

    if submitted_auto:
        p = get_patient_summary_cached(clinic["id"], patient_for_auto)
        if not p or not p.get("edd"):
            st.error("❌ الحامل ليس لديها EDD. أضف LMP أولاً.")
        else:
            try:
                created = auto_schedule_defaults(
                    clinic["id"], patient_for_auto, p["edd"], user["id"]
                )
                clear_all()
                if created:
                    st.success("✅ تم إنشاء {} تحصين".format(len(created)))
                    for c in created:
                        st.write("- {} ({})".format(c["vaccine_name"], c["scheduled_for"]))
                else:
                    st.info("الجدول موجود مسبقاً")
            except Exception as e:
                st.error(str(e))


def _kpi(label, value, color):
    st.markdown("""
    <div style="background:white; border-radius:10px; padding:0.75rem; text-align:center; border-right:3px solid {color}; box-shadow:0 1px 4px rgba(0,0,0,0.05);">
        <div style="font-size:1.5rem; font-weight:800; color:{color};">{value}</div>
        <div style="font-size:0.75rem; color:#6B7280;">{label}</div>
    </div>
    """.format(color=color, value=value, label=label), unsafe_allow_html=True)
