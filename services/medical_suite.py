# -*- coding: utf-8 -*-
"""
Medical Suite Service
الرعاية الطبية المتقدمة — 4 ميزات مدمجة
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from core.db import db


# ============================================
# 1. RISK SCORE CALCULATOR
# ============================================

def calculate_age(dob_str):
    """Calculate age from date of birth"""
    if not dob_str:
        return None
    try:
        if isinstance(dob_str, str):
            dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        elif isinstance(dob_str, date):
            dob = dob_str
        else:
            return None
        days = (date.today() - dob).days
        return days // 365
    except Exception:
        return None


def calculate_risk_score(patient, visits=None):
    """
    Calculate pregnancy risk score.
    Returns: {
        score: 0-100,
        level: low/medium/high,
        factors: [{name, points, note}],
        recommendations: [...]
    }
    """
    if not patient:
        return None

    factors = []
    score = 0

    # 1. Age
    age = calculate_age(patient.get("date_of_birth"))
    if age is not None:
        if age < 18:
            factors.append({"name": "عمر أقل من 18", "points": 15, "note": "خطر مضاعفات"})
            score += 15
        elif age >= 35:
            factors.append({"name": "عمر 35+", "points": 10, "note": "خطر تشوهات كروموسومية"})
            score += 10
        elif age >= 40:
            score += 5  # extra
            factors.append({"name": "عمر 40+", "points": 5, "note": "خطر عالي"})

    # 2. Gravida/Para
    gravida = patient.get("gravida") or 0
    para = patient.get("para") or 0

    if gravida == 1:
        factors.append({"name": "حمل أول", "points": 5, "note": "يحتاج متابعة دقيقة"})
        score += 5
    if gravida >= 5:
        factors.append({"name": "حمل خامس أو أكثر", "points": 10, "note": "خطر نزيف بعد الولادة"})
        score += 10
    if para >= 4:
        factors.append({"name": "4 ولادات سابقة أو أكثر", "points": 8, "note": "خطر تمزق الرحم"})
        score += 8

    # 3. Risk level (from patient record)
    risk = patient.get("risk_level", "low")
    if risk == "high":
        factors.append({"name": "مصنّفة عالية الخطورة", "points": 20, "note": ""})
        score += 20
    elif risk == "medium":
        factors.append({"name": "مصنّفة متوسطة الخطورة", "points": 10, "note": ""})
        score += 10

    # 4. Visits analysis
    if visits:
        # Recent BP
        recent = visits[:3]
        for v in recent:
            systolic = v.get("bp_systolic")
            diastolic = v.get("bp_diastolic")
            if systolic and diastolic:
                if systolic >= 160 or diastolic >= 110:
                    factors.append({"name": "ضغط دم شديد الارتفاع", "points": 25,
                                    "note": "{}/{} — يحتاج تدخل فوري".format(systolic, diastolic)})
                    score += 25
                    break
                elif systolic >= 140 or diastolic >= 90:
                    factors.append({"name": "ارتفاع ضغط الدم", "points": 15,
                                    "note": "{}/{}".format(systolic, diastolic)})
                    score += 15
                    break

        # Low fetal HR
        for v in recent:
            hr = v.get("fetal_heart_rate")
            if hr:
                if hr < 110 or hr > 160:
                    factors.append({"name": "نبض جنين غير طبيعي", "points": 15,
                                    "note": "{} bpm".format(hr)})
                    score += 15
                    break

    # 5. Blood type
    blood = patient.get("blood_type") or ""
    if "-" in blood:
        factors.append({"name": "Rh سلبي", "points": 5, "note": "يحتاج Anti-D"})
        score += 5

    # Clamp score
    score = min(score, 100)

    # Determine level
    if score >= 40:
        level = "high"
    elif score >= 20:
        level = "medium"
    else:
        level = "low"

    # Recommendations
    recs = []
    if level == "high":
        recs.append("🚨 متابعة أسبوعية مطلوبة")
        recs.append("تحويل لأخصائي طب الأمومة والأجنة")
        recs.append("تقييم مستشفى للولادة")
    elif level == "medium":
        recs.append("متابعة كل أسبوعين")
        recs.append("مراقبة ضغط الدم والسكر")
        recs.append("فحوصات إضافية حسب الحالة")
    else:
        recs.append("متابعة روتينية كل 4 أسابيع")
        recs.append("تغذية سليمة ومكملات")

    return {
        "score": score,
        "level": level,
        "factors": factors,
        "recommendations": recs,
        "age": age,
    }


def get_risk_level_meta(level):
    return {
        "low": {"label": "🟢 منخفض", "color": "#10B981"},
        "medium": {"label": "🟡 متوسط", "color": "#F59E0B"},
        "high": {"label": "🔴 عالي", "color": "#DC2626"},
    }.get(level, {"label": "—", "color": "#94A3B8"})


# ============================================
# 2. ANTENATAL CARE PLAN (WHO 8 visits)
# ============================================

WHO_ANTENATAL_SCHEDULE = [
    {
        "visit_num": 1,
        "week_start": 8,
        "week_end": 12,
        "title": "الزيارة الأولى (Booking)",
        "tests": [
            "CBC (تعداد الدم)",
            "فصيلة الدم + Rh",
            "سكر الدم",
            "وظائف الكلى",
            "تحليل البول",
            "HIV, HBsAg, VDRL",
            "سونار (تحديد العمر)",
        ],
        "actions": [
            "تسجيل الحمل",
            "حساب EDD",
            "تقييم المخاطر",
            "بدء حمض الفوليك",
        ],
    },
    {
        "visit_num": 2,
        "week_start": 14,
        "week_end": 20,
        "title": "الزيارة الثانية",
        "tests": ["ضغط الدم", "وزن", "تحليل بول"],
        "actions": ["متابعة نمو الرحم", "سونار تشريحي (18-20)"],
    },
    {
        "visit_num": 3,
        "week_start": 24,
        "week_end": 28,
        "title": "الزيارة الثالثة",
        "tests": [
            "CBC (فقر الدم)",
            "OGTT (سكري الحمل)",
            "ضغط الدم",
            "وزن",
        ],
        "actions": ["قياس ارتفاع الرحم", "فحص حركة الجنين"],
    },
    {
        "visit_num": 4,
        "week_start": 30,
        "week_end": 32,
        "title": "الزيارة الرابعة",
        "tests": ["ضغط الدم", "وزن", "تحليل بول"],
        "actions": ["تقييم نمو الجنين", "فحص وضعية الجنين"],
    },
    {
        "visit_num": 5,
        "week_start": 34,
        "week_end": 36,
        "title": "الزيارة الخامسة",
        "tests": ["ضغط الدم", "وزن", "GBS مسحة"],
        "actions": ["تقييم الحوض", "مناقشة خطة الولادة"],
    },
    {
        "visit_num": 6,
        "week_start": 36,
        "week_end": 38,
        "title": "الزيارة السادسة",
        "tests": ["ضغط الدم", "وزن", "فحص الجنين"],
        "actions": ["تأكيد وضعية الرأس", "مناقشة علامات المخاض"],
    },
    {
        "visit_num": 7,
        "week_start": 38,
        "week_end": 40,
        "title": "الزيارة السابعة",
        "tests": ["ضغط الدم", "وزن", "CTG إذا لزم"],
        "actions": ["متابعة حركة الجنين", "تقييم السائل الأمنيوسي"],
    },
    {
        "visit_num": 8,
        "week_start": 40,
        "week_end": 42,
        "title": "الزيارة الثامنة (ما بعد الأسبوع 40)",
        "tests": ["ضغط الدم", "وزن", "CTG"],
        "actions": [
            "تحريض إذا لزم (بعد 41 أسبوع)",
            "متابعة يومية أو كل يومين",
        ],
    },
]


def calculate_lmp_from_edd(edd):
    """Calculate LMP from EDD (280 days before)"""
    if not edd:
        return None
    try:
        if isinstance(edd, str):
            edd_d = datetime.strptime(edd[:10], "%Y-%m-%d").date()
        elif isinstance(edd, date):
            edd_d = edd
        else:
            return None
        return edd_d - timedelta(days=280)
    except Exception:
        return None


def calculate_edd_from_lmp(lmp):
    """Calculate EDD from LMP (280 days after)"""
    if not lmp:
        return None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        elif isinstance(lmp, date):
            lmp_d = lmp
        else:
            return None
        return lmp_d + timedelta(days=280)
    except Exception:
        return None


def get_antenatal_plan(patient):
    """
    Generate personalized antenatal care plan.
    Returns: {lmp, edd, current_week, visits: [...]}
    """
    if not patient:
        return None

    lmp_str = patient.get("lmp")
    edd_str = patient.get("edd")

    # Calculate LMP from EDD if missing
    if not lmp_str and edd_str:
        lmp = calculate_lmp_from_edd(edd_str)
    else:
        try:
            lmp = datetime.strptime(lmp_str[:10], "%Y-%m-%d").date() if lmp_str else None
        except Exception:
            lmp = None

    # Calculate EDD from LMP if missing
    if not edd_str and lmp:
        edd = calculate_edd_from_lmp(lmp)
    else:
        try:
            edd = datetime.strptime(edd_str[:10], "%Y-%m-%d").date() if edd_str else None
        except Exception:
            edd = None

    if not lmp or not edd:
        return None

    # Current week
    days_pregnant = (date.today() - lmp).days
    current_week = days_pregnant // 7 if days_pregnant > 0 else 0

    # Build visits with dates
    visits = []
    for schedule in WHO_ANTENATAL_SCHEDULE:
        # Pick mid-point week
        target_week = (schedule["week_start"] + schedule["week_end"]) // 2
        target_date = lmp + timedelta(days=target_week * 7)

        # Status
        if current_week > schedule["week_end"]:
            status = "past"
        elif current_week >= schedule["week_start"]:
            status = "current"
        else:
            status = "upcoming"

        visits.append({
            **schedule,
            "target_week": target_week,
            "target_date": target_date,
            "status": status,
        })

    return {
        "lmp": lmp,
        "edd": edd,
        "current_week": current_week,
        "visits": visits,
    }


# ============================================
# 3. ANEMIA SCREENING (already part of lab_tests, but here for tracking)
# ============================================

def get_anemia_thresholds():
    """WHO anemia thresholds by trimester"""
    return {
        "first": {"label": "الثلث الأول (1-12)", "hb": 11.0},
        "second": {"label": "الثلث الثاني (13-27)", "hb": 10.5},
        "third": {"label": "الثلث الثالث (28-40)", "hb": 11.0},
    }


def classify_anemia(hb, week):
    """
    Classify anemia severity.
    hb: hemoglobin g/dL
    week: gestational week
    """
    if not hb or not week:
        return None

    # Determine trimester
    if week <= 12:
        threshold = 11.0
        trimester = "first"
    elif week <= 27:
        threshold = 10.5
        trimester = "second"
    else:
        threshold = 11.0
        trimester = "third"

    if hb >= threshold:
        category = "normal"
        severity = "🟢 طبيعي"
        color = "#10B981"
        recommendation = "استمر بالمكملات الوقائية"
    elif hb >= 10.0:
        category = "mild"
        severity = "🟡 فقر دم خفيف"
        color = "#F59E0B"
        recommendation = "زيادة جرعة الحديد — إعادة الفحص بعد 4 أسابيع"
    elif hb >= 7.0:
        category = "moderate"
        severity = "🟠 فقر دم متوسط"
        color = "#F97316"
        recommendation = "حديد عن طريق الفم بجرعة عالية + فوليك + B12، فحص أسبوعي"
    else:
        category = "severe"
        severity = "🔴 فقر دم شديد"
        color = "#DC2626"
        recommendation = "🚨 تحويل فوري — قد يحتاج نقل دم"

    return {
        "category": category,
        "severity": severity,
        "color": color,
        "threshold": threshold,
        "trimester": trimester,
        "recommendation": recommendation,
        "hb": hb,
    }


# ============================================
# MASTER FUNCTION
# ============================================

def get_patient_medical_summary(clinic_id, patient_id):
    """
    Comprehensive medical summary for a patient.
    Returns: {patient, risk, care_plan, latest_anemia}
    """
    from core.db import db

    try:
        # Fetch patient
        p_rows = db().table("patients").select("*").eq(
            "id", patient_id
        ).eq("clinic_id", clinic_id).limit(1).execute().data or []
        patient = p_rows[0] if p_rows else None

        if not patient:
            return None

        # Fetch recent visits
        visits = db().table("visits").select(
            "visit_date,bp_systolic,bp_diastolic,fetal_heart_rate,gestational_age_weeks"
        ).eq("clinic_id", clinic_id).eq("patient_id", patient_id).order(
            "visit_date", desc=True
        ).limit(10).execute().data or []

        # Risk score
        risk = calculate_risk_score(patient, visits)

        # Care plan
        care_plan = get_antenatal_plan(patient)

        # Latest anemia (from lab_tests)
        anemia = None
        try:
            labs = db().table("lab_tests").select(
                "test_date,result_value"
            ).eq("clinic_id", clinic_id).eq("patient_id", patient_id).eq(
                "test_type", "cbc"
            ).order("test_date", desc=True).limit(1).execute().data or []

            if labs:
                rv = labs[0].get("result_value") or {}
                hb = rv.get("hgb")
                if hb:
                    try:
                        hb = float(hb)
                        week = care_plan["current_week"] if care_plan else 0
                        anemia = classify_anemia(hb, week)
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "patient": patient,
            "risk": risk,
            "care_plan": care_plan,
            "anemia": anemia,
        }
    except Exception as e:
        print("[medical_suite] summary error: {}".format(e))
        return None


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Medical Suite Test")
    print("=" * 60)

    # Test 1: Age
    print("\n1. Age calculation (DOB 1995-03-15):")
    age = calculate_age("1995-03-15")
    print("   Age: {}".format(age))

    # Test 2: Risk score
    print("\n2. Risk score (high-risk patient):")
    patient = {
        "date_of_birth": "1985-01-01",
        "gravida": 5,
        "para": 4,
        "risk_level": "high",
        "blood_type": "O-",
        "lmp": "2026-03-15",
        "edd": "2026-12-20",
    }
    visits = [
        {"bp_systolic": 165, "bp_diastolic": 115, "fetal_heart_rate": 100}
    ]
    risk = calculate_risk_score(patient, visits)
    print("   Score: {}".format(risk["score"]))
    print("   Level: {}".format(risk["level"]))
    print("   Factors:")
    for f in risk["factors"]:
        print("     - {} (+{})".format(f["name"], f["points"]))

    # Test 3: Antenatal plan
    print("\n3. Antenatal care plan:")
    plan = get_antenatal_plan(patient)
    if plan:
        print("   LMP: {}".format(plan["lmp"]))
        print("   EDD: {}".format(plan["edd"]))
        print("   Current week: {}".format(plan["current_week"]))
        print("   Total visits: {}".format(len(plan["visits"])))
        for v in plan["visits"][:3]:
            print("     Visit {}: {} (week {})".format(
                v["visit_num"], v["status"], v["target_week"]))

    # Test 4: Anemia
    print("\n4. Anemia classification:")
    for hb, week in [(9.5, 20), (12.0, 20), (6.5, 30)]:
        r = classify_anemia(hb, week)
        print("   Hb {} @ week {}: {}".format(hb, week, r["severity"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
