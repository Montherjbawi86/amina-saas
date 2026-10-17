# -*- coding: utf-8 -*-
"""
Gestational Diabetes Mellitus (GDM) Service
سكري الحمل — تشخيص + متابعة
"""
from datetime import datetime, date
from typing import Dict, List, Optional


# ============================================
# GDM CRITERIA (IADPSG / WHO 2013)
# ============================================

GDM_CRITERIA = {
    "fasting": {"threshold": 92, "label": "الصيام", "unit": "mg/dL"},
    "1h": {"threshold": 180, "label": "بعد ساعة", "unit": "mg/dL"},
    "2h": {"threshold": 153, "label": "بعد ساعتين", "unit": "mg/dL"},
}


SEVERITY_LEVELS = {
    "normal": {"label": "🟢 طبيعي", "color": "#10B981"},
    "impaired": {"label": "🟡 اختلال سكر صائم", "color": "#F59E0B"},
    "gdm_diet": {"label": "🟠 سكري حمل (نظام غذائي)", "color": "#F97316"},
    "gdm_insulin": {"label": "🔴 سكري حمل (يحتاج أنسولين)", "color": "#DC2626"},
    "overt_dm": {"label": "🚨 سكري صريح (Overt DM)", "color": "#991B1B"},
}


def get_severity_meta(level):
    return SEVERITY_LEVELS.get(level, {"label": "—", "color": "#94A3B8"})


# ============================================
# OGTT EVALUATION
# ============================================

def evaluate_ogtt(fasting, h1, h2):
    """
    Evaluate 75g OGTT (IADPSG/WHO 2013).

    Args:
        fasting: fasting glucose mg/dL
        h1: 1-hour glucose mg/dL
        h2: 2-hour glucose mg/dL

    Returns:
        {level, label, color, values, criteria_met, recommendation}
    """
    criteria_met = []
    abnormal_count = 0

    # Evaluate each value
    if fasting is not None:
        try:
            f = float(fasting)
            if f >= GDM_CRITERIA["fasting"]["threshold"]:
                criteria_met.append("🔴 صيام: {} mg/dL (≥{})".format(f, GDM_CRITERIA["fasting"]["threshold"]))
                abnormal_count += 1
            elif f >= 92:
                criteria_met.append("🟡 صيام: {} mg/dL (قريب من الحد)".format(f))
        except Exception:
            pass

    if h1 is not None:
        try:
            v = float(h1)
            if v >= GDM_CRITERIA["1h"]["threshold"]:
                criteria_met.append("🔴 بعد ساعة: {} mg/dL (≥{})".format(v, GDM_CRITERIA["1h"]["threshold"]))
                abnormal_count += 1
        except Exception:
            pass

    if h2 is not None:
        try:
            v = float(h2)
            if v >= GDM_CRITERIA["2h"]["threshold"]:
                criteria_met.append("🔴 بعد ساعتين: {} mg/dL (≥{})".format(v, GDM_CRITERIA["2h"]["threshold"]))
                abnormal_count += 1
        except Exception:
            pass

    # Classification
    if abnormal_count >= 2:
        level = "gdm_diet"
        recommendation = [
            "🟠 تشخيص سكري الحمل (GDM)",
            "استشارة أخصائي تغذية",
            "نظام غذائي: 30 kcal/kg/day",
            "قياس سكر 4 مرات يومياً (صيام + بعد 3 وجبات)",
            "رياضة خفيفة 30 دقيقة يومياً",
            "إعادة تقييم بعد أسبوعين",
        ]
        urgent = False
    elif abnormal_count == 1:
        level = "impaired"
        recommendation = [
            "🟡 اختلال سكر — يحتاج متابعة",
            "قياس سكر صيام أسبوعياً",
            "نظام غذائي متوازن",
            "مراقبة الوزن",
            "إعادة OGTT بعد 4 أسابيع",
        ]
        urgent = False
    else:
        level = "normal"
        recommendation = [
            "✅ طبيعي — استمر بالمتابعة الروتينية",
            "إعادة فحص إذا ظهرت أعراض",
        ]
        urgent = False

    # Check for Overt DM (very high values)
    if fasting is not None and float(fasting) >= 126:
        level = "overt_dm"
        recommendation = [
            "🚨 سكري صريح (Overt DM) — ليس GDM فقط",
            "تحويل فوري لطبيب الغدد الصماء",
            "بدء أنسولين على الأرجح",
            "تقييم مضاعفات السكري",
        ]
        urgent = True
    elif h2 is not None and float(h2) >= 200:
        level = "overt_dm"
        recommendation = [
            "🚨 سكري صريح — يحتاج علاجاً فورياً",
            "تحويل فوري لطبيب الغدد",
        ]
        urgent = True

    meta = get_severity_meta(level)

    return {
        "level": level,
        "label": meta["label"],
        "color": meta["color"],
        "criteria_met": criteria_met,
        "abnormal_count": abnormal_count,
        "recommendation": recommendation,
        "urgent": urgent,
        "values": {
            "fasting": fasting,
            "1h": h1,
            "2h": h2,
        },
    }


# ============================================
# GLUCOSE MONITORING
# ============================================

def evaluate_glucose_log(readings):
    """
    Evaluate home glucose readings.

    Args:
        readings: [{date, fasting, post_breakfast, post_lunch, post_dinner}]

    Returns:
        {avg, controlled_pct, out_of_range, needs_insulin}
    """
    if not readings:
        return None

    total = 0
    in_range = 0
    out_of_range = []

    # Targets per ADIPS/AAP:
    # Fasting: < 95
    # 1h post: < 140
    # 2h post: < 120

    for r in readings:
        for key, threshold in [("fasting", 95), ("post_breakfast", 140),
                                ("post_lunch", 140), ("post_dinner", 140)]:
            v = r.get(key)
            if v is None:
                continue
            total += 1
            try:
                val = float(v)
                if val <= threshold:
                    in_range += 1
                else:
                    out_of_range.append({
                        "date": r.get("date"),
                        "type": key,
                        "value": val,
                        "threshold": threshold,
                    })
            except Exception:
                pass

    if total == 0:
        return None

    controlled_pct = round(100.0 * in_range / total, 1)
    needs_insulin = controlled_pct < 70 or len(out_of_range) >= 4

    if controlled_pct >= 80:
        level = "controlled"
        label = "🟢 تحت السيطرة"
        color = "#10B981"
    elif controlled_pct >= 70:
        level = "borderline"
        label = "🟡 على الحد"
        color = "#F59E0B"
    else:
        level = "uncontrolled"
        label = "🔴 غير مسيطر — يحتاج أنسولين"
        color = "#DC2626"

    return {
        "total": total,
        "in_range": in_range,
        "out_of_range_count": len(out_of_range),
        "out_of_range": out_of_range,
        "controlled_pct": controlled_pct,
        "needs_insulin": needs_insulin,
        "level": level,
        "label": label,
        "color": color,
    }


# ============================================
# FETCH FROM DATABASE
# ============================================

def get_ogtt_data(clinic_id, patient_id):
    """Fetch latest OGTT values"""
    from core.db import db

    result = {"fasting": None, "1h": None, "2h": None, "date": None}

    try:
        labs = (
            db().table("lab_tests").select("*")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .eq("test_type", "glucose")
            .order("test_date", desc=True)
            .limit(3)
            .execute()
            .data or []
        )

        for lab in labs:
            rv = lab.get("result_value") or {}
            if not isinstance(rv, dict):
                continue

            if not result["fasting"] and rv.get("fasting"):
                result["fasting"] = rv["fasting"]
            if not result["1h"] and rv.get("h1"):
                result["1h"] = rv["h1"]
            if not result["2h"] and rv.get("h2"):
                result["2h"] = rv["h2"]
            if not result["2h"] and rv.get("hba1c"):
                pass  # could be added separately

            if not result["date"]:
                result["date"] = lab.get("test_date")
    except Exception:
        pass

    return result


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("GDM Screening Test")
    print("=" * 60)

    test_cases = [
        (85, 140, 120, "normal"),
        (95, 170, 145, "impaired"),
        (95, 185, 160, "gdm_diet"),
        (95, 190, 165, "gdm_diet"),
        (128, 200, 180, "overt_dm"),
    ]

    for i, (f, h1, h2, expected) in enumerate(test_cases, 1):
        r = evaluate_ogtt(f, h1, h2)
        ok = "✅" if r["level"] == expected else "❌"
        print("\n{}. OGTT (F={}, 1h={}, 2h={})".format(i, f, h1, h2))
        print("   {} Expected: {}, Got: {}".format(ok, expected, r["level"]))
        print("   {}".format(r["label"]))
        for c in r["criteria_met"]:
            print("   - {}".format(c))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
