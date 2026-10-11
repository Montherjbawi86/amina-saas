# -*- coding: utf-8 -*-
"""Users management view"""
import time
from datetime import datetime
import streamlit as st

from services.users import (
    create_staff_user, list_clinic_users_cached, update_user_role,
    toggle_active, update_full_name, reset_password, count_users_by_role,
    ROLE_LABELS, ROLE_DESCRIPTIONS, UserManagementError,
)
from core.session import get_current_user
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Render users tab"""
    # Permission check
    from core.auth import can_manage_users
    if not can_manage_users(user):
        st.warning("🔒 هذه الصفحة متاحة فقط للمديرة (admin) أو الطبيبة الرئيسية")
        st.info("👉 دورك الحالي: {}".format(ROLE_LABELS.get(user.get("role"), user.get("role"))))
        return

    view = st.session_state.get("users_view", "list")
    if view == "list":
        _render_list(clinic, user)
    elif view == "new":
        _render_new(clinic, user)


# ============================================
# LIST
# ============================================
def _render_list(clinic, user):
    st.markdown("### 👥 إدارة المستخدمين")

    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption("{} — {} مستخدم".format(clinic["name"], count_users_by_role(clinic["id"])))
    with c2:
        if st.button("➕ مستخدم جديد", use_container_width=True, type="primary", key="new_user_btn"):
            st.session_state["users_view"] = "new"
            st.rerun()

    show_cache_status("users_cache")
    st.divider()

    # Role summary
    with st.spinner("جاري التحميل..."):
        users = list_clinic_users_cached(clinic["id"])

    counts = {r: 0 for r in ROLE_LABELS}
    for u in users:
        counts[u["role"]] = counts.get(u["role"], 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _role_kpi("👩‍⚕️ طبيبات", counts.get("doctor", 0), "#0EA5A0")
    with c2:
        _role_kpi("👩‍⚕️ ممرضات", counts.get("nurse", 0), "#10B981")
    with c3:
        _role_kpi("📞 استقبال", counts.get("reception", 0), "#22C55E")
    with c4:
        _role_kpi("🔑 مديرة", counts.get("admin", 0), "#F59E0B")

    st.divider()
    st.markdown("**العدد: {}**".format(len(users)))

    if not users:
        st.info("لا يوجد مستخدمون")
        return

    for u in users:
        _render_user_card(clinic, user, u)


def _render_user_card(clinic, current_user, u):
    """Render single user card"""
    is_self = u["id"] == current_user["id"]
    role_icon = ROLE_LABELS.get(u["role"], "👤").split(" ", 1)[0]
    active = u.get("is_active", True)
    active_color = "#10B981" if active else "#EF4444"

    st.markdown("""
    <div style="background:white; border-radius:12px; padding:1rem 1.25rem; margin-bottom:0.5rem; border-right:5px solid {color}; box-shadow:0 2px 6px rgba(0,0,0,0.05); display:flex; align-items:center; gap:1rem;">
        <div style="font-size:2rem;">{icon}</div>
        <div style="flex:1;">
            <div style="font-weight:700; color:#1F2937; font-size:1.05rem;">
                {name} {self_badge}
            </div>
            <div style="color:#6B7280; font-size:0.85rem; margin-top:0.2rem;">
                📧 {email} &nbsp;|&nbsp; {role}
            </div>
            <div style="color:#9CA3AF; font-size:0.75rem; margin-top:0.2rem;">
                آخر دخول: {last_login}
            </div>
        </div>
        <div>
            <span style="background:{color}; color:white; padding:0.3rem 0.75rem; border-radius:999px; font-size:0.75rem; font-weight:700;">
                {status}
            </span>
        </div>
    </div>
    """.format(
        color=active_color,
        icon=role_icon,
        name=u["full_name"],
        self_badge='<span style="color:#0EA5A0; font-size:0.75rem;">(أنت)</span>' if is_self else "",
        email=u["email"],
        role=ROLE_LABELS.get(u["role"], u["role"]),
        last_login=(u.get("last_login") or "—")[:16],
        status="✅ نشط" if active else "🔒 معطل"
    ), unsafe_allow_html=True)

    # Actions in expander
    with st.expander("⚙️ إدارة", expanded=False):
        c1, c2 = st.columns(2)

        with c1:
            # Change role
            role_keys = list(ROLE_LABELS.keys())
            current_idx = role_keys.index(u["role"]) if u["role"] in role_keys else 0
            new_role = st.selectbox(
                "الدور",
                options=role_keys,
                index=current_idx,
                format_func=lambda x: ROLE_LABELS[x],
                key="role_" + u["id"],
                help=ROLE_DESCRIPTIONS.get(u["role"], "")
            )
            if new_role != u["role"]:
                if st.button("💾 تحديث الدور", key="save_role_" + u["id"], use_container_width=True):
                    try:
                        update_user_role(clinic["id"], u["id"], new_role)
                        clear_all()
                        st.success("✅ تم التحديث")
                        time.sleep(0.5)
                        st.rerun()
                    except UserManagementError as e:
                        st.error(str(e))

        with c2:
            # Toggle active
            if not is_self:
                if st.button(
                    "🚫 تعطيل" if active else "✅ تفعيل",
                    key="toggle_" + u["id"],
                    use_container_width=True
                ):
                    new_status = toggle_active(clinic["id"], u["id"])
                    clear_all()
                    st.success("✅ {}".format("تم التعطيل" if not new_status else "تم التفعيل"))
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.info("لا يمكنك تعطيل نفسك")

        st.divider()

        # Edit name
        c1, c2 = st.columns([3, 1])
        with c1:
            new_name = st.text_input("الاسم الكامل", value=u["full_name"], key="name_" + u["id"])
        with c2:
            st.write("")
            if new_name != u["full_name"]:
                if st.button("💾 حفظ", key="save_name_" + u["id"], use_container_width=True):
                    try:
                        update_full_name(clinic["id"], u["id"], new_name)
                        clear_all()
                        st.success("✅ تم الحفظ")
                        time.sleep(0.5)
                        st.rerun()
                    except UserManagementError as e:
                        st.error(str(e))

        # Reset password
        st.markdown("##### 🔑 إعادة تعيين كلمة المرور")
        c1, c2 = st.columns(2)
        with c1:
            new_pw = st.text_input("كلمة مرور جديدة", type="password", key="pw_" + u["id"])
        with c2:
            st.write("")
            if st.button("🔑 إعادة التعيين", key="reset_pw_" + u["id"], use_container_width=True):
                if len(new_pw) < 6:
                    st.error("كلمة المرور قصيرة (6+ أحرف)")
                else:
                    try:
                        reset_password(clinic["id"], u["id"], new_pw)
                        st.success("✅ تم تغيير كلمة المرور")
                    except UserManagementError as e:
                        st.error(str(e))


# ============================================
# NEW USER
# ============================================
def _render_new(clinic, user):
    st.markdown("### ➕ إضافة مستخدم جديد")

    if st.button("⬅️ رجوع للقائمة", key="back_users_list"):
        st.session_state["users_view"] = "list"
        st.rerun()

    with st.form("new_user_form"):
        st.markdown("#### البيانات الأساسية")
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("الاسم الكامل *", placeholder="د. سارة أحمد")
        with c2:
            email = st.text_input("البريد الإلكتروني *", placeholder="sara@clinic.com")

        c1, c2 = st.columns(2)
        with c1:
            password = st.text_input("كلمة المرور * (6+ أحرف)", type="password")
        with c2:
            password2 = st.text_input("تأكيد كلمة المرور *", type="password")

        st.markdown("#### الدور والصلاحيات")
        role = st.selectbox(
            "الدور",
            options=list(ROLE_LABELS.keys()),
            format_func=lambda x: "{} — {}".format(ROLE_LABELS[x], ROLE_DESCRIPTIONS[x]),
            index=1,  # nurse by default
            key="new_user_role"
        )

        st.info("💡 {}".format(ROLE_DESCRIPTIONS[role]))

        submitted = st.form_submit_button("💾 إنشاء المستخدم", use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not full_name: errors.append("الاسم مطلوب")
        if not email or "@" not in email: errors.append("بريد إلكتروني غير صحيح")
        if len(password) < 6: errors.append("كلمة المرور قصيرة")
        if password != password2: errors.append("كلمتا المرور غير متطابقتين")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                u = create_staff_user(
                    clinic_id=clinic["id"],
                    email=email,
                    password=password,
                    full_name=full_name,
                    role=role,
                )
                clear_all()
                st.success("✅ تم إنشاء المستخدم: {}".format(u["full_name"]))
                st.balloons()
                st.session_state["users_view"] = "list"
                time.sleep(0.8)
                st.rerun()
            except UserManagementError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))


def _role_kpi(label, value, color):
    st.markdown("""
    <div style="background:white; border-radius:10px; padding:0.75rem; text-align:center; border-right:3px solid {color}; box-shadow:0 1px 4px rgba(0,0,0,0.05);">
        <div style="font-size:1.5rem; font-weight:800; color:{color};">{value}</div>
        <div style="font-size:0.75rem; color:#6B7280;">{label}</div>
    </div>
    """.format(color=color, value=value, label=label), unsafe_allow_html=True)
