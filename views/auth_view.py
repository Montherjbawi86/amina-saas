# -*- coding: utf-8 -*-
"""
Authentication View — Modern Login/Signup
تصميم عصري لصفحة الدخول والتسجيل
"""
import time
import streamlit as st


# ============================================
# CSS
# ============================================

def _inject_auth_css():
    st.markdown("""
    <style>
    /* Hide default Streamlit chrome on auth page */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu, footer { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* Main container */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .stApp {
        background: linear-gradient(135deg, #065F46 0%, #16A34A 40%, #22C55E 100%) !important;
        background-attachment: fixed;
        min-height: 100vh;
    }

    /* Ambient circles (decorative) */
    .stApp::before {
        content: '';
        position: fixed;
        top: -20%;
        right: -10%;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .stApp::after {
        content: '';
        position: fixed;
        bottom: -15%;
        left: -5%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }

    /* === HERO HEADER === */
    .auth-hero {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem 1rem;
        animation: fadeDown 0.6s ease-out;
    }
    .auth-hero-icon {
        font-size: 4rem;
        display: inline-block;
        animation: heartbeat 2s ease-in-out infinite;
        margin-bottom: 0.5rem;
    }
    .auth-hero-title {
        color: white !important;
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.03em;
        margin: 0 !important;
        text-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .auth-hero-sub {
        color: rgba(255,255,255,0.9) !important;
        font-size: 1.05rem;
        margin-top: 0.5rem !important;
        font-weight: 500;
    }
    .auth-hero-badges {
        display: flex;
        gap: 0.5rem;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    .auth-badge {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        color: white;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.2);
    }

    /* === AUTH CARD === */
    .auth-card-wrapper {
        max-width: 480px;
        margin: 0 auto;
        animation: fadeUp 0.7s ease-out;
    }

    /* Streamlit form styling inside auth page */
    .auth-card-wrapper [data-testid="stForm"] {
        background: white !important;
        border-radius: 20px !important;
        padding: 2rem 2rem 1.5rem 2rem !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25),
                    0 0 0 1px rgba(255,255,255,0.05) !important;
        border: none !important;
    }

    /* Tab styling (inside card) */
    .auth-card-wrapper .stTabs [data-baseweb="tab-list"] {
        background: #F1F5F9 !important;
        border-radius: 12px !important;
        padding: 6px !important;
        gap: 4px !important;
        margin-bottom: 1.5rem !important;
        border: 1px solid #E2E8F0 !important;
    }
    .auth-card-wrapper .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }
    .auth-card-wrapper .stTabs [data-baseweb="tab"]:hover {
        color: #16A34A !important;
        background: #FFFFFF !important;
    }
    .auth-card-wrapper .stTabs [aria-selected="true"] {
        background: #16A34A !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(22,163,74,0.3) !important;
    }
    .auth-card-wrapper .stTabs [aria-selected="true"] * {
        color: white !important;
    }
    .auth-card-wrapper .stTabs [data-baseweb="tab-highlight"],
    .auth-card-wrapper .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* Inputs */
    .auth-card-wrapper .stTextInput > div > div > input,
    .auth-card-wrapper .stSelectbox > div > div {
        border-radius: 10px !important;
        border: 1.5px solid #E2E8F0 !important;
        padding: 0.7rem 0.9rem !important;
        font-size: 0.95rem !important;
        background: #F8FAFC !important;
        transition: all 0.15s ease !important;
    }
    .auth-card-wrapper .stTextInput > div > div > input:focus,
    .auth-card-wrapper .stSelectbox > div > div:focus-within {
        border-color: #16A34A !important;
        background: white !important;
        box-shadow: 0 0 0 4px rgba(22,163,74,0.1) !important;
    }
    .auth-card-wrapper .stTextInput > label,
    .auth-card-wrapper .stSelectbox > label {
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: #334155 !important;
        margin-bottom: 0.35rem !important;
    }

    /* Primary button */
    .auth-card-wrapper .stButton > button[kind="primary"],
    .auth-card-wrapper .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.25rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        color: white !important;
        box-shadow: 0 6px 20px rgba(22,163,74,0.35) !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.01em;
    }
    .auth-card-wrapper .stButton > button[kind="primary"]:hover,
    .auth-card-wrapper .stFormSubmitButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 28px rgba(22,163,74,0.45) !important;
    }

    /* Secondary button */
    .auth-card-wrapper .stButton > button:not([kind="primary"]) {
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background: white !important;
        color: #334155 !important;
        font-weight: 600 !important;
    }
    .auth-card-wrapper .stButton > button:not([kind="primary"]):hover {
        border-color: #16A34A !important;
        color: #16A34A !important;
    }

    /* Plan selector */
    .auth-card-wrapper .stSelectbox [data-baseweb="select"] {
        font-size: 0.9rem !important;
    }

    /* Footer */
    .auth-footer {
        text-align: center;
        color: rgba(255,255,255,0.7);
        font-size: 0.8rem;
        padding: 2rem 1rem 1.5rem 1rem;
        animation: fadeUp 1s ease-out;
    }

    /* === Animations === */
    @keyframes heartbeat {
        0%, 100% { transform: scale(1); }
        10%, 30% { transform: scale(1.1); }
        20%, 40% { transform: scale(1); }
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Mobile */
    @media (max-width: 640px) {
        .auth-hero-title { font-size: 1.9rem !important; }
        .auth-hero-icon { font-size: 3rem; }
        .auth-card-wrapper [data-testid="stForm"] {
            padding: 1.5rem 1.25rem 1rem 1.25rem !important;
            border-radius: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================
# HEADER
# ============================================

def _render_header():
    st.markdown("""
    <div class="auth-hero">
        <div class="auth-hero-icon">👶</div>
        <h1 class="auth-hero-title">أمينة SaaS</h1>
        <p class="auth-hero-sub">نظام إدارة عيادات النساء والولادة</p>
        <div class="auth-hero-badges">
            <span class="auth-badge">🤖 مدعوم بالذكاء الاصطناعي</span>
            <span class="auth-badge">🇮🇶 عربي 100%</span>
            <span class="auth-badge">🔒 آمن ومشفر</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# LOGIN
# ============================================

def _render_login_form():
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(
            "📧 البريد الإلكتروني",
            placeholder="doctor@clinic.com",
            key="login_email"
        )
        password = st.text_input(
            "🔒 كلمة المرور",
            type="password",
            placeholder="••••••••",
            key="login_password"
        )

        st.write("")
        submitted = st.form_submit_button(
            "🚀 تسجيل الدخول",
            use_container_width=True,
            type="primary"
        )

    if submitted:
        if not email or not password:
            st.error("⚠️ الرجاء إدخال البريد وكلمة المرور")
            return

        try:
            from core.auth import login as auth_login, AuthError
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


# ============================================
# SIGNUP
# ============================================

def _render_signup_form():
    with st.form("signup_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            clinic_name = st.text_input(
                "🏥 اسم العيادة *",
                placeholder="عيادة النور",
                key="signup_clinic"
            )
        with c2:
            phone = st.text_input(
                "📞 هاتف العيادة",
                placeholder="+964 770...",
                key="signup_phone"
            )

        doctor_name = st.text_input(
            "👩‍⚕️ اسم الطبيبة *",
            placeholder="د. أمينة محمد",
            key="signup_doctor"
        )

        email_s = st.text_input(
            "📧 البريد الإلكتروني *",
            placeholder="doctor@clinic.com",
            key="signup_email"
        )

        c3, c4 = st.columns(2)
        with c3:
            password_s = st.text_input(
                "🔒 كلمة المرور *",
                type="password",
                placeholder="6+ أحرف",
                key="signup_password"
            )
        with c4:
            password_s2 = st.text_input(
                "🔒 تأكيد كلمة المرور *",
                type="password",
                placeholder="أعد الإدخال",
                key="signup_password2"
            )

        plan = st.selectbox(
            "💎 الباقة",
            options=["starter", "pro", "hospital"],
            format_func=lambda x: {
                "starter": "🟢 Starter — 50 حامل — $49/شهر",
                "pro": "🔵 Pro — 200 حامل — $149/شهر",
                "hospital": "🟣 Hospital — غير محدود — $499/شهر",
            }[x],
            key="signup_plan"
        )

        st.write("")
        submitted_s = st.form_submit_button(
            "✨ إنشاء الحساب",
            use_container_width=True,
            type="primary"
        )

    if submitted_s:
        errors = []
        if not clinic_name:
            errors.append("اسم العيادة مطلوب")
        if not doctor_name:
            errors.append("اسم الطبيبة مطلوب")
        if not email_s or "@" not in email_s:
            errors.append("بريد إلكتروني غير صحيح")
        if len(password_s) < 6:
            errors.append("كلمة المرور قصيرة (6+ أحرف)")
        if password_s != password_s2:
            errors.append("كلمتا المرور غير متطابقتين")

        if errors:
            for e in errors:
                st.error("⚠️ {}".format(e))
            return

        try:
            from core.auth import signup_clinic, AuthError
            from core.session import set_user

            clinic, user_new = signup_clinic(
                clinic_name=clinic_name,
                doctor_name=doctor_name,
                email=email_s,
                password=password_s,
                phone=phone,
                plan=plan
            )
            set_user(user_new, clinic)
            st.success("🎉 تم إنشاء العيادة بنجاح!")
            st.balloons()
            time.sleep(0.6)
            st.rerun()

        except Exception as e:
            st.error("❌ {}".format(str(e)[:200]))


# ============================================
# FOOTER
# ============================================

def _render_footer():
    st.markdown("""
    <div class="auth-footer">
        <div style="font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:0.4rem;">
            © 2026 أمينة SaaS
        </div>
        <div style="opacity:0.7;">
            صُنع بـ 💚 في العراق · كل الحقوق محفوظة
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# MAIN RENDER
# ============================================

def render_auth():
    """Main entry point for auth page"""
    _inject_auth_css()
    _render_header()

    # Centered card
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        st.markdown('<div class="auth-card-wrapper">', unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔐 دخول", "🏥 عيادة جديدة"])

        with tab_login:
            _render_login_form()

        with tab_signup:
            _render_signup_form()

        st.markdown('</div>', unsafe_allow_html=True)

    _render_footer()
