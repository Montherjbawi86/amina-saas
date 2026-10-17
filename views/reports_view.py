# -*- coding: utf-8 -*-
"""
Reports Dashboard — Advanced analytics & reporting
لوحة التقارير المتقدمة
"""
from datetime import date, timedelta, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from services.reports import (
    get_date_presets, get_overview, get_monthly_trends,
    get_abnormal_labs, get_patients_report,
    get_ultrasound_report, get_certificates_report,
)
from services.analytics_pdf import generate_analytics_pdf


# ============================================
# HELPERS
# ============================================

def _date_range_selector(key_suffix=""):
    """Date range picker with presets"""
    presets = get_date_presets()

    c1, c2 = st.columns([1, 2])
    with c1:
        preset_key = st.selectbox(
            "الفترة",
            options=list(presets.keys()),
            format_func=lambda k: presets[k][0],
            index=2,  # default: month (30 days)
            key="date_preset_{}".format(key_suffix)
        )

    label, df, dt = presets[preset_key]

    if preset_key == "all":
        return None, None

    if preset_key == "today":
        return df, dt

    # Custom date inputs for flexibility
    with c2:
        c3, c4 = st.columns(2)
        with c3:
            date_from = st.date_input(
                "من",
                value=df,
                key="date_from_{}".format(key_suffix)
            )
        with c4:
            date_to = st.date_input(
                "إلى",
                value=dt,
                key="date_to_{}".format(key_suffix)
            )

    if date_from and date_to and date_from > date_to:
        st.error("⚠️ 'من' يجب أن يكون قبل 'إلى'")
        return None, None

    return date_from, date_to


# ============================================
# TAB 1: OVERVIEW
# ============================================

def _render_overview_tab(clinic, user, date_from, date_to):
    """Overview KPIs + trends"""

    overview = get_overview(clinic["id"], date_from, date_to)

    if "error" in overview:
        st.error("❌ {}".format(overview["error"]))
        return

    # Row 1: Main KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("👩", overview["total_patients"], "الحوامل النشطات")
    with c2:
        kpi_card_v2("🆕", overview["new_patients"], "جديدات في الفترة")
    with c3:
        kpi_card_v2("🩺", overview["total_visits"], "الزيارات")
    with c4:
        kpi_card_v2("💊", overview["total_prescriptions"], "الوصفات")

    st.write("")

    # Row 2: Advanced KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card_v2("🔬", overview["total_lab_tests"], "التحاليل")
    with c2:
        abnormal = overview["abnormal_lab_tests"]
        kpi_card_v2("⚠️", abnormal, "غير طبيعية")
    with c3:
        kpi_card_v2("📸", overview["total_ultrasound"], "صور سونار")
    with c4:
        kpi_card_v2("📄", overview["total_certificates"], "شهادات")
    with c5:
        kpi_card_v2("💉", overview["total_vaccinations"], "تحصينات")

    st.divider()

    # Alerts summary if abnormalities exist
    if abnormal > 0:
        total_labs = overview["total_lab_tests"]
        pct = round(100.0 * abnormal / total_labs, 1) if total_labs else 0
        st.markdown("""
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;
                    padding:0.9rem 1.2rem;margin-bottom:1rem;display:flex;
                    align-items:center;gap:0.75rem;">
            <div style="font-size:1.5rem;">⚠️</div>
            <div style="flex:1;">
                <div style="font-weight:700;color:#B91C1C;font-size:0.95rem;">
                    تنبيه: {} تحليل غير طبيعي
                </div>
                <div style="color:#7F1D1D;font-size:0.85rem;margin-top:0.15rem;">
                    {}% من التحاليل في الفترة تحتاج مراجعة
                </div>
            </div>
        </div>
        """.format(abnormal, pct), unsafe_allow_html=True)

    # Trends section
    section_header_v2("📈", "الاتجاهات الشهرية")

    months_back = 6
    if date_from and date_to:
        delta = (date_to - date_from).days
        months_back = max(1, min(12, delta // 30 + 1))

    trends = get_monthly_trends(clinic["id"], months_back)

    if not trends or all(t["patients"] == 0 and t["visits"] == 0 for t in trends):
        empty_state(
            "📊",
            "لا توجد بيانات في الفترة",
            "جرب تغيير الفترة أو إضافة بيانات جديدة"
        )
        return

    df = pd.DataFrame(trends)

    # Chart 1: Visits + Patients (line chart)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### 🩺 الزيارات والحوامل")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["label"], y=df["visits"],
            mode="lines+markers",
            name="الزيارات",
            line=dict(color="#16A34A", width=3),
            marker=dict(size=10),
        ))
        fig.add_trace(go.Scatter(
            x=df["label"], y=df["patients"],
            mode="lines+markers",
            name="حوامل جديدة",
            line=dict(color="#0EA5A0", width=3),
            marker=dict(size=10),
        ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### 🔬 التحاليل والسونار")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["label"], y=df["labs"],
            name="تحاليل",
            marker_color="#F59E0B",
        ))
        fig.add_trace(go.Bar(
            x=df["label"], y=df["ultrasounds"],
            name="سونار",
            marker_color="#8B5CF6",
        ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=20, b=10),
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Risk distribution
    risk = overview.get("risk_distribution", {})
    if sum(risk.values()) > 0:
        st.divider()
        c1, c2 = st.columns([1, 2])

        with c1:
            st.markdown("##### 🎯 توزيع المخاطر")
            labels = {"low": "🟢 منخفض", "medium": "🟡 متوسط", "high": "🔴 عالي"}
            data = [{"المستوى": labels.get(k, k), "العدد": v}
                    for k, v in risk.items() if v > 0]
            if data:
                dff = pd.DataFrame(data)
                colors = {
                    "🟢 منخفض": "#10B981",
                    "🟡 متوسط": "#F59E0B",
                    "🔴 عالي": "#EF4444",
                }
                fig = px.pie(
                    dff, values="العدد", names="المستوى",
                    color="المستوى", color_discrete_map=colors, hole=0.5
                )
                fig.update_layout(
                    height=280, margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True,
                )
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("##### 📊 ملخص الفترة")
            summary_rows = [
                ("👩", "الحوامل النشطات", overview["total_patients"]),
                ("🆕", "جديدات في الفترة", overview["new_patients"]),
                ("🩺", "الزيارات", overview["total_visits"]),
                ("💊", "الوصفات", overview["total_prescriptions"]),
                ("🔬", "التحاليل", overview["total_lab_tests"]),
                ("⚠️", "تحاليل غير طبيعية", overview["abnormal_lab_tests"]),
                ("📸", "صور سونار", overview["total_ultrasound"]),
                ("📄", "شهادات", overview["total_certificates"]),
            ]
            for icon, label, val in summary_rows:
                st.markdown("""
                <div style="display:flex;justify-content:space-between;
                            padding:0.5rem 0.75rem;border-bottom:1px solid #F1F5F9;">
                    <span style="color:#64748B;font-size:0.9rem;">{icon} {label}</span>
                    <span style="font-weight:700;color:#0F172A;">{val}</span>
                </div>
                """.format(icon=icon, label=label, val=val),
                unsafe_allow_html=True)


# ============================================
# TAB 2: ABNORMAL LABS
# ============================================

def _render_abnormal_labs_tab(clinic, user, date_from, date_to):
    """Abnormal lab tests report"""

    labs = get_abnormal_labs(clinic["id"], date_from, date_to, limit=200)

    if not labs:
        empty_state(
            "✅",
            "لا توجد تحاليل غير طبيعية",
            "كل التحاليل في هذه الفترة ضمن المعدل الطبيعي"
        )
        return

    # Summary
    total = len(labs)
    severity_counts = {}
    for t in labs:
        sev = t.get("severity", "moderate")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("⚠️", total, "إجمالي غير طبيعية")
    with c2:
        kpi_card_v2("🔴", severity_counts.get("severe", 0), "شديد")
    with c3:
        kpi_card_v2("🟠", severity_counts.get("moderate", 0), "متوسط")
    with c4:
        kpi_card_v2("🟡", severity_counts.get("mild", 0), "خفيف")

    st.divider()
    section_header_v2("📋", "التفاصيل", badge="{} تحليل".format(total))

    # Build dataframe
    rows = []
    for t in labs:
        rows.append({
            "التاريخ": str(t.get("test_date", ""))[:10],
            "الحامل": t.get("_patient_name", "—"),
            "الهاتف": t.get("_patient_phone", ""),
            "التحليل": t.get("test_name", "—"),
            "الخطورة": {
                "severe": "🔴 شديد",
                "moderate": "🟠 متوسط",
                "mild": "🟡 خفيف",
            }.get(t.get("severity", ""), "—"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "التاريخ": st.column_config.TextColumn(width="small"),
            "الحامل": st.column_config.TextColumn(width="medium"),
            "الهاتف": st.column_config.TextColumn(width="small"),
            "التحليل": st.column_config.TextColumn(width="medium"),
            "الخطورة": st.column_config.TextColumn(width="small"),
        }
    )

    # Export CSV
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 تصدير CSV",
        csv,
        "abnormal_labs_{}.csv".format(date.today().strftime("%Y%m%d")),
        "text/csv",
        key="labs_csv_export",
    )


# ============================================
# TAB 3: PATIENTS
# ============================================

def _render_patients_tab(clinic, user, date_from, date_to):
    """Detailed patients report"""

    # Risk filter
    c1, c2 = st.columns([1, 3])
    with c1:
        risk = st.selectbox(
            "مستوى الخطر",
            options=["all", "low", "medium", "high"],
            format_func=lambda x: {
                "all": "🎯 الكل",
                "low": "🟢 منخفض",
                "medium": "🟡 متوسط",
                "high": "🔴 عالي",
            }[x],
            key="patients_risk_filter"
        )

    risk_filter = None if risk == "all" else risk

    patients = get_patients_report(
        clinic["id"], risk_filter, date_from, date_to
    )

    if not patients:
        empty_state(
            "👩",
            "لا توجد حوامل",
            "جرب تغيير الفلاتر أو الفترة"
        )
        return

    # Summary
    total = len(patients)
    total_visits = sum(p["visits"] for p in patients)
    total_labs = sum(p["labs"] for p in patients)
    total_abnormal = sum(p["abnormal_labs"] for p in patients)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card_v2("👩", total, "عدد الحوامل")
    with c2:
        kpi_card_v2("🩺", total_visits, "إجمالي الزيارات")
    with c3:
        kpi_card_v2("🔬", total_labs, "إجمالي التحاليل")
    with c4:
        kpi_card_v2("⚠️", total_abnormal, "تحاليل غير طبيعية")

    st.divider()
    section_header_v2("📋", "التفاصيل", badge="{} حامل".format(total))

    # Build table
    rows = []
    for p in patients:
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
            p["risk_level"], "⚪"
        )
        rows.append({
            "الاسم": p["name"],
            "الهاتف": p["phone"],
            "الخطر": risk_icon,
            "الزيارات": p["visits"],
            "التحاليل": p["labs"],
            "غير طبيعية": p["abnormal_labs"],
            "G/P": "{}/{}".format(p.get("gravida") or 0, p.get("para") or 0),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 تصدير CSV",
        csv,
        "patients_report_{}.csv".format(date.today().strftime("%Y%m%d")),
        "text/csv",
        key="patients_csv_export",
    )


# ============================================
# TAB 4: ULTRASOUND + CERTIFICATES
# ============================================

def _render_media_tab(clinic, user, date_from, date_to):
    """Ultrasound + certificates report"""

    section_header_v2("📸", "تقرير صور السونار")

    us = get_ultrasound_report(clinic["id"], date_from, date_to, limit=100)

    if not us:
        empty_state(
            "📸",
            "لا توجد صور سونار",
            "لم تُرفع صور في هذه الفترة"
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            kpi_card_v2("📸", len(us), "عدد الصور")
        with c2:
            patients_count = len(set(r.get("patient_id") for r in us))
            kpi_card_v2("👩", patients_count, "عدد الحوامل")

        st.write("")

        # Grid of thumbnails
        cols = st.columns(4)
        for idx, img in enumerate(us[:12]):
            col = cols[idx % 4]
            with col:
                try:
                    st.image(img.get("public_url", ""), use_container_width=True)
                except Exception:
                    st.markdown("🖼️")
                caption = img.get("caption") or "سونار"
                st.caption("{} — {}".format(
                    caption[:20],
                    str(img.get("image_date", ""))[:10]
                ))

        if len(us) > 12:
            st.caption("... و {} صورة أخرى".format(len(us) - 12))

    st.divider()

    section_header_v2("📄", "تقرير الشهادات")

    certs = get_certificates_report(clinic["id"], date_from, date_to, limit=100)

    if not certs:
        empty_state(
            "📄",
            "لا توجد شهادات",
            "لم تُصدر شهادات في هذه الفترة"
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            kpi_card_v2("📄", len(certs), "عدد الشهادات")
        with c2:
            patients_count = len(set(r.get("patient_id") for r in certs))
            kpi_card_v2("👩", patients_count, "عدد الحوامل")

        st.write("")

        rows = []
        for c in certs:
            rows.append({
                "التاريخ": str(c.get("issued_at", ""))[:10],
                "الحامل": c.get("_patient_name", "—"),
                "الحالة": "✅ نشطة" if c.get("is_active") else "❌ ملغاة",
                "المعرف": str(c.get("id", ""))[:8].upper(),
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main reports view"""
    page_header_v2(
        title="التقارير والإحصائيات",
        subtitle="تحليلات شاملة لأداء العيادة",
        icon="📊",
        badge=clinic.get("plan", "").upper()
    )

    # Date range selector
    st.markdown("#### 📅 الفترة الزمنية")
    date_from, date_to = _date_range_selector("main")

    if date_from:
        st.caption("📊 يتم عرض بيانات من **{}** إلى **{}**".format(date_from, date_to))
    else:
        st.caption("📊 يتم عرض **كل البيانات**")

    # PDF export row
    c_pdf1, c_pdf2, c_pdf3 = st.columns([5, 1, 1])
    with c_pdf2:
        if st.button("📄 PDF", use_container_width=True, type="primary",
                     key="reports_pdf_btn", help="تصدير التقرير كـ PDF"):
            with st.spinner("⏳ جاري توليد PDF..."):
                try:
                    _overview = get_overview(clinic["id"], date_from, date_to)
                    _trends = get_monthly_trends(clinic["id"], 6)
                    _labs = get_abnormal_labs(clinic["id"], date_from, date_to, limit=15)
                    _patients = get_patients_report(clinic["id"], None, date_from, date_to)

                    _pdf = generate_analytics_pdf(
                        clinic=clinic,
                        user=user,
                        overview=_overview,
                        trends=_trends,
                        abnormal_labs=_labs,
                        patients_report=_patients,
                        date_from=date_from,
                        date_to=date_to,
                    )
                    st.session_state["_analytics_pdf"] = _pdf
                    st.session_state["_analytics_pdf_name"] = "analytics_{}.pdf".format(
                        date.today().strftime("%Y%m%d")
                    )
                    st.success("✅ PDF جاهز!")
                except Exception as e:
                    st.error("❌ {}".format(str(e)[:200]))

    with c_pdf3:
        if st.button("🖨️ طباعة", use_container_width=True,
                     key="reports_print_btn", help="طباعة الصفحة"):
            st.info("💡 اضغط Cmd+P / Ctrl+P")

    # Download PDF if ready
    if st.session_state.get("_analytics_pdf"):
        _pdf = st.session_state["_analytics_pdf"]
        _fname = st.session_state.get("_analytics_pdf_name", "analytics.pdf")
        _size = len(_pdf) / 1024.0

        c_dl1, c_dl2, c_dl3 = st.columns([5, 1, 1])
        with c_dl1:
            st.success("📄 **PDF جاهز** — {:.1f} KB".format(_size))
        with c_dl2:
            st.download_button(
                "⬇️ تحميل",
                data=_pdf,
                file_name=_fname,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="reports_pdf_download"
            )
        with c_dl3:
            if st.button("🗑️", key="reports_pdf_clear", use_container_width=True):
                st.session_state.pop("_analytics_pdf", None)
                st.session_state.pop("_analytics_pdf_name", None)
                st.rerun()

    st.divider()

    # Tabs
    tab_overview, tab_labs, tab_patients, tab_media = st.tabs([
        "📈 نظرة عامة",
        "⚠️ تحاليل غير طبيعية",
        "👩 تقرير الحوامل",
        "📸 صور + شهادات",
    ])

    with tab_overview:
        _render_overview_tab(clinic, user, date_from, date_to)

    with tab_labs:
        _render_abnormal_labs_tab(clinic, user, date_from, date_to)

    with tab_patients:
        _render_patients_tab(clinic, user, date_from, date_to)

    with tab_media:
        _render_media_tab(clinic, user, date_from, date_to)
