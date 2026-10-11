# -*- coding: utf-8 -*-
import streamlit as st
from core.tenant import get_clinic_stats_cached
from core.ui import kpi_card
from core.cache import show_cache_status


def render(clinic, user):
    """Render dashboard tab"""
    show_cache_status("dash_view")
    try:
        stats = get_clinic_stats_cached(clinic["id"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("👩", "{} / {}".format(
                stats["current_patients"], stats["max_patients"]),
                "الحوامل النشطات", "#0EA5A0")
        with c2:
            kpi_card("👥", str(stats["current_users"]), "المستخدمون", "#22C55E")
        with c3:
            kpi_card("💎", stats["plan"].upper(), "الباقة", "#10B981")
        with c4:
            kpi_card("📈", "{}%".format(stats["usage_pct"]), "الاستخدام", "#F59E0B")

        st.write("")
        st.progress(min(stats["usage_pct"] / 100.0, 1.0))
        st.caption("{:.1f}% من السعة".format(stats["usage_pct"]))

        if stats["usage_pct"] > 80:
            st.warning("⚠️ اقتربت من حد الباقة. فكر بالترقية.")

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
                st.info("📭 لا توجد مواعيد اليوم")
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
