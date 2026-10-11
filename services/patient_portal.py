# -*- coding: utf-8 -*-
"""Patient portal (PWA) services"""
import secrets
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db import db, insert, select, update, DBError


class PortalError(Exception):
    pass


OTP_EXPIRY_MINUTES = 10
SESSION_EXPIRY_DAYS = 7


def normalize_phone(phone):
    import re
    if not phone:
        return None
    digits = re.sub(r"[^0-9]", "", str(phone))
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


# ============================================
# ACCOUNT MANAGEMENT
# ============================================
def get_account_by_phone(phone):
    p = normalize_phone(phone)
    if not p:
        return None
    rows = select("patient_accounts", "*", phone=p)
    return rows[0] if rows else None


def get_or_create_account(clinic_id, patient_id, phone):
    """Get or create patient account"""
    p = normalize_phone(phone)
    if not p:
        raise PortalError("رقم هاتف غير صحيح")

    # 1. Check by patient_id first
    rows = select("patient_accounts", "*", patient_id=patient_id)
    if rows:
        # Update phone if changed
        if rows[0].get("phone") != p:
            update("patient_accounts", {"id": rows[0]["id"]}, {"phone": p})
            rows[0]["phone"] = p
        return rows[0]

    # 2. Check by phone (for uniqueness)
    existing = select("patient_accounts", "*", phone=p)
    if existing:
        raise PortalError(
            "رقم الهاتف مسجل لحامل أخرى. استخدمي رقماً مختلفاً."
        )

    # 3. Create new account
    data = {
        "patient_id": patient_id,
        "clinic_id": clinic_id,
        "phone": p,
        "is_active": True,
    }
    try:
        return insert("patient_accounts", data)
    except DBError as e:
        raise PortalError("فشل الإنشاء: " + str(e))



def generate_otp(phone):
    """Generate OTP for patient login"""
    p = normalize_phone(phone)
    account = get_account_by_phone(p)

    if not account:
        raise PortalError("رقم الهاتف غير مسجل. تواصلي مع العيادة.")

    if not account.get("is_active"):
        raise PortalError("الحساب غير نشط")

    # Generate 6-digit code
    code = str(random.randint(100000, 999999))

    update("patient_accounts", {"id": account["id"]}, {
        "otp_code": code,
        "otp_expires_at": (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
    })

    return code, account


def verify_otp(phone, code):
    """Verify OTP and create session (timezone-safe)"""
    from datetime import timezone

    p = normalize_phone(phone)
    if not p:
        raise PortalError("رقم غير صحيح")

    account = get_account_by_phone(p)
    if not account:
        raise PortalError("رقم غير مسجل")

    stored = str(account.get("otp_code") or "").strip()
    given = str(code or "").strip()

    if not stored:
        raise PortalError("لا يوجد رمز نشط. اطلبي من العيادة إرسال رمز جديد")

    if stored != given:
        raise PortalError("رمز غير صحيح")

    # Check expiry (timezone-safe + Python 3.8 compatible)
    expires_str = account.get("otp_expires_at")
    if expires_str:
        try:
            expires_str = str(expires_str).strip()

            # Truncate fractional seconds to 6 digits (Python 3.8 limit)
            import re as _re
            expires_str = _re.sub(
                r"(\.\d{6})\d+",
                r"\1",
                expires_str
            )

            # Parse
            if expires_str.endswith("Z"):
                expires_str = expires_str[:-1] + "+00:00"

            expires = datetime.fromisoformat(expires_str)

            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            if expires < now:
                raise PortalError("انتهت صلاحية الرمز. اطلبي رمزاً جديداً")

        except PortalError:
            raise
        except Exception as e:
            print("Expiry check warning: {}".format(e))
            # Do NOT block verification on parse errors

    # Create session
    token = secrets.token_urlsafe(32)
    session_data = {
        "account_id": account["id"],
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat(),
    }

    try:
        insert("patient_sessions", session_data)
    except DBError as e:
        raise PortalError("فشل الجلسة: " + str(e))

    # Clear OTP
    update("patient_accounts", {"id": account["id"]}, {
        "otp_code": None,
        "otp_expires_at": None,
        "last_login": datetime.now(timezone.utc).isoformat(),
    })

    return token, account



def get_session(token):
    """Get valid session (timezone-safe)"""
    from datetime import timezone

    if not token:
        return None

    rows = select("patient_sessions", "*", token=token)
    if not rows:
        return None

    session = rows[0]

    # Check expiry (timezone-safe)
    expires_str = session.get("expires_at")
    if expires_str:
        try:
            expires_str = str(expires_str).strip()

            # Fix fractional seconds > 6 digits (Python 3.8 limit)
            import re as _re
            expires_str = _re.sub(r"(\.\d{6})\d+", r"\1", expires_str)

            # Handle Z suffix
            if expires_str.endswith("Z"):
                expires_str = expires_str[:-1] + "+00:00"

            expires = datetime.fromisoformat(expires_str)

            # Ensure timezone aware
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)

            if expires < now:
                return None

        except Exception as e:
            print("get_session expiry check warning: {}".format(e))
            # Do NOT block on parse errors — return session anyway

    return session



def get_patient_from_session(token):
    """Get patient info from session"""
    session = get_session(token)
    if not session:
        return None, None

    accounts = select("patient_accounts", "*", id=session["account_id"])
    if not accounts:
        return None, None

    account = accounts[0]

    patients = select("patients", "*", id=account["patient_id"])
    if not patients:
        return None, None

    clinics = select("clinics", "*", id=account["clinic_id"])
    clinic = clinics[0] if clinics else {}

    return patients[0], clinic


def logout(token):
    """Delete session"""
    try:
        q = db().table("patient_sessions").delete().eq("token", token)
        q.execute()
    except Exception:
        pass


# ============================================
# PATIENT DATA HELPERS
# ============================================
def get_patient_appointments(clinic_id, patient_id, days=30):
    """Get patient's upcoming appointments"""
    try:
        now = datetime.utcnow().isoformat()
        end = (datetime.utcnow() + timedelta(days=days)).isoformat()
        q = (db().table("appointments").select("*")
             .eq("clinic_id", clinic_id)
             .eq("patient_id", patient_id)
             .gte("scheduled_at", now)
             .lte("scheduled_at", end)
             .order("scheduled_at"))
        return q.execute().data
    except Exception:
        return []


def get_patient_prescriptions(clinic_id, patient_id, limit=20):
    try:
        q = (db().table("prescriptions").select("*")
             .eq("clinic_id", clinic_id)
             .eq("patient_id", patient_id)
             .order("issued_at", desc=True)
             .limit(limit))
        return q.execute().data
    except Exception:
        return []


def get_patient_vaccinations(clinic_id, patient_id):
    try:
        q = (db().table("vaccinations").select("*")
             .eq("clinic_id", clinic_id)
             .eq("patient_id", patient_id)
             .order("scheduled_for"))
        return q.execute().data
    except Exception:
        return []


def get_patient_visits(clinic_id, patient_id, limit=10):
    try:
        q = (db().table("visits").select("*")
             .eq("clinic_id", clinic_id)
             .eq("patient_id", patient_id)
             .order("visit_date", desc=True)
             .limit(limit))
        return q.execute().data
    except Exception:
        return []


def get_patient_growth(clinic_id, patient_id):
    try:
        q = (db().table("growth_measurements").select("*")
             .eq("clinic_id", clinic_id)
             .eq("patient_id", patient_id)
             .order("gestational_week"))
        return q.execute().data
    except Exception:
        return []
