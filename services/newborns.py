# -*- coding: utf-8 -*-
"""
Newborn Records Service
سجل المواليد
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from collections import Counter

from core.db import db, insert, update, delete


# ============================================
# CONSTANTS
# ============================================

DELIVERY_TYPES = {
    "normal": "طبيعية",
    "c_section": "قيصرية",
    "assisted": "بمساعدة (شفط/جفت)",
    "breech": "مقعدية",
}

DELIVERY_PLACES = {
    "hospital": "مستشفى",
    "clinic": "عيادة",
    "home": "منزل",
    "birth_center": "مركز ولادة",
}

HEALTH_STATUS = {
    "healthy": "🟢 سليم",
    "needs_care": "🟡 يحتاج رعاية",
    "nicu": "🔴 في الحاضنة",
    "critical": "🚨 حرج",
}

GENDERS = {
    "male": "👦 ذكر",
    "female": "👧 أنثى",
}


def get_delivery_type_label(t):
    return DELIVERY_TYPES.get(t, t)


def get_delivery_place_label(t):
    return DELIVERY_PLACES.get(t, t)


def get_health_status_label(t):
    return HEALTH_STATUS.get(t, t)


def get_gender_label(t):
    return GENDERS.get(t, t)


# ============================================
# APGAR HELPERS
# ============================================

def apgar_color(score):
    """Color for APGAR score"""
    if score is None:
        return "#94A3B8"
    if score >= 7:
        return "#10B981"
    elif score >= 4:
        return "#F59E0B"
    else:
        return "#EF4444"


def apgar_label(score):
    if score is None:
        return "—"
    if score >= 7:
        return "🟢 طبيعي"
    elif score >= 4:
        return "🟡 متوسط"
    else:
        return "🔴 منخفض"


# ============================================
# CRUD
# ============================================

def create_newborn(clinic_id, mother_id, data, doctor_id=None):
    """Create a newborn record"""
    if not mother_id:
        raise ValueError("mother_id مطلوب")
    if not data.get("gender"):
        raise ValueError("الجنس مطلوب")
    if not data.get("delivery_date"):
        raise ValueError("تاريخ الولادة مطلوب")

    row = {
        "clinic_id": clinic_id,
        "mother_id": mother_id,
        "doctor_id": doctor_id,
        "visit_id": data.get("visit_id"),
        "delivery_date": str(data.get("delivery_date")),
        "delivery_time": data.get("delivery_time"),
        "delivery_type": data.get("delivery_type", "normal"),
        "delivery_place": data.get("delivery_place"),
        "baby_name": data.get("baby_name"),
        "gender": data["gender"],
        "weight_grams": data.get("weight_grams"),
        "length_cm": data.get("length_cm"),
        "head_circumference_cm": data.get("head_circumference_cm"),
        "apgar_1min": data.get("apgar_1min"),
        "apgar_5min": data.get("apgar_5min"),
        "apgar_10min": data.get("apgar_10min"),
        "health_status": data.get("health_status", "healthy"),
        "complications": data.get("complications"),
        "notes": data.get("notes"),
    }

    return insert("newborns", row)


def get_newborn(clinic_id, newborn_id):
    try:
        rows = (
            db().table("newborns")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("id", newborn_id)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def list_newborns(clinic_id, mother_id=None, gender=None,
                   date_from=None, date_to=None, limit=200):
    """List newborns with filters"""
    try:
        q = db().table("newborns").select("*").eq("clinic_id", clinic_id)

        if mother_id:
            q = q.eq("mother_id", mother_id)
        if gender:
            q = q.eq("gender", gender)
        if date_from:
            q = q.gte("delivery_date", str(date_from))
        if date_to:
            q = q.lte("delivery_date", str(date_to))

        q = q.order("delivery_date", desc=True).limit(limit)
        rows = q.execute().data or []

        # Enrich with mother name
        if rows:
            mids = list({r["mother_id"] for r in rows if r.get("mother_id")})
            if mids:
                moms = (
                    db().table("patients")
                    .select("id,full_name,phone")
                    .in_("id", mids)
                    .execute()
                    .data or []
                )
                mmap = {m["id"]: m for m in moms}
                for r in rows:
                    m = mmap.get(r.get("mother_id"), {})
                    r["_mother_name"] = m.get("full_name", "—")
                    r["_mother_phone"] = m.get("phone", "")

        return rows
    except Exception as e:
        print("[newborns] list error: {}".format(e))
        return []


def update_newborn(clinic_id, newborn_id, **fields):
    """Update a newborn record"""
    allowed = {
        "baby_name", "gender", "weight_grams", "length_cm",
        "head_circumference_cm", "apgar_1min", "apgar_5min", "apgar_10min",
        "delivery_type", "delivery_place", "delivery_time",
        "health_status", "complications", "notes",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise ValueError("لا توجد حقول للتحديث")
    return update("newborns", {"id": newborn_id, "clinic_id": clinic_id}, clean)


def delete_newborn(clinic_id, newborn_id):
    return delete("newborns", id=newborn_id, clinic_id=clinic_id)


# ============================================
# STATS
# ============================================

def get_clinic_summary(clinic_id):
    """Overall clinic newborn stats"""
    try:
        rows = (
            db().table("newborns")
            .select("id,gender,weight_grams,health_status,delivery_type,delivery_date")
            .eq("clinic_id", clinic_id)
            .execute()
            .data or []
        )

        total = len(rows)
        males = sum(1 for r in rows if r.get("gender") == "male")
        females = sum(1 for r in rows if r.get("gender") == "female")

        weights = [r.get("weight_grams") for r in rows if r.get("weight_grams")]
        avg_weight = round(sum(weights) / len(weights), 0) if weights else 0
        min_weight = min(weights) if weights else 0
        max_weight = max(weights) if weights else 0

        c_section_count = sum(1 for r in rows if r.get("delivery_type") == "c_section")
        c_section_pct = round(100.0 * c_section_count / total, 1) if total else 0

        status_counts = Counter(r.get("health_status", "healthy") for r in rows)

        # This month
        this_month = date.today().strftime("%Y-%m")
        this_month_count = sum(
            1 for r in rows
            if str(r.get("delivery_date", ""))[:7] == this_month
        )

        return {
            "total": total,
            "males": males,
            "females": females,
            "avg_weight": int(avg_weight),
            "min_weight": min_weight,
            "max_weight": max_weight,
            "c_section_count": c_section_count,
            "c_section_pct": c_section_pct,
            "status_counts": dict(status_counts),
            "this_month": this_month_count,
        }
    except Exception as e:
        print("[newborns] summary error: {}".format(e))
        return {
            "total": 0, "males": 0, "females": 0,
            "avg_weight": 0, "min_weight": 0, "max_weight": 0,
            "c_section_count": 0, "c_section_pct": 0,
            "status_counts": {}, "this_month": 0,
        }


def get_mother_newborns(clinic_id, mother_id):
    """All newborns for a specific mother"""
    return list_newborns(clinic_id, mother_id=mother_id, limit=50)


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Newborns Service Test")
    print("=" * 60)

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if not clinics:
        print("❌ لا توجد عيادات")
        exit(1)

    cid = clinics[0]["id"]
    print("\n✅ العيادة: {}".format(clinics[0]["name"]))

    # Stats
    summary = get_clinic_summary(cid)
    print("\n📊 الإحصائيات:")
    print("   إجمالي المواليد: {}".format(summary["total"]))
    print("   ذكور: {} | إناث: {}".format(summary["males"], summary["females"]))
    print("   متوسط الوزن: {} غرام".format(summary["avg_weight"]))
    print("   نسبة القيصرية: {}%".format(summary["c_section_pct"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
