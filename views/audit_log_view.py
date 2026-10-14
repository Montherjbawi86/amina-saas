# -*- coding: utf-8 -*-
"""
Audit Log View
واجهة سجل التغييرات
"""
from datetime import date, timedelta, datetime
import streamlit as st
import pandas as pd

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from core.db import db
from services.audit_log import (
    list_logs, get_summary, get_user_activity,
    get_action_icon, get_action_label, get_action_color,
    get_entity_label, get_available_actions, get_available_entities,
)


# ============================================
# HELPERS
# ============================================

def _fetch_users(clinic_id):
    try:
        return db().table("users").select(
            "id,full_name,role"
        ).eq("clinic_id", clinic_id).execute().data or []
    except Exception:
        return []


def _format_timestamp(ts):
    """Format timestamp nicely"""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16]


def _time_ago(ts):
    """Relative time"""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "الآن"
        elif secs < 3600:
            return "قبل {} دقيقة".format(secs // 60)
        elif secs < 86400:
            return "قبل {} ساعة".format(secs // 3600)
        elif secs < 604800:
            return "قبل {} يوم".format(secs // 86400)
        else:
            return "قبل {} أسبوع".format(secs // 604800)
    except Exception:
        return ""


def _render_log_card(log):
    """Single log entry card"""
    action = log.get("action", "view")
    entity = log.get("entity_type", "—")
    icon = get_action_icon(action)
    label = get_action_label(action)
    color = get_action_color(action)
    entity_label = get_entity_label(entity)

    user_name = log.get("_user_name", "—")
    ts = log.get("created_at", "")
    time_str = _format_timestamp(ts)
    relative = _time_ago(ts)

    details = log.get("details") or {}
    details_str = ""
    if details:
        # Show key parts
        parts = []
        for k in list(details.keys())[:3]:
            v = details[k]
            if isinstance(v, (str, int, float)):
                parts.append("{}: {}".format(k, v))
        if parts:
            details_str = " · ".join(parts)

    st.markdown("""
    <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                padding:0.75rem 1rem;margin-bottom:0.4rem;
                border-right:3px solid {color};
                display:flex;gap:0.85rem;align-items:center;">
        <div style="font-size:1.5rem;">{icon}</div>
        <div style="flex:1;min-width:0;">
            <div style="font-weight:600;color:#0F172A;font-size:0.9rem;">
                {label} — {entity}
            </div>
            <div style="color:#64748B;font-size:0.78rem;margin-top:0.2rem;">
                👤 {user} · 🕐 {time_str} ({relative})
            </div>
            {details}
        </div>
    </div>
    """.format(
        color=color,
        icon=icon,
        label=label,
        entity=entity_label,
        user=user_name,
        time_str=time_str,
        relative=relative,
        details='<div style="color:#94A3B8;font-size:0.72rem;margin-top:0.2rem;">{}</div>'.format(details_str) if details_str else "",
    ), unsafe_allow_html=True)


# ============================================
# TAB 1: OVERVIEW
# ============================================

def _render_overview_tab(clinic, user):
    """Summary + stats"""

    summary = get_summary(clinic["id"], days=30)

    # Row 1: KPIs
    total = summary["total"]
    actions = summary.get("actions", {})
    entities = summary.get("entities", {})

    creates = actions.get("create", 0)
    updates = actions.get("update", 0)
    deletes = actions.get("delete", 0)
    logins = actions.get("login", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card_v2("📊", total, "إجراء (30 يوم)")
    with c2:
        kpi_card_v2("➕", creates, "إنشاء")
    with c3:
        kpi_card_v2("✏️", updates, "تعديل")
    with c4:
        kpi_card_v2("🗑️", deletes, "حذف")
    with c5:
        kpi_card_v2("🔓", logins, "تسجيل دخول")

    st.divider()

    # Top users
    section_header_v2("🥇", "الأكثر نشاطاً")

    top_users = summary.get("top_users", [])
    if not top_users:
        st.info("لا توجد بيانات")
    else:
        for i, u in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1] if i <= 5 else "•"
            st.markdown("""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                        padding:0.6rem 1rem;margin-bottom:0.35rem;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:1.2rem;">{medal}</span>
                    <span style="font-weight:600;color:#0F172A;margin-right:0.5rem;">{name}</span>
                </div>
                <div style="background:#F0FDF4;color:#15803D;padding:0.2rem 0.7rem;
                            border-radius:999px;font-weight:700;font-size:0.8rem;">
                    {count} إجراء
                </div>
            </div>
            """.format(medal=medal, name=u.get("name", "—"), count=u.get("count", 0)),
            unsafe_allow_html=True)

    st.divider()

    # By action type
    section_header_v2("⚡", "حسب نوع الإجراء")

    if not actions:
        st.info("لا توجد إجراءات")
    else:
        for action, count in sorted(actions.items(), key=lambda x: -x[1]):
            icon = get_action_icon(action)
            label = get_action_label(action)
            color = get_action_color(action)
            st.markdown("""
            <div style="display:flex;justify-content:space-between;
                        padding:0.5rem 0.85rem;border-bottom:1px solid #F1F5F9;">
                <span style="color:#334155;">
                    <span style="color:{color};font-size:1rem;">{icon}</span>
                    {label}
                </span>
                <span style="font-weight:700;color:#0F172A;">{count}</span>
            </div>
            """.format(color=color, icon=icon, label=label, count=count),
            unsafe_allow_html=True)


# ============================================
# TAB 2: ALL LOGS
# ============================================

def _render_all_logs_tab(clinic, user):
    """Filterable list of all logs"""

    users = _fetch_users(clinic["id"])
    umap = {"all": "كل المستخدمين"}
    for u in users:
        umap[u["id"]] = "{} ({})".format(u.get("full_name", "—"), u.get("role", ""))

    # Filters
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        user_filter = st.selectbox(
            "المستخدم",
            options=list(umap.keys()),
            format_func=lambda x: umap[x],
            key="audit_user_filter"
        )

    with c2:
        actions = ["all"] + get_available_actions()
        action_filter = st.selectbox(
            "الإجراء",
            options=actions,
            format_func=lambda x: "الكل" if x == "all" else "{} {}".format(
                get_action_icon(x), get_action_label(x)),
            key="audit_action_filter"
        )

    with c3:
        entities = ["all"] + get_available_entities()
        entity_filter = st.selectbox(
            "النوع",
            options=entities,
            format_func=lambda x: "الكل" if x == "all" else get_entity_label(x),
            key="audit_entity_filter"
        )

    with c4:
        days = st.selectbox(
            "الفترة",
            options=[1, 7, 30, 90, 365],
            format_func=lambda x: {
                1: "اليوم", 7: "7 أيام", 30: "30 يوم",
                90: "3 أشهر", 365: "سنة"
            }[x],
            index=2,
            key="audit_days_filter"
        )

    # Search
    search = st.text_input(
        "🔍 بحث في التفاصيل",
        placeholder="اسم، كلمة مفتاحية...",
        key="audit_search"
    )

    # Date range
    date_from = date.today() - timedelta(days=days)
    date_to = date.today()

    # Fetch
    with st.spinner("⏳ جاري التحميل..."):
        logs = list_logs(
            clinic["id"],
            user_id=None if user_filter == "all" else user_filter,
            action=None if action_filter == "all" else action_filter,
            entity_type=None if entity_filter == "all" else entity_filter,
            date_from=date_from,
            date_to=date_to,
            search=search or None,
            limit=500,
        )

    if not logs:
        empty_state(
            "📭",
            "لا توجد سجلات",
            "جرب تغيير الفلاتر أو الفترة"
        )
        return

    st.caption("📊 {} نتيجة".format(len(logs)))
    st.write("")

    # Render logs (max 100 at a time)
    for log in logs[:100]:
        _render_log_card(log)

    if len(logs) > 100:
        st.info("📌 عرض أول 100 من {}".format(len(logs)))

    # Export CSV
    st.divider()
    if st.button("📥 تصدير CSV", key="audit_csv_export"):
        rows = []
        for l in logs:
            rows.append({
                "التاريخ": _format_timestamp(l.get("created_at")),
                "المستخدم": l.get("_user_name", "—"),
                "الإجراء": get_action_label(l.get("action", "")),
                "النوع": get_entity_label(l.get("entity_type", "")),
                "التفاصيل": str(l.get("details", ""))[:200],
            })
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ تحميل CSV",
            csv,
            "audit_log_{}.csv".format(date.today().strftime("%Y%m%d")),
            "text/csv",
            key="audit_csv_download"
        )


# ============================================
# TAB 3: USER ACTIVITY
# ============================================

def _render_user_tab(clinic, user):
    """Per-user activity"""

    users = _fetch_users(clinic["id"])
    if not users:
        empty_state("👤", "لا يوجد مستخدمون", "")
        return

    umap = {u["id"]: "{} — {}".format(
        u.get("full_name", "—"),
        u.get("role", "")
    ) for u in users}

    selected = st.selectbox(
        "المستخدم",
        options=list(umap.keys()),
        format_func=lambda x: umap[x],
        key="audit_user_activity"
    )

    if not selected:
        return

    activity = get_user_activity(clinic["id"], selected, days=30)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card_v2("📊", activity["total"], "إجمالي (30 يوم)")
    with c2:
        kpi_card_v2("⚡", len(activity["actions"]), "أنواع الإجراءات")
    with c3:
        kpi_card_v2("📁", len(activity["entities"]), "أنواع البيانات")

    st.divider()
    section_header_v2("⚡", "توزيع الإجراءات")

    for action, count in sorted(activity["actions"].items(), key=lambda x: -x[1]):
        st.markdown("""
        <div style="display:flex;justify-content:space-between;
                    padding:0.5rem 0.85rem;border-bottom:1px solid #F1F5F9;">
            <span>{icon} {label}</span>
            <span style="font-weight:700;color:#0F172A;">{count}</span>
        </div>
        """.format(
            icon=get_action_icon(action),
            label=get_action_label(action),
            count=count,
        ), unsafe_allow_html=True)

    if activity["entities"]:
        st.write("")
        section_header_v2("📁", "توزيع البيانات")
        for ent, count in sorted(activity["entities"].items(), key=lambda x: -x[1]):
            st.markdown("""
            <div style="display:flex;justify-content:space-between;
                        padding:0.5rem 0.85rem;border-bottom:1px solid #F1F5F9;">
                <span>{label}</span>
                <span style="font-weight:700;color:#0F172A;">{count}</span>
            </div>
            """.format(label=get_entity_label(ent), count=count),
            unsafe_allow_html=True)


# ============================================
# TAB 4: HELP
# ============================================

def _render_help_tab():
    """Help & info"""
    st.markdown("""
    ### 📝 ما هو سجل التغييرات؟

    سجل تلقائي لكل إجراء مهم يقوم به المستخدمون:
    - ✅ تسجيل دخول / خروج
    - ✅ إنشاء / تعديل / حذف السجلات
    - ✅ تصدير البيانات
    - ✅ تفعيل 2FA

    ### 🎯 الفائدة

    1. **الشفافية:** تعرف من فعل ماذا ومتى
    2. **الأمان:** كشف الأنشطة المشبوهة
    3. **الامتثال:** متطلبات قانونية للعيادات
    4. **المراجعة:** تتبع الأخطاء

    ### 🔍 أمثلة

    - **من حذف هذا الحامل؟** → ابحث في `action=delete`
    - **متى سجلت دخول؟** → ابحث في `action=login`
    - **ماذا فعلت الممرضة اليوم؟** → فلتر بالمستخدم

    ### ⚠️ ملاحظات

    - السجل **لا يُحذف** تلقائياً (يبقى للأبد)
    - **بيانات الحساسة** (كلمات المرور) لا تُسجَّل
    - **الكمية:** مع 50 عملية/يوم = 18,000/سنة
    """)


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="سجل التغييرات",
        subtitle="تتبع كل إجراء في العيادة",
        icon="📝",
        badge="آخر 30 يوم"
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 نظرة عامة",
        "📋 كل السجلات",
        "👤 نشاط المستخدم",
        "ℹ️ مساعدة",
    ])

    with tab1:
        _render_overview_tab(clinic, user)
    with tab2:
        _render_all_logs_tab(clinic, user)
    with tab3:
        _render_user_tab(clinic, user)
    with tab4:
        _render_help_tab()
