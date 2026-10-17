# -*- coding: utf-8 -*-
"""
Bishop Score Service
تقييم جاهزية عنق الرحم للولادة
"""
from typing import Dict, List, Optional


# ============================================
# BISHOP SCORE COMPONENTS
# ============================================

DILATATION_SCORES = [
    (0, 0, "مغلق"),
    (1, 1, "1 سم"),
    (2, 2, "2 سم"),
    (3, 3, "3 سم"),
    (4, 4, "4 سم"),
    (5, 5, "5 سم"),
    (6, 8, "6 سم"),
    (7, 10, "7 سم"),
    (8, 12, "8+ سم"),
]

EFFACEMENT_SCORES = [
    (0, 0, "0-30%"),
    (30, 1, "30-50%"),
    (50, 2, "50-60%"),
    (60, 3, "60-70%"),
    (70, 4, "70-80%"),
    (80, 5, "80-100%"),
]

STATION_SCORES = [
    (-3, 0, "-3 (عالٍ)"),
    (-2, 1, "-2"),
    (-1, 2, "-1"),
    (0, 3, "0 (منتصف)"),
    (1, 4, "+1"),
    (2, 5, "+2"),
    (3, 5, "+3 (منخفض)"),
]

CONSISTENCY_SCORES = {
    "firm": (0, "صلب"),
    "medium": (1, "متوسط"),
    "soft": (2, "لين"),
}

POSITION_SCORES = {
    "posterior": (0, "خلفي"),
    "mid": (1, "متوسط"),
    "anterior": (2, "أمامي"),
}


# ============================================
# SCORE CALCULATION
# ============================================

def calculate_bishop_score(
    dilatation_cm,
    effacement_percent,
    station,
    consistency,
    position,
):
    """
    Calculate Bishop Score (0-13).

    Args:
        dilatation_cm: 0-10
        effacement_percent: 0-100
        station: -3 to +3
        consistency: 'firm' | 'medium' | 'soft'
        position: 'posterior' | 'mid' | 'anterior'

    Returns:
        {
            score, category, label, color, components, interpretation, recommendation
        }
    """
    components = {}

    # 1. Dilatation (0-3)
    dil_score = 0
    for threshold, score, label in DILATATION_SCORES:
        if dilatation_cm is not None and dilatation_cm >= threshold:
            dil_score = score
    components["dilatation"] = {
        "value": dilatation_cm,
        "score": dil_score,
        "max": 3,
        "label": "التوسع (Dilatation)",
        "unit": "سم",
    }

    # 2. Effacement (0-3)
    eff_score = 0
    for threshold, score, label in EFFACEMENT_SCORES:
        if effacement_percent is not None and effacement_percent >= threshold:
            eff_score = score
    components["effacement"] = {
        "value": effacement_percent,
        "score": eff_score,
        "max": 3,
        "label": "التلاشي (Effacement)",
        "unit": "%",
    }

    # 3. Station (0-3)
    st_score = 0
    if station is not None:
        for st_val, score, label in STATION_SCORES:
            if station == st_val:
                st_score = score
                break
        else:
            # Fallback
            if station <= -3:
                st_score = 0
            elif station >= 2:
                st_score = 5  # actually max is 3
    components["station"] = {
        "value": station,
        "score": st_score,
        "max": 3,
        "label": "المستوى (Station)",
        "unit": "",
    }

    # 4. Consistency (0-2)
    cons_score = 0
    if consistency in CONSISTENCY_SCORES:
        cons_score = CONSISTENCY_SCORES[consistency][0]
    components["consistency"] = {
        "value": consistency,
        "score": cons_score,
        "max": 2,
        "label": "قوام العنق (Consistency)",
        "unit": "",
    }

    # 5. Position (0-2)
    pos_score = 0
    if position in POSITION_SCORES:
        pos_score = POSITION_SCORES[position][0]
    components["position"] = {
        "value": position,
        "score": pos_score,
        "max": 2,
        "label": "وضعية العنق (Position)",
        "unit": "",
    }

    # Total
    total = dil_score + eff_score + st_score + cons_score + pos_score

    # Category
    if total >= 8:
        category = "ready"
        label = "✅ جاهز للتحريض"
        color = "#10B981"
        interpretation = "العنق جاهز للولادة — تحريض آمن"
        recommendation = [
            "تحريض آمن (Oxytocin/Arm rupturing)",
            "احتمالية نجاح عالية للولادة الطبيعية",
            "متابعة مستمرة",
        ]
    elif total >= 6:
        category = "moderate"
        label = "🟡 متوسط الجاهزية"
        color = "#F59E0B"
        interpretation = "العنق متوسط الجاهزية"
        recommendation = [
            "قد يحتاج تحضير بسيط قبل التحريض",
            "استخدام Prostaglandin (Misoprostol) قد يفيد",
            "إعادة التقييم بعد 4-6 ساعات",
        ]
    else:
        category = "unfavorable"
        label = "🔴 غير جاهز"
        color = "#DC2626"
        interpretation = "العنق غير جاهز للولادة"
        recommendation = [
            "لا يُنصح بالتحريض المباشر",
            "يحتاج تحضير العنق أولاً (Cervical Ripening)",
            "استخدام Misoprostol أو Foley Balloon",
            "إعادة التقييم بعد 12-24 ساعة",
        ]

    return {
        "score": total,
        "max_score": 13,
        "category": category,
        "label": label,
        "color": color,
        "components": components,
        "interpretation": interpretation,
        "recommendation": recommendation,
    }


def save_bishop_assessment(clinic_id, patient_id, score_data, notes=None, doctor_id=None):
    """Save Bishop Score to partogram_entries as a special entry"""
    from core.db import db, insert

    try:
        # Find or create active labor record
        labor_rows = (
            db().table("labor_records")
            .select("id")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .eq("status", "active")
            .limit(1)
            .execute()
            .data or []
        )

        if labor_rows:
            labor_id = labor_rows[0]["id"]
        else:
            # Create new labor record
            labor = insert("labor_records", {
                "clinic_id": clinic_id,
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "status": "active",
                "labor_start": __import__("datetime").datetime.utcnow().isoformat(),
            })
            labor_id = labor["id"]

        # Save entry
        entry = insert("partogram_entries", {
            "labor_id": labor_id,
            "clinic_id": clinic_id,
            "cervical_dilatation_cm": score_data["components"]["dilatation"]["value"],
            "fetal_station": score_data["components"]["station"]["value"],
            "effacement_percent": score_data["components"]["effacement"]["value"],
            "cervix_consistency": score_data["components"]["consistency"]["value"],
            "cervix_position": score_data["components"]["position"]["value"],
            "notes": "Bishop Score: {}/13. {}".format(score_data["score"], notes or ""),
        })

        return entry
    except Exception as e:
        print("[bishop] save failed: {}".format(e))
        return None


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Bishop Score Test")
    print("=" * 60)

    test_cases = [
        # (dil, eff, station, cons, pos, expected)
        (0, 30, -3, "firm", "posterior", "unfavorable"),  # 0
        (2, 50, -2, "medium", "mid", "unfavorable"),       # ~4
        (3, 70, -1, "medium", "mid", "moderate"),           # ~7
        (4, 80, 0, "soft", "anterior", "ready"),            # 11
    ]

    for i, tc in enumerate(test_cases, 1):
        dil, eff, st, cons, pos, expected = tc
        r = calculate_bishop_score(dil, eff, st, cons, pos)
        ok = "✅" if r["category"] == expected else "❌"
        print("\n{}. Dil={}cm, Eff={}%, Station={}, Cons={}, Pos={}".format(
            i, dil, eff, st, cons, pos))
        print("   {} Score: {}/13 — {}".format(ok, r["score"], r["label"]))
        for k, comp in r["components"].items():
            print("   - {}: {} ({} / {})".format(
                comp["label"], comp["value"], comp["score"], comp["max"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
