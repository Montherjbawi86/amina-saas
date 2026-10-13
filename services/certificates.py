# -*- coding: utf-8 -*-
"""
Certificates Service
CRUD + snapshot for pregnancy certificates
"""
from datetime import datetime, date
from typing import Optional, Dict, Any

from core.db import db, insert, select


def create_certificate(clinic_id, patient_id, issued_by, snapshot):
    """
    Save certificate to DB.
    Returns certificate row.
    """
    try:
        row = {
            "clinic_id": clinic_id,
            "patient_id": patient_id,
            "issued_by": issued_by,
            "issued_at": datetime.utcnow().isoformat(),
            "snapshot": snapshot,
            "is_active": True,
        }
        result = insert("certificates", row)
        return result
    except Exception as e:
        print("[Certificates] create error: {}".format(e))
        return None


def get_certificate(cert_id):
    """Fetch certificate by ID (for public verification)"""
    try:
        rows = (
            db().table("certificates")
            .select("*")
            .eq("id", cert_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception as e:
        print("[Certificates] get error: {}".format(e))
        return None


def list_clinic_certificates(clinic_id, limit=100):
    """List recent certificates for a clinic"""
    try:
        return (
            db().table("certificates")
            .select("id, patient_id, issued_at, is_active")
            .eq("clinic_id", clinic_id)
            .order("issued_at", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )
    except Exception:
        return []


def build_snapshot(patient, visits, clinic, doctor_name, certificate_id=None):
    """
    Build a self-contained snapshot dict for the certificate.
    Contains all data needed to render the verification page later.
    """
    import uuid

    lmp = patient.get("lmp")
    weeks, days = _calc_gestational(lmp)

    last_visit = visits[0] if visits else {}

    return {
        "certificate_id": certificate_id or str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
        "clinic": {
            "id": clinic.get("id"),
            "name": clinic.get("name"),
            "phone": clinic.get("phone"),
        },
        "doctor": {
            "name": doctor_name or "",
        },
        "patient": {
            "id": patient.get("id"),
            "full_name": patient.get("full_name"),
            "phone": patient.get("phone"),
            "national_id": patient.get("national_id"),
            "date_of_birth": _safe_str(patient.get("date_of_birth")),
            "blood_type": patient.get("blood_type"),
            "risk_level": patient.get("risk_level"),
        },
        "pregnancy": {
            "lmp": _safe_str(lmp),
            "edd": _safe_str(patient.get("edd")),
            "gravida": patient.get("gravida"),
            "para": patient.get("para"),
            "gestational_weeks": weeks,
            "gestational_days": days,
        },
        "visits": {
            "count": len(visits),
            "last_visit_date": _safe_str(last_visit.get("visit_date")) if last_visit else None,
        },
        "notes": patient.get("notes") or "",
    }


def _calc_gestational(lmp):
    """Returns (weeks, days) from LMP to today"""
    if not lmp:
        return None, None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        elif isinstance(lmp, date):
            lmp_d = lmp
        else:
            return None, None
        days = (date.today() - lmp_d).days
        if days < 0:
            return None, None
        return days // 7, days % 7
    except Exception:
        return None, None


def _safe_str(v):
    if v is None:
        return None
    try:
        if isinstance(v, str):
            return v[:10] if len(v) > 10 else v
        if isinstance(v, (datetime, date)):
            return v.strftime("%Y-%m-%d")
        return str(v)
    except Exception:
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("Certificates Service Test")
    print("=" * 50)

    from core.db import db

    try:
        clinics = db().table("clinics").select("id, name").limit(1).execute().data
        if not clinics:
            print("❌ لا توجد عيادات")
            exit(1)

        clinic = clinics[0]
        print("✅ العيادة: {}".format(clinic["name"]))

        patients = db().table("patients").select("*").eq("clinic_id", clinic["id"]).limit(1).execute().data
        if not patients:
            print("⚠️ لا يوجد حوامل — استخدم بيانات وهمية")
            patient = {
                "id": "test-patient-id",
                "full_name": "اختبار",
                "phone": "+964...",
                "lmp": "2026-08-04",
                "edd": "2027-05-11",
            }
        else:
            patient = patients[0]
            print("✅ الحامل: {}".format(patient.get("full_name")))

        snapshot = build_snapshot(patient, [], clinic, "د. اختبار")
        print("✅ Snapshot build: OK")
        print("   weeks: {}".format(snapshot["pregnancy"]["gestational_weeks"]))

    except Exception as e:
        print("❌ {}".format(e))
