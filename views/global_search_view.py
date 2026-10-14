# -*- coding: utf-8 -*-
"""
Global Search View
واجهة البحث الشامل
"""
import streamlit as st

from core.ui import page_header_v2, empty_state, kpi_card_v2
from services.global_search import search_all


def _navigate_to(nav, extra=None):
    """Navigate to a section"""
    st.session_state["nav_section"] = nav
    if extra:
        if extra.get("patient_id"):
            st.session_state["selected_patient_id"] = extra["patient_id"]
    st.rerun()


def _render_result_card(r):
    """Single result card"""
    st.markdown("""
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                padding:1rem 1.25rem;margin-bottom:0.5rem;
                border-right:4px solid {color};
                transition:all 0.2s ease;">
        <div style="font-weight:700;color:#0F172A;font-size:1rem;">
            {icon} {title}
        </div>
        <div style="color:#64748B;font-size:0.85rem;margin-top:0.35rem;">
            {subtitle}
        </div>
        {meta}
    </div>
    """.format(
        color=r.get("color", "#16A34A"),
        icon=r.get("icon", "•"),
        title=r.get("title", "—"),
        subtitle=r.get("subtitle", ""),
        meta='<div style="color:#94A3B8;font-size:0.78rem;margin-top:0.3rem;">{}</div>'.format(
            r.get("meta", "")) if r.get("meta") else "",
    ), unsafe_allow_html=True)

    # Action button
    c1, c2, c3 = st.columns([1, 1, 5])
    with c1:
        if st.button("↗️ فتح", key="open_{}_{}".format(r["type"], r["id"]),
                     use_container_width=True):
            _navigate_to(r.get("nav", "dashboard"), r.get("extra"))


def _render_empty_search():
    """Initial empty state"""
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem;">
        <div style="font-size:4rem;margin-bottom:0.75rem;">🔍</div>
        <h2 style="color:#0F172A;margin:0.5rem 0;">البحث الشامل</h2>
        <p style="color:#64748B;margin-top:0.5rem;">
            ابحث في كل بيانات العيادة — حوامل، زيارات، تحاليل، شهادات، وصفات
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 أمثلة للبحث:")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**👩 حوامل**")
        st.caption("اسم أو رقم هاتف")
        st.code("فاطمة", language=None)
    with c2:
        st.markdown("**🔬 تحاليل**")
        st.caption("نوع التحليل")
        st.code("CBC", language=None)
    with c3:
        st.markdown("**💊 وصفات**")
        st.caption("التشخيص")
        st.code("فقر دم", language=None)
    with c4:
        st.markdown("**📄 شهادات**")
        st.caption("اسم الحامل")
        st.code("زينب", language=None)


def _render_tab_results(results, tab_key):
    """Render results for a specific tab"""
    items = results.get(tab_key, [])
    if not items:
        empty_state("📭", "لا توجد نتائج", "جرب كلمة بحث أخرى")
        return

    for r in items:
        _render_result_card(r)


def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="البحث الشامل",
        subtitle="ابحث في كل بيانات العيادة بسرعة",
        icon="🔍",
    )

    # Search input
    c1, c2 = st.columns([4, 1])
    with c1:
        query = st.text_input(
            "🔍 ابحث...",
            placeholder="اسم حامل، رقم هاتف، نوع تحليل، تشخيص...",
            label_visibility="collapsed",
            key="global_search_input"
        )
    with c2:
        if st.button("🔍 بحث", type="primary", use_container_width=True,
                     key="global_search_btn"):
            if query and len(query.strip()) >= 2:
                st.session_state["_search_query"] = query.strip()

    # Also search on Enter (auto via rerun)
    if query and len(query.strip()) >= 2:
        st.session_state["_search_query"] = query.strip()

    current_query = st.session_state.get("_search_query", "")

    if not current_query or len(current_query) < 2:
        _render_empty_search()
        return

    # Perform search
    with st.spinner("⏳ جاري البحث..."):
        results = search_all(clinic["id"], current_query)

    total = results.get("total", 0)

    # Summary
    if total == 0:
        st.warning("🔍 لا توجد نتائج لـ **{}**".format(current_query))
        empty_state(
            "❓",
            "لم نجد شيئاً",
            "جرب كلمة بحث أخرى — قد تحتاج كتابة أطول للاسم"
        )
        return

    st.success("✅ وجدنا **{}** نتيجة لـ **{}**".format(total, current_query))
    st.write("")

    # Summary cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card_v2("👩", len(results["patients"]), "حوامل")
    with c2:
        kpi_card_v2("🩺", len(results["visits"]), "زيارات")
    with c3:
        kpi_card_v2("🔬", len(results["labs"]), "تحاليل")
    with c4:
        kpi_card_v2("📄", len(results["certificates"]), "شهادات")
    with c5:
        kpi_card_v2("💊", len(results["prescriptions"]), "وصفات")

    st.divider()

    # Tabs
    tabs = st.tabs([
        "🎯 الكل ({})".format(total),
        "👩 حوامل ({})".format(len(results["patients"])),
        "🩺 زيارات ({})".format(len(results["visits"])),
        "🔬 تحاليل ({})".format(len(results["labs"])),
        "📄 شهادات ({})".format(len(results["certificates"])),
        "💊 وصفات ({})".format(len(results["prescriptions"])),
    ])

    with tabs[0]:
        # All results
        any_shown = False
        for category, label in [
            ("patients", "👩 الحوامل"),
            ("visits", "🩺 الزيارات"),
            ("labs", "🔬 التحاليل"),
            ("certificates", "📄 الشهادات"),
            ("prescriptions", "💊 الوصفات"),
        ]:
            items = results.get(category, [])
            if items:
                any_shown = True
                st.markdown("#### {}".format(label))
                for r in items[:5]:
                    _render_result_card(r)
                if len(items) > 5:
                    st.caption("... و{} أخرى (اذهب للتبويب)".format(len(items) - 5))
                st.write("")

        if not any_shown:
            st.info("لا توجد نتائج")

    with tabs[1]:
        _render_tab_results(results, "patients")

    with tabs[2]:
        _render_tab_results(results, "visits")

    with tabs[3]:
        _render_tab_results(results, "labs")

    with tabs[4]:
        _render_tab_results(results, "certificates")

    with tabs[5]:
        _render_tab_results(results, "prescriptions")
