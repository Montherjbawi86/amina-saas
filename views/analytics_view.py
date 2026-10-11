# -*- coding: utf-8 -*-
"""Analytics & reports view"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from services.analytics import (
    get_clinic_overview, get_monthly_patients, get_monthly_visits,
    get_top_patients_by_visits, get_upcoming_week_appointments,
    get_alerts_summary,
)


def render(clinic, user):
    """Render analytics tab"""
    st.markdown("### 📈 التقارير والإحصائيات")
    st.caption("نظرة شاملة على أداء العيادة")

    # ============ ROW 1: KPI CARDS ============
    overview = get_clinic_overview(clinic["id"])

    if "error" in overview:
        st.error("خطأ في التحميل: {}".format(overview["error"]))
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi("👩", overview["total_patients"], "إجمالي الحوامل", "#0EA5A0")
    with c2:
        _kpi("🆕", overview["new_patients_this_month"], "جديدات هذا الشهر", "#10B981")
    with c3:
        _kpi("🩺", overview["total_visits"], "إجمالي الزيارات", "#22C55E")
    with c4:
        _kpi("📅", overview["total_appointments"], "إجمالي المواعيد", "#F59E0B")

    st.write("")

    # ============ ROW 2: KPIs ============
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi("💊", overview["total_prescriptions"], "الوصفات", "#10B981")
    with c2:
        _kpi("💉", overview["total_vaccinations"], "التحصينات", "#10B981")
    with c3:
        _kpi("📎", overview["total_files"], "الملفات", "#22C55E")
    with c4:
        adherence = overview["adherence_pct"]
        color = "#10B981" if adherence >= 70 else "#F59E0B" if adherence >= 40 else "#EF4444"
        _kpi("✅", "{}%".format(adherence), "الالتزام بالمواعيد", color)

    st.divider()

    # ============ CHARTS ROW 1 ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📈 الحوامل الجدد (6 أشهر)")
        monthly = get_monthly_patients(clinic["id"], months_back=6)
        if monthly:
            df = pd.DataFrame(monthly)
            fig = px.bar(df, x="label", y="count",
                labels={"label": "الشهر", "count": "العدد"},
                color_discrete_sequence=["#0EA5A0"])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False)
            fig.update_traces(marker_line_color="#087A76", marker_line_width=1)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### 🩺 الزيارات (6 أشهر)")
        monthly_v = get_monthly_visits(clinic["id"], months_back=6)
        if monthly_v:
            df = pd.DataFrame(monthly_v)
            fig = px.line(df, x="label", y="count", markers=True,
                labels={"label": "الشهر", "count": "العدد"})
            fig.update_traces(line_color="#22C55E", marker_size=10)
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # ============ CHARTS ROW 2 ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🎯 توزيع المخاطر")
        risk = overview.get("risk_distribution", {})
        if risk and sum(risk.values()) > 0:
            labels = {
                "low": "🟢 منخفض",
                "medium": "🟡 متوسط",
                "high": "🔴 عالي",
            }
            data = [{"المستوى": labels.get(k, k), "العدد": v}
                    for k, v in risk.items() if v > 0]
            if data:
                df = pd.DataFrame(data)
                colors = {"🟢 منخفض": "#10B981", "🟡 متوسط": "#F59E0B", "🔴 عالي": "#EF4444"}
                fig = px.pie(df, values="العدد", names="المستوى",
                    color="المستوى", color_discrete_map=colors, hole=0.4)
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات")

    with c2:
        st.markdown("#### 📅 حالة المواعيد")
        appt_status = overview.get("appt_status", {})
        if appt_status:
            labels = {
                "scheduled": "🔵 منتظر",
                "confirmed": "🟢 مؤكد",
                "completed": "✅ مكتمل",
                "cancelled": "🔴 ملغى",
                "no_show": "🟠 لم يحضر",
            }
            data = [{"الحالة": labels.get(k, k), "العدد": v}
                    for k, v in appt_status.items() if v > 0]
            if data:
                df = pd.DataFrame(data)
                fig = px.bar(df, x="العدد", y="الحالة", orientation="h",
                    color="الحالة",
                    color_discrete_map={
                        "🔵 منتظر": "#22C55E",
                        "🟢 مؤكد": "#10B981",
                        "✅ مكتمل": "#6B7280",
                        "🔴 ملغى": "#EF4444",
                        "🟠 لم يحضر": "#F59E0B",
                    })
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد مواعيد")

    st.divider()

    # ============ ALERTS + UPCOMING ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🔔 التنبيهات الطبية")
        alerts = get_alerts_summary(clinic["id"])
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _kpi_mini("🚨", alerts.get("critical", 0), "حرج", "#DC2626")
        with c2:
            _kpi_mini("🔴", alerts.get("high", 0), "عالي", "#EF4444")
        with c3:
            _kpi_mini("🟡", alerts.get("medium", 0), "متوسط", "#F59E0B")
        with c4:
            _kpi_mini("🟢", alerts.get("low", 0), "منخفض", "#10B981")

    with c2:
        st.markdown("#### 📅 مواعيد الأسبوع القادم")
        upcoming = get_upcoming_week_appointments(clinic["id"])
        st.markdown("""
        <div style="background:linear-gradient(135deg,#F0FDFA 0%,#CCFBF1 100%); border-radius:14px; padding:1.5rem; text-align:center; border-right:5px solid #0EA5A0;">
            <div style="font-size:3rem; font-weight:800; color:#0EA5A0;">{}</div>
            <div style="color:#6B7280; font-size:1rem; margin-top:0.3rem;">موعد خلال 7 أيام</div>
        </div>
        """.format(upcoming), unsafe_allow_html=True)

    st.divider()

    # ============ TOP PATIENTS ============
    st.markdown("#### 🏆 أكثر الحوامل زيارة")
    top = get_top_patients_by_visits(clinic["id"], limit=10)

    if not top:
        st.info("لا توجد بيانات")
    else:
        df = pd.DataFrame([{
            "الاسم": p["name"],
            "الهاتف": p["phone"],
            "المخاطر": {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(p["risk_level"], "⚪"),
            "عدد الزيارات": p["visits"],
        } for p in top])
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 تحميل CSV", csv, "top_patients.csv", "text/csv")

    # ============ EXPORT ALL ============
    st.divider()
    st.markdown("#### 📥 تصدير التقرير الكامل")

    full_report = {
        "clinic": clinic.get("name", ""),
        "generated_at": str(pd.Timestamp.now()),
        "overview": overview,
        "monthly_patients": get_monthly_patients(clinic["id"], 6),
        "monthly_visits": get_monthly_visits(clinic["id"], 6),
        "top_patients": top,
        "alerts": alerts,
    }

    import json
    report_json = json.dumps(full_report, ensure_ascii=False, indent=2, default=str)
    st.download_button(
        "📥 تحميل التقرير (JSON)",
        report_json.encode("utf-8"),
        "clinic_report_{}.json".format(str(clinic["id"])[:8]),
        "application/json"
    )


# ============================================
# HELPERS
# ============================================
def _kpi(icon, value, label, color):
    st.markdown("""
    <div style="background:white; border-radius:12px; padding:1rem; text-align:center; border-right:4px solid {color}; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
        <div style="font-size:1.75rem;">{icon}</div>
        <div style="font-size:1.5rem; font-weight:800; color:{color}; margin-top:0.25rem;">{value}</div>
        <div style="font-size:0.75rem; color:#6B7280; margin-top:0.15rem;">{label}</div>
    </div>
    """.format(icon=icon, value=value, label=label, color=color), unsafe_allow_html=True)


def _kpi_mini(icon, value, label, color):
    st.markdown("""
    <div style="background:white; border-radius:10px; padding:0.6rem 0.5rem; text-align:center; border-right:3px solid {color};">
        <div style="font-size:1.25rem;">{icon}</div>
        <div style="font-size:1.1rem; font-weight:800; color:{color};">{value}</div>
        <div style="font-size:0.7rem; color:#6B7280;">{label}</div>
    </div>
    """.format(icon=icon, value=value, label=label, color=color), unsafe_allow_html=True)
