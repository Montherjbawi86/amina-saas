# -*- coding: utf-8 -*-
"""Vaccinations management"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from core.db import db, insert, select, update, DBError


class VaccinationError(Exception):
    pass


# Standard pregnancy vaccination schedule (by gestational week)
DEFAULT_SCHEDULE = [
    {"name": "Tdap (كزاز + دفتيريا + سعال ديكي)", "week": 27, "dose": 1},
    {"name": "Influenza (إنفلونزا)", "week": 14, "dose": 1},
]


def create_vaccination(clinic_id, patient_id, vaccine_name, **kwargs):
    if not patient_id or not vaccine_name:
        raise VaccinationError("patient_id and vaccine_name required")

    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "doctor_id": kwargs.get("doctor_id"),
        "vaccine_name": vaccine_name,
        "dose_number": int(kwargs.get("dose_number") or 1),
        "given_at": kwargs.get("given_at"),
        "scheduled_for": kwargs.get("scheduled_for"),
        "status": kwargs.get("status", "pending"),
        "batch_number": kwargs.get("batch_number"),
        "site": kwargs.get("site"),
        "notes": kwargs.get("notes"),
    }

    if data["status"] not in ("pending", "given", "missed", "skipped"):
        raise VaccinationError("Invalid status")

    try:
        return insert("vaccinations", data)
    except DBError as e:
        raise VaccinationError("Failed: " + str(e))


def list_vaccinations(clinic_id, patient_id=None, status=None, limit=100):
    q = db().table("vaccinations").select("*").eq("clinic_id", clinic_id)
    if patient_id:
        q = q.eq("patient_id", patient_id)
    if status:
        q = q.eq("status", status)
    return q.order("scheduled_for").limit(limit).execute().data


def update_vaccination(clinic_id, vaccination_id, **fields):
    allowed = {"vaccine_name", "dose_number", "given_at", "scheduled_for",
               "status", "batch_number", "site", "notes"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise VaccinationError("No fields to update")
    return update("vaccinations", {"id": vaccination_id, "clinic_id": clinic_id}, clean)


def delete_vaccination(clinic_id, vaccination_id):
    q = db().table("vaccinations").delete().eq("id", vaccination_id).eq("clinic_id", clinic_id)
    return q.execute().data


def mark_given(clinic_id, vaccination_id, batch_number=None, site=None):
    """Mark vaccine as given today"""
    return update_vaccination(
        clinic_id, vaccination_id,
        status="given",
        given_at=date.today().isoformat(),
        batch_number=batch_number,
        site=site,
    )


def auto_schedule_defaults(clinic_id, patient_id, edd_date, doctor_id=None):
    """
    Auto-create pending vaccinations based on EDD.
    edd_date: ISO string YYYY-MM-DD
    """
    try:
        edd = datetime.strptime(edd_date[:10], "%Y-%m-%d").date()
    except Exception:
        raise VaccinationError("Invalid EDD date")

    existing = list_vaccinations(clinic_id, patient_id=patient_id)
    existing_names = {v["vaccine_name"] for v in existing}

    created = []
    for item in DEFAULT_SCHEDULE:
        if item["name"] in existing_names:
            continue
        # Compute date: 280 - (week * 7) days before EDD
        days_before = 280 - (item["week"] * 7)
        scheduled = edd - timedelta(days=days_before)
        try:
            v = create_vaccination(
                clinic_id, patient_id, item["name"],
                dose_number=item["dose"],
                scheduled_for=scheduled.isoformat(),
                status="pending",
                doctor_id=doctor_id,
            )
            created.append(v)
        except VaccinationError:
            pass
    return created


def get_upcoming(clinic_id, days=14):
    """Upcoming vaccinations in next N days"""
    today = date.today()
    end = today + timedelta(days=days)
    q = (db().table("vaccinations").select("*")
         .eq("clinic_id", clinic_id)
         .eq("status", "pending")
         .gte("scheduled_for", today.isoformat())
         .lte("scheduled_for", end.isoformat())
         .order("scheduled_for"))
    return q.execute().data


def get_status_color(status):
    return {
        "pending": "#F59E0B",
        "given": "#10B981",
        "missed": "#EF4444",
        "skipped": "#6B7280",
    }.get(status, "#6B7280")


def get_status_label(status):
    return {
        "pending": "⏳ منتظرة",
        "given": "✅ تم إعطاؤها",
        "missed": "❌ فائتة",
        "skipped": "⏭️ متجاوزة",
    }.get(status, status)


# Cached helpers
def list_vaccinations_cached(clinic_id, patient_id=None):
    try:
        import streamlit as st
    except ImportError:
        return list_vaccinations(clinic_id, patient_id=patient_id)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid, pid):
        return list_vaccinations(cid, patient_id=pid)

    return _cached(clinic_id, patient_id)


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from core.auth import create_user
    from services.patients import create_patient
    from core.db import delete as db_delete

    print("=" * 50)
    print("Vaccinations Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Vacc Test " + suffix, "Dr. V", "v-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "d-{}@t.com".format(suffix), "secret123", "Dr", "doctor")
    # EDD 3 months from now
    edd = (date.today() + timedelta(days=90)).isoformat()
    patient = create_patient(clinic["id"], "زينب علي", "+9647700", edd=edd)

    print("\n1. Create manual vaccination:")
    v = create_vaccination(
        clinic["id"], patient["id"], "Tdap",
        dose_number=1, scheduled_for=date.today().isoformat(),
        status="pending", doctor_id=user["id"]
    )
    print("   OK: {}".format(v["id"][:8]))

    print("\n2. Mark as given:")
    mark_given(clinic["id"], v["id"], batch_number="ABC123", site="ذراع أيسر")
    v2 = select("vaccinations", "*", id=v["id"])[0]
    print("   Status: {} | Batch: {}".format(v2["status"], v2.get("batch_number")))

    print("\n3. Auto-schedule defaults:")
    scheduled = auto_schedule_defaults(clinic["id"], patient["id"], edd, user["id"])
    print("   Created: {}".format(len(scheduled)))
    for s in scheduled:
        print("   - {} on {}".format(s["vaccine_name"][:40], s["scheduled_for"]))

    print("\n4. List all:")
    all_v = list_vaccinations(clinic["id"], patient_id=patient["id"])
    print("   Total: {}".format(len(all_v)))
    for v in all_v:
        print("   - [{}] {}".format(v["status"], v["vaccine_name"][:40]))

    print("\n5. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Vaccinations module OK")
    print("=" * 50)
