# -*- coding: utf-8 -*-
import streamlit as st
from core.tenant import get_clinic_stats_cached
from core.ui import (
    kpi_card_v2, page_header_v2, empty_state,
    info_card, section_header_v2
)
from core.cache import show_cache_status
from services.dashboard_alerts import get_all_alerts, count_alerts


def render(clinic, user):
    """Render dashboard tab"""
    # Modern page header
    page_header_v2(
        title="لوحة التحكم",
        subtitle="نظرة عامة على العيادة والمتابعة اليومية",
        icon="📊",
        badge=clinic.get("plan", "").upper()
    )

    # Print controls

    show_cache_status("dash_view")
    try:
        stats = get_clinic_stats_cached(clinic["id"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card_v2("👩", "{} / {}".format(
                stats["current_patients"], stats["max_patients"]),
                "الحوامل النشطات")
        with c2:
            kpi_card_v2("👥", str(stats["current_users"]), "المستخدمون")
        with c3:
            kpi_card_v2("💎", stats["plan"].upper(), "الباقة")
        with c4:
            kpi_card_v2("📈", "{}%".format(stats["usage_pct"]), "الاستخدام")

        st.write("")
        st.progress(min(stats["usage_pct"] / 100.0, 1.0))
        st.caption("{:.1f}% من السعة".format(stats["usage_pct"]))

        if stats["usage_pct"] > 80:
            st.warning("⚠️ اقتربت من حد الباقة. فكر بالترقية.")

        # ============ SMART ALERTS ============
        try:
            _alerts = get_all_alerts(clinic["id"])
            _counts = count_alerts(_alerts)
            _total_alerts = _counts["total"]

            if _total_alerts > 0:
                st.divider()
                st.subheader("🚨 يحتاج انتباهك الآن")
                st.caption("{} تنبيه".format(_total_alerts))

                # Row 1: Overdue vaccinations + Abnormal labs
                c1, c2 = st.columns(2)

                with c1:
                    _ov = _alerts["overdue_vaccinations"]
                    if _ov:
                        st.markdown("##### 💉 تطعيمات متأخرة")
                        for v in _ov[:3]:
                            days = v.get("_days_overdue", 0)
                            st.markdown("""
                            <div style="background:#FEF2F2;border:1px solid #FECACA;
                                        border-radius:10px;padding:0.6rem 0.85rem;
                                        margin-bottom:0.35rem;">
                                <div style="font-weight:600;color:#991B1B;font-size:0.88rem;">
                                    💉 {vaccine}
                                </div>
                                <div style="color:#7F1D1D;font-size:0.78rem;margin-top:0.2rem;">
                                    👩 {name} · متأخر {days} يوم
                                </div>
                            </div>
                            """.format(
                                vaccine=v.get("vaccine_name", "—")[:35],
                                name=v.get("_patient_name", "—"),
                                days=days,
                            ), unsafe_allow_html=True)

                        if len(_ov) > 3:
                            st.caption("... و{} أخرى".format(len(_ov) - 3))

                with c2:
                    _labs = _alerts["abnormal_labs"]
                    if _labs:
                        st.markdown("##### ⚠️ تحاليل غير طبيعية")
                        for t in _labs[:3]:
                            sev = t.get("severity", "moderate")
                            color_map = {
                                "severe": ("#991B1B", "#FEE2E2", "#FECACA"),
                                "moderate": ("#9A3412", "#FFF7ED", "#FED7AA"),
                                "mild": ("#854D0E", "#FEFCE8", "#FEF08A"),
                            }
                            fg, bg, border = color_map.get(sev, ("#9A3412", "#FFF7ED", "#FED7AA"))
                            st.markdown("""
                            <div style="background:{bg};border:1px solid {border};
                                        border-radius:10px;padding:0.6rem 0.85rem;
                                        margin-bottom:0.35rem;">
                                <div style="font-weight:600;color:{fg};font-size:0.88rem;">
                                    🔬 {test}
                                </div>
                                <div style="color:{fg};font-size:0.78rem;margin-top:0.2rem;opacity:0.85;">
                                    👩 {name} · {days} يوم
                                </div>
                            </div>
                            """.format(
                                bg=bg, border=border, fg=fg,
                                test=t.get("test_name", "—")[:35],
                                name=t.get("_patient_name", "—"),
                                days=t.get("_days_ago", "?"),
                            ), unsafe_allow_html=True)

                        if len(_labs) > 3:
                            st.caption("... و{} أخرى".format(len(_labs) - 3))

                # Row 2: High-risk + urgent appointments
                c3, c4 = st.columns(2)

                with c3:
                    _hr = _alerts["high_risk_no_visit"]
                    if _hr:
                        st.markdown("##### 🚨 مخاطر عالية — بدون زيارة")
                        for p in _hr[:3]:
                            st.markdown("""
                            <div style="background:#FEF2F2;border:1px solid #FECACA;
                                        border-radius:10px;padding:0.6rem 0.85rem;
                                        margin-bottom:0.35rem;">
                                <div style="font-weight:600;color:#991B1B;font-size:0.88rem;">
                                    👩 {name}
                                </div>
                                <div style="color:#7F1D1D;font-size:0.78rem;margin-top:0.2rem;">
                                    📞 {phone}
                                </div>
                            </div>
                            """.format(
                                name=p.get("name", "—"),
                                phone=p.get("phone", "—"),
                            ), unsafe_allow_html=True)

                        if len(_hr) > 3:
                            st.caption("... و{} أخرى".format(len(_hr) - 3))

                with c4:
                    _appts = _alerts["urgent_appointments"]
                    if _appts:
                        st.markdown("##### 📅 مواعيد عاجلة (اليوم/غداً)")
                        for a in _appts[:3]:
                            try:
                                from datetime import datetime as _dt
                                dt_obj = _dt.fromisoformat(a["scheduled_at"].replace("Z", ""))
                                time_str = dt_obj.strftime("%m-%d %H:%M")
                            except Exception:
                                time_str = "—"

                            st.markdown("""
                            <div style="background:#EFF6FF;border:1px solid #BFDBFE;
                                        border-radius:10px;padding:0.6rem 0.85rem;
                                        margin-bottom:0.35rem;">
                                <div style="font-weight:600;color:#1E40AF;font-size:0.88rem;">
                                    📅 {time}
                                </div>
                                <div style="color:#1E3A8A;font-size:0.78rem;margin-top:0.2rem;">
                                    👩 {name}
                                </div>
                            </div>
                            """.format(
                                time=time_str,
                                name=a.get("_patient_name", "—"),
                            ), unsafe_allow_html=True)

                        if len(_appts) > 3:
                            st.caption("... و{} أخرى".format(len(_appts) - 3))

                if _total_alerts > 8:
                    st.info("👉 اذهب إلى **📊 التقارير** لرؤية كل التنبيهات")
        except Exception as _e:
            print("[dashboard] alerts error: {}".format(_e))

        # Print footer

        # ============ TODAY'S APPOINTMENTS ============
        st.divider()
        st.subheader("📅 مواعيد اليوم")

        try:
            from services.appointments import (
                today_appointments, STATUS_LABELS, get_status_color,
                get_status_icon, get_type_icon,
            )
            from services.patients import list_patients_cached

            today_appts = today_appointments(clinic["id"])

            if not today_appts:
                empty_state(
                    "📅",
                    "لا توجد مواعيد اليوم",
                    "عندما تحجز مواعيد للحوامل، ستظهر هنا تلقائياً"
                )
            else:
                st.markdown("**العدد: {}**".format(len(today_appts)))
                patients_map = {p["id"]: p for p in list_patients_cached(clinic["id"])}

                for a in today_appts[:6]:
                    p = patients_map.get(a["patient_id"], {})
                    name = p.get("full_name", "—")
                    status = a.get("status", "scheduled")
                    s_icon = get_status_icon(status)
                    s_label = STATUS_LABELS.get(status, status)
                    s_color = get_status_color(status)

                    try:
                        from datetime import datetime as _dt
                        t_str = _dt.fromisoformat(a["scheduled_at"].replace("Z", "")).strftime("%H:%M")
                    except Exception:
                        t_str = "—"

                    t_icon = get_type_icon(a.get("type", "routine"))

                    html = (
                        '<div style="background:white; border-radius:10px; padding:0.6rem 0.9rem; '
                        'margin-bottom:0.4rem; border-right:4px solid ' + s_color + '; '
                        'display:flex; align-items:center; gap:0.75rem; box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
                        '<div style="font-weight:800; color:' + s_color + '; font-size:1.1rem; min-width:55px;">' + t_str + '</div>'
                        '<div style="flex:1;">'
                        '<div style="font-weight:600; color:#1F2937; font-size:0.9rem;">' + t_icon + ' ' + name + '</div>'
                        '</div>'
                        '<div style="background:' + s_color + '; color:white; padding:0.2rem 0.6rem; '
                        'border-radius:999px; font-size:0.7rem; font-weight:700;">'
                        + s_icon + ' ' + s_label +
                        '</div>'
                        '</div>'
                    )
                    st.markdown(html, unsafe_allow_html=True)

                if len(today_appts) > 6:
                    st.caption("عرض 6 من {}".format(len(today_appts)))
        except Exception as e:
            st.warning("لا يمكن تحميل المواعيد: {}".format(e))

        st.divider()

        # ============ ALERTS SECTION ============
        st.subheader("🔔 تنبيهات طبية")

        try:
            from services.patients import list_patients_cached
            from services.visits import list_visits_cached
            from views.alerts_view import render_clinic_alerts_dashboard

            all_patients = list_patients_cached(clinic["id"])

            visits_by_patient = {}
            for p in all_patients[:30]:
                try:
                    visits_by_patient[p["id"]] = list_visits_cached(clinic["id"], p["id"], limit=10)
                except Exception:
                    visits_by_patient[p["id"]] = []

            render_clinic_alerts_dashboard(clinic, all_patients, visits_by_patient, limit=5)
        except Exception as e:
            st.warning("لا يمكن تحميل التنبيهات: {}".format(e))

        st.divider()
        st.subheader("🚀 البدء السريع")
        st.info("👉 استخدم التبويبات أعلاه للتنقل: **👩 الحوامل** · **🩺 الزيارات** · **🤖 تحليل AI**")

        # ============ QUICK ACTIONS ============
        st.divider()
        st.subheader("⚡ إجراءات سريعة")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("➕ حامل جديدة", use_container_width=True, type="primary", key="dash_add_patient"):
                st.session_state["patient_view"] = "new"
                st.session_state["nav_section"] = "patients"
                st.session_state["selected_patient_id"] = None
                st.rerun()
        with c2:
            if st.button("👩 قائمة الحوامل", use_container_width=True, key="dash_patients"):
                st.session_state["nav_section"] = "patients"
                st.rerun()
        with c3:
            if st.button("📅 المواعيد", use_container_width=True, key="dash_appts"):
                st.session_state["nav_section"] = "appointments"
                st.rerun()
        with c4:
            if st.button("📈 التقارير", use_container_width=True, key="dash_reports"):
                st.session_state["nav_section"] = "admin"
                st.rerun()

    except Exception as e:
        st.error("فشل تحميل الإحصائيات: {}".format(e))
