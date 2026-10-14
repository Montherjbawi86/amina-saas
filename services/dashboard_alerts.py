# -*- coding: utf-8 -*-
"""
Dashboard Alerts Service
تنبيهات ذكية للوحة التحكم
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from collections import Counter

from core.db import db


# ============================================
# HELPERS
# ============================================

def _parse_date(v):
    if not v:
        return None
    try:
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _days_ago(d):
    if not d:
        return None
    return (date.today() - d).days


# ============================================
# ALERT: OVERDUE VACCINATIONS
# ============================================

def get_overdue_vaccinations(clinic_id, limit=10):
    """Vaccinations that are pending and past their scheduled date"""
    try:
        today = date.today()
        rows = (
            db().table("vaccinations")
            .select("id,patient_id,vaccine_name,scheduled_for,status,dose_number")
            .eq("clinic_id", clinic_id)
            .eq("status", "pending")
            .lt("scheduled_for", today.isoformat())
            .order("scheduled_for")
            .limit(limit)
            .execute()
            .data or []
        )

        if not rows:
            return []

        # Enrich with patient name
        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name,phone")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p for p in pats}

        for r in rows:
            p = pmap.get(r.get("patient_id"), {})
            r["_patient_name"] = p.get("full_name", "—")
            r["_patient_phone"] = p.get("phone", "")
            d = _parse_date(r.get("scheduled_for"))
            r["_days_overdue"] = _days_ago(d) if d else 0

        return rows
    except Exception as e:
        print("[dashboard_alerts] overdue vacc error: {}".format(e))
        return []


# ============================================
# ALERT: ABNORMAL LABS (last 30 days)
# ============================================

def get_recent_abnormal_labs(clinic_id, days=30, limit=10):
    """Abnormal lab tests in last N days"""
    try:
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = (
            db().table("lab_tests")
            .select("id,patient_id,test_name,test_date,severity,result_value")
            .eq("clinic_id", clinic_id)
            .eq("is_abnormal", True)
            .gte("test_date", since)
            .order("test_date", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )

        if not rows:
            return []

        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name,phone")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p for p in pats}

        for r in rows:
            p = pmap.get(r.get("patient_id"), {})
            r["_patient_name"] = p.get("full_name", "—")
            r["_patient_phone"] = p.get("phone", "")
            d = _parse_date(r.get("test_date"))
            r["_days_ago"] = _days_ago(d) if d else None

        return rows
    except Exception as e:
        print("[dashboard_alerts] abnormal labs error: {}".format(e))
        return []


# ============================================
# ALERT: HIGH-RISK WITHOUT RECENT VISIT
# ============================================

def get_high_risk_no_visit(clinic_id, days=30, limit=10):
    """High-risk patients without a visit in last N days"""
    try:
        # Get high-risk patients
        patients = (
            db().table("patients")
            .select("id,full_name,phone,risk_level,created_at")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .eq("risk_level", "high")
            .execute()
            .data or []
        )

        if not patients:
            return []

        # Get all visits in last N days
        since = (date.today() - timedelta(days=days)).isoformat()
        visits = (
            db().table("visits")
            .select("patient_id,visit_date")
            .eq("clinic_id", clinic_id)
            .gte("visit_date", since)
            .execute()
            .data or []
        )

        visited_pids = {v["patient_id"] for v in visits if v.get("patient_id")}

        result = []
        for p in patients:
            if p["id"] not in visited_pids:
                result.append({
                    "patient_id": p["id"],
                    "name": p.get("full_name", "—"),
                    "phone": p.get("phone", ""),
                    "risk_level": p.get("risk_level", "high"),
                })

        return result[:limit]
    except Exception as e:
        print("[dashboard_alerts] high-risk error: {}".format(e))
        return []


# ============================================
# ALERT: UPCOMING APPOINTMENTS (today + tomorrow)
# ============================================

def get_urgent_appointments(clinic_id, limit=10):
    """Appointments for today and tomorrow"""
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        rows = (
            db().table("appointments")
            .select("id,patient_id,scheduled_at,status,type")
            .eq("clinic_id", clinic_id)
            .in_("status", ["scheduled", "confirmed"])
            .gte("scheduled_at", today.isoformat())
            .lte("scheduled_at", tomorrow.isoformat() + "T23:59:59")
            .order("scheduled_at")
            .limit(limit)
            .execute()
            .data or []
        )

        if not rows:
            return []

        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name,phone")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p for p in pats}

        for r in rows:
            p = pmap.get(r.get("patient_id"), {})
            r["_patient_name"] = p.get("full_name", "—")
            r["_patient_phone"] = p.get("phone", "")

        return rows
    except Exception as e:
        print("[dashboard_alerts] urgent appts error: {}".format(e))
        return []


# ============================================
# MASTER: GET ALL ALERTS
# ============================================

def get_all_alerts(clinic_id):
    """Get all dashboard alerts in one call"""
    return {
        "overdue_vaccinations": get_overdue_vaccinations(clinic_id, limit=5),
        "abnormal_labs": get_recent_abnormal_labs(clinic_id, days=30, limit=5),
        "high_risk_no_visit": get_high_risk_no_visit(clinic_id, days=30, limit=5),
        "urgent_appointments": get_urgent_appointments(clinic_id, limit=5),
    }


def count_alerts(alerts):
    """Count all alerts by category"""
    if not alerts:
        return {"total": 0, "by_category": {}}
    return {
        "total": sum(len(v) for v in alerts.values()),
        "by_category": {k: len(v) for k, v in alerts.items()},
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard Alerts Test")
    print("=" * 60)

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if not clinics:
        print("❌ لا توجد عيادات")
        exit(1)

    cid = clinics[0]["id"]
    print("\n✅ العيادة: {}".format(clinics[0]["name"]))

    alerts = get_all_alerts(cid)
    counts = count_alerts(alerts)

    print("\n📊 التنبيهات:")
    print("   إجمالي: {}".format(counts["total"]))
    for k, v in counts["by_category"].items():
        print("   - {}: {}".format(k, v))

    print("\n🔴 تطعيمات متأخرة:")
    for v in alerts["overdue_vaccinations"]:
        print("   - {} ({}) — متأخر {} يوم".format(
            v.get("_patient_name"), v.get("vaccine_name"), v.get("_days_overdue", 0)))

    print("\n⚠️ تحاليل غير طبيعية (آخر 30 يوم):")
    for t in alerts["abnormal_labs"]:
        print("   - {} ({}) — {}".format(
            t.get("_patient_name"), t.get("test_name"), t.get("severity")))

    print("\n🚨 حوامل بمخاطر عالية بدون زيارة:")
    for p in alerts["high_risk_no_visit"]:
        print("   - {}".format(p.get("name")))

    print("\n📅 مواعيد عاجلة (اليوم/غداً):")
    for a in alerts["urgent_appointments"]:
        print("   - {} — {}".format(a.get("_patient_name"), a.get("scheduled_at", "")[:16]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
