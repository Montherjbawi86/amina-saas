# -*- coding: utf-8 -*-
"""WhatsApp messaging UI"""
import streamlit as st

from services.messaging import (
    list_templates, render_message, build_whatsapp_link,
    appointment_reminder_message, vaccination_reminder_message,
    follow_up_message, congratulations_message, lab_result_message,
    general_inquiry_message, MessageError,
)


# ============================================
# COMPONENTS
# ============================================
def render_send_dialog(clinic, patient, template_key="appointment_reminder",
                        extra_vars=None, key_prefix="msg"):
    """
    Render WhatsApp send dialog.
    extra_vars can include: appt_date, appt_time, appt_type, appt_dt,
                           vaccine_name, vacc_date
    """
    extra_vars = extra_vars or {}

    name = patient.get("full_name", "—")
    phone = patient.get("phone", "")

    if not phone:
        st.error("❌ لا يوجد رقم هاتف لهذه الحامل")
        return

    # Template selector
    templates = list_templates()
    options = [t["key"] for t in templates]
    labels = {t["key"]: "{} {}".format(t["icon"], t["label"]) for t in templates}

    template_key = st.selectbox(
        "القالب",
        options=options,
        format_func=lambda x: labels[x],
        index=options.index(template_key) if template_key in options else 0,
        key="tpl_" + key_prefix
    )

    # ========== VARIABLES ==========
    variables = {
        "name": name,
        "clinic_name": clinic.get("name", ""),
    }

    # Handle appointment date/time
    appt_dt = extra_vars.get("appt_dt") or extra_vars.get("appt_date")
    if appt_dt:
        try:
            if hasattr(appt_dt, "strftime"):
                dt = appt_dt
            else:
                dt = datetime.fromisoformat(str(appt_dt).replace("Z", ""))
            variables["appt_date"] = dt.strftime("%Y-%m-%d")
            variables["appt_time"] = dt.strftime("%H:%M")
        except Exception:
            s = str(appt_dt)
            variables["appt_date"] = s[:10]
            variables["appt_time"] = ""
    else:
        # Default: now + 7 days at 10:00
        from datetime import datetime as _dt, timedelta as _td
        default_dt = _dt.now().replace(hour=10, minute=0, second=0, microsecond=0) + _td(days=7)
        variables["appt_date"] = default_dt.strftime("%Y-%m-%d")
        variables["appt_time"] = default_dt.strftime("%H:%M")

    # Appointment type
    variables["appt_type"] = extra_vars.get("appt_type") or "متابعة دورية"

    # Vaccination
    if extra_vars.get("vaccine_name"):
        variables["vaccine_name"] = extra_vars["vaccine_name"]
    if extra_vars.get("vacc_date"):
        variables["vacc_date"] = str(extra_vars["vacc_date"])[:10]

    # Merge remaining extra vars (without overwriting)
    for k, v in extra_vars.items():
        if k not in variables:
            variables[k] = v

    # ========== EDITABLE FIELDS for appointment ==========
    if template_key in ("appointment_reminder", "appointment_confirm"):
        with st.expander("✏️ تعديل التاريخ والوقت", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                try:
                    _def_date = datetime.strptime(variables["appt_date"], "%Y-%m-%d").date()
                except Exception:
                    from datetime import date as _date
                    _def_date = _date.today()
                new_date = st.date_input("التاريخ", value=_def_date, key="ed_date_" + key_prefix)
            with c2:
                try:
                    _def_time = datetime.strptime(variables.get("appt_time") or "10:00", "%H:%M").time()
                except Exception:
                    from datetime import time as _time
                    _def_time = _time(10, 0)
                new_time = st.time_input("الوقت", value=_def_time, key="ed_time_" + key_prefix)

            new_type = st.text_input(
                "النوع",
                value=variables.get("appt_type", "متابعة دورية"),
                key="ed_type_" + key_prefix
            )

            variables["appt_date"] = new_date.strftime("%Y-%m-%d")
            variables["appt_time"] = new_time.strftime("%H:%M")
            variables["appt_type"] = new_type

    # ========== RENDER MESSAGE ==========
    if template_key == "custom":
        custom_text = st.text_area(
            "نص الرسالة",
            height=180,
            key="custom_" + key_prefix,
            placeholder="اكتب رسالتك..."
        )
        variables["custom_text"] = custom_text
        message = custom_text
    else:
        message = render_message(template_key, variables)

    # ========== PREVIEW ==========
    st.markdown("##### 👁️ المعاينة")
    st.text_area(
        "الرسالة",
        value=message,
        height=250,
        key="preview_" + key_prefix,
        label_visibility="collapsed"
    )

    st.caption("📞 سيتم الإرسال إلى: **{}**".format(phone))

    # ========== BUTTONS ==========
    c1, c2 = st.columns(2)
    with c1:
        try:
            wa_link = build_whatsapp_link(phone, message)
            st.link_button(
                "📱 إرسال WhatsApp",
                wa_link,
                use_container_width=True,
                type="primary"
            )
        except MessageError as e:
            st.error(str(e))
    with c2:
        if st.button("📋 نسخ النص", use_container_width=True, key="copy_" + key_prefix):
            st.code(message, language=None)
            st.success("انسخي النص يدوياً")


def send_button_inline(clinic, patient, template_key, extra_vars=None,
                        label="📱 إرسال WhatsApp", key_suffix=""):
    """Compact button to open WhatsApp directly"""
    if not patient or not patient.get("phone"):
        return

    name = patient.get("full_name", "")
    phone = patient.get("phone", "")

    variables = {
        "name": name,
        "clinic_name": clinic.get("name", ""),
    }
    if extra_vars:
        variables.update(extra_vars)

    try:
        if template_key == "appointment_reminder":
            msg = appointment_reminder_message(
                name, clinic["name"],
                variables.get("appt_dt", ""), variables.get("appt_type", "")
            )
        elif template_key == "vaccination_reminder":
            msg = vaccination_reminder_message(
                name, clinic["name"],
                variables.get("vaccine_name", ""), variables.get("vacc_date", "")
            )
        elif template_key == "follow_up":
            msg = follow_up_message(name, clinic["name"])
        elif template_key == "congratulations":
            msg = congratulations_message(name, clinic["name"])
        elif template_key == "lab_result":
            msg = lab_result_message(name, clinic["name"])
        elif template_key == "general_inquiry":
            msg = general_inquiry_message(name, clinic["name"])
        else:
            msg = render_message(template_key, variables)

        link = build_whatsapp_link(phone, msg)
        st.link_button(label, link, use_container_width=True)
    except Exception as e:
        st.caption("⚠️ {}".format(str(e)[:40]))


# ============================================
# PATIENT DETAIL WIDGET
# ============================================
def patient_messaging_section(clinic, patient):
    """Full messaging section for patient detail page"""
    with st.expander("📱 إرسال رسالة WhatsApp", expanded=False):
        if not patient.get("phone"):
            st.warning("⚠️ لا يوجد رقم هاتف مسجل")
            return
        render_send_dialog(clinic, patient, key_prefix="pat_" + str(patient.get("id", ""))[:8])


# ============================================
# APPOINTMENT REMINDER BUTTON
# ============================================
def appointment_reminder_button(clinic, patient, appt):
    """Compact reminder button for appointments list (opens WhatsApp directly)"""
    if not patient or not patient.get("phone"):
        return

    from services.appointments import TYPE_LABELS
    type_label = TYPE_LABELS.get(appt.get("type", "routine"), "موعد")

    # Build the message directly
    try:
        from services.messaging import appointment_reminder_message, build_whatsapp_link
        msg = appointment_reminder_message(
            patient.get("full_name", ""),
            clinic.get("name", ""),
            appt.get("scheduled_at", ""),
            type_label
        )
        link = build_whatsapp_link(patient.get("phone", ""), msg)
        st.link_button("📱 تذكير", link, use_container_width=True)
    except Exception as e:
        st.caption("⚠️ {}".format(str(e)[:40]))
