# -*- coding: utf-8 -*-
"""
Two-Factor Authentication View
واجهة إعدادات 2FA
"""
import base64
import streamlit as st

from core.ui import page_header, spacer
from services.two_factor import (
    setup_2fa, enable_2fa, disable_2fa,
    get_user_2fa, is_2fa_enabled, get_remaining_backup_codes,
    regenerate_backup_codes,
)


def _render_status(user):
    """Current 2FA status badge"""
    enabled = is_2fa_enabled(user["id"])

    if enabled:
        st.markdown("""
        <div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:12px;
                    padding:1.25rem 1.5rem;display:flex;align-items:center;gap:1rem;">
            <div style="font-size:2rem;">🛡️</div>
            <div style="flex:1;">
                <div style="font-weight:700;color:#047857;font-size:1.1rem;">
                    الحماية الثنائية مُفعّلة
                </div>
                <div style="color:#065F46;font-size:0.85rem;margin-top:0.25rem;">
                    حسابك محمي برمز إضافي عند كل تسجيل دخول
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        remaining = get_remaining_backup_codes(user["id"])
        if remaining <= 3:
            st.warning("⚠️ بقي لديك **{}** رموز احتياطية فقط — يُنصح بتوليد رموز جديدة".format(remaining))
    else:
        st.markdown("""
        <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:12px;
                    padding:1.25rem 1.5rem;display:flex;align-items:center;gap:1rem;">
            <div style="font-size:2rem;">⚠️</div>
            <div style="flex:1;">
                <div style="font-weight:700;color:#B45309;font-size:1.1rem;">
                    الحماية الثنائية غير مُفعّلة
                </div>
                <div style="color:#92400E;font-size:0.85rem;margin-top:0.25rem;">
                    ننصح بتفعيلها لحماية بيانات المرضى
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_setup_flow(user):
    """Setup flow: QR → verify → enable"""
    st.markdown("#### 🔐 إعداد الحماية الثنائية")

    if "2fa_setup_data" not in st.session_state:
        st.info("👉 اضغط زر البدء لتوليد رمز QR لربطه بتطبيق Google Authenticator")
        if st.button("🚀 بدء الإعداد", type="primary", use_container_width=True, key="2fa_start"):
            with st.spinner("⏳ جاري التحضير..."):
                try:
                    data = setup_2fa(user["id"], user["clinic_id"], user["email"])
                    st.session_state["2fa_setup_data"] = data
                    st.rerun()
                except Exception as e:
                    st.error("❌ {}".format(str(e)[:200]))
        return

    # Setup data exists
    data = st.session_state["2fa_setup_data"]

    st.markdown("##### 1️⃣ امسح الرمز بهاتفك")
    st.caption("استخدم أحد التطبيقات: Google Authenticator، Authy، Microsoft Authenticator، 1Password")

    c1, c2 = st.columns([1, 1])

    with c1:
        # QR image
        try:
            qr_bytes = base64.b64decode(data["qr_base64"])
            st.image(qr_bytes, caption="امسح هذا الرمز", use_container_width=True)
        except Exception:
            st.error("فشل عرض QR")

    with c2:
        st.markdown("**أو أدخل الرمز يدوياً:**")
        st.code(data["secret"], language=None)
        st.caption("انسخ الرمز والصقه في التطبيق")

        st.markdown("---")
        st.markdown("**الخطوات:**")
        st.markdown("""
        1. افتح تطبيق المصادقة
        2. اضغط ➕ لإضافة حساب
        3. اختر "Scan QR code" أو "Enter setup key"
        4. امسح الرمز أو الصق المفتاح
        5. اكتب الاسم: **أمينة SaaS**
        """)

    st.divider()
    st.markdown("##### 2️⃣ أدخل الرمز المكوّن من 6 أرقام")

    with st.form("verify_2fa_form"):
        code = st.text_input(
            "الرمز من التطبيق",
            placeholder="123456",
            max_chars=6,
            key="2fa_verify_code"
        )
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ تفعيل", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ إلغاء", use_container_width=True)

    if cancel:
        st.session_state.pop("2fa_setup_data", None)
        st.rerun()

    if submit:
        if not code or len(code.strip()) != 6:
            st.error("⚠️ أدخل 6 أرقام")
        else:
            try:
                result = enable_2fa(user["id"], code.strip())
                st.session_state["2fa_backup_codes"] = result["backup_codes"]
                st.session_state.pop("2fa_setup_data", None)
                st.success("🎉 تم تفعيل الحماية الثنائية!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error("❌ {}".format(str(e)[:200]))


def _render_backup_codes(codes, title="🔑 الرموز الاحتياطية"):
    """Render backup codes with download option"""
    st.markdown("#### {}".format(title))

    st.warning("""
    ⚠️ **مهم جداً:** احفظ هذه الرموز في مكان آمن الآن!
    
    - استخدمها إذا فُقد هاتفك
    - كل رمز يعمل **مرة واحدة** فقط
    - لن تُعرض مرة أخرى
    """)

    codes_text = "\n".join(codes)

    c1, c2 = st.columns([2, 1])
    with c1:
        st.code(codes_text, language=None)
    with c2:
        st.download_button(
            "📥 تحميل كملف نصي",
            data="أمينة SaaS — الرموز الاحتياطية\n" + "=" * 40 + "\n\n" + codes_text,
            file_name="amina_backup_codes.txt",
            mime="text/plain",
            use_container_width=True,
            key="2fa_download_codes"
        )

    if st.button("✅ حفظتها، إخفاء", type="primary", use_container_width=True, key="2fa_hide_codes"):
        st.session_state.pop("2fa_backup_codes", None)
        st.rerun()


def _render_manage_flow(user):
    """Manage existing 2FA"""
    st.markdown("#### 🔧 إدارة الحماية")

    # Backup codes
    remaining = get_remaining_backup_codes(user["id"])
    st.metric("🔑 رموز احتياطية متبقية", remaining)

    spacer(1)

    # Regenerate codes
    with st.expander("🔄 توليد رموز احتياطية جديدة"):
        st.warning("⚠️ الرموز الحالية ستصبح غير صالحة")
        if st.button("🔄 توليد 10 رموز جديدة", key="2fa_regen", use_container_width=True):
            try:
                codes = regenerate_backup_codes(user["id"])
                st.session_state["2fa_backup_codes"] = codes
                st.rerun()
            except Exception as e:
                st.error("❌ {}".format(str(e)[:200]))

    spacer(1)

    # Disable
    with st.expander("🚫 إلغاء تفعيل الحماية الثنائية"):
        st.error("⚠️ **تحذير:** بعد الإلغاء، لن يُطلب منك رمز إضافي عند الدخول")
        st.caption("يمكنك إعادة التفعيل في أي وقت")
        if st.button("🚫 إلغاء التفعيل", key="2fa_disable", use_container_width=True):
            try:
                disable_2fa(user["id"])
                st.success("✅ تم إلغاء التفعيل")
            except Exception as e:
                st.error("❌ {}".format(str(e)[:200]))


def _render_help():
    """Help section"""
    with st.expander("ℹ️ ما هي الحماية الثنائية؟"):
        st.markdown("""
        ### 🛡️ شرح مبسّط

        **بدون 2FA:**
        - تسجيل الدخول: البريد + كلمة المرور فقط
        - إذا سُرقت كلمة المرور → الحساب مكشوف ❌

        **مع 2FA:**
        - تسجيل الدخول: البريد + كلمة المرور + **رمز من هاتفك** ✅
        - حتى لو سُرقت كلمة المرور، السارق لا يستطيع الدخول بدون هاتفك

        ### 📱 التطبيقات المدعومة

        - Google Authenticator (الأشهر)
        - Authy
        - Microsoft Authenticator
        - 1Password
        - أي تطبيق يدعم TOTP

        ### 🔑 الرموز الاحتياطية

        - **10 رموز** تُولَّد عند التفعيل
        - استخدمها إذا فُقد هاتفك
        - كل رمز يعمل **مرة واحدة**
        - احفظها في مكان آمن (مدير كلمات مرور، ورقة)

        ### ❓ متى تُطلب مني؟

        - عند **كل تسجيل دخول**
        - بعد إغلاق المتصفح (انتهاء الجلسة)
        """)

    with st.expander("🔒 الأمان والخصوصية"):
        st.markdown("""
        - ✅ **Secret** يُخزَّن في قاعدة البيانات **بدون** تشفير إضافي (Supabase محمي)
        - ✅ **TOTP** لا يحتاج إنترنت (يعمل offline على الهاتف)
        - ✅ **الرموز الاحتياطية** تُخزَّن بصيغة واضحة (يمكن قراءتها)
        - ✅ **لا نُخزّن** الأرقام التي تدخلها (تُتحقق فقط)
        - ✅ **لا يمكن** استرجاع الحساب بدون هاتف أو backup codes
        """, unsafe_allow_html=True)


def render(clinic, user):
    """Main render"""
    page_header(
        "الحماية الثنائية (2FA)",
        "طبقة أمان إضافية لحماية حسابك",
        icon="🛡️"
    )

    # Status
    _render_status(user)
    spacer(1)

    # Show backup codes if just generated
    if "2fa_backup_codes" in st.session_state and st.session_state["2fa_backup_codes"]:
        _render_backup_codes(st.session_state["2fa_backup_codes"])
        spacer(1)
        return  # Don't show other flows while showing codes

    # Main flow
    enabled = is_2fa_enabled(user["id"])

    if not enabled:
        # Setup
        if "2fa_setup_data" in st.session_state:
            _render_setup_flow(user)
        else:
            st.markdown("#### 🔐 الحماية غير مفعّلة")
            st.info("احمِ حسابك بإضافة خطوة تحقق ثانية عند تسجيل الدخول")
            if st.button("🚀 بدء الإعداد", type="primary", use_container_width=True, key="2fa_start_main"):
                with st.spinner("⏳ جاري التحضير..."):
                    try:
                        data = setup_2fa(user["id"], user["clinic_id"], user["email"])
                        st.session_state["2fa_setup_data"] = data
                        st.rerun()
                    except Exception as e:
                        st.error("❌ {}".format(str(e)[:200]))
    else:
        # Manage
        _render_manage_flow(user)

    spacer(2)
    _render_help()
