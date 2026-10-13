# -*- coding: utf-8 -*-
"""
Pregnancy Certificate View
واجهة إصدار شهادات الحمل
"""
from datetime import date
from urllib.parse import quote
import os
import streamlit as st

from core.db import db
from core.ui import page_header, spacer
from services.certificate_pdf import generate_certificate_pdf
from services.certificates import create_certificate, build_snapshot


def _fetch_patients(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id, full_name, phone, national_id")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
            .data or []
        )
    except Exception:
        return []


def _fetch_patient_full(clinic_id, patient_id):
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


def _fetch_visits(clinic_id, patient_id):
    try:
        visits = (
            db().table("visits")
            .select("visit_date, doctor_id")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .order("visit_date", desc=True)
            .execute()
            .data or []
        )
        # Enrich with doctor name
        if visits:
            doctor_ids = list({v.get("doctor_id") for v in visits if v.get("doctor_id")})
            doctors_map = {}
            if doctor_ids:
                docs = (
                    db().table("users")
                    .select("id, full_name")
                    .in_("id", doctor_ids)
                    .execute()
                    .data or []
                )
                doctors_map = {d["id"]: d.get("full_name", "") for d in docs}
            for v in visits:
                v["_doctor_name"] = doctors_map.get(v.get("doctor_id"), "")
        return visits
    except Exception:
        return []


def _generate_for_patient(clinic, user, patient_id):
    """Generate certificate, save to DB, store in session"""
    patient = _fetch_patient_full(clinic["id"], patient_id)
    if not patient:
        st.error("❌ لم يتم العثور على الحامل")
        return

    visits = _fetch_visits(clinic["id"], patient_id)
    doctor_name = user.get("full_name", "") if user else ""

    # 1. Build snapshot
    snapshot = build_snapshot(patient, visits, clinic, doctor_name)

    # 2. Save to DB
    cert_row = create_certificate(
        clinic_id=clinic["id"],
        patient_id=patient_id,
        issued_by=user.get("id") if user else None,
        snapshot=snapshot,
    )

    if not cert_row:
        st.error("❌ فشل حفظ الشهادة في قاعدة البيانات")
        return

    cert_id = cert_row.get("id")
    snapshot["certificate_id"] = cert_id

    # 3. Get site URL from config/env
    import os
    site_url = os.getenv("SITE_URL", "https://amina-saas.onrender.com")

    # 4. Generate PDF with QR -> URL
    try:
        pdf = generate_certificate_pdf(
            patient=patient,
            visits=visits,
            clinic=clinic,
            doctor_name=doctor_name,
            certificate_id=cert_id,
            site_url=site_url,
        )

        st.session_state["_cert_data"] = pdf
        fname = "certificate_{}_{}.pdf".format(
            patient.get("full_name", "patient").replace(" ", "_")[:30],
            date.today().strftime("%Y%m%d")
        )
        st.session_state["_cert_filename"] = fname
        st.session_state["_cert_patient_name"] = patient.get("full_name", "")
        st.session_state["_cert_id"] = str(cert_id)[:8].upper()
        st.session_state["_cert_full_id"] = str(cert_id)

        st.success("✅ تم توليد شهادة **{}**".format(patient.get("full_name", "")))
        st.caption("🔗 رابط التحقق: `{}/?cert={}`".format(site_url, cert_id))
    except Exception as e:
        st.error("❌ خطأ في التوليد")
        st.exception(e)




# ============ WHATSAPP HELPERS ============

def _normalize_phone(phone):
    """Convert phone to international format for wa.me (no +, no spaces)"""
    if not phone:
        return None
    # Remove spaces, dashes, parens
    p = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    # Remove leading +
    if p.startswith("+"):
        p = p[1:]
    # Remove leading 00
    if p.startswith("00"):
        p = p[2:]
    # Iraq default: if starts with 0, add 964
    if p.startswith("0"):
        p = "964" + p[1:]
    # If no country code and short, add 964
    if len(p) < 10:
        p = "964" + p
    return p


def _build_whatsapp_message(patient_name, clinic_name, doctor_name, cert_url):
    """Build WhatsApp message in Arabic"""
    msg = """مرحباً {name} 🌸

شهادة حملك الرسمية من *{clinic}* جاهزة:

🔗 {url}

📋 افتحي الرابط للتحقق من الشهادة وتحميل PDF.

مع تحيات،
د. {doctor}""".format(
        name=patient_name,
        clinic=clinic_name,
        url=cert_url,
        doctor=doctor_name or "الطبيبة"
    )
    return msg


def _build_wa_url(phone, message):
    """Build wa.me URL"""
    normalized = _normalize_phone(phone)
    if not normalized:
        return None
    encoded = quote(message)
    return "https://wa.me/{}?text={}".format(normalized, encoded)



def render(clinic, user):
    page_header(
        "شهادة حمل",
        "إصدار شهادة حمل رسمية PDF مع QR للتحقق",
        icon="📄"
    )

    # ========== Generate from selected patient ==========
    patients = _fetch_patients(clinic["id"])

    if not patients:
        st.warning("⚠️ لا يوجد حوامل مسجلات")
        st.info("👉 سجّل حاملاً أولاً من قسم **👩 الحوامل**")
        return

    st.markdown("#### 1️⃣ اختر الحامل")

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    selected_id = st.selectbox(
        "الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="cert_patient_select",
        label_visibility="collapsed"
    )

    st.markdown("#### 2️⃣ إصدار الشهادة")
    spacer(1)

    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("📄 توليد الشهادة", type="primary", use_container_width=True,
                     key="cert_generate_btn"):
            with st.spinner("⏳ جاري التوليد..."):
                _generate_for_patient(clinic, user, selected_id)

    # ========== Download + Share buttons ==========
    if "_cert_data" in st.session_state and st.session_state["_cert_data"]:
        st.divider()
        st.markdown("#### 3️⃣ شارك / حمّل الشهادة")

        size_kb = len(st.session_state["_cert_data"]) / 1024.0
        patient_name = st.session_state.get("_cert_patient_name", "")
        cert_id_short = st.session_state.get("_cert_id", "")

        # Info
        site_url = os.getenv("SITE_URL", "https://amina-saas.onrender.com").rstrip("/")
        cert_url = "{}/?cert={}".format(site_url, st.session_state.get("_cert_full_id", ""))
        st.info("📁 جاهز — **{}** — **{:.1f} KB**".format(patient_name, size_kb))

        # Verification link
        if cert_id_short:
            st.markdown("##### 🔗 رابط التحقق")
            st.code(cert_url, language=None)

        # Action buttons
        c1, c2 = st.columns(2)

        # WhatsApp button
        with c1:
            # Find patient phone
            selected_id = st.session_state.get("cert_patient_select")
            patients_list = _fetch_patients(clinic["id"])
            patient_phone = None
            for p in patients_list:
                if p["id"] == selected_id:
                    patient_phone = p.get("phone")
                    break

            wa_url = _build_wa_url(
                patient_phone,
                _build_whatsapp_message(
                    patient_name,
                    clinic.get("name", ""),
                    user.get("full_name", "") if user else "",
                    cert_url,
                )
            )

            if wa_url:
                st.link_button(
                    "📱 إرسال عبر WhatsApp",
                    wa_url,
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.button(
                    "📱 إرسال WhatsApp (لا يوجد رقم)",
                    disabled=True,
                    use_container_width=True,
                    key="wa_disabled"
                )

        # Download PDF
        with c2:
            st.download_button(
                label="⬇️ تحميل PDF",
                data=st.session_state["_cert_data"],
                file_name=st.session_state.get("_cert_filename", "certificate.pdf"),
                mime="application/pdf",
                use_container_width=True,
                key="cert_download_btn"
            )

        # Copy URL button
        st.markdown("##### 📋 نسخ الرابط")
        st.code(cert_url, language=None)
        st.caption("👆 اضغط على أيقونة النسخ بجانب الرابط")

        spacer(1)

        if st.button("🗑️ حذف من الذاكرة", key="cert_clear_btn"):
            st.session_state.pop("_cert_data", None)
            st.session_state.pop("_cert_filename", None)
            st.session_state.pop("_cert_patient_name", None)
            st.session_state.pop("_cert_id", None)
            st.session_state.pop("_cert_full_id", None)
            st.rerun()

    # ========== Help ==========
    spacer(2)
    with st.expander("📖 معلومات"):
        st.markdown("""
        ### ما تحتوي عليه الشهادة؟

        - 🏥 ترويسة العيادة + اسم الطبيبة
        - 👩 معلومات الحامل (الاسم، العمر، الرقم الوطني، فصيلة الدم)
        - 📅 تفاصيل الحمل (LMP، EDD، أسابيع الحمل الحالية، G/P)
        - 📊 ملخص المتابعة (عدد الزيارات، آخر زيارة)
        - 📋 توصيات الطبيبة (من ملاحظات الحامل)
        - 📱 QR للتحقق
        - ✍️ مكان للختم والتوقيع

        ### الاستخدامات

        - 📄 إجازة مرضية
        - 🏥 التسجيل في مستشفى الولادة
        - 📱 إرسال عبر WhatsApp للحامل
        - 🖨️ طباعة للحفظ في الملف
        """)


# ========== Helper: button inside patients view ==========
def quick_generate_button(clinic, user, patient_id, key_suffix=""):
    """
    زر سريع لإصدار شهادة لحامل معينة.
    يُستخدم داخل views/patients.py
    """
    if st.button("📄 شهادة حمل", key="quick_cert_{}".format(key_suffix),
                 use_container_width=True):
        with st.spinner("⏳ جاري التوليد..."):
            _generate_for_patient(clinic, user, patient_id)
        st.rerun()


def render_download_if_ready():
    """يُعرض زر التحميل إذا كانت هناك شهادة جاهزة في session"""
    if "_cert_data" in st.session_state and st.session_state["_cert_data"]:
        st.success("✅ الشهادة جاهزة: **{}**".format(
            st.session_state.get("_cert_patient_name", "")))

        size_kb = len(st.session_state["_cert_data"]) / 1024.0
        st.caption("📁 الحجم: {:.1f} KB".format(size_kb))

        st.download_button(
            label="⬇️ تحميل شهادة الحمل PDF",
            data=st.session_state["_cert_data"],
            file_name=st.session_state.get("_cert_filename", "certificate.pdf"),
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="cert_download_inline"
        )

        if st.button("🗑️ إخفاء", key="cert_clear_inline"):
            st.session_state.pop("_cert_data", None)
            st.session_state.pop("_cert_filename", None)
            st.session_state.pop("_cert_patient_name", None)
            st.rerun()
