# -*- coding: utf-8 -*-
"""Postpartum Care View — Breastfeeding + Postpartum Plan"""
from datetime import datetime, date, timedelta
import streamlit as st

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from core.save_helper import save_button, mark_result
from services.breastfeeding import (
    create_session, list_sessions, get_last_24h_sessions,
    analyze_breastfeeding, SESSION_TYPES, SIDES, STOOL_COLORS,
    get_session_type_label, get_side_label, get_stool_label,
)
from services.postpartum import (
    generate_postpartum_plan, create_visit, list_visits, get_latest_visit,
    analyze_postpartum_risk, LOCHIA_TYPES, UTERUS_INVOLUTION,
    PERINEUM_HEALING, CORD_STATUS,
    get_lochia_label, get_uterus_label, get_perineum_label, get_cord_label,
)


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_mothers(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id,full_name,phone")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _get_delivery_date(clinic_id, mother_id):
    """Get most recent delivery date for a mother"""
    try:
        rows = (
            db().table("newborns")
            .select("delivery_date")
            .eq("clinic_id", clinic_id)
            .eq("mother_id", mother_id)
            .order("delivery_date", desc=True)
            .limit(1)
            .execute()
            .data or []
        )
        if rows:
            return rows[0].get("delivery_date")
    except Exception:
        pass
    return None


def render(clinic, user):
    page_header_v2(
        title="ما بعد الولادة",
        subtitle="الرضاعة + خطة المتابعة",
        icon="🤱",
    )

    mothers = _fetch_mothers(clinic["id"])
    if not mothers:
        empty_state("👩", "لا يوجد حوامل", "سجل حاملاً أولاً")
        return

    pmap = {m["id"]: "{} — {}".format(m.get("full_name", ""), m.get("phone", "")) for m in mothers}

    saved_id = st.session_state.get("_pp_current_mother")
    if saved_id not in pmap:
        saved_id = list(pmap.keys())[0]

    selected_id = st.selectbox(
        "👩 اختر الأم",
        options=list(pmap.keys()),
        format_func=lambda x: pmap[x],
        index=list(pmap.keys()).index(saved_id) if saved_id in pmap else 0,
        key="pp_mother_select"
    )
    st.session_state["_pp_current_mother"] = selected_id

    mother = next((m for m in mothers if m["id"] == selected_id), None)
    if not mother:
        return

    delivery_date = _get_delivery_date(clinic["id"], selected_id)

    if delivery_date:
        st.caption("📅 تاريخ الولادة: {}".format(str(delivery_date)[:10]))
    else:
        st.caption("⚠️ لم يتم تسجيل ولادة لهذه الأم")

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "🍼 الرضاعة",
        "📅 خطة المتابعة",
        "📊 التحليل",
    ])

    with tab1:
        _render_breastfeeding_tab(clinic, user, mother)

    with tab2:
        _render_plan_tab(clinic, user, mother, delivery_date)

    with tab3:
        _render_analysis_tab(clinic, user, mother)


@st.fragment
def _render_breastfeeding_tab(clinic, user, mother):
    """Breastfeeding log"""

    section_header_v2("🍼", "سجل الرضاعة")

    # Add new session
    with st.expander("➕ إضافة جلسة رضاعة", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            session_type = st.selectbox(
                "نوع الجلسة",
                options=list(SESSION_TYPES.keys()),
                format_func=lambda x: SESSION_TYPES[x],
                key="bf_type"
            )
            side = st.selectbox(
                "الجانب",
                options=[""] + list(SIDES.keys()),
                format_func=lambda x: "—" if x == "" else SIDES[x],
                key="bf_side"
            )
            duration = st.number_input(
                "المدة (دقيقة)",
                min_value=0, max_value=120,
                value=15, step=1,
                key="bf_duration"
            )
        with c2:
            amount = st.number_input(
                "الكمية (ml) — للشفط",
                min_value=0, max_value=500,
                value=0, step=10,
                key="bf_amount"
            )
            diaper_wet = st.checkbox("حفاض مبلل", key="bf_wet")
            diaper_dirty = st.checkbox("حفاض متسخ", key="bf_dirty")

        stool_color = ""
        if diaper_dirty:
            stool_color = st.selectbox(
                "لون البراز",
                options=list(STOOL_COLORS.keys()),
                format_func=lambda x: STOOL_COLORS[x],
                key="bf_stool"
            )

        notes = st.text_input("ملاحظات", key="bf_notes")

        def _do_save_session():
            try:
                create_session(
                    clinic_id=clinic["id"],
                    mother_id=mother["id"],
                    data={
                        "session_type": session_type,
                        "side": side or None,
                        "duration_min": duration if duration > 0 else None,
                        "amount_ml": amount if amount > 0 else None,
                        "diaper_wet": diaper_wet,
                        "diaper_dirty": diaper_dirty,
                        "stool_color": stool_color or None,
                        "notes": notes or None,
                    },
                )
                mark_result("bf_session", success=True)
            except Exception as e:
                mark_result("bf_session", success=False, error=e)

        save_button("bf_session", _do_save_session, label="💾 حفظ الجلسة")

    # Sessions list
    sessions = list_sessions(clinic["id"], mother["id"], limit=20)

    if not sessions:
        st.info("📭 لا توجد جلسات مسجلة")
        return

    st.write("")
    st.caption("📊 {} جلسة".format(len(sessions)))

    for s in sessions[:10]:
        ts = s.get("recorded_at", "")
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = str(ts)[:16]

        details = []
        if s.get("duration_min"):
            details.append("⏱️ {}د".format(s["duration_min"]))
        if s.get("amount_ml"):
            details.append("🥛 {}ml".format(s["amount_ml"]))
        if s.get("diaper_wet"):
            details.append("💧 مبلل")
        if s.get("diaper_dirty"):
            details.append("💩 متسخ")
        if s.get("side"):
            details.append("📌 {}".format(SIDES.get(s["side"], s["side"])))

        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                    padding:0.7rem 1rem;margin-bottom:0.4rem;
                    border-right:3px solid #16A34A;">
            <div style="display:flex;justify-content:space-between;">
                <div style="font-weight:600;color:#0F172A;">
                    {icon} {type}
                </div>
                <div style="color:#64748B;font-size:0.8rem;">{time}</div>
            </div>
            <div style="color:#64748B;font-size:0.82rem;margin-top:0.3rem;">
                {details}
            </div>
        </div>
        """.format(
            icon="🍼" if s.get("session_type") == "breastfeeding" else "🤱",
            type=SESSION_TYPES.get(s.get("session_type"), "—"),
            time=time_str,
            details=" · ".join(details) if details else "—",
        ), unsafe_allow_html=True)


@st.fragment
def _render_plan_tab(clinic, user, mother, delivery_date):
    """Postpartum care plan"""

    if not delivery_date:
        empty_state(
            "📅",
            "لا توجد ولادة مسجلة",
            "سجل ولادة من قسم 'سجل المواليد' أولاً"
        )
        return

    plan = generate_postpartum_plan(delivery_date)

    section_header_v2("📅", "خطة المتابعة (WHO)")

    for v in plan:
        status = v["status"]
        if status == "past":
            color = "#10B981"
            icon = "✅"
            label = "منتهية"
        elif status == "current":
            color = "#0EA5E9"
            icon = "🔵"
            label = "حالية"
        else:
            color = "#F59E0B"
            icon = "⏳"
            label = "قادمة"

        with st.expander(
            "{} {} — {}".format(icon, v["title"], label),
            expanded=(status == "current")
        ):
            st.markdown("**📅 التاريخ المتوقع:** {}".format(v["target_date"]))

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**👩 فحوصات الأم:**")
                for c in v["checks_mother"]:
                    st.markdown("  - {}".format(c))
            with c2:
                st.markdown("**👶 فحوصات المولود:**")
                for c in v["checks_baby"]:
                    st.markdown("  - {}".format(c))


@st.fragment
def _render_analysis_tab(clinic, user, mother):
    """Analysis summary"""

    section_header_v2("📊", "التحليل الشامل")

    # Breastfeeding analysis
    bf = analyze_breastfeeding(clinic["id"], mother["id"])

    st.markdown("##### 🍼 الرضاعة (آخر 24 ساعة)")

    color = bf["color"]
    st.markdown("""
    <div style="background:white;border:2px solid {color};border-radius:14px;
                padding:1.25rem;border-right:6px solid {color};margin-bottom:1rem;">
        <div style="font-weight:700;color:{color};font-size:1.15rem;">
            {label}
        </div>
        <div style="color:#334155;margin-top:0.5rem;font-size:0.9rem;">
            {sessions} جلسة · متوسط {duration} دقيقة
        </div>
        <div style="color:#334155;font-size:0.85rem;margin-top:0.25rem;">
            💧 {wet} حفاض مبلل · 💩 {dirty} متسخ
        </div>
    </div>
    """.format(
        color=color,
        label=bf["label"],
        sessions=bf["sessions_24h"],
        duration=bf.get("avg_duration", 0),
        wet=bf.get("wet_diapers", 0),
        dirty=bf.get("dirty_diapers", 0),
    ), unsafe_allow_html=True)

    if bf.get("issues"):
        for issue in bf["issues"]:
            st.warning("⚠️ {}".format(issue))

    st.markdown("**التوصيات:**")
    for r in bf["recommendation"]:
        st.markdown("  - {}".format(r))

    # Latest postpartum visit
    latest = get_latest_visit(clinic["id"], mother["id"])
    if latest:
        st.divider()
        st.markdown("##### 🩺 آخر زيارة ما بعد الولادة")

        risk = analyze_postpartum_risk(latest)
        rc = risk["color"]

        st.markdown("""
        <div style="background:white;border:2px solid {color};border-radius:14px;
                    padding:1rem;border-right:6px solid {color};">
            <div style="font-weight:700;color:{color};">
                {status_label}
            </div>
            <div style="color:#64748B;font-size:0.85rem;margin-top:0.3rem;">
                📅 {date}
            </div>
        </div>
        """.format(
            color=rc,
            status_label={"critical": "🚨 حرج", "warning": "⚠️ يحتاج متابعة", "normal": "✅ طبيعي"}[risk["status"]],
            date=str(latest.get("visit_date", ""))[:10],
        ), unsafe_allow_html=True)

        for a in risk["alerts"]:
            st.warning("⚠️ {}".format(a["message"]))
