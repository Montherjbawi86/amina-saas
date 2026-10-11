# -*- coding: utf-8 -*-
"""Prescriptions management"""
from typing import Dict, List, Optional
from datetime import datetime, date

from core.db import db, insert, select, update, DBError


class PrescriptionError(Exception):
    pass


# Common medications (Arabic)
COMMON_MEDICATIONS = [
    "حمض الفوليك 5mg",
    "حديد 65mg",
    "كالسيوم 500mg",
    "فيتامين D 1000IU",
    "باراسيتامول 500mg",
    "أوميبرازول 20mg",
    "ميتفورمين 500mg",
    "أسبرين 75mg",
    "بروجستيرون 200mg",
    "أموكسيسيلين 500mg",
]


def create_prescription(clinic_id, patient_id, doctor_id, medications, **kwargs):
    """
    Create a prescription.
    medications: list of dicts {name, dose, frequency, duration, notes}
    """
    if not patient_id or not doctor_id:
        raise PrescriptionError("patient_id and doctor_id required")
    if not medications or not isinstance(medications, list):
        raise PrescriptionError("At least one medication required")

    # Validate each medication
    for med in medications:
        if not isinstance(med, dict) or not med.get("name"):
            raise PrescriptionError("Each medication must have a name")

    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "visit_id": kwargs.get("visit_id"),
        "diagnosis": kwargs.get("diagnosis"),
        "medications": medications,
        "instructions": kwargs.get("instructions"),
        "follow_up_days": kwargs.get("follow_up_days"),
        "notes": kwargs.get("notes"),
    }

    try:
        return insert("prescriptions", data)
    except DBError as e:
        raise PrescriptionError("Failed to create: " + str(e))


def get_prescription(clinic_id, prescription_id):
    rows = select("prescriptions", "*", id=prescription_id, clinic_id=clinic_id)
    return rows[0] if rows else None


def list_prescriptions(clinic_id, patient_id=None, limit=50):
    q = db().table("prescriptions").select("*").eq("clinic_id", clinic_id)
    if patient_id:
        q = q.eq("patient_id", patient_id)
    return q.order("issued_at", desc=True).limit(limit).execute().data


def update_prescription(clinic_id, prescription_id, **fields):
    allowed = {"diagnosis", "medications", "instructions", "follow_up_days", "notes"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise PrescriptionError("No fields to update")
    return update("prescriptions", {"id": prescription_id, "clinic_id": clinic_id}, clean)


def delete_prescription(clinic_id, prescription_id):
    q = db().table("prescriptions").delete().eq("id", prescription_id).eq("clinic_id", clinic_id)
    return q.execute().data


def count_prescriptions(clinic_id, patient_id=None):
    q = db().table("prescriptions").select("id", count="exact").eq("clinic_id", clinic_id)
    if patient_id:
        q = q.eq("patient_id", patient_id)
    return q.execute().count or 0


# ============================================
# Cached helpers
# ============================================
def list_prescriptions_cached(clinic_id, patient_id=None):
    try:
        import streamlit as st
    except ImportError:
        return list_prescriptions(clinic_id, patient_id=patient_id)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid, pid):
        return list_prescriptions(cid, patient_id=pid)

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
    print("Prescriptions Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Presc Test " + suffix, "Dr. P", "p-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "d-{}@t.com".format(suffix), "secret123", "Dr", "doctor")
    patient = create_patient(clinic["id"], "سارة محمد", "+9647700")

    print("\n1. Create prescription:")
    rx = create_prescription(
        clinic["id"], patient["id"], user["id"],
        medications=[
            {"name": "حمض الفوليك 5mg", "dose": "1 قرص", "frequency": "يومياً", "duration": "3 أشهر"},
            {"name": "حديد 65mg", "dose": "1 قرص", "frequency": "مرتين يومياً", "duration": "شهرين"},
        ],
        diagnosis="فقر دم خفيف مع حمل",
        instructions="يُؤخذ مع الطعام",
        follow_up_days=30,
    )
    print("   OK: {}".format(rx["id"][:8]))

    print("\n2. List patient prescriptions:")
    rxs = list_prescriptions(clinic["id"], patient_id=patient["id"])
    print("   Total: {}".format(len(rxs)))
    for r in rxs:
        print("   - {} medications | diagnosis: {}".format(
            len(r["medications"]), r.get("diagnosis", "—")))

    print("\n3. Count:")
    print("   {}".format(count_prescriptions(clinic["id"], patient["id"])))

    print("\n4. Validation - empty medications:")
    try:
        create_prescription(clinic["id"], patient["id"], user["id"], medications=[])
        print("   FAIL")
    except PrescriptionError as e:
        print("   OK: {}".format(str(e)[:60]))

    print("\n5. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Prescriptions module OK")
    print("=" * 50)
