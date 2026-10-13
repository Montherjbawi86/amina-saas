# -*- coding: utf-8 -*-
"""
Excel Export View
واجهة Streamlit لتصدير البيانات إلى Excel
"""
from datetime import date, timedelta, datetime
import streamlit as st

from core.ui import page_header, spacer
from services.excel_export import (
    export_patients, export_visits, export_prescriptions,
    export_vaccinations, export_all
)


EXPORT_TYPES = {
    "all": {
        "label": "📦 الكل (ملف واحد، 4 أوراق)",
        "func": export_all,
        "has_date_filter": True,
        "filename": "amina_all",
    },
    "patients": {
        "label": "👩 الحوامل",
        "func": export_patients,
        "has_date_filter": False,
        "filename": "amina_patients",
    },
    "visits": {
        "label": "🩺 الزيارات",
        "func": export_visits,
        "has_date_filter": True,
        "filename": "amina_visits",
    },
    "prescriptions": {
        "label": "💊 الوصفات",
        "func": export_prescriptions,
        "has_date_filter": True,
        "filename": "amina_prescriptions",
    },
    "vaccinations": {
        "label": "💉 التحصينات",
        "func": export_vaccinations,
        "has_date_filter": True,
        "filename": "amina_vaccinations",
    },
}


def render(clinic, user):
    page_header(
        "تصدير Excel",
        "حمّل بيانات العيادة كملف Excel (xlsx)",
        icon="📊"
    )

    st.info(
        "💡 الملفات بصيغة **xlsx** — تفتح مباشرة في Excel, "
        "Google Sheets, Numbers. **العربية مدعومة** (اتجاه من اليمين لليسار)."
    )

    st.markdown("#### 1️⃣ اختر نوع البيانات")

    export_type = st.selectbox(
        "نوع التصدير",
        options=list(EXPORT_TYPES.keys()),
        format_func=lambda k: EXPORT_TYPES[k]["label"],
        label_visibility="collapsed",
        key="excel_export_type"
    )

    export_info = EXPORT_TYPES[export_type]
    st.caption(export_info["label"])

    date_from = None
    date_to = None

    if export_info["has_date_filter"]:
        st.markdown("#### 2️⃣ فلتر التاريخ (اختياري)")

        apply_date = st.checkbox(
            "تطبيق فلتر التاريخ",
            value=False,
            key="excel_apply_date"
        )

        if apply_date:
            c1, c2 = st.columns(2)
            with c1:
                date_from = st.date_input(
                    "من تاريخ",
                    value=date.today() - timedelta(days=30),
                    key="excel_date_from"
                )
            with c2:
                date_to = st.date_input(
                    "إلى تاريخ",
                    value=date.today(),
                    key="excel_date_to"
                )

            if date_from and date_to and date_from > date_to:
                st.error("⚠️ 'من تاريخ' يجب أن يكون قبل 'إلى تاريخ'")
                return
    else:
        st.caption("ℹ️ هذا التصدير لا يدعم فلترة التاريخ (كل السجلات)")

    st.markdown("#### 3️⃣ توليد الملف")
    spacer(1)

    if st.button(
        "📊 توليد ملف Excel",
        type="primary",
        use_container_width=True,
        key="excel_generate_btn"
    ):
        with st.spinner("⏳ جاري تجهيز الملف..."):
            try:
                func = export_info["func"]

                if export_info["has_date_filter"]:
                    data = func(clinic["id"], date_from=date_from, date_to=date_to)
                else:
                    data = func(clinic["id"])

                ts = datetime.now().strftime("%Y%m%d_%H%M")
                filename = "{}_{}.xlsx".format(export_info["filename"], ts)

                st.session_state["_excel_data"] = data
                st.session_state["_excel_filename"] = filename
                st.session_state["_excel_size"] = len(data)

                st.success("✅ تم تجهيز الملف! ({:.1f} KB)".format(len(data) / 1024.0))

            except Exception as e:
                st.error("❌ خطأ أثناء التصدير")
                st.exception(e)

    if "_excel_data" in st.session_state and st.session_state["_excel_data"]:
        st.markdown("#### 4️⃣ حمّل الملف")
        spacer(1)

        size_kb = st.session_state.get("_excel_size", 0) / 1024.0
        st.info("📁 جاهز للتحميل — **{:.1f} KB**".format(size_kb))

        st.download_button(
            label="⬇️ تحميل الملف الآن",
            data=st.session_state["_excel_data"],
            file_name=st.session_state["_excel_filename"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
            key="excel_download_btn"
        )

        spacer(1)

        if st.button("🗑️ حذف الملف من الذاكرة", key="excel_clear_btn"):
            st.session_state.pop("_excel_data", None)
            st.session_state.pop("_excel_filename", None)
            st.session_state.pop("_excel_size", None)
            st.rerun()

    spacer(2)
    with st.expander("📖 معلومات مفيدة"):
        st.markdown("""
        ### ما الذي يُصدَّر؟

        - **📦 الكل:** ملف واحد فيه 4 أوراق (الحوامل، الزيارات، الوصفات، التحصينات)
        - **👩 الحوامل:** قائمة كاملة بالحوامل + بيانات الحمل (LMP, EDD, أسابيع الحمل)
        - **🩺 الزيارات:** كل الزيارات الطبية مع العلامات الحيوية
        - **💊 الوصفات:** الوصفات مع الأدوية والتشخيص
        - **💉 التحصينات:** سجل اللقاحات

        ### نصائح

        - **الأدوية (jsonb)** تُحوَّل إلى نص مقروء داخل الخلية
        - **تحليل AI** يُدرج كنص JSON (يمكن أن يكون طويلاً)
        - **التواريخ** بصيغة `YYYY-MM-DD`
        - **RTL** مفعّل تلقائياً في كل الأوراق
        """)
