# -*- coding: utf-8 -*-
"""Public pregnancy certificate viewer — no auth required"""
from datetime import datetime
import streamlit as st

from services.certificates import get_certificate


def _format_date(v):
    if not v:
        return "—"
    return str(v)[:10]


def _gestational_display(weeks, days):
    if weeks is None:
        return "—"
    if days:
        return "{} أسبوع + {} يوم".format(weeks, days)
    return "{} أسبوع".format(weeks)


def render_public_cert():
    """Render public certificate verification page"""
    token = None
    try:
        if hasattr(st, "query_params"):
            token = st.query_params.get("cert")
    except Exception:
        pass

    if not token:
        st.error("❌ رابط غير صالح")
        return

    # Fetch from DB
    cert = get_certificate(token)

    if not cert:
        st.markdown("""
        <div style="text-align:center; padding:3rem 1rem;">
            <div style="font-size:4rem;">❌</div>
            <h2 style="color:#B91C1C;">شهادة غير صالحة</h2>
            <p style="color:#64748B;">هذه الشهادة غير موجودة أو تم إلغاؤها.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    snap = cert.get("snapshot", {})
    if not snap:
        st.error("❌ بيانات الشهادة تالفة")
        return

    patient = snap.get("patient", {})
    pregnancy = snap.get("pregnancy", {})
    visits = snap.get("visits", {})
    clinic = snap.get("clinic", {})
    doctor = snap.get("doctor", {})

    # ============ HEADER ============
    st.markdown("""
    <div style="background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
                border-radius: 16px; padding: 2rem 1.5rem; text-align: center;
                color: white; margin-bottom: 1.5rem;">
        <div style="font-size: 3rem;">✅</div>
        <h1 style="color: white !important; margin: 0.5rem 0 0 0; font-size: 1.6rem;">
            شهادة حمل موثّقة
        </h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.95;">{clinic}</p>
    </div>
    """.format(clinic=clinic.get("name", "العيادة")), unsafe_allow_html=True)

    # ============ VERIFICATION BADGE ============
    st.success("✅ هذه الشهادة صادرة رسمياً من النظام")

    # ============ PATIENT INFO ============
    st.markdown("### 👩 معلومات الحامل")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**الاسم:** {}".format(patient.get("full_name", "—")))
        st.write("**الهاتف:** {}".format(patient.get("phone", "—")))
        st.write("**الرقم الوطني:** {}".format(patient.get("national_id") or "—"))
    with c2:
        st.write("**تاريخ الميلاد:** {}".format(_format_date(patient.get("date_of_birth"))))
        st.write("**فصيلة الدم:** {}".format(patient.get("blood_type") or "—"))
        st.write("**مستوى الخطر:** {}".format(patient.get("risk_level") or "—"))

    st.divider()

    # ============ PREGNANCY DETAILS ============
    st.markdown("### 🤰 تفاصيل الحمل")
    c3, c4 = st.columns(2)
    with c3:
        st.write("**آخر دورة (LMP):** {}".format(_format_date(pregnancy.get("lmp"))))
        st.write("**الولادة المتوقعة (EDD):** {}".format(_format_date(pregnancy.get("edd"))))
    with c4:
        st.write("**عمر الحمل:** {}".format(_gestational_display(
            pregnancy.get("gestational_weeks"),
            pregnancy.get("gestational_days"))))
        st.write("**G/P:** {}/{}".format(
            pregnancy.get("gravida") or 0,
            pregnancy.get("para") or 0))

    st.divider()

    # ============ VISITS SUMMARY ============
    st.markdown("### 📋 ملخص المتابعة")
    c5, c6 = st.columns(2)
    with c5:
        st.write("**عدد الزيارات:** {}".format(visits.get("count", 0)))
    with c6:
        st.write("**آخر زيارة:** {}".format(_format_date(visits.get("last_visit_date"))))

    st.divider()

    # ============ DOCTOR / ISSUE INFO ============
    st.markdown("### 👩‍⚕️ معلومات الإصدار")
    c7, c8 = st.columns(2)
    with c7:
        st.write("**الطبيبة:** {}".format(doctor.get("name") or "—"))
    with c8:
        st.write("**تاريخ الإصدار:** {}".format(_format_date(cert.get("issued_at"))))

    # Notes
    if snap.get("notes"):
        st.markdown("### 📝 توصيات الطبيبة")
        st.info(snap["notes"])

    # ============ FOOTER ============
    st.markdown("""
    <div style="text-align:center; padding:2rem 1rem; color:#94A3B8; font-size:0.8rem; border-top:1px solid #E2E8F0; margin-top:2rem;">
        <div><b style="color:#16A34A;">👶 أمينة SaaS</b></div>
        <div style="margin-top:0.5rem;">رقم الشهادة: {cert_id}</div>
        <div style="margin-top:0.5rem;">هذه الصفحة للتحقق الرسمي من الشهادة</div>
    </div>
    """.format(cert_id=str(cert.get("id", ""))[:8].upper()), unsafe_allow_html=True)
