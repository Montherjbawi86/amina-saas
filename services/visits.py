"""Medical visits management"""
from typing import Dict, List, Optional
from datetime import datetime

from core.db import db, insert, select, DBError


class VisitError(Exception):
    pass


def create_visit(clinic_id, patient_id, doctor_id, **fields):
    """Create a new medical visit"""
    if not patient_id or not doctor_id:
        raise VisitError("patient_id and doctor_id are required")

    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "visit_date": fields.get("visit_date") or datetime.utcnow().isoformat(),
        "gestational_age_weeks": fields.get("gestational_age_weeks"),
        "weight_kg": fields.get("weight_kg"),
        "bp_systolic": fields.get("bp_systolic"),
        "bp_diastolic": fields.get("bp_diastolic"),
        "fundal_height_cm": fields.get("fundal_height_cm"),
        "fetal_heart_rate": fields.get("fetal_heart_rate"),
        "notes": fields.get("notes"),
    }

    # Clean None values
    data = {k: v for k, v in data.items() if v is not None or k in ("clinic_id", "patient_id", "doctor_id", "visit_date")}

    # Basic validation
    _validate_visit(data)

    try:
        return insert("visits", data)
    except DBError as e:
        raise VisitError("Failed to create visit: " + str(e))


def _validate_visit(data):
    """Validate medical values"""
    if data.get("bp_systolic") and (data["bp_systolic"] < 50 or data["bp_systolic"] > 250):
        raise VisitError("Systolic BP must be 50-250")
    if data.get("bp_diastolic") and (data["bp_diastolic"] < 30 or data["bp_diastolic"] > 150):
        raise VisitError("Diastolic BP must be 30-150")
    if data.get("weight_kg") and (data["weight_kg"] < 30 or data["weight_kg"] > 200):
        raise VisitError("Weight must be 30-200 kg")
    if data.get("fetal_heart_rate") and (data["fetal_heart_rate"] < 60 or data["fetal_heart_rate"] > 220):
        raise VisitError("Fetal heart rate must be 60-220 bpm")
    if data.get("fundal_height_cm") and (data["fundal_height_cm"] < 5 or data["fundal_height_cm"] > 60):
        raise VisitError("Fundal height must be 5-60 cm")


def list_visits(clinic_id, patient_id, limit=50):
    """List all visits for a patient, newest first"""
    return (
        db().table("visits")
        .select("*")
        .eq("clinic_id", clinic_id)
        .eq("patient_id", patient_id)
        .order("visit_date", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def get_visit(clinic_id, visit_id):
    rows = select("visits", "*", id=visit_id, clinic_id=clinic_id)
    return rows[0] if rows else None


def delete_visit(clinic_id, visit_id):
    q = db().table("visits").delete().eq("id", visit_id).eq("clinic_id", clinic_id)
    return q.execute().data


def count_visits(clinic_id, patient_id):
    r = (
        db().table("visits")
        .select("id", count="exact")
        .eq("clinic_id", clinic_id)
        .eq("patient_id", patient_id)
        .execute()
    )
    return r.count or 0


def get_latest_visit(clinic_id, patient_id):
    rows = list_visits(clinic_id, patient_id, limit=1)
    return rows[0] if rows else None


# ============================================
# Health analysis
# ============================================
def analyze_bp(systolic, diastolic):
    """Classify blood pressure"""
    if not systolic or not diastolic:
        return None
    if systolic >= 140 or diastolic >= 90:
        return {"level": "high", "label": "🔴 مرتفع", "warning": "قد يشير لتسمم الحمل"}
    if systolic >= 130 or diastolic >= 85:
        return {"level": "elevated", "label": "🟡 مرتفع قليلاً", "warning": None}
    if systolic < 90 or diastolic < 60:
        return {"level": "low", "label": "🟠 منخفض", "warning": "قد يشير لفقر دم أو جفاف"}
    return {"level": "normal", "label": "🟢 طبيعي", "warning": None}


def analyze_fhr(bpm):
    """Fetal heart rate analysis"""
    if not bpm:
        return None
    if bpm < 110:
        return {"level": "low", "label": "🔴 منخفض (تباطؤ)"}
    if bpm > 160:
        return {"level": "high", "label": "🔴 مرتفع (تسارع)"}
    return {"level": "normal", "label": "🟢 طبيعي (110-160)"}


def calculate_bmi(weight_kg, height_cm=None):
    """Calculate BMI if height available (default 160cm for demo)"""
    if not weight_kg:
        return None
    h = (height_cm or 160) / 100.0
    return round(weight_kg / (h * h), 1)


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from datetime import date, timedelta
    from core.tenant import create_clinic
    from core.auth import create_user
    from services.patients import create_patient
    from core.db import delete as db_delete

    print("=" * 50)
    print("Visits Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Visits Test " + suffix, "Dr. Test", "vt-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "doc-{}@t.com".format(suffix), "secret123", "Dr. V", "doctor")

    lmp = (date.today() - timedelta(days=120)).isoformat()
    patient = create_patient(clinic["id"], "سارة محمد", "+9647700", lmp=lmp)
    print("\nClinic + Patient created")

    print("\n1. Create visit:")
    v = create_visit(
        clinic["id"], patient["id"], user["id"],
        weight_kg=68.5,
        bp_systolic=120, bp_diastolic=80,
        fetal_heart_rate=145,
        fundal_height_cm=22,
        notes="زيارة روتينية"
    )
    print("   OK: {}".format(v["id"][:8]))

    print("\n2. List visits:")
    visits = list_visits(clinic["id"], patient["id"])
    print("   Total: {}".format(len(visits)))

    print("\n3. Add second visit:")
    v2 = create_visit(
        clinic["id"], patient["id"], user["id"],
        weight_kg=70.0,
        bp_systolic=145, bp_diastolic=95,
        fetal_heart_rate=155
    )
    print("   OK")

    print("\n4. Latest visit:")
    latest = get_latest_visit(clinic["id"], patient["id"])
    print("   Weight: {}, BP: {}/{}".format(
        latest["weight_kg"], latest["bp_systolic"], latest["bp_diastolic"]))

    print("\n5. Analyze BP (145/95):")
    bp = analyze_bp(145, 95)
    print("   {} - {}".format(bp["label"], bp.get("warning")))

    print("\n6. Analyze FHR (155):")
    fhr = analyze_fhr(155)
    print("   {}".format(fhr["label"]))

    print("\n7. Validate bad BP:")
    try:
        create_visit(clinic["id"], patient["id"], user["id"], bp_systolic=500, bp_diastolic=80)
        print("   FAIL: should reject")
    except VisitError as e:
        print("   OK: {}".format(e))

    print("\n8. Count visits:")
    print("   {}".format(count_visits(clinic["id"], patient["id"])))

    print("\n9. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Visits module OK")
    print("=" * 50)


# ============================================
# Cached helpers (Streamlit)
# ============================================
def list_visits_cached(clinic_id, patient_id, limit=50):
    """Cached version of list_visits"""
    try:
        import streamlit as st
    except ImportError:
        return list_visits(clinic_id, patient_id, limit=limit)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid, pid, lim):
        return list_visits(cid, pid, limit=lim)

    return _cached(clinic_id, patient_id, limit)
