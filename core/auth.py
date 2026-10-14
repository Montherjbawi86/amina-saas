"""Authentication module: signup, login, session"""
from typing import Dict, Optional, List
from datetime import datetime
import bcrypt

from core.db import db, insert, select, update, DBError
from core.tenant import create_clinic, get_clinic, TenantError


class AuthError(Exception):
    pass


# ============================================
# Password hashing
# ============================================
def hash_password(plain: str) -> str:
    if not plain or len(plain) < 6:
        raise AuthError("Password must be at least 6 characters")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ============================================
# User management
# ============================================
def create_user(clinic_id, email, password, full_name, role="doctor"):
    if not email or "@" not in email:
        raise AuthError("Invalid email")
    if role not in ("doctor", "nurse", "admin", "reception"):
        raise AuthError("Invalid role: " + role)

    clinic = get_clinic(clinic_id)
    if not clinic:
        raise AuthError("Clinic not found")
    if not clinic["is_active"]:
        raise AuthError("Clinic is inactive")

    existing = select("users", "id", email=email, clinic_id=clinic_id)
    if existing:
        raise AuthError("Email already registered in this clinic")

    user_data = {
        "clinic_id": clinic_id,
        "email": email.lower().strip(),
        "password_hash": hash_password(password),
        "full_name": full_name,
        "role": role,
    }

    try:
        user = insert("users", user_data)
    except DBError as e:
        raise AuthError("Failed to create user: " + str(e))

    return _public_user(user)


def _public_user(user):
    """Remove sensitive fields before returning to UI/session"""
    return {
        "id": user["id"],
        "clinic_id": user["clinic_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": user.get("is_active", True),
    }


# ============================================
# Signup flow: create clinic + doctor in one shot
# ============================================
def signup_clinic(
    clinic_name,
    doctor_name,
    email,
    password,
    phone=None,
    plan="starter"
):
    """
    Public signup: creates clinic AND doctor user.
    Returns: (clinic_dict, user_dict)
    """
    if not clinic_name or not doctor_name or not email or not password:
        raise AuthError("All fields are required")

    try:
        clinic = create_clinic(
            name=clinic_name,
            doctor_name=doctor_name,
            email=email,
            phone=phone,
            plan=plan
        )
    except TenantError as e:
        raise AuthError(str(e))

    try:
        user = create_user(
            clinic_id=clinic["id"],
            email=email,
            password=password,
            full_name=doctor_name,
            role="doctor"
        )
    except AuthError as e:
        # Rollback clinic if user creation failed
        from core.db import delete
        try:
            delete("clinics", id=clinic["id"])
        except Exception:
            pass
        raise

    # Audit log
    try:
        from services.audit_log import log_action
        log_action(
            clinic_id=clinic["id"],
            user_id=user["id"],
            action="signup",
            entity_type="clinic",
            entity_id=clinic["id"],
            details={"clinic_name": clinic_name, "plan": plan},
        )
    except Exception:
        pass

    return clinic, user


# ============================================
# Login
# ============================================
def login(email, password, clinic_id=None):
    """
    Authenticate a user.
    If clinic_id is None, search all clinics for this email.
    Returns the public user dict on success.
    """
    if not email or not password:
        raise AuthError("Email and password required")

    email = email.lower().strip()

    if clinic_id:
        rows = select("users", "*", email=email, clinic_id=clinic_id)
    else:
        rows = select("users", "*", email=email)

    if not rows:
        raise AuthError("Invalid email or password")

    # Pick the first matching user (in case email reused across clinics)
    user = rows[0]

    if not verify_password(password, user["password_hash"]):
        raise AuthError("Invalid email or password")

    if not user.get("is_active", True):
        raise AuthError("Account is disabled")

    # Verify clinic is still active
    clinic = get_clinic(user["clinic_id"])
    if not clinic:
        raise AuthError("Clinic not found")
    if not clinic["is_active"]:
        raise AuthError("Clinic is disabled")

    # Update last_login
    try:
        update("users", {"id": user["id"]}, {"last_login": datetime.utcnow().isoformat()})
    except Exception:
        pass

    # Audit log
    try:
        from services.audit_log import log_action
        log_action(
            clinic_id=user["clinic_id"],
            user_id=user["id"],
            action="login",
            entity_type="session",
            details={"email": email, "role": user.get("role")},
        )
    except Exception:
        pass

    return _public_user(user)


def get_user(user_id):
    rows = select("users", "*", id=user_id)
    return _public_user(rows[0]) if rows else None


def list_clinic_users(clinic_id):
    rows = select("users", "*", clinic_id=clinic_id)
    return [_public_user(u) for u in rows]


def change_password(user_id, old_password, new_password):
    rows = select("users", "*", id=user_id)
    if not rows:
        raise AuthError("User not found")
    user = rows[0]
    if not verify_password(old_password, user["password_hash"]):
        raise AuthError("Old password is incorrect")
    new_hash = hash_password(new_password)
    update("users", {"id": user_id}, {"password_hash": new_hash})
    return True


# ============================================
# Permission checks (simple role hierarchy)
# ============================================
ROLE_LEVELS = {"reception": 1, "nurse": 2, "doctor": 3, "admin": 4}


def has_permission(user, required_role):
    if not user:
        return False
    return ROLE_LEVELS.get(user.get("role"), 0) >= ROLE_LEVELS.get(required_role, 99)


def can_manage_users(user):
    return has_permission(user, "admin")


def can_prescribe(user):
    return has_permission(user, "doctor")


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.db import delete

    print("=" * 50)
    print("Auth Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    test_email = "doctor-{}@clinic.com".format(suffix)

    print("\n1. Signup clinic + doctor:")
    clinic, user = signup_clinic(
        clinic_name="Auth Test Clinic " + suffix,
        doctor_name="Dr. Auth",
        email=test_email,
        password="secret123",
        plan="starter"
    )
    print("   Clinic: {} ({})".format(clinic["name"], clinic["id"][:8]))
    print("   User:   {} ({})".format(user["full_name"], user["id"][:8]))

    print("\n2. Login with correct password:")
    u = login(test_email, "secret123")
    print("   OK: {}".format(u["email"]))

    print("\n3. Login with wrong password:")
    try:
        login(test_email, "wrongpass")
        print("   FAIL: should have rejected")
    except AuthError as e:
        print("   OK: {}".format(e))

    print("\n4. Login with unknown email:")
    try:
        login("nobody@nowhere.com", "any")
        print("   FAIL: should have rejected")
    except AuthError as e:
        print("   OK: {}".format(e))

    print("\n5. Add a nurse:")
    nurse = create_user(
        clinic_id=clinic["id"],
        email="nurse-{}@clinic.com".format(suffix),
        password="nurse123",
        full_name="Nurse Test",
        role="nurse"
    )
    print("   OK: {} ({})".format(nurse["full_name"], nurse["role"]))

    print("\n6. Permissions:")
    print("   doctor can prescribe: {}".format(can_prescribe(u)))
    print("   nurse can prescribe:  {}".format(can_prescribe(nurse)))
    print("   doctor can manage:    {}".format(can_manage_users(u)))

    print("\n7. Change password:")
    change_password(u["id"], "secret123", "newsecret456")
    u2 = login(test_email, "newsecret456")
    print("   OK: new password works")

    print("\n8. Duplicate user in same clinic:")
    try:
        create_user(clinic["id"], test_email, "x12345", "Dup", "doctor")
        print("   FAIL: should have rejected")
    except AuthError as e:
        print("   OK: {}".format(e))

    print("\n9. List clinic users:")
    users = list_clinic_users(clinic["id"])
    print("   Total: {}".format(len(users)))
    for usr in users:
        print("     - {} ({})".format(usr["email"], usr["role"]))

    print("\n10. Cleanup:")
    delete("clinics", id=clinic["id"])
    print("    OK: removed clinic and users (cascade)")

    print("\n" + "=" * 50)
    print("Auth module OK")
    print("=" * 50)
