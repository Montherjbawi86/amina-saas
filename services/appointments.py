# -*- coding: utf-8 -*-
"""Appointments management"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date

from core.db import db, insert, select, update, DBError


class AppointmentError(Exception):
    pass


STATUS_LABELS = {
    "scheduled": "منتظر",
    "confirmed": "مؤكد",
    "completed": "مكتمل",
    "cancelled": "ملغى",
    "no_show": "لم يحضر",
}

TYPE_LABELS = {
    "routine": "روتينية",
    "ultrasound": "سونار",
    "lab": "تحليل",
    "consultation": "استشارة",
    "emergency": "طارئة",
}


def create_appointment(clinic_id, patient_id, scheduled_at, **kwargs):
    """
    Create appointment.
    scheduled_at: ISO string or datetime
    """
    if not patient_id or not scheduled_at:
        raise AppointmentError("patient_id and scheduled_at required")

    if isinstance(scheduled_at, datetime):
        scheduled_at = scheduled_at.isoformat()

    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "doctor_id": kwargs.get("doctor_id"),
        "scheduled_at": scheduled_at,
        "duration_min": int(kwargs.get("duration_min") or 30),
        "type": kwargs.get("type", "routine"),
        "status": "scheduled",
        "notes": kwargs.get("notes"),
    }

    if data["type"] not in TYPE_LABELS:
        raise AppointmentError("Invalid type: " + data["type"])

    try:
        return insert("appointments", data)
    except DBError as e:
        raise AppointmentError("Failed to create: " + str(e))


def list_appointments(clinic_id, from_date=None, to_date=None, status=None, patient_id=None, limit=200):
    """List appointments with filters"""
    q = db().table("appointments").select("*").eq("clinic_id", clinic_id)

    if from_date:
        if isinstance(from_date, (date, datetime)):
            from_date = from_date.isoformat()
        q = q.gte("scheduled_at", from_date)
    if to_date:
        if isinstance(to_date, (date, datetime)):
            to_date = to_date.isoformat()
        q = q.lte("scheduled_at", to_date)
    if status:
        q = q.eq("status", status)
    if patient_id:
        q = q.eq("patient_id", patient_id)

    return q.order("scheduled_at").limit(limit).execute().data


def get_appointment(clinic_id, appointment_id):
    rows = select("appointments", "*", id=appointment_id, clinic_id=clinic_id)
    return rows[0] if rows else None


def update_appointment(clinic_id, appointment_id, **fields):
    allowed = {"scheduled_at", "duration_min", "type", "status", "notes", "doctor_id"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if isinstance(clean.get("scheduled_at"), datetime):
        clean["scheduled_at"] = clean["scheduled_at"].isoformat()
    if not clean:
        raise AppointmentError("No fields to update")
    return update("appointments", {"id": appointment_id, "clinic_id": clinic_id}, clean)


def delete_appointment(clinic_id, appointment_id):
    q = db().table("appointments").delete().eq("id", appointment_id).eq("clinic_id", clinic_id)
    return q.execute().data


def today_appointments(clinic_id):
    """Get today's appointments"""
    today = date.today()
    return list_appointments(
        clinic_id,
        from_date=datetime.combine(today, datetime.min.time()).isoformat(),
        to_date=datetime.combine(today, datetime.max.time()).isoformat(),
    )


def upcoming_appointments(clinic_id, days=7):
    """Get next N days"""
    now = datetime.now()
    return list_appointments(
        clinic_id,
        from_date=now.isoformat(),
        to_date=(now + timedelta(days=days)).isoformat(),
        status=None,
    )


def count_by_status(clinic_id):
    """Count appointments by status"""
    rows = db().table("appointments").select("status").eq("clinic_id", clinic_id).execute().data
    counts = {k: 0 for k in STATUS_LABELS}
    for r in rows:
        s = r.get("status", "scheduled")
        counts[s] = counts.get(s, 0) + 1
    return counts


def get_patient_appointments(clinic_id, patient_id, limit=20):
    return list_appointments(clinic_id, patient_id=patient_id, limit=limit)


def get_status_color(status):
    return {
        "scheduled": "#3B82F6",
        "confirmed": "#10B981",
        "completed": "#6B7280",
        "cancelled": "#EF4444",
        "no_show": "#F59E0B",
    }.get(status, "#6B7280")


def get_status_icon(status):
    return {
        "scheduled": "🔵",
        "confirmed": "🟢",
        "completed": "✅",
        "cancelled": "🔴",
        "no_show": "🟠",
    }.get(status, "⚪")


def get_type_icon(t):
    return {
        "routine": "📋",
        "ultrasound": "📷",
        "lab": "🔬",
        "consultation": "💬",
        "emergency": "🚨",
    }.get(t, "📋")


# ============================================
# Cached helpers (Streamlit)
# ============================================
def list_appointments_cached(clinic_id, from_iso=None, to_iso=None, status=None):
    try:
        import streamlit as st
    except ImportError:
        return list_appointments(clinic_id, from_date=from_iso, to_date=to_iso, status=status)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid, f, t, s):
        return list_appointments(cid, from_date=f, to_date=t, status=s)

    return _cached(clinic_id, from_iso, to_iso, status)


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from core.auth import create_user
    from services.patients import create_patient
    from core.db import delete as db_delete
    from datetime import timedelta

    print("=" * 50)
    print("Appointments Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Apt Test " + suffix, "Dr. Apt", "apt-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "d-{}@t.com".format(suffix), "secret123", "Dr", "doctor")
    patient = create_patient(clinic["id"], "سارة محمد", "+9647700")

    print("\n1. Create appointment (tomorrow 10 AM):")
    tomorrow = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    a = create_appointment(
        clinic["id"], patient["id"], tomorrow,
        doctor_id=user["id"], duration_min=30, type="routine",
        notes="متابعة دورية"
    )
    print("   OK: {} at {}".format(a["id"][:8], a["scheduled_at"][:16]))

    print("\n2. List tomorrow's appointments:")
    apts = list_appointments(
        clinic["id"],
        from_date=tomorrow.replace(hour=0).isoformat(),
        to_date=tomorrow.replace(hour=23, minute=59).isoformat()
    )
    print("   Total: {}".format(len(apts)))

    print("\n3. Confirm appointment:")
    update_appointment(clinic["id"], a["id"], status="confirmed")
    a2 = get_appointment(clinic["id"], a["id"])
    print("   New status: {} ({})".format(a2["status"], STATUS_LABELS[a2["status"]]))

    print("\n4. Count by status:")
    counts = count_by_status(clinic["id"])
    for k, v in counts.items():
        if v > 0:
            print("   {}: {}".format(STATUS_LABELS[k], v))

    print("\n5. Patient appointments:")
    patient_apts = get_patient_appointments(clinic["id"], patient["id"])
    print("   Total: {}".format(len(patient_apts)))

    print("\n6. Invalid type rejected:")
    try:
        create_appointment(clinic["id"], patient["id"], tomorrow, type="invalid")
        print("   FAIL")
    except AppointmentError as e:
        print("   OK: {}".format(str(e)[:60]))

    print("\n7. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Appointments module OK")
    print("=" * 50)
