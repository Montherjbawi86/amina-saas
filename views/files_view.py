# -*- coding: utf-8 -*-
"""Files view v4 — using st.form to prevent auto-upload"""
import time
import streamlit as st

from services.files import (
    upload_file, list_files_cached, delete_file, download_file,
    format_size, CATEGORY_LABELS, FileError,
)
from services.patients import get_patient_summary_cached
from core.cache import clear_all


def render(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    if not pid:
        st.markdown("### 📎 الملفات الطبية")
        st.info("👉 اختر حاملاً من تبويب **👩 الحوامل** أولاً")
        return

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.info("👉 اختر حاملاً أولاً")
        return

    st.markdown("### 📎 الملفات الطبية — {}".format(p["full_name"]))
    st.caption("رفع وإدارة صور السونار، نتائج التحاليل، والتقارير")

    tab_upload, tab_list = st.tabs(["⬆️ رفع ملف", "📁 الملفات"])

    with tab_upload:
        _render_upload(clinic, user, p)

    with tab_list:
        _render_list(clinic, p)


# ============================================
# UPLOAD — wrapped in st.form
# ============================================
def _render_upload(clinic, user, p):
    st.markdown("#### ⬆️ رفع ملف جديد")

    # Show success from previous upload
    prev = st.session_state.pop("upload_success_msg", None)
    if prev:
        st.success(prev)

    ver = st.session_state.get("uploader_version", 0)

    # ============ THE FORM ============
    with st.form(key="upload_form_v_{}".format(ver), clear_on_submit=True):

        uploaded = st.file_uploader(
            "اختر الملف (صور، PDF، مستندات)",
            type=["jpg", "jpeg", "png", "pdf", "txt", "docx", "heic", "webp"],
            accept_multiple_files=False,
            key="uform_up_{}".format(ver)
        )

        category = st.selectbox(
            "التصنيف",
            options=list(CATEGORY_LABELS.keys()),
            format_func=lambda x: CATEGORY_LABELS[x],
            index=0,
            key="uform_cat_{}".format(ver)
        )

        notes = st.text_area("ملاحظات (اختياري)", height=80,
            placeholder="مثال: سونار الأسبوع 20",
            key="uform_notes_{}".format(ver))

        st.caption("📦 حجم أقصى: 50 MB")

        # Form submit — only triggers here
        submitted = st.form_submit_button(
            "⬆️ رفع الملف",
            use_container_width=True,
            type="primary"
        )

    # Only runs when user clicks submit
    if submitted:
        if not uploaded:
            st.error("❌ يرجى اختيار ملف أولاً")
        elif uploaded.size > 50 * 1024 * 1024:
            st.error("❌ الملف أكبر من 50 MB")
        else:
            try:
                with st.spinner("جاري الرفع..."):
                    file_bytes = uploaded.getvalue()
                    rec = upload_file(
                        clinic_id=clinic["id"],
                        patient_id=p["id"],
                        uploaded_by=user["id"],
                        file_bytes=file_bytes,
                        file_name=uploaded.name,
                        category=category,
                        notes=notes or None,
                        content_type=uploaded.type or "application/octet-stream",
                    )

                clear_all()

                # Bump version → next form is fresh
                st.session_state["uploader_version"] = ver + 1
                st.session_state["upload_success_msg"] = "✅ تم رفع: {}".format(rec["file_name"])

                st.balloons()
                time.sleep(0.5)
                st.rerun()

            except FileError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))


# ============================================
# LIST
# ============================================
def _render_list(clinic, p):
    st.markdown("#### 📁 ملفات الحامل")

    c1, c2 = st.columns([2, 3])
    with c1:
        cat_filter = st.selectbox(
            "تصفية حسب التصنيف",
            ["all"] + list(CATEGORY_LABELS.keys()),
            format_func=lambda x: "الكل" if x == "all" else CATEGORY_LABELS[x],
            key="flt_cat_v4"
        )
    with c2:
        st.write("")
        if st.button("🔄 تحديث القائمة", key="ref_list_v4"):
            clear_all()
            st.rerun()

    with st.spinner("جاري التحميل..."):
        files = list_files_cached(clinic["id"], p["id"])

    if cat_filter != "all":
        files = [f for f in files if f.get("category") == cat_filter]

    if not files:
        st.info("📭 لا توجد ملفات")
        return

    st.markdown("**العدد: {}**".format(len(files)))
    st.divider()

    for f in files:
        _render_file_card(clinic, f)


def _render_file_card(clinic, f):
    cat = f.get("category", "other")
    cat_label = CATEGORY_LABELS.get(cat, cat)
    size_str = format_size(f.get("file_size_bytes"))
    uploaded = (f.get("uploaded_at") or "—")[:16]
    icon = cat_label.split(" ")[0] if cat_label else "📎"
    is_image = (f.get("file_type") or "").startswith("image/")
    fid = f["id"]

    notes_html = ""
    if f.get("notes"):
        notes_html = '<div style="color:#9CA3AF; font-size:0.8rem; margin-top:0.3rem;">📝 ' + f["notes"] + '</div>'

    card = (
        '<div style="background:white; border-radius:12px; padding:1rem 1.25rem; '
        'margin-bottom:0.5rem; border-right:5px solid #0EA5A0; '
        'box-shadow:0 2px 6px rgba(0,0,0,0.05);">'
        '<div style="display:flex; align-items:center; gap:1rem;">'
        '<div style="font-size:2rem;">' + icon + '</div>'
        '<div style="flex:1;">'
        '<div style="font-weight:700; color:#1F2937; font-size:1rem;">' + f.get("file_name", "—") + '</div>'
        '<div style="color:#6B7280; font-size:0.85rem; margin-top:0.2rem;">'
        + cat_label + ' | 📦 ' + size_str + ' | 📅 ' + uploaded +
        '</div>' + notes_html + '</div></div></div>'
    )
    st.markdown(card, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 3])

    with c1:
        if st.button("⬇️ تحميل", key="dlbtn_" + fid, use_container_width=True):
            try:
                data, rec = download_file(clinic["id"], fid)
                st.session_state["dl_" + fid] = (data, rec["file_name"],
                    rec.get("file_type") or "application/octet-stream")
            except Exception as e:
                st.error(str(e)[:60])

        if st.session_state.get("dl_" + fid):
            data, name, mime = st.session_state["dl_" + fid]
            st.download_button("💾 حفظ", data, name, mime,
                key="save_" + fid, use_container_width=True)

    with c2:
        if st.button("🗑️ حذف", key="delbtn_" + fid, use_container_width=True):
            try:
                delete_file(clinic["id"], fid)
                clear_all()
                st.success("✅ تم الحذف")
                time.sleep(0.4)
                st.rerun()
            except FileError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(str(e)[:80]))

    if is_image:
        with st.expander("👁️ معاينة", expanded=False):
            try:
                data, rec = download_file(clinic["id"], fid)
                st.image(data, caption=f.get("file_name"), use_column_width=True)
            except Exception:
                st.warning("لا يمكن عرض الصورة")

    st.write("")


def file_count_widget(clinic, patient_id):
    try:
        from services.files import count_files_cached
        return count_files_cached(clinic["id"], patient_id)
    except Exception:
        return 0
