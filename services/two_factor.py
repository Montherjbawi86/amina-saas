# -*- coding: utf-8 -*-
"""
Two-Factor Authentication (TOTP) Service
يدعم Google Authenticator, Authy, 1Password
"""
from datetime import datetime
from io import BytesIO
import base64
import secrets
import string

import pyotp
import qrcode

from core.db import db, insert, update, delete


ISSUER_NAME = "أمينة SaaS"


# ============================================
# GENERATE
# ============================================

def generate_secret():
    """Generate a new TOTP secret"""
    return pyotp.random_base32()


def generate_qr_base64(email, secret):
    """
    Generate QR code as base64 PNG.
    Scan with Google Authenticator.
    """
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=email,
        issuer_name=ISSUER_NAME
    )

    qr = qrcode.QRCode(version=1, box_size=8, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return base64.b64encode(buf.getvalue()).decode("ascii"), uri


def generate_backup_codes(count=10):
    """Generate N backup codes (XXXX-XXXX format)"""
    codes = []
    for _ in range(count):
        part1 = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        part2 = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        codes.append("{}-{}".format(part1, part2))
    return codes


# ============================================
# ENABLE / DISABLE
# ============================================

def setup_2fa(user_id, clinic_id, email):
    """
    Initialize 2FA (does NOT enable yet).
    Returns: {secret, qr_base64, uri}
    """
    secret = generate_secret()
    qr_b64, uri = generate_qr_base64(email, secret)

    # Upsert row (disabled by default)
    existing = get_user_2fa(user_id)
    if existing:
        update("user_2fa", {"user_id": user_id}, {
            "secret": secret,
            "is_enabled": False,
            "backup_codes": [],
            "backup_codes_used": [],
            "updated_at": datetime.utcnow().isoformat(),
        })
    else:
        insert("user_2fa", {
            "user_id": user_id,
            "clinic_id": clinic_id,
            "secret": secret,
            "is_enabled": False,
            "backup_codes": [],
            "backup_codes_used": [],
        })

    return {
        "secret": secret,
        "qr_base64": qr_b64,
        "uri": uri,
    }


def enable_2fa(user_id, verification_code):
    """
    Verify the code and enable 2FA.
    Generates 10 backup codes.
    Returns: {backup_codes: [...]} on success, raises on failure.
    """
    row = get_user_2fa(user_id)
    if not row:
        raise ValueError("لم يتم إعداد 2FA بعد — اضغط 'بدء الإعداد' أولاً")

    secret = row["secret"]
    if not verify_totp_code(secret, verification_code):
        raise ValueError("الرمز غير صحيح — تأكد من الوقت في جهازك وحاول مرة أخرى")

    backup_codes = generate_backup_codes(10)

    update("user_2fa", {"user_id": user_id}, {
        "is_enabled": True,
        "backup_codes": backup_codes,
        "backup_codes_used": [],
        "enabled_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    })

    return {"backup_codes": backup_codes}


def disable_2fa(user_id):
    """Disable 2FA for a user"""
    row = get_user_2fa(user_id)
    if not row:
        return False

    update("user_2fa", {"user_id": user_id}, {
        "is_enabled": False,
        "secret": generate_secret(),  # rotate secret
        "backup_codes": [],
        "backup_codes_used": [],
        "updated_at": datetime.utcnow().isoformat(),
    })
    return True


# ============================================
# VERIFY
# ============================================

def verify_totp_code(secret, code):
    """Verify a 6-digit TOTP code"""
    if not secret or not code:
        return False
    code = str(code).strip().replace(" ", "")
    if not code.isdigit():
        return False
    try:
        totp = pyotp.TOTP(secret)
        # valid_window=1 allows ±30 seconds drift
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def verify_backup_code(user_id, code):
    """
    Verify and consume a backup code.
    Returns True if valid (and marks as used).
    """
    row = get_user_2fa(user_id)
    if not row:
        return False

    code = str(code).strip().upper()
    codes = row.get("backup_codes") or []
    used = row.get("backup_codes_used") or []

    if code not in codes:
        return False

    # Check not already used
    if code in used:
        return False

    # Mark as used
    used.append(code)
    update("user_2fa", {"user_id": user_id}, {
        "backup_codes_used": used,
        "last_used_at": datetime.utcnow().isoformat(),
    })
    return True


def verify_any_code(user_id, code):
    """
    Verify a code — either TOTP (6 digits) or backup code.
    Returns: (is_valid, method) — method = "totp" | "backup" | None
    """
    row = get_user_2fa(user_id)
    if not row or not row.get("is_enabled"):
        return True, "none"  # 2FA not enabled, allow

    code = str(code).strip().upper()

    # If 6 digits → TOTP
    if code.isdigit() and len(code) == 6:
        if verify_totp_code(row["secret"], code):
            update("user_2fa", {"user_id": user_id}, {
                "last_used_at": datetime.utcnow().isoformat(),
            })
            return True, "totp"

    # Try as backup code
    if verify_backup_code(user_id, code):
        return True, "backup"

    return False, None


# ============================================
# GET / STATUS
# ============================================

def get_user_2fa(user_id):
    """Get user's 2FA row (may be None)"""
    try:
        rows = (
            db().table("user_2fa")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception as e:
        print("[2FA] get error: {}".format(e))
        return None


def is_2fa_enabled(user_id):
    """Check if user has 2FA enabled"""
    row = get_user_2fa(user_id)
    return bool(row and row.get("is_enabled"))


def get_remaining_backup_codes(user_id):
    """Count of unused backup codes"""
    row = get_user_2fa(user_id)
    if not row:
        return 0
    total = len(row.get("backup_codes") or [])
    used = len(row.get("backup_codes_used") or [])
    return total - used


def regenerate_backup_codes(user_id):
    """Generate new set of backup codes"""
    row = get_user_2fa(user_id)
    if not row or not row.get("is_enabled"):
        raise ValueError("2FA غير مفعّل")

    codes = generate_backup_codes(10)
    update("user_2fa", {"user_id": user_id}, {
        "backup_codes": codes,
        "backup_codes_used": [],
        "updated_at": datetime.utcnow().isoformat(),
    })
    return codes


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Two-Factor Auth Service Test")
    print("=" * 60)

    # Generate secret
    secret = generate_secret()
    print("\n1. Secret generated: {}...".format(secret[:16]))

    # Generate QR
    qr_b64, uri = generate_qr_base64("test@clinic.com", secret)
    print("2. QR code generated: {} chars (base64)".format(len(qr_b64)))
    print("3. OTP URI: {}...".format(uri[:60]))

    # Verify with correct code
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    print("\n4. Current code: {}".format(current_code))
    print("   Verify correct: {}".format(verify_totp_code(secret, current_code)))
    print("   Verify wrong:   {}".format(verify_totp_code(secret, "000000")))

    # Backup codes
    codes = generate_backup_codes(3)
    print("\n5. Backup codes sample:")
    for c in codes:
        print("   - {}".format(c))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
