# -*- coding: utf-8 -*-
"""Streamlit session management (Streamlit 1.28 compatible)"""
import streamlit as st
from typing import Optional, Dict


SESSION_USER_KEY = "amina_user"
SESSION_CLINIC_KEY = "amina_clinic"


def _get_qp(key, default=None):
    """Get query param (compatible with 1.28+)"""
    try:
        # Streamlit 1.30+
        if hasattr(st, "query_params"):
            return st.query_params.get(key, default)
        # Streamlit < 1.30
        params = dict(st.query_params)
        vals = params.get(key)
        if isinstance(vals, list):
            return vals[0] if vals else default
        return vals or default
    except Exception:
        return default


def _set_qp(key, value):
    """Set query param"""
    try:
        if hasattr(st, "query_params"):
            st.query_params[key] = value
        else:
            params = dict(st.query_params)
            params[key] = value
            # no-op: query_params already updated
    except Exception:
        pass


def _clear_qp():
    """Clear query params"""
    try:
        if hasattr(st, "query_params"):
            st.query_params.clear()
        else:
            st.query_params.clear()
    except Exception:
        pass


def init_session():
    if SESSION_USER_KEY not in st.session_state:
        st.session_state[SESSION_USER_KEY] = None
    if SESSION_CLINIC_KEY not in st.session_state:
        st.session_state[SESSION_CLINIC_KEY] = None

    # Try restore from query params
    if st.session_state[SESSION_USER_KEY] is None:
        uid = _get_qp("uid")
        cid = _get_qp("cid")
        if uid and cid:
            try:
                from core.auth import get_user
                from core.tenant import get_clinic
                u = get_user(uid)
                if u and u.get("is_active"):
                    c = get_clinic(cid)
                    if c and c.get("is_active"):
                        st.session_state[SESSION_USER_KEY] = u
                        st.session_state[SESSION_CLINIC_KEY] = c
            except Exception:
                pass


def set_user(user, clinic):
    st.session_state[SESSION_USER_KEY] = user
    st.session_state[SESSION_CLINIC_KEY] = clinic
    # Persist to query params
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
