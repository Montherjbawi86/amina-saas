"""Patient (pregnant woman) management"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date

from core.db import db, insert, select, update, delete, DBError


class PatientError(Exception):
    pass


def calculate_edd(lmp_date):
    """
    Naegele's rule: EDD = LMP + 280 days
    lmp_date: str 'YYYY-MM-DD' or date object
    Returns: str 'YYYY-MM-DD'
    """
    if not lmp_date:
        return None
    if isinstance(lmp_date, str):
        lmp = datetime.strptime(lmp_date, "%Y-%m-%d").date()
    else:
        lmp = lmp_date
    edd = lmp + timedelta(days=280)
    return edd.isoformat()


def calculate_gestational_age(lmp_date, on_date=None):
    """
    Returns (weeks, days) since LMP.
    """
    if not lmp_date:
        return (0, 0)
    if isinstance(lmp_date, str):
        lmp = datetime.strptime(lmp_date, "%Y-%m-%d").date()
    else:
        lmp = lmp_date
    ref = on_date or date.today()
    delta = (ref - lmp).days
    if delta < 0:
        return (0, 0)
    return (delta // 7, delta % 7)


def create_patient(clinic_id, full_name, phone, **kwargs):
    """Create a new pregnant patient"""
    if not full_name or not phone:
        raise PatientError("الاسم والهاتف مطلوبان")

    # Check plan limit
    from core.tenant import can_add_patient
    if not can_add_patient(clinic_id):
        raise PatientError("وصلتِ للحد الأقصى من الحوامل في باقتك الحالية")

    lmp = kwargs.get("lmp")
    edd = kwargs.get("edd") or calculate_edd(lmp)

    data = {
        "clinic_id": clinic_id,
        "full_name": full_name.strip(),
        "phone": phone.strip(),
        "national_id": kwargs.get("national_id"),
        "date_of_birth": kwargs.get("date_of_birth"),
        "blood_type": kwargs.get("blood_type"),
        "lmp": lmp,
        "edd": edd,
        "gravida": int(kwargs.get("gravida") or 0),
        "para": int(kwargs.get("para") or 0),
        "risk_level": kwargs.get("risk_level", "low"),
        "notes": kwargs.get("notes"),
    }

    try:
        return insert("patients", data)
    except DBError as e:
        raise PatientError("فشل إنشاء الملف: " + str(e))


def get_patient(clinic_id, patient_id):
    rows = select("patients", "*", id=patient_id, clinic_id=clinic_id)
    return rows[0] if rows else None


def list_patients(clinic_id, search=None, risk_level=None, active_only=True):
    """List patients for a clinic with optional filters"""
    q = db().table("patients").select("*").eq("clinic_id", clinic_id)
    if active_only:
        q = q.eq("is_active", True)
    if risk_level:
        q = q.eq("risk_level", risk_level)
    if search:
        q = q.ilike("full_name", "%{}%".format(search))
    return q.order("created_at", desc=True).execute().data


def update_patient(clinic_id, patient_id, **fields):
    allowed = {
        "full_name", "phone", "national_id", "date_of_birth", "blood_type",
        "lmp", "edd", "gravida", "para", "risk_level", "notes", "is_active"
    }
    clean = {k: v for k, v in fields.items() if k in allowed}

    # Recompute EDD if LMP changed
    if "lmp" in clean and "edd" not in clean:
        clean["edd"] = calculate_edd(clean["lmp"])

    if not clean:
        raise PatientError("لا توجد حقول للتحديث")

    return update("patients", {"id": patient_id, "clinic_id": clinic_id}, clean)


def delete_patient(clinic_id, patient_id):
    """Soft delete"""
    return update("patients", {"id": patient_id, "clinic_id": clinic_id}, {"is_active": False})


def count_patients(clinic_id):
    r = (
        db().table("patients")
        .select("id", count="exact")
        .eq("clinic_id", clinic_id)
        .eq("is_active", True)
        .execute()
    )
    return r.count or 0


def get_risk_color(risk_level):
    return {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
    }.get(risk_level, "⚪")


def get_patient_summary(clinic_id, patient_id):
    """Full summary with gestational age computed"""
    p = get_patient(clinic_id, patient_id)
    if not p:
        return None

    weeks, days = calculate_gestational_age(p.get("lmp"))
    p["gestational_weeks"] = weeks
    p["gestational_days"] = days
    p["gestational_display"] = "{} أسبوع + {} يوم".format(weeks, days) if weeks else "-"
    p["risk_icon"] = get_risk_color(p.get("risk_level"))
    return p


if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from core.db import delete as db_delete

    print("=" * 50)
    print("Patients Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic(
        "Patients Test " + suffix, "Dr. Test",
        "pt-{}@test.com".format(suffix)
    )
    print("\nClinic: {}".format(clinic["id"][:8]))

    print("\n1. Create patient (LMP = 100 days ago):")
    from datetime import date, timedelta
    lmp = (date.today() - timedelta(days=100)).isoformat()
    p = create_patient(
        clinic["id"],
        "فاطمة أحمد",
        "+9647701234567",
        lmp=lmp,
        blood_type="O+",
        gravida=2,
        para=1,
        risk_level="low"
    )
    print("   OK: {} ({})".format(p["full_name"], p["id"][:8]))
    print("   LMP: {} -> EDD: {}".format(p["lmp"], p["edd"]))

    print("\n2. Gestational age:")
    summary = get_patient_summary(clinic["id"], p["id"])
    print("   {}".format(summary["gestational_display"]))

    print("\n3. List patients:")
    patients = list_patients(clinic["id"])
    print("   Total: {}".format(len(patients)))

    print("\n4. Search by name:")
    found = list_patients(clinic["id"], search="فاطمة")
    print("   Found: {}".format(len(found)))

    print("\n5. Update risk level:")
    update_patient(clinic["id"], p["id"], risk_level="high")
    p2 = get_patient(clinic["id"], p["id"])
    print("   New risk: {}".format(p2["risk_level"]))

    print("\n6. Count:")
    print("   {}".format(count_patients(clinic["id"])))

    print("\n7. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Patients module OK")
    print("=" * 50)


# ============================================
# Cached helpers (Streamlit)
# ============================================
def list_patients_cached(clinic_id, search=None, risk_level=None, active_only=True):
    """Cached version of list_patients"""
    try:
        import streamlit as st
    except ImportError:
        return list_patients(clinic_id, search=search, risk_level=risk_level, active_only=active_only)

    @st.cache_data(ttl=30, show_spinner=False)
    def _cached(cid, s, r, a):
        return list_patients(cid, search=s, risk_level=r, active_only=a)

    return _cached(clinic_id, search, risk_level, active_only)


def get_patient_summary_cached(clinic_id, patient_id):
    """Cached version of get_patient_summary"""
    try:
        import streamlit as st
    except ImportError:
        return get_patient_summary(clinic_id, patient_id)

    @st.cache_data(ttl=60, show_spinner=False)
    def _cached(cid, pid):
        return get_patient_summary(cid, pid)

    return _cached(clinic_id, patient_id)
