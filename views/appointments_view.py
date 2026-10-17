# -*- coding: utf-8 -*-
"""Appointments view for Streamlit"""
from datetime import datetime, timedelta, date
import streamlit as st

from services.appointments import (
    list_appointments_cached, create_appointment, update_appointment,
    delete_appointment, get_appointment, count_by_status,
    STATUS_LABELS, TYPE_LABELS,
    get_status_color, get_status_icon, get_type_icon,
    AppointmentError,
)
from services.patients import list_patients_cached
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Render appointments tab"""
    view = st.session_state.get("appt_view", "list")

    if view == "list":
        _render_list(clinic, user)
    elif view == "new":
        _render_new(clinic, user)


# ============================================
# LIST VIEW
# ============================================
def _render_list(clinic, user):
    st.markdown("### 📅 المواعيد")

    # ============ FILTERS ============
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        period = st.selectbox(
            "الفترة",
            ["اليوم", "غداً", "هذا الأسبوع", "الأسبوع القادم", "هذا الشهر", "الكل"],
            key="appt_period"
        )
    with c2:
        status_filter = st.selectbox(
            "الحالة",
            ["الكل"] + list(STATUS_LABELS.keys()),
            format_func=lambda x: "الكل" if x == "الكل" else STATUS_LABELS[x],
            key="appt_status"
        )
    with c3:
        st.write("")
        show_cache_status("appt_cache_updated")
    with c4:
        st.write("")
        if st.button("➕ موعد", use_container_width=True, type="primary", key="new_appt_btn"):
            st.session_state["appt_view"] = "new"
            st.rerun()

    # ============ COMPUTE RANGE ============
    today = date.today()
    if period == "اليوم":
        from_iso = datetime.combine(today, datetime.min.time()).isoformat()
        to_iso = datetime.combine(today, datetime.max.time()).isoformat()
    elif period == "غداً":
        tomorrow = today + timedelta(days=1)
        from_iso = datetime.combine(tomorrow, datetime.min.time()).isoformat()
        to_iso = datetime.combine(tomorrow, datetime.max.time()).isoformat()
    elif period == "هذا الأسبوع":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        from_iso = datetime.combine(start, datetime.min.time()).isoformat()
        to_iso = datetime.combine(end, datetime.max.time()).isoformat()
    elif period == "الأسبوع القادم":
        start = today + timedelta(days=7 - today.weekday())
        end = start + timedelta(days=6)
        from_iso = datetime.combine(start, datetime.min.time()).isoformat()
        to_iso = datetime.combine(end, datetime.max.time()).isoformat()
    elif period == "هذا الشهر":
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        from_iso = datetime.combine(start, datetime.min.time()).isoformat()
        to_iso = datetime.combine(end, datetime.max.time()).isoformat()
    else:  # الكل
        from_iso = None
        to_iso = None

    status_val = None if status_filter == "الكل" else status_filter

    # ============ STATS ============
    counts = count_by_status(clinic["id"])
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi_small("🔵 منتظر", counts.get("scheduled", 0), "#22C55E")
    with c2:
        _kpi_small("🟢 مؤكد", counts.get("confirmed", 0), "#10B981")
    with c3:
        _kpi_small("✅ مكتمل", counts.get("completed", 0), "#6B7280")
    with c4:
        _kpi_small("🔴 ملغى", counts.get("cancelled", 0), "#EF4444")
    with c5:
        _kpi_small("🟠 لم يحضر", counts.get("no_show", 0), "#F59E0B")

    st.divider()

    # ============ LOAD ============
    with st.spinner("جاري التحميل..."):
        appts = list_appointments_cached(clinic["id"], from_iso, to_iso, status_val)

    if not appts:
        st.info("📭 لا توجد مواعيد في هذه الفترة")
        return

    st.markdown("**العدد: {}**".format(len(appts)))

    # Group by date
    grouped = {}
    for a in appts:
        try:
            dt = datetime.fromisoformat(a["scheduled_at"].replace("Z", ""))
            key = dt.date()
        except Exception:
            key = None
        grouped.setdefault(key, []).append(a)

    # Load patients for names
    patients = {p["id"]: p for p in list_patients_cached(clinic["id"])}

    for day in sorted([k for k in grouped.keys() if k is not None]):
        is_today = day == today
        is_tomorrow = day == (today + timedelta(days=1))
        label = day.strftime("%Y-%m-%d (%A)")
        if is_today:
            label = "🟢 اليوم — " + day.strftime("%Y-%m-%d")
        elif is_tomorrow:
            label = "🟡 غداً — " + day.strftime("%Y-%m-%d")

        st.markdown("#### {}".format(label))

        for a in grouped[day]:
            _render_appointment_card(a, patients, clinic, user)

    st.divider()


# ============================================
# SINGLE CARD
# ============================================
def _render_appointment_card(a, patients, clinic, user):
    patient = patients.get(a["patient_id"], {})
    name = patient.get("full_name", "مريضة غير معروفة")
    phone = patient.get("phone", "")

    try:
        dt = datetime.fromisoformat(a["scheduled_at"].replace("Z", ""))
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = "—"

    status = a.get("status", "scheduled")
    s_color = get_status_color(status)
    s_icon = get_status_icon(status)
    s_label = STATUS_LABELS.get(status, status)

    type_key = a.get("type", "routine")
    t_icon = get_type_icon(type_key)
    t_label = TYPE_LABELS.get(type_key, type_key)

    notes_html = ""
    if a.get("notes"):
        notes_html = '<div style="font-size:0.75rem; color:#9CA3AF; margin-top:0.25rem;">📝 {}</div>'.format(a["notes"])

    card_html = (
        '<div style="background:white; border-radius:12px; padding:0.85rem 1rem; '
        'margin-bottom:0.5rem; border-right:5px solid ' + s_color + '; '
        'box-shadow:0 2px 6px rgba(0,0,0,0.05); display:flex; align-items:center; gap:1rem;">'
        '<div style="text-align:center; min-width:70px;">'
        '<div style="font-size:1.5rem; font-weight:800; color:' + s_color + ';">' + time_str + '</div>'
        '<div style="font-size:0.7rem; color:#9CA3AF;">' + str(a.get("duration_min", 30)) + ' د</div>'
        '</div>'
        '<div style="flex:1;">'
        '<div style="font-weight:700; color:#1F2937;">' + t_icon + ' ' + name + '</div>'
        '<div style="font-size:0.8rem; color:#6B7280; margin-top:0.25rem;">📞 ' + phone + ' &nbsp;|&nbsp; ' + t_label + '</div>'
        + notes_html +
        '</div>'
        '<div style="text-align:center;">'
        '<div style="background:' + s_color + '; color:white; padding:0.25rem 0.75rem; '
        'border-radius:999px; font-size:0.75rem; font-weight:700;">'
        + s_icon + ' ' + s_label +
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

    # Actions
    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 2])
    with c1:
        if status == "scheduled":
            if st.button("✅ تأكيد", key="conf_" + a["id"], use_container_width=True):
                update_appointment(clinic["id"], a["id"], status="confirmed")
                clear_all()
                st.success("تم التأكيد")
    with c2:
        if status in ("scheduled", "confirmed"):
            if st.button("✔️ إتمام", key="comp_" + a["id"], use_container_width=True):
                update_appointment(clinic["id"], a["id"], status="completed")
                clear_all()
                st.success("تم الإتمام")
    with c3:
        if status in ("scheduled", "confirmed"):
            if st.button("❌ إلغاء", key="canc_" + a["id"], use_container_width=True):
                update_appointment(clinic["id"], a["id"], status="cancelled")
                clear_all()
                st.rerun()
    with c4:
        if st.button("🗑️ حذف", key="del_" + a["id"], use_container_width=True):
            if st.session_state.get("confirm_apt_del") == a["id"]:
                delete_appointment(clinic["id"], a["id"])
                clear_all()
                st.session_state["confirm_apt_del"] = None
                st.rerun()
            else:
                st.session_state["confirm_apt_del"] = a["id"]
                st.warning("اضغط مرة أخرى للتأكيد")
    with c5:
        try:
            from views.messaging_view import appointment_reminder_button
            _pat = patients.get(a["patient_id"])
            if _pat:
                appointment_reminder_button(clinic, _pat, a)
        except Exception:
            st.write("")
    st.write("")


# ============================================
# NEW APPOINTMENT
# ============================================
def _render_new(clinic, user):
    st.markdown("### ➕ حجز موعد جديد")
    if st.button("⬅️ رجوع للقائمة", key="back_list_from_new"):
        st.session_state["appt_view"] = "list"
        st.rerun()

    # Optional: preselect patient
    preselected_pid = st.session_state.get("selected_patient_id")

    patients = list_patients_cached(clinic["id"])
    if not patients:
        st.warning("⚠️ لا توجد حوامل مسجلات. أضف حاملاً أولاً.")
        return

    patient_map = {p["id"]: "{} — {}".format(p["full_name"], p["phone"]) for p in patients}

    with st.form("new_appt_form"):
        # Patient
        default_idx = 0
        if preselected_pid and preselected_pid in patient_map:
            default_idx = list(patient_map.keys()).index(preselected_pid)

        pid = st.selectbox(
            "الحامل *",
            options=list(patient_map.keys()),
            format_func=lambda x: patient_map[x],
            index=default_idx
        )

        # Date + time
        c1, c2 = st.columns(2)
        with c1:
            apt_date = st.date_input("التاريخ *", value=date.today())
        with c2:
            apt_time = st.time_input("الوقت *", value=datetime.now().replace(hour=10, minute=0, second=0).time())

        # Duration + type
        c1, c2 = st.columns(2)
        with c1:
            duration = st.number_input("المدة (دقيقة)", min_value=10, max_value=180, value=30, step=5)
        with c2:
            apt_type = st.selectbox(
                "النوع",
                options=list(TYPE_LABELS.keys()),
                format_func=lambda x: "{} {}".format(get_type_icon(x), TYPE_LABELS[x])
            )

        notes = st.text_area("ملاحظات", height=80)

        submitted = st.form_submit_button("💾 حفظ الموعد", use_container_width=True, type="primary")

    if submitted:
        try:
            scheduled = datetime.combine(apt_date, apt_time)
            create_appointment(
                clinic_id=clinic["id"],
                patient_id=pid,
                scheduled_at=scheduled,
                doctor_id=user["id"],
                duration_min=duration,
                type=apt_type,
                notes=notes or None,
            )
            clear_all()
            st.success("✅ تم حفظ الموعد")
            st.balloons()
            st.session_state["appt_view"] = "list"
            import time
            time.sleep(0.8)
            st.rerun()
        except AppointmentError as e:
            st.error(str(e))
        except Exception as e:
            st.error("خطأ: {}".format(e))


# ============================================
# KPI SMALL
# ============================================
def _kpi_small(label, value, color):
    st.markdown("""
    <div style="background:white; border-radius:10px; padding:0.6rem 0.75rem; text-align:center; border-right:3px solid {color}; box-shadow:0 1px 4px rgba(0,0,0,0.05);">
        <div style="font-size:1.5rem; font-weight:800; color:{color};">{value}</div>
        <div style="font-size:0.75rem; color:#6B7280;">{label}</div>
    </div>
    """.format(color=color, value=value, label=label), unsafe_allow_html=True)


# ============================================
# WIDGET: QUICK BOOK (used in patient detail)
# ============================================
def quick_book_appointment(clinic, user, patient_id):
    """Small form for quick booking from patient detail"""
    with st.form("quick_book_form_" + patient_id):
        st.markdown("##### 📅 حجز موعد سريع")
        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input("التاريخ", value=date.today() + timedelta(days=7), key="qb_d_" + patient_id)
        with c2:
            t = st.time_input("الوقت", value=datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).time(), key="qb_t_" + patient_id)

        c1, c2 = st.columns(2)
        with c1:
            dur = st.number_input("المدة (د)", min_value=10, max_value=180, value=30, step=5, key="qb_dur_" + patient_id)
        with c2:
            t_type = st.selectbox("النوع", options=list(TYPE_LABELS.keys()),
                format_func=lambda x: "{} {}".format(get_type_icon(x), TYPE_LABELS[x]),
                key="qb_type_" + patient_id)

        notes = st.text_input("ملاحظات", key="qb_notes_" + patient_id)

        if st.form_submit_button("💾 حجز", use_container_width=True, type="primary"):
            try:
                scheduled = datetime.combine(d, t)
                create_appointment(
                    clinic_id=clinic["id"], patient_id=patient_id,
                    scheduled_at=scheduled, doctor_id=user["id"],
                    duration_min=dur, type=t_type, notes=notes or None,
                )
                clear_all()
                st.success("✅ تم حجز الموعد")
                st.balloons()
            except AppointmentError as e:
                st.error(str(e))
