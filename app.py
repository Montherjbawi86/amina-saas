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

# ============ GUEST VIEW (Login/Signup) ============
if not user or not clinic:
    import time

    st.markdown("""
    <div style="background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
                border-radius: 16px; padding: 2rem 1.5rem; text-align: center;
                color: white; margin-bottom: 1.5rem;
                box-shadow: 0 8px 24px rgba(22,163,74,0.25);">
        <div style="font-size:3rem;">👶</div>
        <h1 style="color:white !important; margin:0.5rem 0 0 0; font-size:1.75rem;">أمينة SaaS</h1>
        <p style="opacity:0.95; margin-top:0.5rem;">نظام إدارة عيادات النساء والولادة</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔐 تسجيل الدخول", "🏥 تسجيل عيادة جديدة"])

    with tab_login:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.form("login_form"):
                email = st.text_input("البريد الإلكتروني", placeholder="doctor@clinic.com")
                password = st.text_input("كلمة المرور", type="password")
                submitted = st.form_submit_button("🚀 دخول", use_container_width=True, type="primary")
            if submitted:
                try:
                    from core.auth import login as auth_login
                    from core.tenant import get_clinic as tc_get_clinic
                    from core.session import set_user

                    u = auth_login(email, password)
                    c = tc_get_clinic(u["clinic_id"])
                    set_user(u, c)
                    st.success("✅ مرحباً {}".format(u["full_name"]))
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error("❌ {}".format(str(e)[:200]))

    with tab_signup:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.form("signup_form"):
                clinic_name = st.text_input("اسم العيادة *", placeholder="عيادة النور")
                phone = st.text_input("هاتف العيادة", placeholder="+964...")
                doctor_name = st.text_input("اسم الطبيبة *", placeholder="د. أمينة")
                email_s = st.text_input("البريد الإلكتروني *", placeholder="doctor@clinic.com")
                password_s = st.text_input("كلمة المرور * (6+ أحرف)", type="password", key="spw")
                password_s2 = st.text_input("تأكيد كلمة المرور *", type="password", key="spw2")
                plan = st.selectbox("الباقة", ["starter", "pro", "hospital"],
                    format_func=lambda x: {
                        "starter": "Starter - 50 حامل - $49/شهر",
                        "pro": "Pro - 200 حامل - $149/شهر",
                        "hospital": "Hospital - غير محدود - $499/شهر",
                    }[x])
                submitted_s = st.form_submit_button("✨ إنشاء الحساب", use_container_width=True, type="primary")

            if submitted_s:
                errors = []
                if not clinic_name: errors.append("اسم العيادة مطلوب")
                if not doctor_name: errors.append("اسم الطبيبة مطلوب")
                if not email_s or "@" not in email_s: errors.append("بريد إلكتروني غير صحيح")
                if len(password_s) < 6: errors.append("كلمة المرور قصيرة")
                if password_s != password_s2: errors.append("كلمتا المرور غير متطابقتين")

                if errors:
                    for e in errors: st.error(e)
                else:
                    try:
                        from core.auth import signup_clinic, AuthError
                        from core.session import set_user

                        clinic, user_new = signup_clinic(
                            clinic_name=clinic_name, doctor_name=doctor_name,
                            email=email_s, password=password_s,
                            phone=phone, plan=plan
                        )
                        set_user(user_new, clinic)
                        st.success("✅ تم إنشاء العيادة!")
                        st.balloons()
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error("خطأ: {}".format(str(e)[:200]))

    st.stop()

# Alert count disabled for performance (0 = no badge)
_critical_count = 0

# ============ NAVBAR + SIDEBAR ============
if st.session_state.get("nav_section") is None:
    st.session_state["nav_section"] = "dashboard"

_selected = render_sidebar(clinic, user, active=st.session_state.get("nav_section", "dashboard"))
if _selected == "__logout__":
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
