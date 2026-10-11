# -*- coding: utf-8 -*-
"""AI analysis — clean, patient-centric design"""
import time
import json
import streamlit as st

from services.patients import list_patients_cached, get_patient_summary_cached
from services.visits import list_visits_cached
from services.ai_analysis import (
    analyze_patient, AIError, DEFAULT_MODEL, DEEP_MODEL, get_saved_analysis
)
from core.cache import clear_all


def render(clinic, user, key_prefix="main"):
    """AI analysis page — clean workflow"""

    # ============ PAGE HEADER ============
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h1 style="margin:0 !important; font-size:1.75rem !important; color:#0F172A;">
            🤖 تحليل المخاطر بالذكاء الاصطناعي
        </h1>
        <p style="color:#64748B; margin:0.35rem 0 0 0; font-size:0.95rem;">
            اختر حاملاً لتحليل بياناتها الطبية والحصول على تقرير ذكي
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ============ STEP 1: SELECT PATIENT ============
    try:
        all_patients = list_patients_cached(clinic["id"])
    except Exception as e:
        st.error("تعذر تحميل الحوامل: {}".format(e))
        return

    if not all_patients:
        st.info("📭 لا توجد حوامل مسجلات بعد")
        st.caption("أضف حاملاً جديدة من قسم **👩 الحوامل**")
        return

    # ============ STEP 1: SELECTOR CARD ============
    st.markdown("""
    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1rem;">
        <div style="font-size:0.75rem; font-weight:700; color:#15803D; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.25rem;">
            الخطوة 1
        </div>
        <div style="font-weight:700; color:#0F172A; font-size:1rem;">
            اختر الحامل للتحليل
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Search
    search = st.text_input(
        "🔍 ابحث بالاسم أو الهاتف",
        placeholder="اكتبي اسم الحامل...",
        key="ai_search_" + key_prefix
    )

    # Filter
    if search:
        filtered = [
            p for p in all_patients
            if search.lower() in p.get("full_name", "").lower()
            or search in (p.get("phone") or "")
        ]
    else:
        filtered = all_patients

    if not filtered:
        st.warning("لا توجد نتائج مطابقة لـ \"{}\"".format(search))
        return

    # Build options
    pmap = {}
    for p in filtered:
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(p.get("risk_level", "low"), "⚪")
        label = "{} {} — {}".format(risk_icon, p["full_name"], p.get("phone", ""))
        pmap[p["id"]] = label

    # Preselect
    default_pid = st.session_state.get("selected_patient_id")
    default_idx = 0
    if default_pid and default_pid in pmap:
        default_idx = list(pmap.keys()).index(default_pid)

    selected_pid = st.selectbox(
        "الحامل",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        index=default_idx,
        key="ai_patient_" + key_prefix,
        label_visibility="collapsed"
    )

    if not selected_pid:
        return

    # Save selection
    st.session_state["selected_patient_id"] = selected_pid

    # Load patient
    p = get_patient_summary_cached(clinic["id"], selected_pid)
    if not p:
        st.error("الملف غير موجود")
        return

    visits = list_visits_cached(clinic["id"], selected_pid, limit=50)

    # ============ PATIENT SUMMARY CARD ============
    st.write("")

    risk = p.get("risk_level", "low")
    risk_cfg = {
        "low":    {"bg": "#ECFDF5", "fg": "#047857", "icon": "🟢", "label": "منخفض"},
        "medium": {"bg": "#FFFBEB", "fg": "#B45309", "icon": "🟡", "label": "متوسط"},
        "high":   {"bg": "#FEF2F2", "fg": "#B91C1C", "icon": "🔴", "label": "عالي"},
    }.get(risk, {"bg": "#F3F4F6", "fg": "#374151", "icon": "⚪", "label": "—"})

    st.markdown("""
    <div style="background:white; border:1px solid #E2E8F0; border-radius:14px; padding:1.25rem 1.5rem; margin-bottom:1.25rem;">
        <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
            <div style="width:56px; height:56px; border-radius:14px; background:#F0FDF4; display:flex; align-items:center; justify-content:center; font-size:1.75rem; border:1px solid #BBF7D0;">
                👩
            </div>
            <div style="flex:1;">
                <div style="font-weight:800; color:#0F172A; font-size:1.25rem;">
                    {name}
                </div>
                <div style="color:#64748B; font-size:0.9rem; margin-top:0.2rem;">
                    📞 {phone}
                </div>
            </div>
            <div style="background:{risk_bg}; color:{risk_fg}; padding:0.35rem 0.9rem; border-radius:8px; font-weight:700; font-size:0.85rem;">
                {risk_icon} {risk_label}
            </div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:1rem; padding-top:1rem; border-top:1px solid #F1F5F9;">
            <div>
                <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing:0.05em;">عمر الحمل</div>
                <div style="font-weight:800; color:#0F172A; font-size:1.1rem; margin-top:0.2rem;">{ga}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing:0.05em;">الزيارات</div>
                <div style="font-weight:800; color:#0F172A; font-size:1.1rem; margin-top:0.2rem;">{visits_count}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing:0.05em;">G / P</div>
                <div style="font-weight:800; color:#0F172A; font-size:1.1rem; margin-top:0.2rem;">{gp}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing:0.05em;">EDD</div>
                <div style="font-weight:800; color:#0F172A; font-size:1.1rem; margin-top:0.2rem;">{edd}</div>
            </div>
        </div>
    </div>
    """.format(
        name=p["full_name"],
        phone=p.get("phone", "—"),
        risk_bg=risk_cfg["bg"],
        risk_fg=risk_cfg["fg"],
        risk_icon=risk_cfg["icon"],
        risk_label=risk_cfg["label"],
        ga=p.get("gestational_display", "—"),
        visits_count=len(visits),
        gp="{}/{}".format(p.get("gravida", 0), p.get("para", 0)),
        edd=p.get("edd") or "—"
    ), unsafe_allow_html=True)

    # ============ CHECK VISITS ============
    if not visits:
        st.warning("⚠️ **لا توجد زيارات مسجلة لهذه الحامل**")
        st.caption("التحليل يحتاج بيانات الزيارات (الوزن، الضغط، نبض الجنين، إلخ)")
        st.info("👉 أضف زيارة من قسم **👩 الحوامل** → افتح الملف → 🩺 زيارة جديدة")
        return

    # ============ STEP 2: RUN ANALYSIS ============
    st.markdown("""
    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1rem;">
        <div style="font-size:0.75rem; font-weight:700; color:#15803D; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.25rem;">
            الخطوة 2
        </div>
        <div style="font-weight:700; color:#0F172A; font-size:1rem;">
            اختر النموذج وابدأ التحليل
        </div>
    </div>
    """, unsafe_allow_html=True)

    _result_key = "ai_result_" + str(selected_pid)[:8]

    # Two-column: model select + run button
    cc1, cc2 = st.columns([2, 1])
    with cc1:
        model = st.radio(
            "النموذج",
            [DEFAULT_MODEL, DEEP_MODEL],
            format_func=lambda x: {
                "openai/gpt-oss-20b": "⚡ سريع (10 ثواني) — للتحليل اليومي",
                "openai/gpt-oss-120b": "🧠 عميق (30 ثانية) — للحالات المعقدة"
            }.get(x, x),
            key="ai_model_" + key_prefix,
            horizontal=True
        )
    with cc2:
        st.write("")
        st.write("")
        run = st.button("🚀 بدء التحليل", type="primary", use_container_width=True,
                        key="ai_run_" + key_prefix)

    # Run
    if run:
        with st.spinner("🧠 جاري التحليل بالذكاء الاصطناعي..."):
            try:
                t0 = time.time()
                result = analyze_patient(p, visits, model=model)
                result["_elapsed"] = time.time() - t0
                st.session_state[_result_key] = result
                st.success("✅ تم التحليل في {:.1f} ثانية".format(result["_elapsed"]))
                st.rerun()
            except AIError as e:
                st.error("❌ فشل: {}".format(str(e)[:200]))
            except Exception as e:
                st.error("❌ خطأ: {}".format(str(e)[:200]))

    # ============ DISPLAY RESULT ============
    result = st.session_state.get(_result_key)

    if not result:
        try:
            saved = get_saved_analysis(clinic["id"], selected_pid)
            if saved:
                result = saved
                st.info("📂 عرض تحليل محفوظ سابقاً")
        except Exception:
            pass

    if not result:
        st.info("👆 اضغط **🚀 بدء التحليل** للحصول على التقرير الذكي")
        return

    st.divider()

    # ============ RESULT HEADER ============
    st.markdown("""
    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1rem;">
        <div style="font-size:0.75rem; font-weight:700; color:#15803D; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.25rem;">
            النتيجة
        </div>
        <div style="font-weight:700; color:#0F172A; font-size:1rem;">
            التقرير الطبي الذكي
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Risk banner
    res_risk = result.get("risk_level", "low")
    res_cfg = {
        "high":   {"bg": "#FEF2F2", "fg": "#B91C1C", "border": "#EF4444",
                   "icon": "🔴", "label": "خطر عالي"},
        "medium": {"bg": "#FFFBEB", "fg": "#B45309", "border": "#F59E0B",
                   "icon": "🟡", "label": "خطر متوسط"},
        "low":    {"bg": "#ECFDF5", "fg": "#047857", "border": "#10B981",
                   "icon": "🟢", "label": "خطر منخفض"},
    }.get(res_risk, {"bg": "#F3F4F6", "fg": "#374151", "border": "#6B7280",
                     "icon": "⚪", "label": "—"})

    st.markdown(
        '<div style="background:' + res_cfg["bg"] + '; border-radius:14px; padding:1.5rem; '
        'border:1px solid ' + res_cfg["border"] + '; border-right:6px solid ' + res_cfg["border"] + '; margin-bottom:1rem;">'
        '<div style="display:flex; align-items:center; gap:1rem;">'
        '<div style="font-size:2.5rem;">' + res_cfg["icon"] + '</div>'
        '<div style="flex:1;">'
        '<div style="font-weight:800; color:' + res_cfg["fg"] + '; font-size:1.3rem; margin-bottom:0.5rem;">' + res_cfg["label"] + '</div>'
        '<div style="color:#374151; line-height:1.6; font-size:0.95rem;">' + result.get("summary", "") + '</div>'
        '</div></div></div>',
        unsafe_allow_html=True
    )

    if result.get("urgent"):
        st.error("🚨 **حالة عاجلة** — يُنصح بالتدخل الطبي الفوري")

    # Concerns
    concerns = result.get("concerns", [])
    if concerns:
        st.subheader("⚠️ المخاوف الطبية ({})".format(len(concerns)))
        for c in concerns:
            sev = c.get("severity", "medium")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟠"}.get(sev, "⚪")
            with st.expander("{} {}".format(icon, c.get("issue", "")),
                             expanded=(sev == "high")):
                st.write("**الإجراء المقترح:**")
                st.info(c.get("action", "—"))

    # Positives + Recommendations
    c1, c2 = st.columns(2)
    with c1:
        positives = result.get("positives", [])
        if positives:
            st.subheader("✅ الإيجابيات")
            for pos in positives:
                st.success("✓ {}".format(pos))
    with c2:
        recs = result.get("recommendations", [])
        if recs:
            st.subheader("📋 التوصيات")
            for rec in recs:
                st.info("→ {}".format(rec))

    # Metadata
    st.divider()
    days = result.get("next_visit_days", 7)
    c1, c2, c3 = st.columns(3)
    c1.metric("⏰ الزيارة القادمة", "بعد {} يوم".format(days))
    c2.metric("🤖 النموذج", result.get("model", "—").split("/")[-1])
    c3.metric("📅 التاريخ", (result.get("analyzed_at") or "—")[:10])

    if "_elapsed" in result:
        st.caption("⏱️ مدة التنفيذ: {:.2f} ثانية".format(result["_elapsed"]))

    # Actions
    st.write("")
    a1, a2 = st.columns(2)
    with a1:
        report = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 تحميل التقرير JSON",
            report.encode("utf-8"),
            "ai_report_{}.json".format(str(selected_pid)[:8]),
            "application/json",
            key="ai_dl_" + key_prefix,
            use_container_width=True
        )
    with a2:
        if st.button("🗑️ مسح النتيجة الحالية", use_container_width=True,
                     key="ai_clear_" + key_prefix):
            st.session_state[_result_key] = None
            clear_all()
            st.rerun()
