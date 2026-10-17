# -*- coding: utf-8 -*-
"""Breastfeeding Tracking Service"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from collections import Counter

from core.db import db, insert


SESSION_TYPES = {
    "breastfeeding": "رضاعة طبيعية",
    "pumping": "شفط (Pump)",
    "formula": "حليب صناعي",
    "mixed": "مختلط",
}

SIDES = {
    "left": "يسار",
    "right": "يمين",
    "both": "كلاهما",
}

STOOL_COLORS = {
    "yellow": "أصفر (طبيعي)",
    "green": "أخضر (طبيعي)",
    "brown": "بني (طبيعي)",
    "black": "أسود (meconium)",
    "red": "أحمر (دم)",
    "white": "أبيض (يحتاج فحص)",
}


def get_session_type_label(t):
    return SESSION_TYPES.get(t, t)


def get_side_label(s):
    return SIDES.get(s, s)


def get_stool_label(s):
    return STOOL_COLORS.get(s, s)


def create_session(clinic_id, mother_id, data, newborn_id=None):
    if not mother_id:
        raise ValueError("mother_id required")

    row = {
        "clinic_id": clinic_id,
        "mother_id": mother_id,
        "newborn_id": newborn_id,
        "session_type": data.get("session_type", "breastfeeding"),
        "side": data.get("side"),
        "duration_min": data.get("duration_min"),
        "amount_ml": data.get("amount_ml"),
        "diaper_wet": data.get("diaper_wet", False),
        "diaper_dirty": data.get("diaper_dirty", False),
        "stool_color": data.get("stool_color"),
        "baby_weight_grams": data.get("baby_weight_grams"),
        "notes": data.get("notes"),
        "recorded_at": data.get("recorded_at") or datetime.utcnow().isoformat(),
    }
    return insert("breastfeeding_sessions", row)


def list_sessions(clinic_id, mother_id, limit=50):
    try:
        return (
            db().table("breastfeeding_sessions")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("mother_id", mother_id)
            .order("recorded_at", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )
    except Exception:
        return []


def get_last_24h_sessions(clinic_id, mother_id):
    try:
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        return (
            db().table("breastfeeding_sessions")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("mother_id", mother_id)
            .gte("recorded_at", since)
            .order("recorded_at", desc=True)
            .execute()
            .data or []
        )
    except Exception:
        return []


def analyze_breastfeeding(clinic_id, mother_id):
    sessions_24h = get_last_24h_sessions(clinic_id, mother_id)

    if not sessions_24h:
        return {
            "sessions_24h": 0,
            "assessment": "no_data",
            "label": "لا توجد بيانات",
            "color": "#94A3B8",
            "recommendation": ["سجل جلسات الرضاعة اليوم"],
            "warning": None,
            "issues": [],
        }

    total_sessions = len(sessions_24h)
    total_duration = sum(s.get("duration_min") or 0 for s in sessions_24h)
    avg_duration = round(total_duration / total_sessions, 1) if total_sessions else 0

    wet_diapers = sum(1 for s in sessions_24h if s.get("diaper_wet"))
    dirty_diapers = sum(1 for s in sessions_24h if s.get("diaper_dirty"))

    warning = None
    issues = []

    if total_sessions < 8:
        issues.append("عدد الجلسات اقل من 8")
    if total_sessions > 12:
        warning = "كثرة الرضاعة (اكثر من 12)"
    if avg_duration < 10 and total_sessions < 10:
        issues.append("مدة الرضاعة قصيرة")
    if wet_diapers < 6:
        issues.append("حفاضات مبللة اقل من 6")
    if dirty_diapers < 1:
        issues.append("لا توجد حفاضات متسخة")

    if not issues and not warning:
        assessment = "good"
        label = "رضاعة كافية"
        color = "#10B981"
        recommendation = ["استمر بالرضاعة الطبيعية"]
    elif len(issues) >= 3:
        assessment = "critical"
        label = "رضاعة غير كافية"
        color = "#DC2626"
        recommendation = [
            "مراجعة طبية فورية",
            "استشارة اخصائي رضاعة",
            "تقييم وزن المولود",
        ]
    elif issues:
        assessment = "warning"
        label = "يحتاج متابعة"
        color = "#F59E0B"
        recommendation = [
            "زيادة عدد الجلسات",
            "فحص وزن المولود",
        ]
    else:
        assessment = "good"
        label = "رضاعة كافية"
        color = "#10B981"
        recommendation = ["استمر"]

    return {
        "sessions_24h": total_sessions,
        "avg_duration": avg_duration,
        "wet_diapers": wet_diapers,
        "dirty_diapers": dirty_diapers,
        "assessment": assessment,
        "label": label,
        "color": color,
        "issues": issues,
        "warning": warning,
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    print("=" * 50)
    print("Breastfeeding Service Test")
    print("=" * 50)

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if clinics:
        cid = clinics[0]["id"]
        print("Clinic: {}".format(clinics[0]["name"]))
        patients = db().table("patients").select("id,full_name").eq("clinic_id", cid).limit(1).execute().data
        if patients:
            pid = patients[0]["id"]
            analysis = analyze_breastfeeding(cid, pid)
            print("Sessions: {}".format(analysis["sessions_24h"]))
            print("Assessment: {}".format(analysis["label"]))

    print("OK")
