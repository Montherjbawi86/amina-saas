"""DB client for amina-saas"""
from typing import Any, Optional, List, Dict
from functools import lru_cache
from supabase import create_client, Client
from postgrest.exceptions import APIError
from core.config import settings, validate_config

_ok, _errors = validate_config()
if not _ok and settings.is_production:
    raise RuntimeError("Config errors: " + " | ".join(_errors))

@lru_cache(maxsize=1)
def get_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def db() -> Client:
    return get_client()

class DBError(Exception):
    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details

def safe_query(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except APIError as e:
        raise DBError(str(e), getattr(e, 'code', None), getattr(e, 'details', None))
    except Exception as e:
        raise DBError(str(e))

def select(table, columns="*", **filters):
    q = db().table(table).select(columns)
    for k, v in filters.items():
        q = q.eq(k, v)
    return safe_query(q.execute).data

def insert(table, data):
    result = safe_query(db().table(table).insert(data).execute)
    return result.data[0] if result.data else {}

def update(table, filters, data):
    q = db().table(table).update(data)
    for k, v in filters.items():
        q = q.eq(k, v)
    return safe_query(q.execute).data

def delete(table, **filters):
    q = db().table(table).delete()
    for k, v in filters.items():
        q = q.eq(k, v)
    return safe_query(q.execute).data

def health_check():
    tables = ['clinics', 'users', 'patients', 'appointments', 'visits']
    result = {"ok": True, "tables": {}, "errors": []}
    for t in tables:
        try:
            r = db().table(t).select("*", count="exact").limit(1).execute()
            result["tables"][t] = r.count or 0
        except Exception as e:
            result["ok"] = False
            result["errors"].append(t + ": " + str(e)[:80])
    return result

if __name__ == "__main__":
    print("=" * 50)
    print("DB Health Check")
    print("=" * 50)
    h = health_check()
    for t, count in h["tables"].items():
        print("OK {:15s} -> {} rows".format(t, count))
    if h["errors"]:
        print("ERRORS:")
        for e in h["errors"]:
            print("   " + e)
    else:
        print("All tables OK")


# ============================================
# Cached helpers (Streamlit only)
# ============================================
def cached_select(table, columns="*", ttl=30, **filters):
    """
    Cached SELECT for Streamlit pages.
    TTL in seconds. Requires streamlit import inside.
    """
    try:
        import streamlit as st
    except ImportError:
        return select(table, columns, **filters)

    @st.cache_data(ttl=ttl, show_spinner=False)
    def _run(table, columns, filters_tuple):
        return select(table, columns, **dict(filters_tuple))

    return _run(table, columns, tuple(sorted(filters.items())))


def clear_cache():
    """Clear all Streamlit caches"""
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:
        pass
