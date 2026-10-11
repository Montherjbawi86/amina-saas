# -*- coding: utf-8 -*-
"""Public prescription viewer — no auth required"""
import streamlit as st
from datetime import datetime

from services.share_links import get_share_link, increment_view
from services.prescriptions import get_prescription
from services.patients import get_patient_summary
from core.db import db


def render_public_rx():
    """Render a public prescription page"""
    # Get token from query params
    token = None
    try:
        if hasattr(st, "query_params"):
            token = st.query_params.get("rx")
        if not token:
            params = st.experimental_get_query_params()
            token = params.get("rx", [None])[0]
    except Exception:
        pass

    if not token:
        st.error("❌ رابط غير صالح")
        return

    # Fetch link
    link = get_share_link(token)
    if not link:
        st.markdown("""
        <div style="text-align:center; padding:3rem 1rem;">
            <div style="font-size:4rem;">⏰</div>
            <h2 style="color:#B91C1C;">انتهت صلاحية الرابط</h2>
            <p style="color:#64748B;">هذا الرابط لم يعد صالحاً. يرجى التواصل مع العيادة.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Increment view
    increment_view(token)

    # Fetch prescription + patient + clinic
    try:
        rx = get_prescription(link["clinic_id"], link["resource_id"])
        if not rx:
            st.error("❌ الوصفة غير موجودة")
            return

        patient_rows = db().table("patients").select("*").eq("id", rx["patient_id"]).execute().data
        patient = patient_rows[0] if patient_rows else {}

        clinic_rows = db().table("clinics").select("*").eq("id", link["clinic_id"]).execute().data
        clinic = clinic_rows[0] if clinic_rows else {}
    except Exception as e:
        st.error("خطأ: {}".format(e))
        return

    # ============ HEADER ============
    st.markdown("""
    <div style="background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
                border-radius: 16px; padding: 2rem 1.5rem; text-align: center;
                color: white; margin-bottom: 1.5rem;">
        <div style="font-size: 3rem;">💊</div>
        <h1 style="color: white !important; margin: 0.5rem 0 0 0; font-size: 1.75rem;">
            وصفة طبية
        </h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.95;">{clinic}</p>
    </div>
    """.format(clinic=clinic.get("name", "العيادة")), unsafe_allow_html=True)

    # ============ PATIENT INFO ============
    st.markdown("### 👩 معلومات المريضة")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**الاسم:** {}".format(patient.get("full_name", "—")))
        st.write("**الهاتف:** {}".format(patient.get("phone", "—")))
    with c2:
        st.write("**فصيلة الدم:** {}".format(patient.get("blood_type") or "—"))
        try:
            d = datetime.fromisoformat(rx["issued_at"].replace("Z", ""))
            st.write("**التاريخ:** {}".format(d.strftime("%Y-%m-%d")))
        except Exception:
            st.write("**التاريخ:** —")

    st.divider()

    # ============ DIAGNOSIS ============
    if rx.get("diagnosis"):
        st.markdown("### 📋 التشخيص")
        st.info(rx["diagnosis"])

    # ============ MEDICATIONS ============
    st.markdown("### 💊 الأدوية الموصوفة")

    meds = rx.get("medications", [])
    for i, med in enumerate(meds, 1):
        st.markdown("""
        <div style="background:white; border:1px solid #E2E8F0; border-radius:12px;
                    padding:1rem 1.25rem; margin-bottom:0.5rem;
                    border-right:4px solid #16A34A;">
            <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">
                {i}. {name}
            </div>
            <div style="color:#64748B; font-size:0.9rem; margin-top:0.5rem;">
                💊 <b>{dose}</b> &nbsp;|&nbsp; ⏰ {freq} &nbsp;|&nbsp; 📅 {dur}
            </div>
            {notes}
        </div>
        """.format(
            i=i,
            name=med.get("name", "—"),
            dose=med.get("dose") or "—",
            freq=med.get("frequency") or "—",
            dur=med.get("duration") or "—",
            notes='<div style="color:#9CA3AF; font-size:0.85rem; margin-top:0.35rem;">📝 {}</div>'.format(med["notes"]) if med.get("notes") else ""
        ), unsafe_allow_html=True)

    # ============ INSTRUCTIONS ============
    if rx.get("instructions"):
        st.markdown("### 📝 التعليمات")
        st.success(rx["instructions"])

    if rx.get("notes"):
        st.markdown("### 💬 ملاحظات")
        st.warning(rx["notes"])

    st.divider()

    # ============ DOWNLOAD PDF ============
    try:
        from services.prescription_pdf import generate_prescription_pdf
        with st.spinner("جاري تحضير PDF..."):
            pdf_bytes = generate_prescription_pdf(
                prescription=rx,
                patient=patient,
                clinic=clinic,
                doctor_name=clinic.get("doctor_name", "")
            )
        st.download_button(
            "📥 تحميل الوصفة PDF",
            pdf_bytes,
            "prescription.pdf",
            "application/pdf",
            use_container_width=True,
            type="primary"
        )
    except Exception:
        pass

    # ============ FOOTER ============
    st.markdown("""
    <div style="text-align:center; padding:2rem 1rem; color:#94A3B8; font-size:0.8rem; border-top:1px solid #E2E8F0; margin-top:2rem;">
        <div><b style="color:#16A34A;">👶 أمينة SaaS</b></div>
        <div style="margin-top:0.5rem;">هذه الوصفة صالحة لمدة 30 يوماً من تاريخ الإصدار</div>
    </div>
    """, unsafe_allow_html=True)
