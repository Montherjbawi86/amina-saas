# -*- coding: utf-8 -*-
"""
Ultrasound Gallery View
واجهة معرض صور السونار
"""
from datetime import date, timedelta
from io import BytesIO
import zipfile
import streamlit as st

from core.db import db
from core.save_helper import save_button, mark_result
from core.ui import page_header, spacer
from services.ultrasound import (
    upload_image, list_images, list_patient_images,
    get_image, update_image, delete_image,
    get_patient_summary, get_clinic_summary,
    ALLOWED_TYPES, MAX_FILE_SIZE,
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


def _format_size(size_bytes):
    if not size_bytes:
        return "0 B"
    kb = size_bytes / 1024.0
    if kb < 1024:
        return "{:.1f} KB".format(kb)
    return "{:.1f} MB".format(kb / 1024.0)


def _format_date(v):
    if not v:
        return "—"
    return str(v)[:10]


# ============================================
# TAB 1: UPLOAD
# ============================================

def _render_upload_tab(clinic, user):
    st.markdown("#### 📤 رفع صور سونار جديدة")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        st.warning("⚠️ لا يوجد حوامل")
        st.info("👉 سجّل حاملاً أولاً من قسم **👩 الحوامل**")
        return

    pmap = {p["id"]: "{} — {}".format(p.get("full_name", ""), p.get("phone", "")) for p in patients}

    # === Metadata section ===
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_id = st.selectbox(
            "الحامل *",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            key="us_patient"
        )
    with c2:
        image_date = st.date_input(
            "تاريخ الصورة",
            value=date.today(),
            key="us_date"
        )
    with c3:
        gest_weeks = st.number_input(
            "أسابيع الحمل",
            min_value=1, max_value=45,
            value=20,
            key="us_weeks"
        )

    caption = st.text_input(
        "العنوان (اختياري)",
        placeholder="مثال: سونار الجنين — 20 أسبوع",
        key="us_caption"
    )

    notes = st.text_area(
        "ملاحظات",
        placeholder="ملاحظات الطبيبة...",
        height=80,
        key="us_notes"
    )

    # === Files ===
    st.markdown("##### 📁 الملفات")
    st.caption("الحد الأقصى: 10 MB لكل ملف · jpg, png, webp, pdf")

    uploaded_files = st.file_uploader(
        "اختر صور السونار (يمكن اختيار أكثر من صورة)",
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        accept_multiple_files=True,
        key="us_files"
    )

    if uploaded_files:
        st.info("📎 {} ملف جاهز للرفع".format(len(uploaded_files)))
        total_size = sum(f.size for f in uploaded_files)
        st.caption("الحجم الكلي: {}".format(_format_size(total_size)))

    spacer(1)

    if st.button("📤 رفع الصور", type="primary", use_container_width=True,
                 key="us_upload_btn"):
        if not uploaded_files:
            st.error("⚠️ اختر صورة واحدة على الأقل")
            return

        progress = st.progress(0)
        status = st.empty()
        success_count = 0
        failed = []

        for i, f in enumerate(uploaded_files):
            try:
                status.info("⏳ جاري رفع: {} ({}/{})".format(f.name, i + 1, len(uploaded_files)))

                # Read bytes
                file_bytes = f.read()

                # Determine mime
                mime = f.type or "image/jpeg"
                if f.name.lower().endswith(".pdf"):
                    mime = "application/pdf"

                upload_image(
                    clinic_id=clinic["id"],
                    patient_id=selected_id,
                    file_bytes=file_bytes,
                    file_name=f.name,
                    mime_type=mime,
                    doctor_id=user.get("id") if user else None,
                    image_date=image_date,
                    gestational_weeks=gest_weeks,
                    caption=caption or None,
                    notes=notes or None,
                )
                success_count += 1
                progress.progress((i + 1) / len(uploaded_files))

            except Exception as e:
                failed.append("{}: {}".format(f.name, str(e)[:80]))

        status.empty()
        progress.empty()

        if success_count:
            st.success("✅ تم رفع {} صورة بنجاح".format(success_count))
            st.balloons()

        if failed:
            st.error("❌ فشل {} ملف:".format(len(failed)))
            for err in failed:
                st.write("- {}".format(err))

        if success_count and not failed:
            st.rerun()


# ============================================
# TAB 2: GALLERY
# ============================================

def _render_gallery_tab(clinic, user):
    st.markdown("#### 🖼️ المعرض")

    patients = _fetch_patients(clinic["id"])
    if not patients:
        st.info("📭 لا يوجد حوامل")
        return

    pmap = {"": "الكل"}
    for p in patients:
        pmap[p["id"]] = p.get("full_name", "")

    # Filters
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        filter_patient = st.selectbox(
            "الحامل",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            key="us_gallery_patient"
        )
    with c2:
        weeks_from = st.number_input(
            "من أسبوع", min_value=0, max_value=45, value=0,
            key="us_weeks_from"
        )
    with c3:
        weeks_to = st.number_input(
            "إلى أسبوع", min_value=0, max_value=45, value=0,
            key="us_weeks_to"
        )

    # Fetch
    images = list_images(
        clinic_id=clinic["id"],
        patient_id=filter_patient if filter_patient else None,
        min_weeks=weeks_from if weeks_from > 0 else None,
        max_weeks=weeks_to if weeks_to > 0 else None,
        limit=200,
    )

    if not images:
        st.info("📭 لا توجد صور بهذه المعايير")
        return

    st.caption("📸 {} صورة".format(len(images)))

    # Patient map for display
    pmap_names = {p["id"]: p.get("full_name", "") for p in patients}

    # Grid view (3 columns)
    cols = st.columns(3)
    for idx, img in enumerate(images):
        col = cols[idx % 3]
        with col:
            _render_image_card(img, pmap_names.get(img.get("patient_id"), ""))


def _render_image_card(img, patient_name):
    """Render a single ultrasound image card"""
    is_pdf = (img.get("mime_type") == "application/pdf")
    url = img.get("public_url", "")

    # Preview
    if is_pdf:
        st.markdown("""
        <div style="background:#F1F5F9;border-radius:10px;padding:2rem;text-align:center;">
            <div style="font-size:3rem;">📄</div>
            <div style="font-weight:600;color:#0F172A;margin-top:0.5rem;">PDF</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        try:
            st.image(url, use_container_width=True)
        except Exception:
            st.markdown("""
            <div style="background:#F1F5F9;border-radius:10px;padding:2rem;text-align:center;">
                <div style="font-size:3rem;">🖼️</div>
                <div style="color:#94A3B8;">لا يمكن عرض الصورة</div>
            </div>
            """, unsafe_allow_html=True)

    # Info
    caption = img.get("caption") or img.get("file_name") or "سونار"
    date_str = _format_date(img.get("image_date"))
    weeks = img.get("gestational_weeks")

    st.markdown("""
    <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                padding:0.75rem 1rem;margin-bottom:0.75rem;">
        <div style="font-weight:600;color:#0F172A;font-size:0.9rem;margin-bottom:0.3rem;">
            {caption}
        </div>
        <div style="color:#64748B;font-size:0.78rem;">
            📅 {date} {weeks}
        </div>
        {patient}
    </div>
    """.format(
        caption=caption[:40],
        date=date_str,
        weeks="| 🤰 {} أسبوع".format(weeks) if weeks else "",
        patient='<div style="color:#16A34A;font-size:0.75rem;margin-top:0.2rem;">👩 {}</div>'.format(patient_name) if patient_name else "",
    ), unsafe_allow_html=True)

    # Actions
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if url:
            st.link_button("⬇️ فتح", url, use_container_width=True)
    with c2:
        if st.button("✏️", key="us_edit_{}".format(img["id"]), help="تعديل",
                     use_container_width=True):
            st.session_state["us_edit_id"] = img["id"]
            st.rerun()
    with c3:
        if st.button("🗑️", key="us_del_{}".format(img["id"]), help="حذف",
                     use_container_width=True):
            if delete_image(clinic_ctx_id(), img["id"]):
                st.success("🗑️ تم الحذف")


def clinic_ctx_id():
    """Get current clinic id from session"""
    try:
        from core.session import get_current_clinic
        c = get_current_clinic()
        return c["id"] if c else None
    except Exception:
        return None


# ============================================
# TAB 3: STATS
# ============================================

def _render_stats_tab(clinic, user):
    st.markdown("#### 📊 إحصائيات")

    # Clinic total
    clinic_summary = get_clinic_summary(clinic["id"])
    c1, c2 = st.columns(2)
    c1.metric("📸 إجمالي الصور في العيادة", clinic_summary.get("total", 0))

    patients = _fetch_patients(clinic["id"])
    if not patients:
        st.info("📭 لا يوجد حوامل")
        return

    c2.metric("👩 عدد الحوامل", len(patients))

    spacer(1)
    st.markdown("##### 📋 إحصائيات لكل حامل")

    pmap = {p["id"]: p.get("full_name", "") for p in patients}

    selected_id = st.selectbox(
        "اختر حاملاً",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        key="us_stats_patient"
    )

    if not selected_id:
        return

    summary = get_patient_summary(clinic["id"], selected_id)

    c1, c2, c3 = st.columns(3)
    c1.metric("📸 عدد الصور", summary["total"])
    c2.metric("💾 الحجم", "{:.1f} MB".format(summary["total_size_mb"]))

    weeks_range = summary.get("weeks_range")
    if weeks_range:
        c3.metric("🤰 نطاق الأسابيع", "{} - {}".format(weeks_range[0], weeks_range[1]))

    if summary["total"] == 0:
        st.info("📭 لا توجد صور لهذه الحامل")
        return

    # Timeline
    st.markdown("##### 📅 السجل الزمني")
    st.write("**أول صورة:** {}".format(_format_date(summary.get("first_date"))))
    st.write("**آخر صورة:** {}".format(_format_date(summary.get("last_date"))))

    # Download all as ZIP
    st.markdown("##### 📦 تحميل الكل")
    if st.button("📦 تجهيز ملف ZIP", key="us_zip_btn"):
        with st.spinner("⏳ جاري التجهيز..."):
            try:
                images = list_patient_images(clinic["id"], selected_id, limit=200)
                if not images:
                    st.warning("لا توجد صور")
                    return

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    import urllib.request
                    for img in images:
                        try:
                            url = img.get("public_url")
                            if not url:
                                continue
                            with urllib.request.urlopen(url, timeout=10) as resp:
                                data = resp.read()
                            fname = "{}_{}".format(
                                _format_date(img.get("image_date")),
                                img.get("file_name", "image.jpg")
                            )
                            zf.writestr(fname, data)
                        except Exception:
                            continue

                zip_buffer.seek(0)
                zip_bytes = zip_buffer.getvalue()

                st.session_state["_us_zip_data"] = zip_bytes
                st.session_state["_us_zip_name"] = "{}_{}.zip".format(
                    pmap.get(selected_id, "patient").replace(" ", "_")[:30],
                    date.today().strftime("%Y%m%d")
                )
                st.success("✅ تم التجهيز")
            except Exception as e:
                st.error("❌ {}".format(str(e)[:150]))

    if "_us_zip_data" in st.session_state and st.session_state["_us_zip_data"]:
        st.download_button(
            "⬇️ تحميل ZIP",
            data=st.session_state["_us_zip_data"],
            file_name=st.session_state.get("_us_zip_name", "ultrasounds.zip"),
            mime="application/zip",
            use_container_width=True,
            type="primary",
            key="us_zip_download"
        )


# ============================================
# EDIT MODAL
# ============================================

def _render_edit_modal(clinic, user):
    edit_id = st.session_state.get("us_edit_id")
    if not edit_id:
        return

    img = get_image(clinic["id"], edit_id)
    if not img:
        st.session_state.pop("us_edit_id", None)
        return

    with st.expander("✏️ تعديل الصورة", expanded=True):
        new_caption = st.text_input("العنوان", value=img.get("caption") or "", key="edit_cap")
        new_notes = st.text_area("ملاحظات", value=img.get("notes") or "", height=80, key="edit_notes")
        new_weeks = st.number_input("أسابيع الحمل",
            min_value=1, max_value=45,
            value=img.get("gestational_weeks") or 20,
            key="edit_weeks")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 حفظ", type="primary", use_container_width=True, key="edit_save"):
                try:
                    update_image(clinic["id"], edit_id,
                                 caption=new_caption or None,
                                 notes=new_notes or None,
                                 gestational_weeks=new_weeks)
                    st.session_state.pop("us_edit_id", None)
                    st.success("✅ تم الحفظ")
                except Exception as e:
                    st.error("❌ {}".format(str(e)[:150]))
        with c2:
            if st.button("❌ إلغاء", use_container_width=True, key="edit_cancel"):
                st.session_state.pop("us_edit_id", None)
                st.rerun()


# ============================================
# MAIN
# ============================================

@st.fragment
def render(clinic, user):
    page_header(
        "معرض صور السونار",
        "رفع وتنظيم صور السونار لكل حامل",
        icon="📸"
    )

    # Edit modal (if active)
    _render_edit_modal(clinic, user)

    tab_upload, tab_gallery, tab_stats = st.tabs([
        "📤 رفع",
        "🖼️ المعرض",
        "📊 إحصائيات",
    ])

    with tab_upload:
        _render_upload_tab(clinic, user)
    with tab_gallery:
        _render_gallery_tab(clinic, user)
    with tab_stats:
        _render_stats_tab(clinic, user)
