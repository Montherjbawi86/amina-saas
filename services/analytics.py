# -*- coding: utf-8 -*-
"""Analytics & reporting"""
from datetime import datetime, timedelta, date
from typing import Dict, List
from collections import Counter

from core.db import db


def _month_key(dt_str):
    """YYYY-MM from ISO date string"""
    if not dt_str:
        return None
    try:
        return str(dt_str)[:7]
    except Exception:
        return None


def get_clinic_overview(clinic_id):
    """High-level KPIs"""
    try:
        # Patients
        patients = db().table("patients").select(
            "id,created_at,risk_level,lmp,edd"
        ).eq("clinic_id", clinic_id).eq("is_active", True).execute().data

        total_patients = len(patients)

        # Risk distribution
        risk_counts = Counter(p.get("risk_level", "low") for p in patients)

        # New this month
        this_month = date.today().strftime("%Y-%m")
        new_this_month = sum(
            1 for p in patients
            if _month_key(p.get("created_at")) == this_month
        )

        # Visits
        visits = db().table("visits").select(
            "id,visit_date,patient_id"
        ).eq("clinic_id", clinic_id).execute().data

        total_visits = len(visits)

        # Avg visits per patient
        avg_visits = round(total_visits / total_patients, 1) if total_patients else 0

        # Appointments
        appts = db().table("appointments").select(
            "id,status,scheduled_at"
        ).eq("clinic_id", clinic_id).execute().data

        appt_status = Counter(a.get("status", "scheduled") for a in appts)

        completed = appt_status.get("completed", 0)
        total_appt = len(appts)
        adherence = round(100.0 * completed / total_appt, 1) if total_appt else 0

        # Prescriptions
        presc = db().table("prescriptions").select("id").eq("clinic_id", clinic_id).execute().data
        total_presc = len(presc)

        # Vaccinations
        vacc = db().table("vaccinations").select("id,status").eq("clinic_id", clinic_id).execute().data
        vacc_given = sum(1 for v in vacc if v.get("status") == "given")
        vacc_pending = sum(1 for v in vacc if v.get("status") == "pending")

        # Files
        files = db().table("medical_files").select("id").eq("clinic_id", clinic_id).execute().data
        total_files = len(files)

        return {
            "total_patients": total_patients,
            "new_patients_this_month": new_this_month,
            "total_visits": total_visits,
            "avg_visits_per_patient": avg_visits,
            "total_appointments": total_appt,
            "appt_status": dict(appt_status),
            "adherence_pct": adherence,
            "risk_distribution": dict(risk_counts),
            "total_prescriptions": total_presc,
            "total_vaccinations": len(vacc),
            "vacc_given": vacc_given,
            "vacc_pending": vacc_pending,
            "total_files": total_files,
        }
    except Exception as e:
        return {"error": str(e)[:200]}


def get_monthly_patients(clinic_id, months_back=6):
    """Patients count per month (last N months)"""
    try:
        since = (datetime.now() - timedelta(days=months_back * 31)).date()
        patients = db().table("patients").select(
            "id,created_at"
        ).eq("clinic_id", clinic_id).gte("created_at", since.isoformat()).execute().data

        counts = Counter(_month_key(p.get("created_at")) for p in patients if p.get("created_at"))
        # Build sorted list of last N months
        result = []
        today = date.today()
        for i in range(months_back - 1, -1, -1):
            d = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            key = d.strftime("%Y-%m")
            label = d.strftime("%b %Y")
            result.append({"month": key, "label": label, "count": counts.get(key, 0)})
        return result
    except Exception:
        return []


def get_monthly_visits(clinic_id, months_back=6):
    """Visits per month"""
    try:
        since = (datetime.now() - timedelta(days=months_back * 31)).date()
        visits = db().table("visits").select(
            "visit_date"
        ).eq("clinic_id", clinic_id).gte("visit_date", since.isoformat()).execute().data

        counts = Counter(_month_key(v.get("visit_date")) for v in visits if v.get("visit_date"))
        result = []
        today = date.today()
        for i in range(months_back - 1, -1, -1):
            d = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            key = d.strftime("%Y-%m")
            label = d.strftime("%b %Y")
            result.append({"month": key, "label": label, "count": counts.get(key, 0)})
        return result
    except Exception:
        return []


def get_top_patients_by_visits(clinic_id, limit=10):
    """Top patients with most visits"""
    try:
        visits = db().table("visits").select(
            "patient_id"
        ).eq("clinic_id", clinic_id).execute().data

        counts = Counter(v.get("patient_id") for v in visits if v.get("patient_id"))
        top_ids = [pid for pid, _ in counts.most_common(limit)]

        if not top_ids:
            return []

        # Fetch patient names
        patients = db().table("patients").select(
            "id,full_name,phone,risk_level"
        ).in_("id", top_ids).execute().data

        pmap = {p["id"]: p for p in patients}
        result = []
        for pid in top_ids:
            p = pmap.get(pid, {})
            result.append({
                "patient_id": pid,
                "name": p.get("full_name", "—"),
                "phone": p.get("phone", ""),
                "risk_level": p.get("risk_level", "low"),
                "visits": counts[pid],
            })
        return result
    except Exception:
        return []


def get_upcoming_week_appointments(clinic_id):
    """Count of appointments in next 7 days"""
    try:
        today = date.today()
        end = today + timedelta(days=7)
        q = db().table("appointments").select("id").eq("clinic_id", clinic_id).gte(
            "scheduled_at", today.isoformat()
        ).lte("scheduled_at", end.isoformat()).execute()
        return len(q.data)
    except Exception:
        return 0


def get_alerts_summary(clinic_id):
    """Alert counts by severity"""
    try:
        from services.alerts import get_clinic_alerts, count_alerts_by_level
        from services.patients import list_patients_cached
        from services.visits import list_visits_cached

        patients = list_patients_cached(clinic_id)
        visits_map = {}
        for p in patients[:50]:
            try:
                visits_map[p["id"]] = list_visits_cached(clinic_id, p["id"], limit=5)
            except Exception:
                visits_map[p["id"]] = []

        alerts = get_clinic_alerts(clinic_id, patients, visits_map)
        return count_alerts_by_level(alerts)
    except Exception:
        return {"critical": 0, "high": 0, "medium": 0, "low": 0}


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic

    print("=" * 50)
    print("Analytics Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Analytics Test " + suffix, "Dr. A", "an-{}@t.com".format(suffix))

    print("\n1. Overview (empty clinic):")
    ov = get_clinic_overview(clinic["id"])
    for k, v in ov.items():
        if k != "error":
            print("   {}: {}".format(k, v))

    print("\n2. Monthly patients (should be 6 empty months):")
    mp = get_monthly_patients(clinic["id"], months_back=3)
    for m in mp:
        print("   {}: {}".format(m["label"], m["count"]))

    print("\n3. Alerts summary:")
    print("   {}".format(get_alerts_summary(clinic["id"])))

    print("\n4. Cleanup:")
    from core.db import delete as db_delete
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Analytics module OK")
    print("=" * 50)
