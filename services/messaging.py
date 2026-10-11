# -*- coding: utf-8 -*-
"""WhatsApp messaging — improved templates"""
import re
from datetime import datetime
from urllib.parse import quote


class MessageError(Exception):
    pass


def normalize_phone(phone):
    if not phone:
        return None
    digits = re.sub(r"[^0-9]", "", str(phone))
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


# ============================================
# IMPROVED TEMPLATES
# ============================================
TEMPLATES = {
    "appointment_reminder": {
        "label": "📅 تذكير موعد",
        "icon": "📅",
        "context": "appointment",
        "text": (
            "*تذكير بموعد*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "نذكّرك بموعدك في *{clinic_name}*:\n\n"
            "🗓️ التاريخ: *{appt_date}*\n"
            "⏰ الوقت: *{appt_time}*\n"
            "📋 النوع: {appt_type}\n"
            "━━━━━━━━━━━━━━━\n"
            "يرجى الحضور قبل الموعد بـ *10 دقائق*.\n\n"
            "للتأكيد أو التعديل، يرجى الرد على هذه الرسالة.\n\n"
            "_مع تمنياتنا لك بالصحة والعافية_ 💜"
        ),
    },
    "appointment_confirm": {
        "label": "✅ تأكيد موعد",
        "icon": "✅",
        "context": "appointment",
        "text": (
            "*تأكيد موعد*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "تم *تأكيد* موعدك في {clinic_name}:\n\n"
            "🗓️ التاريخ: *{appt_date}*\n"
            "⏰ الوقت: *{appt_time}*\n"
            "📋 النوع: {appt_type}\n"
            "━━━━━━━━━━━━━━━\n"
            "نراك على خير 💜"
        ),
    },
    "vaccination_reminder": {
        "label": "💉 تذكير تحصين",
        "icon": "💉",
        "context": "vaccination",
        "text": (
            "*تذكير بموعد تحصين*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "نذكّرك بموعد التحصين في *{clinic_name}*:\n\n"
            "💉 التحصين: *{vaccine_name}*\n"
            "🗓️ التاريخ: *{vacc_date}*\n"
            "━━━━━━━━━━━━━━━\n"
            "يرجى الحضور في الموعد المحدد.\n\n"
            "_مع تمنياتنا لك بالصحة_ 💜"
        ),
    },
    "follow_up": {
        "label": "🩺 متابعة",
        "icon": "🩺",
        "context": "patient",
        "text": (
            "*متابعة صحية*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "لاحظنا أنك لم تزوري *{clinic_name}* مؤخراً.\n\n"
            "صحتك وصحة جنينك تهمنا! 💜\n\n"
            "نرجو التواصل معنا لحجز موعد المتابعة.\n\n"
            "_نحن هنا لخدمتك في أي وقت_"
        ),
    },
    "congratulations": {
        "label": "🎉 تهانٍ بولادة",
        "icon": "🎉",
        "context": "patient",
        "text": (
            "*ألف مبروك!* 🎉\n"
            "━━━━━━━━━━━━━━━\n"
            "*{name}* الغالية 🌸\n\n"
            "نهنئك بقدوم مولودك الجديد!\n"
            "نسأل الله أن يجعله من الصالحين 🌟\n\n"
            "لا تنسي زيارتنا للمتابعة بعد الولادة.\n\n"
            "_بالرفاء والبنين_ 💜"
        ),
    },
    "lab_result": {
        "label": "📊 نتيجة تحليل",
        "icon": "📊",
        "context": "patient",
        "text": (
            "*نتائج التحاليل جاهزة*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "نتائج تحاليلك الأخيرة في *{clinic_name}* جاهزة.\n\n"
            "يرجى المرور لاستلامها ومناقشتها مع الطبيبة.\n\n"
            "_مع تمنياتنا بالصحة_ 💜"
        ),
    },
    "general_inquiry": {
        "label": "📱 استفسار عام",
        "icon": "📱",
        "context": "patient",
        "text": (
            "*من {clinic_name}*\n"
            "━━━━━━━━━━━━━━━\n"
            "السلام عليكم *{name}* 🌸\n\n"
            "كيف حالك؟ نتمنى أن تكوني بخير.\n\n"
            "نحن هنا لخدمتك في أي استفسار.\n\n"
            "_لا تترددي بالتواصل معنا_ 💜"
        ),
    },
    "custom": {
        "label": "✏️ رسالة مخصصة",
        "icon": "✏️",
        "context": "patient",
        "text": "",
    },
}


def get_template(key):
    return TEMPLATES.get(key)


def list_templates(context=None):
    items = []
    for key, t in TEMPLATES.items():
        if context and t.get("context") != context:
            continue
        items.append({"key": key, "label": t["label"], "icon": t["icon"]})
    return items


def render_message(template_key, variables):
    tpl = TEMPLATES.get(template_key)
    if not tpl:
        raise MessageError("قالب غير موجود")
    if template_key == "custom":
        return variables.get("custom_text", "")
    text = tpl["text"]
    for k, v in variables.items():
        text = text.replace("{" + k + "}", str(v))
    text = re.sub(r"\{[^}]+\}", "", text)
    return text


def build_whatsapp_link(phone, message):
    p = normalize_phone(phone)
    if not p:
        raise MessageError("رقم هاتف غير صحيح")
    encoded = quote(message, safe="")
    base = "https://wa.me/"
    return base + p + "?text=" + encoded


def appointment_reminder_message(patient_name, clinic_name, appt_dt, appt_type_label):
    try:
        dt = datetime.fromisoformat(str(appt_dt).replace("Z", ""))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    except Exception:
        date_str = str(appt_dt)[:10]
        time_str = ""
    return render_message("appointment_reminder", {
        "name": patient_name, "clinic_name": clinic_name,
        "appt_date": date_str, "appt_time": time_str, "appt_type": appt_type_label,
    })


def vaccination_reminder_message(patient_name, clinic_name, vaccine_name, vacc_date):
    return render_message("vaccination_reminder", {
        "name": patient_name, "clinic_name": clinic_name,
        "vaccine_name": vaccine_name, "vacc_date": str(vacc_date or "")[:10],
    })


def follow_up_message(patient_name, clinic_name):
    return render_message("follow_up", {"name": patient_name, "clinic_name": clinic_name})


def congratulations_message(patient_name, clinic_name):
    return render_message("congratulations", {"name": patient_name, "clinic_name": clinic_name})


def lab_result_message(patient_name, clinic_name):
    return render_message("lab_result", {"name": patient_name, "clinic_name": clinic_name})


def general_inquiry_message(patient_name, clinic_name):
    return render_message("general_inquiry", {"name": patient_name, "clinic_name": clinic_name})


if __name__ == "__main__":
    print("=" * 50)
    print("Messaging Test")
    print("=" * 50)
    for p in ["+964 770 123 4567", "0770-123-4567"]:
        print("   {} -> {}".format(p, normalize_phone(p)))
    msg = appointment_reminder_message("فاطمة أحمد", "عيادة النور", "2026-10-15T10:00:00", "متابعة دورية")
    print("\n--- Template output ---")
    print(msg)
    print("\n--- wa.me link ---")
    link = build_whatsapp_link("+9647701234567", msg)
    print(link[:120] + "...")
    print("\nMessaging module OK")
