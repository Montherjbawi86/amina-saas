# -*- coding: utf-8 -*-
"""Patient PWA portal"""
from datetime import datetime
import time
import streamlit as st

from services.patient_portal import (
    verify_otp, get_patient_from_session, logout,
    get_patient_appointments, get_patient_prescriptions,
    get_patient_vaccinations, get_patient_visits, get_patient_growth,
    get_account_by_phone,
    PortalError,
)


def render_patient_portal():
    """Main PWA entry — URL-first for reliability"""

    # ============ GET TOKEN (URL first) ============
    token = None

    # 1. Try URL first
    try:
        params = st.experimental_get_query_params()
        url_token = params.get("t", [None])
        if url_token and url_token[0]:
            token = url_token[0]
    except Exception:
        pass

    # 2. Fallback to new API
    if not token:
        try:
            if hasattr(st, "query_params"):
                token = st.query_params.get("t")
        except Exception:
            pass

    # 3. Fallback to session
    if not token:
        token = st.session_state.get("_pwa_token")

    # ============ VERIFY SESSION ============
    patient = None
    clinic = None
    if token:
        try:
            patient, clinic = get_patient_from_session(token)
        except Exception:
            pass

    # ============ ROUTE ============
    if patient:
        # Save for next rerun
        st.session_state["_pwa_token"] = token
        _render_dashboard(patient, clinic, token)
    else:
        # Invalid or no token — show login
        _render_login()



def _render_login():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%); }
    .main .block-container { max-width: 420px; padding-top: 3rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding: 2rem 0;">
        <div style="font-size:4rem;">👶</div>
        <h1 style="color:#16A34A; margin:0.5rem 0 0 0; font-size:1.75rem;">أمينة</h1>
        <p style="color:#64748B; margin:0.5rem 0;">بوابة الحامل</p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.get("portal_step", "phone")

    if step == "phone":
        st.markdown("### 📞 أدخلي رقم هاتفك")
        st.caption("نفس الرقم المسجل في العيادة")

        with st.form("phone_form"):
            phone = st.text_input("رقم الهاتف", placeholder="مثال: 00491749349733", label_visibility="collapsed")
            submitted = st.form_submit_button("📱 متابعة", use_container_width=True, type="primary")

        if submitted:
            try:
                from services.patient_portal import normalize_phone, get_account_by_phone
                from core.db import db

                _norm = normalize_phone(phone)

                # Try to find account
                account = get_account_by_phone(phone)

                # If not found, try to find patient with this phone and create account
                if not account and _norm:
                    # Search patients by normalized phone
                    patients = db().table("patients").select(
                        "id,phone,clinic_id,full_name"
                    ).execute().data

                    matched = None
                    for p in patients:
                        if normalize_phone(p.get("phone")) == _norm:
                            matched = p
                            break

                    if matched:
                        # Auto-create account
                        from services.patient_portal import get_or_create_account
                        try:
                            account = get_or_create_account(
                                clinic_id=matched["clinic_id"],
                                patient_id=matched["id"],
                                phone=matched["phone"]
                            )
                            st.info("✅ تم العثور على حسابك — {} ".format(matched["full_name"]))
                        except Exception as _ce:
                            st.error("خطأ في إنشاء الحساب: {}".format(str(_ce)[:100]))
                            account = None

                if not account:
                    st.error("❌ رقم الهاتف غير مسجل")
                    st.info("👉 تأكدي من الرقم كما سجلته العيادة")
                elif not account.get("otp_code"):
                    st.warning("⚠️ لا يوجد رمز نشط")
                    st.info("👉 اطلبي من العيادة إرسال رمز التحقق")
                else:
                    st.session_state["portal_phone"] = account["phone"]
                    st.session_state["portal_step"] = "otp"
                    st.success("✅ أدخلي الرمز الذي وصلك على الواتساب")
                    time.sleep(0.5)
                    st.rerun()
            except Exception as e:
                st.error("خطأ: {}".format(str(e)[:150]))

    elif step == "otp":
        phone = st.session_state.get("portal_phone", "")

        st.markdown("""
        <div style="background:#F0FDF4; border:2px solid #16A34A; border-radius:12px;
                    padding:1.25rem; text-align:center; margin:1rem 0;">
            <div style="font-size:3rem;">📱</div>
            <div style="font-weight:700; color:#15803D; font-size:1.1rem; margin-top:0.5rem;">
                وصلك رمز التحقق
            </div>
            <div style="color:#64748B; font-size:0.85rem; margin-top:0.5rem;">
                على الواتساب: <b>{}</b>
            </div>
        </div>
        """.format(phone), unsafe_allow_html=True)

        with st.form("otp_form"):
            code = st.text_input("🔐 أدخلي الرمز", max_chars=6, placeholder="000000")
            submitted = st.form_submit_button("✅ دخول", use_container_width=True, type="primary")

        if submitted:
            try:
                token, account = verify_otp(phone, code)

                # Save in session
                st.session_state["_pwa_token"] = token

                # Force URL update — this triggers reload in Streamlit 1.28
                try:
                    st.experimental_set_query_params(pwa="1", t=token)
                except Exception:
                    pass

                st.success("✅ مرحباً! جاري التحميل...")
                st.balloons()

                # Delay then rerun
                import time as _t
                _t.sleep(0.5)
                st.rerun()

            except PortalError as e:
                st.error("❌ {}".format(str(e)))
            except Exception as e:
                st.error("خطأ: {}".format(str(e)[:100]))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ تغيير الرقم", use_container_width=True):
                st.session_state["portal_step"] = "phone"
                st.rerun()
        with c2:
            if st.button("📱 لم يصلني", use_container_width=True):
                st.info("👉 اطلبي من العيادة إرسال رمز جديد")



def _render_dashboard(patient, clinic, token):
    st.markdown("""
    <style>
    .stApp { background: #F8FAFC; }
    .main .block-container { max-width: 480px; padding: 1rem; }
    [data-testid="stSidebar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

    weeks = 0
    days = 0
    try:
        from services.patients import calculate_gestational_age
        weeks, days = calculate_gestational_age(patient.get("lmp"))
    except Exception:
        pass

    st.markdown("""
    <div style="background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
                border-radius: 16px; padding: 1.5rem; color: white; margin-bottom: 1rem;">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div>
                <div style="font-size:0.75rem; opacity:0.9;">مرحباً</div>
                <div style="font-weight:800; font-size:1.1rem; margin-top:0.2rem;">{name}</div>
                <div style="font-size:0.75rem; opacity:0.9; margin-top:0.2rem;">{clinic}</div>
            </div>
            <div style="font-size:2.5rem;">👶</div>
        </div>
    </div>
    """.format(name=patient.get("full_name", ""), clinic=clinic.get("name", "")), unsafe_allow_html=True)

    if weeks:
        st.markdown("""
        <div style="background:white; border-radius:12px; padding:1.25rem; text-align:center;
                    border:1px solid #E2E8F0; margin-bottom:1rem;">
            <div style="font-size:0.8rem; color:#64748B;">عمر الحمل</div>
            <div style="font-size:2rem; font-weight:800; color:#16A34A; margin:0.25rem 0;">
                {weeks} أسبوع + {days} يوم
            </div>
            <div style="font-size:0.8rem; color:#64748B;">EDD: {edd}</div>
        </div>
        """.format(weeks=weeks, days=days, edd=patient.get("edd") or "—"), unsafe_allow_html=True)

    appointments = get_patient_appointments(clinic["id"], patient["id"], days=60)
    st.markdown("### 📅 مواعيدك القادمة")
    if not appointments:
        st.info("لا توجد مواعيد قادمة")
    else:
        for a in appointments[:3]:
            try:
                dt = datetime.fromisoformat(a["scheduled_at"].replace("Z", ""))
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = "—"
            st.markdown("""
            <div style="background:white; border-radius:10px; padding:0.85rem;
                        margin-bottom:0.4rem; border-right:4px solid #16A34A;">
                <div style="font-weight:700; color:#0F172A;">📅 {date}</div>
                <div style="color:#64748B; font-size:0.8rem;">{type}</div>
            </div>
            """.format(date=date_str, type=a.get("type", "متابعة")), unsafe_allow_html=True)

    prescriptions = get_patient_prescriptions(clinic["id"], patient["id"], limit=5)
    if prescriptions:
        st.markdown("### 💊 وصفاتك")
        for rx in prescriptions[:3]:
            with st.expander("💊 وصفة — {}".format((rx.get("issued_at") or "")[:10])):
                st.write("**التشخيص:** {}".format(rx.get("diagnosis") or "—"))
                for i, med in enumerate(rx.get("medications", []), 1):
                    st.write("{}. **{}** — {}".format(i, med.get("name", ""), med.get("dose", "")))

    vaccinations = get_patient_vaccinations(clinic["id"], patient["id"])
    pending = [v for v in vaccinations if v.get("status") == "pending"]
    if pending:
        st.markdown("### 💉 تحصينات قادمة")
        for v in pending[:3]:
            st.markdown("""
            <div style="background:white; border-radius:10px; padding:0.85rem;
                        margin-bottom:0.4rem; border-right:4px solid #F59E0B;">
                <div style="font-weight:700; color:#0F172A;">💉 {name}</div>
                <div style="color:#64748B; font-size:0.85rem;">📅 {date}</div>
            </div>
            """.format(name=v.get("vaccine_name", ""), date=(v.get("scheduled_for") or "")[:10]), unsafe_allow_html=True)

    visits = get_patient_visits(clinic["id"], patient["id"], limit=3)
    if visits:
        st.markdown("### 🩺 آخر الزيارات")
        for v in visits:
            with st.expander("🩺 {}".format((v.get("visit_date") or "")[:10])):
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("الوزن", "{} كغ".format(v.get("weight_kg") or "—"))
                    st.metric("ضغط", "{}/{}".format(v.get("bp_systolic") or "-", v.get("bp_diastolic") or "-"))
                with c2:
                    st.metric("نبض", "{}".format(v.get("fetal_heart_rate") or "—"))

    st.divider()
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        logout(token)
        st.session_state.pop("_pwa_token", None)
        st.session_state.pop("portal_step", None)
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
            else:
                st.experimental_set_query_params()
        except Exception:
            pass
        st.rerun()
