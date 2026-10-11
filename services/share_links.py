# -*- coding: utf-8 -*-
"""Public share links for prescriptions, reports, etc."""
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db import db, insert, select, update, DBError


class ShareError(Exception):
    pass


DEFAULT_EXPIRY_DAYS = 30


def create_share_link(clinic_id, patient_id, resource_type, resource_id, expiry_days=DEFAULT_EXPIRY_DAYS):
    """Create a unique share token"""
    if resource_type not in ("prescription", "report", "visit"):
        raise ShareError("Invalid resource type")

    # Generate short token (URL-safe)
    token = secrets.token_urlsafe(16)

    data = {
        "token": token,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "expires_at": (datetime.utcnow() + timedelta(days=expiry_days)).isoformat(),
    }

    try:
        return insert("share_links", data)
    except DBError as e:
        raise ShareError("Failed: " + str(e))


def get_share_link(token):
    """Fetch a share link by token"""
    rows = select("share_links", "*", token=token)
    if not rows:
        return None
    link = rows[0]

    # Check expiry
    try:
        expires = datetime.fromisoformat(link["expires_at"].replace("Z", ""))
        if expires < datetime.utcnow():
            return None
    except Exception:
        pass

    return link


def increment_view(token):
    """Increment view count"""
    rows = select("share_links", "id,view_count", token=token)
    if not rows:
        return
    link = rows[0]
    try:
        update("share_links", {"id": link["id"]}, {
            "view_count": (link.get("view_count") or 0) + 1,
            "last_viewed_at": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass


def build_public_url(base_url, token):
    """Build the public URL"""
    base = base_url.rstrip("/")
    return "{}/?rx={}".format(base, token)
