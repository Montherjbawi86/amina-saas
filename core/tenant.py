"""Tenant (Clinic) management for multi-tenancy"""
from typing import Dict, List, Optional

from core.db import db, insert, select, update, delete, DBError


class TenantError(Exception):
    pass


def _slugify(name):
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\u0600-\u06FF]+", "-", s)
    s = s.strip("-")
    return s[:50] or "clinic"


def create_clinic(name, doctor_name, email, phone=None, plan="starter"):
    if not name or not doctor_name or not email:
        raise TenantError("name, doctor_name and email are required")

    if plan not in ("starter", "pro", "hospital"):
        raise TenantError("Invalid plan: " + plan)

    max_patients_map = {"starter": 50, "pro": 200, "hospital": 100000}
    max_patients = max_patients_map[plan]

    slug_base = _slugify(name)
    slug = slug_base

    existing = select("clinics", "id", slug=slug)
    if existing:
        import uuid
        slug = "{}-{}".format(slug_base, uuid.uuid4().hex[:6])

    existing_email = select("clinics", "id", email=email)
    if existing_email:
        raise TenantError("Email already registered: " + email)

    clinic_data = {
        "name": name,
        "slug": slug,
        "doctor_name": doctor_name,
        "email": email,
        "phone": phone,
        "plan": plan,
        "max_patients": max_patients,
    }

    try:
        clinic = insert("clinics", clinic_data)
    except DBError as e:
        raise TenantError("Failed to create clinic: " + str(e))

    return clinic


def get_clinic(clinic_id):
    rows = select("clinics", "*", id=clinic_id)
    return rows[0] if rows else None


def get_clinic_by_slug(slug):
    rows = select("clinics", "*", slug=slug)
    return rows[0] if rows else None


def update_clinic(clinic_id, **fields):
    allowed = {"name", "phone", "plan", "max_patients", "is_active"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise TenantError("No valid fields to update")
    return update("clinics", {"id": clinic_id}, clean)


def get_clinic_stats(clinic_id):
    clinic = get_clinic(clinic_id)
    if not clinic:
        raise TenantError("Clinic not found")

    patients_count = (
        db().table("patients")
        .select("id", count="exact")
        .eq("clinic_id", clinic_id)
        .execute()
        .count or 0
    )
    users_count = (
        db().table("users")
        .select("id", count="exact")
        .eq("clinic_id", clinic_id)
        .execute()
        .count or 0
    )

    return {
        "clinic_id": clinic_id,
        "plan": clinic["plan"],
        "max_patients": clinic["max_patients"],
        "current_patients": patients_count,
        "current_users": users_count,
        "usage_pct": round(100.0 * patients_count / max(clinic["max_patients"], 1), 1),
        "trial_ends_at": clinic.get("trial_ends_at"),
        "is_active": clinic["is_active"],
    }


def can_add_patient(clinic_id):
    stats = get_clinic_stats(clinic_id)
    return stats["current_patients"] < stats["max_patients"]


def list_clinics(limit=100):
    return (
        db().table("clinics")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


if __name__ == "__main__":
    print("=" * 50)
    print("Tenant Module Test")
    print("=" * 50)

    import uuid
    suffix = uuid.uuid4().hex[:6]

    print("\n1. Create clinic:")
    c = create_clinic(
        name="Test Clinic " + suffix,
        doctor_name="Dr. Test",
        email="test-{}@clinic.com".format(suffix),
        plan="starter"
    )
    print("   OK: {} (slug={}, plan={}, max={})".format(
        c["id"][:8], c["slug"], c["plan"], c["max_patients"]))

    print("\n2. Get clinic:")
    fetched = get_clinic(c["id"])
    print("   OK: {}".format(fetched["name"]))

    print("\n3. Stats:")
    stats = get_clinic_stats(c["id"])
    print("   patients: {}/{} ({}%)".format(
        stats["current_patients"], stats["max_patients"], stats["usage_pct"]))

    print("\n4. Can add patient:")
    print("   {}".format(can_add_patient(c["id"])))

    print("\n5. Duplicate email rejected:")
    try:
        create_clinic("Dup", "Dr. X", c["email"])
        print("   FAIL: should have rejected")
    except TenantError as e:
        print("   OK: {}".format(str(e)[:50]))

    print("\n6. Cleanup:")
    delete("clinics", id=c["id"])
    print("   OK: removed")

    print("\n" + "=" * 50)
    print("Tenant module OK")
    print("=" * 50)


# ============================================
# Cached helpers (Streamlit)
# ============================================
def get_clinic_stats_cached(clinic_id):
    """
    Cached version of get_clinic_stats for Streamlit.
    Falls back to direct query if Streamlit unavailable.
    """
    try:
        import streamlit as st
    except ImportError:
        return get_clinic_stats(clinic_id)

    @st.cache_data(ttl=60, show_spinner=False)
    def _cached(cid):
        return get_clinic_stats(cid)

    return _cached(clinic_id)
