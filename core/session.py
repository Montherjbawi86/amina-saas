# -*- coding: utf-8 -*-
"""Streamlit session management (clean, no external storage)"""
import streamlit as st


SESSION_USER_KEY = "amina_user"
SESSION_CLINIC_KEY = "amina_clinic"


# ============================================
# QUERY PARAMS
# ============================================

def _get_qp(key, default=None):
    try:
        if hasattr(st, "query_params"):
            return st.query_params.get(key, default)
        return default
    except Exception:
        return default


def _set_qp(key, value):
    try:
        if hasattr(st, "query_params"):
            st.query_params[key] = str(value)
    except Exception:
        pass


def _clear_qp():
    try:
        st.query_params.clear()
    except Exception:
        pass


# ============================================
# MAIN API
# ============================================

def init_session():
    """Initialize session — restore from query params if present"""
    if SESSION_USER_KEY not in st.session_state:
        st.session_state[SESSION_USER_KEY] = None
    if SESSION_CLINIC_KEY not in st.session_state:
        st.session_state[SESSION_CLINIC_KEY] = None

    # Already logged in this session
    if st.session_state[SESSION_USER_KEY] is not None:
        return

    # Try restore from query params
    uid = _get_qp("uid")
    cid = _get_qp("cid")
    if uid and cid:
        try:
            from core.auth import get_user
            from core.tenant import get_clinic
            u = get_user(uid)
            c = get_clinic(cid) if u else None
            if u and u.get("is_active") and c and c.get("is_active"):
                st.session_state[SESSION_USER_KEY] = u
                st.session_state[SESSION_CLINIC_KEY] = c
                print("[session] restored from URL: {}".format(u.get("email")))
        except Exception as e:
            print("[session] restore error: {}".format(str(e)[:100]))


def set_user(user, clinic):
    """Set current user — persist uid/cid to URL"""
    st.session_state[SESSION_USER_KEY] = user
    st.session_state[SESSION_CLINIC_KEY] = clinic
    _set_qp("uid", user["id"])
    _set_qp("cid", clinic["id"])


def get_current_user():
    return st.session_state.get(SESSION_USER_KEY)


def get_current_clinic():
    return st.session_state.get(SESSION_CLINIC_KEY)


def is_logged_in():
    return get_current_user() is not None


def logout():
    st.session_state[SESSION_USER_KEY] = None
    st.session_state[SESSION_CLINIC_KEY] = None
    _clear_qp()
    st.rerun()


def require_login():
    if not is_logged_in():
        st.error("🔒 يجب تسجيل الدخول أولاً")
        st.info("👉 اذهب لصفحة **تسجيل الدخول** من الأعلى")
        st.stop()


def current_clinic_id():
    clinic = get_current_clinic()
    return clinic["id"] if clinic else None


def current_user_id():
    user = get_current_user()
    return user["id"] if user else None
