# -*- coding: utf-8 -*-
"""
Reports Service — Advanced reporting & analytics
خدمة التقارير المتقدمة
"""
from datetime import datetime, timedelta, date
from collections import Counter
from typing import Optional, Dict, List

from core.db import db


# ============================================
# DATE HELPERS
# ============================================

def _parse_date(v):
    """Parse any date/datetime value to date"""
    if not v:
        return None
    try:
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        s = str(v)[:10]
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _in_range(d, date_from, date_to):
    """Check if date d is within range (inclusive)"""
    if d is None:
        return False
    if date_from and d < date_from:
        return False
    if date_to and d > date_to:
        return False
    return True


# ============================================
# DATE RANGE FILTERS
# ============================================

def get_date_presets():
    """Return preset date ranges for UI"""
    today = date.today()
    return {
        "today": ("اليوم", today, today),
        "week": ("آخر 7 أيام", today - timedelta(days=7), today),
        "month": ("آخر 30 يوم", today - timedelta(days=30), today),
        "quarter": ("آخر 3 أشهر", today - timedelta(days=90), today),
        "half_year": ("آخر 6 أشهر", today - timedelta(days=180), today),
        "year": ("آخر سنة", today - timedelta(days=365), today),
        "all": ("كل الوقت", None, None),
    }


# ============================================
# OVERVIEW (with date filter)
# ============================================

def get_overview(clinic_id, date_from=None, date_to=None):
    """Comprehensive overview KPIs"""
    try:
        # Patients (all time — date filter for "new")
        patients = db().table("patients").select(
            "id,full_name,created_at,risk_level,is_active"
        ).eq("clinic_id", clinic_id).execute().data or []

        total_patients = sum(1 for p in patients if p.get("is_active", True))

        # New patients in range
        new_in_range = 0
        for p in patients:
            d = _parse_date(p.get("created_at"))
            if _in_range(d, date_from, date_to):
                new_in_range += 1

        # Risk distribution (active patients)
        risk = Counter(
            p.get("risk_level", "low")
            for p in patients
            if p.get("is_active", True)
        )

        # Visits
        visits = db().table("visits").select(
            "id,visit_date,patient_id"
        ).eq("clinic_id", clinic_id).execute().data or []

        visits_in_range = 0
        for v in visits:
            d = _parse_date(v.get("visit_date"))
            if _in_range(d, date_from, date_to):
                visits_in_range += 1

        # Prescriptions
        presc = db().table("prescriptions").select(
            "id,issued_at"
        ).eq("clinic_id", clinic_id).execute().data or []

        presc_in_range = 0
        for p in presc:
            d = _parse_date(p.get("issued_at"))
            if _in_range(d, date_from, date_to):
                presc_in_range += 1

        # Lab tests
        lab = db().table("lab_tests").select(
            "id,test_date,is_abnormal,test_type"
        ).eq("clinic_id", clinic_id).execute().data or []

        lab_in_range = 0
        lab_abnormal = 0
        for t in lab:
            d = _parse_date(t.get("test_date"))
            if _in_range(d, date_from, date_to):
                lab_in_range += 1
                if t.get("is_abnormal"):
                    lab_abnormal += 1

        # Ultrasound
        us = db().table("ultrasound_images").select(
            "id,image_date"
        ).eq("clinic_id", clinic_id).execute().data or []

        us_in_range = 0
        for u in us:
            d = _parse_date(u.get("image_date"))
            if _in_range(d, date_from, date_to):
                us_in_range += 1

        # Certificates
        try:
            certs = db().table("certificates").select(
                "id,issued_at"
            ).eq("clinic_id", clinic_id).execute().data or []

            certs_in_range = 0
            for c in certs:
                d = _parse_date(c.get("issued_at"))
                if _in_range(d, date_from, date_to):
                    certs_in_range += 1
        except Exception:
            certs_in_range = 0

        # Vaccinations
        vacc = db().table("vaccinations").select(
            "id,status,given_at"
        ).eq("clinic_id", clinic_id).execute().data or []

        vacc_in_range = 0
        for v in vacc:
            d = _parse_date(v.get("given_at"))
            if _in_range(d, date_from, date_to):
                vacc_in_range += 1

        return {
            "total_patients": total_patients,
            "new_patients": new_in_range,
            "total_visits": visits_in_range,
            "total_prescriptions": presc_in_range,
            "total_lab_tests": lab_in_range,
            "abnormal_lab_tests": lab_abnormal,
            "total_ultrasound": us_in_range,
            "total_certificates": certs_in_range,
            "total_vaccinations": vacc_in_range,
            "risk_distribution": dict(risk),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


# ============================================
# MONTHLY TRENDS
# ============================================

def _month_label(d):
    """Format: 'Nov 2026'"""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return "{} {}".format(months[d.month - 1], d.year)


def get_monthly_trends(clinic_id, months_back=6):
    """Get trends for patients/visits/labs/ultrasound by month"""
    try:
        today = date.today()
        since = (today - timedelta(days=months_back * 31)).isoformat()

        # Build month keys
        month_keys = []
        for i in range(months_back - 1, -1, -1):
            d = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            month_keys.append((d.strftime("%Y-%m"), _month_label(d)))

        def _count_by_month(rows, date_field):
            counts = Counter()
            for r in rows:
                d = _parse_date(r.get(date_field))
                if d:
                    counts[d.strftime("%Y-%m")] += 1
            return counts

        # Fetch data
        patients = db().table("patients").select(
            "created_at"
        ).eq("clinic_id", clinic_id).gte("created_at", since).execute().data or []
        p_counts = _count_by_month(patients, "created_at")

        visits = db().table("visits").select(
            "visit_date"
        ).eq("clinic_id", clinic_id).gte("visit_date", since).execute().data or []
        v_counts = _count_by_month(visits, "visit_date")

        labs = db().table("lab_tests").select(
            "test_date"
        ).eq("clinic_id", clinic_id).gte("test_date", since).execute().data or []
        l_counts = _count_by_month(labs, "test_date")

        us = db().table("ultrasound_images").select(
            "image_date"
        ).eq("clinic_id", clinic_id).gte("image_date", since).execute().data or []
        u_counts = _count_by_month(us, "image_date")

        # Build result
        result = []
        for key, label in month_keys:
            result.append({
                "month": key,
                "label": label,
                "patients": p_counts.get(key, 0),
                "visits": v_counts.get(key, 0),
                "labs": l_counts.get(key, 0),
                "ultrasounds": u_counts.get(key, 0),
            })
        return result
    except Exception as e:
        print("[reports] monthly trends error: {}".format(e))
        return []


# ============================================
# ABNORMAL LAB TESTS REPORT
# ============================================

def get_abnormal_labs(clinic_id, date_from=None, date_to=None, limit=200):
    """Get all abnormal lab tests in range"""
    try:
        rows = db().table("lab_tests").select(
            "id,patient_id,test_type,test_name,test_date,severity,result_value,is_abnormal"
        ).eq("clinic_id", clinic_id).eq("is_abnormal", True).order(
            "test_date", desc=True
        ).limit(limit).execute().data or []

        # Filter by date
        filtered = []
        for r in rows:
            d = _parse_date(r.get("test_date"))
            if _in_range(d, date_from, date_to):
                filtered.append(r)

        # Enrich with patient names
        if filtered:
            pids = list({r["patient_id"] for r in filtered if r.get("patient_id")})
            if pids:
                pats = db().table("patients").select(
                    "id,full_name,phone"
                ).in_("id", pids).execute().data or []
                pmap = {p["id"]: p for p in pats}
                for r in filtered:
                    p = pmap.get(r.get("patient_id"), {})
                    r["_patient_name"] = p.get("full_name", "—")
                    r["_patient_phone"] = p.get("phone", "")

        return filtered
    except Exception as e:
        print("[reports] abnormal labs error: {}".format(e))
        return []


# ============================================
# PATIENTS REPORT
# ============================================

def get_patients_report(clinic_id, risk_filter=None, date_from=None, date_to=None):
    """Patients with summary (visits, labs, ultrasound counts)"""
    try:
        q = db().table("patients").select(
            "id,full_name,phone,risk_level,lmp,edd,gravida,para,is_active,created_at"
        ).eq("clinic_id", clinic_id)

        if risk_filter and risk_filter in ("low", "medium", "high"):
            q = q.eq("risk_level", risk_filter)

        patients = q.execute().data or []

        # Filter by date
        if date_from or date_to:
            patients = [
                p for p in patients
                if _in_range(_parse_date(p.get("created_at")), date_from, date_to)
            ]

        # Count visits per patient
        pids = [p["id"] for p in patients]
        if not pids:
            return []

        visits = db().table("visits").select(
            "patient_id"
        ).eq("clinic_id", clinic_id).in_("patient_id", pids).execute().data or []
        visit_counts = Counter(v.get("patient_id") for v in visits)

        labs = db().table("lab_tests").select(
            "patient_id,is_abnormal"
        ).eq("clinic_id", clinic_id).in_("patient_id", pids).execute().data or []
        lab_counts = Counter(l.get("patient_id") for l in labs)
        lab_abnormal_counts = Counter(
            l.get("patient_id") for l in labs if l.get("is_abnormal")
        )

        # Compose
        result = []
        for p in patients:
            pid = p["id"]
            result.append({
                "patient_id": pid,
                "name": p.get("full_name", "—"),
                "phone": p.get("phone", ""),
                "risk_level": p.get("risk_level", "low"),
                "visits": visit_counts.get(pid, 0),
                "labs": lab_counts.get(pid, 0),
                "abnormal_labs": lab_abnormal_counts.get(pid, 0),
                "lmp": p.get("lmp"),
                "edd": p.get("edd"),
                "gravida": p.get("gravida"),
                "para": p.get("para"),
            })
        return result
    except Exception as e:
        print("[reports] patients report error: {}".format(e))
        return []


# ============================================
# ULTRASOUND REPORT
# ============================================

def get_ultrasound_report(clinic_id, date_from=None, date_to=None, limit=200):
    """Recent ultrasound images with patient names"""
    try:
        rows = db().table("ultrasound_images").select(
            "id,patient_id,image_date,gestational_weeks,caption,public_url"
        ).eq("clinic_id", clinic_id).order(
            "image_date", desc=True
        ).limit(limit).execute().data or []

        filtered = []
        for r in rows:
            d = _parse_date(r.get("image_date"))
            if _in_range(d, date_from, date_to):
                filtered.append(r)

        if filtered:
            pids = list({r["patient_id"] for r in filtered if r.get("patient_id")})
            if pids:
                pats = db().table("patients").select(
                    "id,full_name"
                ).in_("id", pids).execute().data or []
                pmap = {p["id"]: p for p in pats}
                for r in filtered:
                    r["_patient_name"] = pmap.get(r.get("patient_id"), {}).get("full_name", "—")

        return filtered
    except Exception as e:
        print("[reports] ultrasound error: {}".format(e))
        return []


# ============================================
# CERTIFICATES REPORT
# ============================================

def get_certificates_report(clinic_id, date_from=None, date_to=None, limit=200):
    """Recent certificates"""
    try:
        rows = db().table("certificates").select(
            "id,patient_id,issued_at,is_active"
        ).eq("clinic_id", clinic_id).order(
            "issued_at", desc=True
        ).limit(limit).execute().data or []

        filtered = []
        for r in rows:
            d = _parse_date(r.get("issued_at"))
            if _in_range(d, date_from, date_to):
                filtered.append(r)

        # Enrich
        if filtered:
            pids = list({r["patient_id"] for r in filtered if r.get("patient_id")})
            if pids:
                pats = db().table("patients").select(
                    "id,full_name"
                ).in_("id", pids).execute().data or []
                pmap = {p["id"]: p for p in pats}
                for r in filtered:
                    r["_patient_name"] = pmap.get(r.get("patient_id"), {}).get("full_name", "—")

        return filtered
    except Exception:
        return []


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Reports Service Test")
    print("=" * 60)

    print("\n📅 Date presets:")
    for k, (label, df, dt) in get_date_presets().items():
        print("   {}: {} ({} → {})".format(k, label, df, dt))

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if clinics:
        cid = clinics[0]["id"]
        print("\n✅ Test clinic: {}".format(clinics[0]["name"]))

        overview = get_overview(cid)
        print("\n📊 Overview:")
        for k, v in overview.items():
            print("   {}: {}".format(k, v))

        trends = get_monthly_trends(cid, 3)
        print("\n📈 Trends (3 months):")
        for t in trends:
            print("   {}: P={} V={} L={} US={}".format(
                t["label"], t["patients"], t["visits"], t["labs"], t["ultrasounds"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
