# -*- coding: utf-8 -*-
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("LANG", "en_US.UTF-8")
os.environ.setdefault("LC_ALL", "en_US.UTF-8")

import time
import streamlit as st

from core.session import (
    init_session, is_logged_in, get_current_user,
    get_current_clinic, set_user, logout
)
from core.auth import login, signup_clinic, AuthError
from core.tenant import get_clinic
from core.ui import inject_css, inject_sidebar_styles, modern_navbar, render_sidebar

import views.dashboard as view_dashboard
import views.patients as view_patients
import views.visits as view_visits
import views.appointments_view as view_appointments
import views.prescriptions_view as view_prescriptions
import views.vaccinations_view as view_vaccinations
import views.growth_view as view_growth
import views.users_view as view_users
import views.ai_view as view_ai
import views.analytics_view as view_analytics
import views.files_view as view_files

st.set_page_config(
    page_title="أمينة SaaS",
    page_icon="👶",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()
inject_sidebar_styles()
init_session()


# ============ PUBLIC PRESCRIPTION VIEW (no auth) ============
try:
    _rx_token = None
    if hasattr(st, 'query_params'):
        _rx_token = st.query_params.get('rx')
    if not _rx_token:
        _qp = st.query_params.get('rx')
        _rx_token = _qp[0] if isinstance(_qp, list) else _qp

    if _rx_token:
        from views.public_rx import render_public_rx
        render_public_rx()
        st.stop()
except Exception:
    pass

# ============ PUBLIC CERTIFICATE VIEW (no auth) ============
try:
    _cert_token = None
    if hasattr(st, 'query_params'):
        _cert_token = st.query_params.get('cert')
    if not _cert_token:
        _qp = st.query_params.get('cert')
        _cert_token = _qp[0] if isinstance(_qp, list) else _qp

    if _cert_token:
        from views.public_cert import render_public_cert
        render_public_cert()
        st.stop()
except Exception:
    pass

# ============ PATIENT PORTAL (PWA) ============
try:
    _pwa_mode = None
    _pwa_token = None
    _pwa_from_session = st.session_state.get("_pwa_token")

    try:
        if hasattr(st, "query_params"):
            _pwa_mode = st.query_params.get("pwa")
            _pwa_token = st.query_params.get("t")
    except Exception:
        pass

    if _pwa_mode or _pwa_token or _pwa_from_session:
        from views.patient_portal_view import render_patient_portal
        render_patient_portal()
        st.stop()
except Exception:
    pass

user = get_current_user()
clinic = get_current_clinic()

# ============ 2FA VERIFICATION GATE ============
# If user is logged in AND has 2FA enabled AND hasn't verified yet -> show gate
if user and clinic:
    try:
        from services.two_factor import is_2fa_enabled, verify_any_code
        _2fa_verified = st.session_state.get("_2fa_verified_user")
        if is_2fa_enabled(user["id"]) and _2fa_verified != user["id"]:
            # Show 2FA gate
            st.markdown("""
            <div style="max-width:480px;margin:3rem auto;text-align:center;">
                <div style="font-size:4rem;">🛡️</div>
                <h2 style="color:#0F172A;margin:0.5rem 0;">التحقق الثنائي</h2>
                <p style="color:#64748B;margin-bottom:1.5rem;">
                    أدخل الرمز من تطبيق المصادقة على هاتفك
                </p>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                with st.form("2fa_gate_form"):
                    _code = st.text_input(
                        "الرمز (6 أرقام) أو رمز احتياطي",
                        placeholder="123456",
                        max_chars=20,
                        key="gate_2fa_code"
                    )
                    _submitted = st.form_submit_button(
                        "🔓 تحقق", use_container_width=True, type="primary"
                    )

                if _submitted:
                    if not _code or not _code.strip():
                        st.error("⚠️ أدخل الرمز")
                    else:
                        is_valid, method = verify_any_code(user["id"], _code.strip())
                        if is_valid:
                            st.session_state["_2fa_verified_user"] = user["id"]
                            if method == "backup":
                                st.warning("⚠️ تم استخدام رمز احتياطي — بقي لديك {} رموز".format(
                                    __import__("services.two_factor", fromlist=["get_remaining_backup_codes"]).get_remaining_backup_codes(user["id"])
                                ))
                            st.success("✅ تم التحقق")
                            st.rerun()
                        else:
                            st.error("❌ الرمز غير صحيح")

                if st.button("🚪 تسجيل الخروج", use_container_width=True, key="gate_logout"):
                    from core.session import logout
                    st.session_state.pop("_2fa_verified_user", None)
                    logout()

            st.stop()
    except Exception as _e:
        # On any error, don't block login (fail-safe)
        pass

# ============ GUEST VIEW (Login/Signup) — Modern Design ============
if not user or not clinic:
    from views.auth_view import render_auth
    render_auth()
    st.stop()

# Alert count disabled for performance (0 = no badge)
_critical_count = 0

# ============ NAVBAR + SIDEBAR ============
if st.session_state.get("nav_section") is None:
    st.session_state["nav_section"] = "dashboard"

_selected = render_sidebar(clinic, user, active=st.session_state.get("nav_section", "dashboard"))
if _selected == "__logout__":
    st.session_state.pop("_2fa_verified_user", None)
    logout()

modern_navbar(user, clinic, alert_count=_critical_count)

# ============ FLOATING ACTION BUTTON ============
_fab_col1, _fab_col2 = st.columns([5, 1])
with _fab_col2:
    if st.button("➕ حامل جديدة", key="fab_new_patient", use_container_width=True, type="primary"):
        st.session_state["patient_view"] = "new"
        st.session_state["nav_section"] = "patients"
        st.session_state["selected_patient_id"] = None
        st.rerun()

st.write("")

# ============ MAIN CONTENT (based on sidebar nav) ============
_nav = st.session_state.get("nav_section", "dashboard")

# ============ DASHBOARD ============
if _nav == "dashboard":
    view_dashboard.render(clinic, user)

# ============ GLOBAL SEARCH ============
elif _nav == "search":
    import views.global_search_view as view_search
    view_search.render(clinic, user)

# ============ APPOINTMENTS ============
elif _nav == "appointments":
    view_appointments.render(clinic, user)

# ============ PATIENTS ============
elif _nav == "patients":
    view_patients.render(clinic, user)

# ============ MEDICAL RECORD ============
elif _nav == "medical":
    st.markdown("### 📋 السجل الطبي")

    pid = st.session_state.get("selected_patient_id")
    if not pid:
        st.info("👉 اختر حاملاً من قسم **👩 الحوامل** أولاً")
        st.caption("بعد اختيار الحامل، ستظهر هنا: الوصفات، التحصينات، نمو الجنين، الزيارات، الملفات")

        try:
            from services.patients import list_patients_cached as _list_pats
            _pats = _list_pats(clinic["id"])
            if _pats:
                with st.expander("🔍 اختيار سريع لحامل"):
                    _pmap = {p["id"]: "{} — {}".format(p["full_name"], p["phone"]) for p in _pats}
                    _selected = st.selectbox(
                        "الحامل", options=list(_pmap.keys()),
                        format_func=lambda x: _pmap[x],
                        key="medical_quick_select"
                    )
                    if st.button("✓ اختيار", key="medical_select_btn", type="primary"):
                        st.session_state["selected_patient_id"] = _selected
                        st.rerun()
        except Exception:
            pass
    else:
        try:
            from services.patients import get_patient_summary_cached as _get_pat
            _p = _get_pat(clinic["id"], pid)
            if _p:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.caption("الحامل المختارة: **{}** — {}".format(
                        _p["full_name"], _p.get("gestational_display", "")))
                with c2:
                    if st.button("🔄 تغيير الحامل", key="change_patient_medical"):
                        st.session_state["selected_patient_id"] = None
                        st.rerun()
        except Exception:
            pass

        med_presc, med_vacc, med_growth, med_visits, med_files = st.tabs([
            "💊 الوصفات",
            "💉 التحصينات",
            "📈 نمو الجنين",
            "🩺 الزيارات",
            "📎 الملفات"
        ])

        with med_presc:
            view_prescriptions.render(clinic, user)

        with med_vacc:
            view_vaccinations.render(clinic, user)

        with med_growth:
            view_growth.render(clinic, user)

        with med_visits:
            view_visits.render(clinic, user)

        with med_files:
            view_files.render(clinic, user)

# ============ AI ANALYSIS (Sidebar) ============
elif _nav == "ai":
    view_ai.render(clinic, user, key_prefix="unified")

# ============ EXCEL EXPORT ============
elif _nav == "export":
    import views.excel_export_view as view_excel
    view_excel.render(clinic, user)

# ============ PREGNANCY CERTIFICATE ============
elif _nav == "certificate":
    import views.certificate_view as view_cert
    view_cert.render(clinic, user)

# ============ LAB TESTS ============
elif _nav == "lab_tests":
    import views.lab_tests_view as view_lab
    view_lab.render(clinic, user)

# ============ ULTRASOUND GALLERY ============
elif _nav == "ultrasound":
    import views.ultrasound_view as view_us
    view_us.render(clinic, user)

# ============ VACCINATION SCHEDULE ============
elif _nav == "vaccination_schedule":
    import views.vaccination_schedule_view as view_vax
    view_vax.render(clinic, user)

# ============ NEWBORNS ============
elif _nav == "newborns":
    import views.newborns_view as view_nb
    view_nb.render(clinic, user)

# ============ REPORTS ============
elif _nav == "reports":
    import views.reports_view as view_reports
    view_reports.render(clinic, user)

# ============ AUDIT LOG ============
elif _nav == "audit_log":
    import views.audit_log_view as view_audit
    view_audit.render(clinic, user)

# ============ TWO-FACTOR AUTH ============
elif _nav == "two_factor":
    import views.two_factor_view as view_2fa
    view_2fa.render(clinic, user)

# ============ ADMIN ============
elif _nav == "admin":
    st.markdown("### ⚙️ الإدارة")

    adm_users, adm_analytics, adm_ai, adm_settings = st.tabs([
        "👥 المستخدمون",
        "📈 التقارير",
        "🤖 تحليل AI",
        "⚙️ الإعدادات"
    ])

    with adm_users:
        view_users.render(clinic, user)

    with adm_analytics:
        view_analytics.render(clinic, user)

    with adm_ai:
        view_ai.render(clinic, user, key_prefix="unified")

    with adm_settings:
        st.markdown("#### ⚙️ الإعدادات")
        st.caption("معلومات العيادة والإحصائيات")
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📋 معلومات العيادة")
            st.write("- **الاسم:** {}".format(clinic["name"]))
            st.write("- **البريد:** {}".format(clinic.get("email", "—")))
            st.write("- **الهاتف:** {}".format(clinic.get("phone") or "—"))
            st.write("- **الباقة:** {}".format(clinic["plan"].upper()))
            st.write("- **Slug:** {}".format(clinic.get("slug", "—")))

        with c2:
            st.markdown("##### 📊 الحدود والاستخدام")
            try:
                from core.tenant import get_clinic_stats_cached
                _stats = get_clinic_stats_cached(clinic["id"])
                st.write("- **الحوامل:** {} / {}".format(
                    _stats["current_patients"], _stats["max_patients"]))
                st.write("- **المستخدمون:** {}".format(_stats["current_users"]))
                st.write("- **الاستخدام:** {}%".format(_stats["usage_pct"]))
            except Exception:
                st.write("—")

        st.divider()
        st.info("🚧 إعدادات متقدمة قريباً: تغيير الباقة، الفواتير، الطباعة")
