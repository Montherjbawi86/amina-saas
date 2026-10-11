# -*- coding: utf-8 -*-
"""Prescriptions view"""
import time
from datetime import date
import streamlit as st

from services.prescriptions import (
    create_prescription, list_prescriptions_cached, delete_prescription,
    COMMON_MEDICATIONS, PrescriptionError,
)
from services.patients import list_patients_cached, get_patient_summary_cached
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Render prescriptions tab"""
    view = st.session_state.get("presc_view", "list")
    if view == "list":
        _render_list(clinic, user)
    elif view == "new":
        _render_new(clinic, user)


# ============================================
# LIST
# ============================================
def _render_list(clinic, user):
    st.markdown("### 💊 الوصفات الطبية")

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        # Filter by patient (optional)
        patients = list_patients_cached(clinic["id"])
        patient_options = {"all": "كل الحوامل"} if patients else {}
        for p in patients:
            patient_options[p["id"]] = p["full_name"]

        selected_pid = st.selectbox(
            "تصفية حسب الحامل",
            options=list(patient_options.keys()),
            format_func=lambda x: patient_options[x],
            key="presc_patient_filter"
        )
    with c2:
        st.write("")
        show_cache_status("presc_cache")
    with c3:
        st.write("")
        if st.button("➕ وصفة جديدة", use_container_width=True, type="primary", key="new_presc_btn"):
            st.session_state["presc_view"] = "new"
            st.rerun()

    st.divider()

    with st.spinner("جاري التحميل..."):
        prescs = list_prescriptions_cached(
            clinic["id"],
            patient_id=None if selected_pid == "all" else selected_pid,
        )

    if not prescs:
        st.info("📭 لا توجد وصفات")
        return

    # Patient map
    patients_map = {p["id"]: p for p in patients}
    st.markdown("**العدد: {}**".format(len(prescs)))

    for rx in prescs:
        p = patients_map.get(rx["patient_id"], {})
        name = p.get("full_name", "—")
        meds = rx.get("medications", []) or []
        med_count = len(meds)

        with st.expander("💊 {} — {} — {} دواء".format(
            name, (rx.get("issued_at") or "")[:10], med_count
        ), expanded=False):
            # Patient + diagnosis
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("**الحامل:** {}".format(name))
                st.markdown("**📋 التشخيص:** {}".format(rx.get("diagnosis") or "—"))
            with c2:
                st.markdown("**📅 التاريخ:** {}".format((rx.get("issued_at") or "")[:10]))
                if rx.get("follow_up_days"):
                    st.markdown("**🔄 المتابعة:** بعد {} يوم".format(rx["follow_up_days"]))

            # Medications table
            st.markdown("#### 💊 الأدوية")
            for i, med in enumerate(meds, 1):
                st.markdown("""
                <div style="background:#F9FAFB; padding:0.6rem 0.9rem; border-radius:8px; margin-bottom:0.4rem; border-right:4px solid #0EA5A0;">
                    <div style="font-weight:700; color:#1F2937;">{i}. {name}</div>
                    <div style="font-size:0.85rem; color:#6B7280; margin-top:0.25rem;">
                        💊 {dose} &nbsp;|&nbsp; ⏰ {freq} &nbsp;|&nbsp; 📅 {dur}
                    </div>
                    {notes_html}
                </div>
                """.format(
                    i=i, name=med.get("name", "—"),
                    dose=med.get("dose") or "—",
                    freq=med.get("frequency") or "—",
                    dur=med.get("duration") or "—",
                    notes_html='<div style="font-size:0.75rem; color:#9CA3AF; margin-top:0.25rem;">📝 {}</div>'.format(med["notes"]) if med.get("notes") else ""
                ), unsafe_allow_html=True)

            if rx.get("instructions"):
                st.info("📝 **التعليمات:** {}".format(rx["instructions"]))

            # Actions
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
            with c1:
                # PDF + WhatsApp
                if st.button("📄 PDF", key="pdf_presc_" + rx["id"], use_container_width=True, type="primary"):
                    st.session_state["gen_rx_pdf_" + rx["id"]] = True

                if st.session_state.get("gen_rx_pdf_" + rx["id"]):
                    try:
                        from services.prescription_pdf import generate_prescription_pdf
                        from services.patients import get_patient_summary_cached
                        from services.messaging import build_whatsapp_link

                        _patient = get_patient_summary_cached(clinic["id"], rx["patient_id"])
                        if not _patient:
                            st.error("الملف غير موجود")
                        else:
                            with st.spinner("جاري توليد PDF..."):
                                pdf_bytes = generate_prescription_pdf(
                                    prescription=rx,
                                    patient=_patient,
                                    clinic=clinic,
                                    doctor_name=user.get("full_name", "")
                                )

                            # ============ DOWNLOAD + WHATSAPP (Combined) ============
                            st.markdown("""
                            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:0.75rem 1rem; margin:0.5rem 0;">
                                <div style="font-size:0.8rem; font-weight:700; color:#15803D; margin-bottom:0.5rem;">
                                    ✅ التقرير جاهز
                                </div>
                                <div style="font-size:0.85rem; color:#475569;">
                                    اضغط <b>📄 تحميل + 📱 واتساب</b> لإرسال الوصفة
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Primary button: Download
                            st.download_button(
                                "📄 تحميل PDF",
                                pdf_bytes,
                                "prescription_{}.pdf".format(str(rx["id"])[:8]),
                                "application/pdf",
                                key="dl_rx_" + rx["id"],
                                use_container_width=True,
                                type="primary"
                            )

                            # WhatsApp + instructions
                            if _patient.get("phone"):
                                # Enhanced message with PDF reference
                                wa_pdf_msg = (
                                    "*وصفة طبية* 💊" + chr(10) +
                                    "━━━━━━━━━━━━━━━" + chr(10) +
                                    "السلام عليكم *{}* 🌸".format(_patient["full_name"]) + chr(10) + chr(10) +
                                    "وصفتك الطبية من *{}* جاهزة.".format(clinic.get("name", "")) + chr(10) + chr(10) +
                                    "📋 التشخيص: {}".format(rx.get("diagnosis") or "—") + chr(10) + chr(10) +
                                    "_سيتم إرفاق الملف (PDF) الآن_ 💜"
                                )
                                wa_pdf_link = build_whatsapp_link(_patient["phone"], wa_pdf_msg)

                                # Row: WhatsApp button + Copy PDF path
                                st.link_button(
                                    "📱 فتح واتساب",
                                    wa_pdf_link,
                                    use_container_width=True
                                )

                                # Instructions
                                st.info(
                                    "💡 **الخطوات:**\n"
                                    "1. اضغط **📄 تحميل PDF** (يُحفظ في Downloads)\n"
                                    "2. اضغط **📱 فتح واتساب**\n"
                                    "3. في واتساب: 📎 → اختر الملف → Send"
                                )

                                # Copy PDF path helper
                                pdf_name = "prescription_{}.pdf".format(str(rx["id"])[:8])
                                st.caption("📁 اسم الملف: `{}`".format(pdf_name))

                                # Direct WhatsApp Web with file hint
                                st.markdown(
                                    '<div style="text-align:center; margin-top:0.5rem;">'
                                    '<a href="' + wa_pdf_link + '" target="_blank" style="color:#16A34A; font-size:0.8rem; text-decoration:none;">'
                                    '🔗 أو افتح WhatsApp Web مباشرة'
                                    '</a></div>',
                                    unsafe_allow_html=True
                                )

                                # ============ SIMPLE SHARE: Download + WhatsApp ============
                                import base64
                                _pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                                _pdf_filename = "prescription_{}.pdf".format(str(rx["id"])[:8])
                                _wa_link = wa_pdf_link

                                # Instructions card
                                st.markdown("""
                                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:0.85rem; margin-top:0.75rem;">
                                    <div style="font-weight:700; color:#15803D; font-size:0.9rem; margin-bottom:0.5rem;">
                                        📋 خطوات الإرسال
                                    </div>
                                    <div style="font-size:0.85rem; color:#475569; line-height:1.8;">
                                        <div>1️⃣ اضغط <b>📄 تحميل PDF</b> (يُحفظ في Downloads)</div>
                                        <div>2️⃣ اضغط <b>📱 فتح واتساب</b></div>
                                        <div>3️⃣ في واتساب: اضغط <b>📎</b> → اختر الملف → Send</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Both buttons side by side
                                bc1, bc2 = st.columns(2)
                                with bc1:
                                    st.download_button(
                                        "📄 تحميل PDF",
                                        pdf_bytes,
                                        _pdf_filename,
                                        "application/pdf",
                                        key="dl_both_" + rx["id"],
                                        use_container_width=True,
                                        type="primary"
                                    )
                                with bc2:
                                    st.link_button(
                                        "📱 فتح واتساب",
                                        _wa_link,
                                        use_container_width=True
                                    )

                                # Filename reminder
                                st.caption("📁 الملف: `{}`".format(_pdf_filename))

                    except Exception as e:
                        st.error("فشل PDF: {}".format(str(e)[:100]))
                        st.session_state["gen_rx_pdf_" + rx["id"]] = False

            with c2:
                # WhatsApp + PDF button
                try:
                    from services.messaging import build_whatsapp_link
                    from services.patients import get_patient_summary_cached

                    _patient = get_patient_summary_cached(clinic["id"], rx["patient_id"])
                    if _patient and _patient.get("phone"):
                        # Simple WhatsApp message (short)
                        wa_msg = (
                            "*وصفة طبية* 💊\n"
                            "━━━━━━━━━━━━━━━\n"
                            "السلام عليكم *{}* 🌸\n\n"
                            "وصفتك من *{}* جاهزة.\n"
                            "📋 التشخيص: {}\n\n"
                            "سيتم إرسال الملف (PDF) بعد قليل.\n\n"
                            "_مع تمنياتنا بالشفاء العاجل_ 💜"
                        ).format(
                            _patient["full_name"],
                            clinic.get("name", ""),
                            rx.get("diagnosis") or "—"
                        )

                        wa_link = build_whatsapp_link(_patient["phone"], wa_msg)
                        st.link_button("📱 واتساب", wa_link, use_container_width=True)
                    else:
                        st.button("📱 واتساب", disabled=True, use_container_width=True, key="wa_disabled_" + rx["id"])
                except Exception as e:
                    st.caption("—")

            with c3:
                if st.button("🗑️ حذف", key="del_presc_" + rx["id"], use_container_width=True):
                    if st.session_state.get("confirm_presc_del") == rx["id"]:
                        try:
                            delete_prescription(clinic["id"], rx["id"])
                            clear_all()
                            st.session_state["confirm_presc_del"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    else:
                        st.session_state["confirm_presc_del"] = rx["id"]
                        st.warning("اضغط مرة أخرى")

            with c4:
                # QR + WhatsApp share
                if st.button("📱 QR", key="qr_share_" + rx["id"], use_container_width=True, type="primary"):
                    st.session_state["show_qr_" + rx["id"]] = True

            # ============ QR SHARE PANEL ============
            if st.session_state.get("show_qr_" + rx["id"]):
                try:
                    from services.share_links import create_share_link
                    from services.patients import get_patient_summary_cached
                    from services.messaging import build_whatsapp_link
                    import qrcode
                    from io import BytesIO

                    _patient = get_patient_summary_cached(clinic["id"], rx["patient_id"])

                    # Create share link
                    share = create_share_link(
                        clinic_id=clinic["id"],
                        patient_id=rx["patient_id"],
                        resource_type="prescription",
                        resource_id=rx["id"],
                        expiry_days=30
                    )
                    token = share["token"]

                    # Build URL (adjust to your domain later)
                    # Auto-detect base URL
                    base_url = st.session_state.get("_public_base_url")
                    if not base_url:
                        # Try to detect from browser (Streamlit 1.40+)
                        try:
                            # Production URL from env
                            import os as _os
                            base_url = _os.getenv("PUBLIC_BASE_URL", "")
                        except Exception:
                            pass
                    if not base_url:
                        base_url = "https://amina-saas.onrender.com"
                    public_url = "{}/?rx={}".format(base_url.rstrip("/"), token)

                    # Generate QR
                    qr = qrcode.QRCode(version=None, box_size=8, border=2)
                    qr.add_data(public_url)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="#16A34A", back_color="white")
                    buf = BytesIO()
                    qr_img.save(buf, format="PNG")
                    buf.seek(0)

                    # Display
                    st.markdown("---")
                    st.markdown("#### 📱 مشاركة الوصفة عبر QR")

                    qc1, qc2 = st.columns([1, 2])
                    with qc1:
                        st.image(buf.getvalue(), width=200, caption="امسحي الرمز")
                    with qc2:
                        st.markdown("**رابط للحامل:**")
                        st.code(public_url, language=None)
                        st.caption("⏱️ صالح لمدة 30 يوماً")

                        # WhatsApp message with link
                        if _patient and _patient.get("phone"):
                            wa_msg = (
                                "*وصفة طبية* 💊" + chr(10) +
                                "━━━━━━━━━━━━━━━" + chr(10) +
                                "السلام عليكم *{}* 🌸".format(_patient["full_name"]) + chr(10) + chr(10) +
                                "وصفتك جاهزة! اضغط الرابط لرؤيتها:" + chr(10) +
                                public_url + chr(10) + chr(10) +
                                "📋 التشخيص: {}".format(rx.get("diagnosis") or "—") + chr(10) + chr(10) +
                                "_مع تمنياتنا بالشفاء العاجل_ 💜"
                            )
                            wa_link = build_whatsapp_link(_patient["phone"], wa_msg)
                            st.link_button(
                                "📱 إرسال الرابط عبر واتساب",
                                wa_link,
                                use_container_width=True
                            )

                        # Copy button
                        st.caption("أو انسخي الرابط يدوياً 👆")

                    # Close button
                    if st.button("✖️ إغلاق", key="close_qr_" + rx["id"]):
                        st.session_state["show_qr_" + rx["id"]] = False
                        st.rerun()

                except Exception as e:
                    st.error("خطأ: {}".format(str(e)[:150]))
                    st.session_state["show_qr_" + rx["id"]] = False

            st.write("")


# ============================================
# NEW PRESCRIPTION
# ============================================
def _render_new(clinic, user):
    st.markdown("### ➕ وصفة طبية جديدة")

    if st.button("⬅️ رجوع للقائمة", key="back_presc_list"):
        st.session_state["presc_view"] = "list"
        st.rerun()

    # Patient select
    patients = list_patients_cached(clinic["id"])
    if not patients:
        st.warning("⚠️ لا توجد حوامل. أضف حاملاً أولاً.")
        return

    patient_map = {p["id"]: "{} — {}".format(p["full_name"], p["phone"]) for p in patients}

    # Preselect
    preselected = st.session_state.get("selected_patient_id")
    default_idx = 0
    if preselected and preselected in patient_map:
        default_idx = list(patient_map.keys()).index(preselected)

    pid = st.selectbox(
        "الحامل *",
        options=list(patient_map.keys()),
        format_func=lambda x: patient_map[x],
        index=default_idx,
        key="new_presc_patient"
    )

    st.divider()

    # Diagnosis + instructions (outside form for live updates)
    diagnosis = st.text_input("📋 التشخيص", placeholder="مثال: فقر دم خفيف مع حمل")
    instructions = st.text_area("📝 تعليمات عامة", height=80, placeholder="مثال: يُؤخذ مع الطعام")

    c1, c2 = st.columns(2)
    with c1:
        follow_up = st.number_input("🔄 المتابعة بعد (يوم)", min_value=0, max_value=180, value=30, step=7)
    with c2:
        visit_id = None  # optional

    st.divider()
    st.markdown("### 💊 الأدوية")

    # Initialize medications list in session
    if "presc_meds" not in st.session_state:
        st.session_state["presc_meds"] = [{"name": "", "dose": "", "frequency": "", "duration": "", "notes": ""}]

    meds = st.session_state["presc_meds"]

    # Render each medication
    for i, med in enumerate(meds):
        with st.container():
            st.markdown("**دواء {}**".format(i + 1))
            c1, c2 = st.columns([3, 1])
            with c1:
                # Quick select from common meds
                name = st.text_input(
                    "الاسم",
                    value=med.get("name", ""),
                    key="med_name_{}".format(i),
                    placeholder="اسم الدواء والجرعة"
                )
            with c2:
                st.write("")
                if st.button("🗑️ حذف", key="del_med_{}".format(i)):
                    st.session_state["presc_meds"].pop(i)
                    st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1:
                dose = st.text_input("الجرعة", value=med.get("dose", ""),
                    key="med_dose_{}".format(i), placeholder="قرص/مل")
            with c2:
                freq = st.text_input("التكرار", value=med.get("frequency", ""),
                    key="med_freq_{}".format(i), placeholder="يومياً")
            with c3:
                dur = st.text_input("المدة", value=med.get("duration", ""),
                    key="med_dur_{}".format(i), placeholder="7 أيام")

            notes_med = st.text_input("ملاحظات الدواء", value=med.get("notes", ""),
                key="med_notes_{}".format(i))

            # Save back to session
            st.session_state["presc_meds"][i] = {
                "name": name, "dose": dose, "frequency": freq,
                "duration": dur, "notes": notes_med,
            }
            st.divider()

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("➕ إضافة دواء آخر", use_container_width=True):
            st.session_state["presc_meds"].append(
                {"name": "", "dose": "", "frequency": "", "duration": "", "notes": ""}
            )
            st.rerun()
    with c2:
        # Quick add common medications
        common = st.selectbox(
            "أو اختر من الأدوية الشائعة:",
            ["— اختر —"] + COMMON_MEDICATIONS,
            key="common_med_selector"
        )
        if common != "— اختر —" and st.button("➕ إضافة " + common, key="add_common_btn"):
            st.session_state["presc_meds"].append(
                {"name": common, "dose": "", "frequency": "", "duration": "", "notes": ""}
            )
            st.rerun()

    st.divider()

    if st.button("💾 حفظ الوصفة", use_container_width=True, type="primary", key="save_presc"):
        # Validate
        valid_meds = [m for m in st.session_state["presc_meds"] if m.get("name")]
        if not valid_meds:
            st.error("❌ يجب إضافة دواء واحد على الأقل")
        else:
            try:
                rx = create_prescription(
                    clinic_id=clinic["id"],
                    patient_id=pid,
                    doctor_id=user["id"],
                    medications=valid_meds,
                    diagnosis=diagnosis or None,
                    instructions=instructions or None,
                    follow_up_days=int(follow_up) if follow_up else None,
                    visit_id=visit_id,
                )
                clear_all()
                st.success("✅ تم حفظ الوصفة")
                st.balloons()
                # Reset
                st.session_state["presc_meds"] = [{"name": "", "dose": "", "frequency": "", "duration": "", "notes": ""}]
                st.session_state["presc_view"] = "list"
                time.sleep(0.8)
                st.rerun()
            except PrescriptionError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))


# ============================================
# WIDGET: quick add from patient detail
# ============================================
def quick_add_prescription(clinic, user, patient_id):
    """Render a quick prescription button from patient detail"""
    if st.button("💊 وصفة طبية جديدة", key="quick_rx_" + patient_id, use_container_width=True):
        st.session_state["selected_patient_id"] = patient_id
        st.session_state["presc_view"] = "new"
        st.session_state["presc_meds"] = [{"name": "", "dose": "", "frequency": "", "duration": "", "notes": ""}]
        st.success("✅ اذهب لتبويب **💊 الوصفات**")
