"""Caching helpers for Streamlit with safe fallback"""
import streamlit as st
import time
from typing import Any, Callable


def cached(ttl: int = 60, key_prefix: str = ""):
    """
    Decorator for caching function results with TTL.
    Usage:
        @cached(ttl=30, key_prefix="patients")
        def load_patients(clinic_id, search, risk):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        cached_fn = st.cache_data(ttl=ttl, show_spinner=False)(fn)
        return cached_fn
    return decorator


def clear_all():
    """Clear all Streamlit caches. Call after mutations (insert/update/delete)"""
    try:
        st.cache_data.clear()
    except Exception:
        pass


def clear_key(prefix: str):
    """Clear caches matching a key prefix (best-effort)"""
    clear_all()


class Timer:
    """Context manager to measure duration"""
    def __init__(self, label: str = ""):
        self.label = label
        self.start = None
        self.elapsed = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start


def show_cache_status(last_updated_key: str = "last_updated"):
    """Display 'last updated' info + refresh button.
    Returns True if user clicked refresh."""
    col1, col2 = st.columns([4, 1])
    with col1:
        last = st.session_state.get(last_updated_key)
        # Guard: only treat as timestamp if numeric
        if last and isinstance(last, (int, float)):
            try:
                delta = int(time.time() - last)
                if delta < 60:
                    st.caption("🕐 آخر تحديث: قبل {} ثانية".format(delta))
                elif delta < 3600:
                    st.caption("🕐 آخر تحديث: قبل {} دقيقة".format(delta // 60))
                else:
                    st.caption("🕐 آخر تحديث: قبل {} ساعة".format(delta // 3600))
            except Exception:
                st.caption("🕐 جاهز")
        else:
            st.caption("🕐 جاهز")
    with col2:
        clicked = st.button("🔄 تحديث", key="refresh_" + last_updated_key, use_container_width=True)
        if clicked:
            clear_all()
            st.session_state[last_updated_key] = time.time()
            st.rerun()
        return clicked


def mark_updated(key: str = "last_updated"):
    """Mark cache as freshly updated"""
    st.session_state[key] = time.time()


# ============================================
# Global performance settings
# ============================================
DEFAULT_TTL = 300  # 5 minutes
PATIENTS_TTL = 60  # 1 minute
VISITS_TTL = 60
APPOINTMENTS_TTL = 30
ALERTS_TTL = 300
