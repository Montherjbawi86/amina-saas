# -*- coding: utf-8 -*-
"""Postpartum Care Plan Service"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from core.db import db, insert, update


WHO_POSTPARTUM_SCHEDULE = [
    {
        "visit_num": 1,
        "day_from_birth": 1,
        "title": "24 ساعة بعد الولادة",
        "checks_mother": [
            "قياس الضغط",
            "فحص النزيف (Lochia)",
            "فحص الرحم",
            "تقييم الجرح/الخياطة",
            "بدء الرضاعة",
            "تقييم المزاج (EPDS)",
        ],
        "checks_baby": [
            "قياس الوزن",
            "فحص التنفس",
            "فحص الحبل السري",
            "بدء التطعيمات (BCG + HepB)",
            "تقييم الرضاعة",
        ],
    },
    {
        "visit_num": 2,
        "day_from_birth": 7,
        "title": "أسبوع 1",
        "checks_mother": [
            "قياس الضغط",
            "فحص الرحم",
            "تقييم الجرح",
            "تقييم النزيف",
        ],
        "checks_baby": [
            "قياس الوزن",
            "فحص اليرقان (Jaundice)",
            "متابعة الرضاعة",
        ],
    },
    {
        "visit_num": 3,
        "day_from_birth": 14,
        "title": "أسبوع 2",
        "checks_mother": [
            "متابعة الضغط",
            "تقييم النزيف",
            "تقييم المزاج",
        ],
        "checks_baby": [
            "قياس الوزن",
            "تقييم الرضاعة",
        ],
    },
    {
        "visit_num": 4,
        "day_from_birth": 42,
        "title": "أسبوع 6 (الزيارة النهائية)",
        "checks_mother": [
            "قياس الضغط",
            "فحص الرحم",
            "فحص الحوض",
            "تقييم EPDS (اكتئاب ما بعد الولادة)",
            "مناقشة تنظيم الأسرة",
        ],
        "checks_baby": [
            "قياس الوزن",
            "محيط الرأس",
            "اكتمال التطعيمات",
            "تقييم النمو والتطور",
        ],
    },
]


LOCHIA_TYPES = {
    "normal": "طبيعي",
    "heavy": "ثقيل (نزيف)",
    "abnormal": "غير طبيعي (رائحة/التهاب)",
}

UTERUS_INVOLUTION = {
    "good": "جيد (تراجع طبيعي)",
    "delayed": "متأخر",
}

PERINEUM_HEALING = {
    "good": "شفاء جيد",
    "delayed": "تأخر في الشفاء",
    "infection": "التهاب",
}

CORD_STATUS = {
    "normal": "طبيعي",
    "delayed": "تأخر الجفاف",
    "infection": "التهاب",
}


def get_lochia_label(v):
    return LOCHIA_TYPES.get(v, v)


def get_uterus_label(v):
    return UTERUS_INVOLUTION.get(v, v)


def get_perineum_label(v):
    return PERINEUM_HEALING.get(v, v)


def get_cord_label(v):
    return CORD_STATUS.get(v, v)


# ============================================
# PLAN GENERATION
# ============================================

def generate_postpartum_plan(delivery_date):
    """Generate postpartum visit plan from delivery date"""
    if not delivery_date:
        return []

    try:
        if isinstance(delivery_date, str):
            d = datetime.strptime(delivery_date[:10], "%Y-%m-%d").date()
        else:
            d = delivery_date
    except Exception:
        return []

    plan = []
    for schedule in WHO_POSTPARTUM_SCHEDULE:
        target_date = d + timedelta(days=schedule["day_from_birth"])
        days_since = (date.today() - d).days

        if days_since > schedule["day_from_birth"]:
            status = "past"
        elif days_since >= schedule["day_from_birth"] - 2:
            status = "current"
        else:
            status = "upcoming"

        plan.append({
            **schedule,
            "target_date": target_date,
            "status": status,
        })

    return plan


# ============================================
# CRUD
# ============================================

def create_visit(clinic_id, mother_id, data, newborn_id=None):
    row = {
        "clinic_id": clinic_id,
        "mother_id": mother_id,
        "newborn_id": newborn_id,
        "visit_date": data.get("visit_date") or str(date.today()),
        "visit_type": data.get("visit_type", "routine"),
        "week_number": data.get("week_number"),
        "bp_systolic": data.get("bp_systolic"),
        "bp_diastolic": data.get("bp_diastolic"),
        "lochia": data.get("lochia"),
        "uterus_involution": data.get("uterus_involution"),
        "perineum_healing": data.get("perineum_healing"),
        "mood_score": data.get("mood_score"),
        "baby_weight_grams": data.get("baby_weight_grams"),
        "baby_feeding": data.get("baby_feeding"),
        "jaundice": data.get("jaundice"),
        "cord_status": data.get("cord_status"),
        "complications": data.get("complications"),
        "notes": data.get("notes"),
    }
    return insert("postpartum_visits", row)


def list_visits(clinic_id, mother_id, limit=20):
    try:
        return (
            db().table("postpartum_visits")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("mother_id", mother_id)
            .order("visit_date", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )
    except Exception:
        return []


def get_latest_visit(clinic_id, mother_id):
    visits = list_visits(clinic_id, mother_id, limit=1)
    if visits:
        return visits[0]
    return None


# ============================================
# ANALYSIS
# ============================================

def analyze_postpartum_risk(data):
    """Analyze postpartum visit data for risks"""
    alerts = []
    color = "#10B981"

    bp_sys = data.get("bp_systolic")
    bp_dia = data.get("bp_diastolic")
    if bp_sys and bp_dia:
        if bp_sys >= 160 or bp_dia >= 110:
            alerts.append({"level": "critical", "message": "ضغط شديد الارتفاع"})
            color = "#DC2626"
        elif bp_sys >= 140 or bp_dia >= 90:
            alerts.append({"level": "warning", "message": "ارتفاع ضغط الدم"})
            if color == "#10B981":
                color = "#F59E0B"

    if data.get("lochia") == "heavy":
        alerts.append({"level": "critical", "message": "نزيف ما بعد الولادة"})
        color = "#DC2626"

    if data.get("lochia") == "abnormal":
        alerts.append({"level": "warning", "message": "نزيف غير طبيعي (التهاب محتمل)"})
        if color == "#10B981":
            color = "#F59E0B"

    if data.get("uterus_involution") == "delayed":
        alerts.append({"level": "warning", "message": "تراجع الرحم متأخر"})

    if data.get("perineum_healing") == "infection":
        alerts.append({"level": "critical", "message": "التهاب في جرح الولادة"})
        color = "#DC2626"

    mood = data.get("mood_score")
    if mood is not None:
        try:
            m = int(mood)
            if m <= 3:
                alerts.append({"level": "critical", "message": "اكتئاب ما بعد الولادة (EPDS منخفض)"})
                color = "#DC2626"
            elif m <= 5:
                alerts.append({"level": "warning", "message": "تقييم المزاج منخفض"})
        except Exception:
            pass

    if data.get("jaundice") and data.get("baby_weight_grams"):
        alerts.append({"level": "warning", "message": "يرقان المولود"})

    if data.get("cord_status") == "infection":
        alerts.append({"level": "critical", "message": "التهاب في الحبل السري"})

    return {
        "alerts": alerts,
        "color": color,
        "status": "critical" if color == "#DC2626" else ("warning" if color == "#F59E0B" else "normal"),
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Postpartum Service Test")
    print("=" * 50)

    # Test plan generation
    from datetime import date as _date
    plan = generate_postpartum_plan(_date.today() - timedelta(days=5))
    print("\nPlan (5 days after birth):")
    for v in plan:
        print("  Visit {}: {} ({})".format(
            v["visit_num"], v["title"], v["status"]
        ))

    # Test risk analysis
    print("\nRisk analysis (severe case):")
    risk = analyze_postpartum_risk({
        "bp_systolic": 165,
        "bp_diastolic": 110,
        "lochia": "heavy",
        "mood_score": 2,
    })
    print("  Status: {}".format(risk["status"]))
    for a in risk["alerts"]:
        print("  - {}".format(a["message"]))

    print("\nOK")
