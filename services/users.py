# -*- coding: utf-8 -*-
"""User management for clinic staff"""
from typing import Dict, List, Optional
from datetime import datetime

from core.db import db, insert, select, update, delete, DBError
from core.auth import hash_password, AuthError


class UserManagementError(Exception):
    pass


ROLE_LABELS = {
    "doctor": "👩‍⚕️ طبيبة",
    "nurse": "👩‍⚕️ ممرضة",
    "reception": "📞 استقبال",
    "admin": "🔑 مديرة",
}

ROLE_DESCRIPTIONS = {
    "doctor": "صلاحيات كاملة طبية (تشخيص، وصفات، تحليل)",
    "nurse": "قياسات ومتابعة، بدون تشخيص",
    "reception": "إدارة المواعيد والمرضى، بدون طبي",
    "admin": "إدارة النظام والمستخدمين",
}


def create_staff_user(clinic_id, email, password, full_name, role="nurse"):
    """Add a staff member to a clinic"""
    if not email or "@" not in email:
        raise UserManagementError("Invalid email")
    if role not in ROLE_LABELS:
        raise UserManagementError("Invalid role: " + role)
    if not full_name:
        raise UserManagementError("Full name required")
    if len(password) < 6:
        raise UserManagementError("Password must be at least 6 chars")

    # Check existing
    existing = select("users", "id", email=email.lower().strip(), clinic_id=clinic_id)
    if existing:
        raise UserManagementError("البريد مستخدم مسبقاً في هذه العيادة")

    data = {
        "clinic_id": clinic_id,
        "email": email.lower().strip(),
        "password_hash": hash_password(password),
        "full_name": full_name.strip(),
        "role": role,
        "is_active": True,
    }

    try:
        u = insert("users", data)
    except DBError as e:
        raise UserManagementError("فشل الإنشاء: " + str(e))

    return _public(u)


def _public(user):
    if not user:
        return None
    return {
        "id": user["id"],
        "clinic_id": user["clinic_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": user.get("is_active", True),
        "last_login": user.get("last_login"),
        "created_at": user.get("created_at"),
    }


def list_clinic_users(clinic_id):
    """List all users in a clinic"""
    rows = select("users", "*", clinic_id=clinic_id)
    return [_public(u) for u in rows]


def get_user(clinic_id, user_id):
    rows = select("users", "*", id=user_id, clinic_id=clinic_id)
    return _public(rows[0]) if rows else None


def update_user_role(clinic_id, user_id, new_role):
    if new_role not in ROLE_LABELS:
        raise UserManagementError("Invalid role")
    return update("users", {"id": user_id, "clinic_id": clinic_id}, {"role": new_role})


def toggle_active(clinic_id, user_id):
    """Toggle is_active status"""
    user = get_user(clinic_id, user_id)
    if not user:
        raise UserManagementError("User not found")
    new_status = not user["is_active"]
    update("users", {"id": user_id, "clinic_id": clinic_id}, {"is_active": new_status})
    return new_status


def update_full_name(clinic_id, user_id, full_name):
    if not full_name:
        raise UserManagementError("Name required")
    return update("users", {"id": user_id, "clinic_id": clinic_id}, {"full_name": full_name.strip()})


def reset_password(clinic_id, user_id, new_password):
    if len(new_password) < 6:
        raise UserManagementError("كلمة مرور قصيرة")
    new_hash = hash_password(new_password)
    return update("users", {"id": user_id, "clinic_id": clinic_id}, {"password_hash": new_hash})


def delete_user(clinic_id, user_id):
    """Hard delete. Use with caution."""
    q = db().table("users").delete().eq("id", user_id).eq("clinic_id", clinic_id)
    return q.execute().data


def count_users_by_role(clinic_id):
    rows = select("users", "role", clinic_id=clinic_id)
    counts = {r: 0 for r in ROLE_LABELS}
    for r in rows:
        role = r.get("role", "doctor")
        counts[role] = counts.get(role, 0) + 1
    return counts


# Cached
def list_clinic_users_cached(clinic_id):
    try:
        import streamlit as st
    except ImportError:
        return list_clinic_users(clinic_id)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid):
        return list_clinic_users(cid)

    return _cached(clinic_id)


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from core.db import delete as db_delete

    print("=" * 50)
    print("Users Management Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Users Test " + suffix, "Dr. Owner", "owner-{}@t.com".format(suffix))

    print("\n1. Create doctor (owner):")
    doc = create_staff_user(clinic["id"], "doc-{}@t.com".format(suffix), "secret123",
                            "د. أمينة", "doctor")
    print("   OK: {} - {}".format(doc["email"], doc["role"]))

    print("\n2. Create nurse:")
    nurse = create_staff_user(clinic["id"], "nurse-{}@t.com".format(suffix), "secret123",
                              "ممرضة سارة", "nurse")
    print("   OK: {} - {}".format(nurse["email"], nurse["role"]))

    print("\n3. Create receptionist:")
    rec = create_staff_user(clinic["id"], "rec-{}@t.com".format(suffix), "secret123",
                            "استقبال علي", "reception")
    print("   OK: {} - {}".format(rec["email"], rec["role"]))

    print("\n4. List all:")
    users = list_clinic_users(clinic["id"])
    print("   Total: {}".format(len(users)))
    for u in users:
        print("   - [{}] {}".format(u["role"], u["full_name"]))

    print("\n5. Count by role:")
    counts = count_users_by_role(clinic["id"])
    for role, count in counts.items():
        if count:
            print("   {}: {}".format(ROLE_LABELS[role], count))

    print("\n6. Toggle active (nurse):")
    new_status = toggle_active(clinic["id"], nurse["id"])
    print("   Nurse is now: {}".format("نشطة" if new_status else "معطلة"))

    print("\n7. Change role (nurse -> admin):")
    update_user_role(clinic["id"], nurse["id"], "admin")
    u = get_user(clinic["id"], nurse["id"])
    print("   New role: {}".format(u["role"]))

    print("\n8. Duplicate email rejected:")
    try:
        create_staff_user(clinic["id"], "doc-{}@t.com".format(suffix), "x12345", "Dup", "nurse")
        print("   FAIL")
    except UserManagementError as e:
        print("   OK: {}".format(str(e)[:60]))

    print("\n9. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Users module OK")
    print("=" * 50)
