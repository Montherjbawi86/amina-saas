# -*- coding: utf-8 -*-
"""
Preeclampsia Screening Service
فحص ما قبل تسمم الحمل
"""
from datetime import datetime, date
from typing import Dict, List, Optional


# ============================================
# SEVERITY LEVELS
# ============================================

SEVERITY_LEVELS = {
    "none": {"label": "🟢 لا يوجد", "color": "#10B981"},
    "gestational_htn": {"label": "🟡 ارتفاع ضغط حمل", "color": "#F59E0B"},
    "mild_preeclampsia": {"label": "🟠 تسمم حمل خفيف", "color": "#F97316"},
    "severe_preeclampsia": {"label": "🔴 تسمم حمل شديد", "color": "#DC2626"},
    "hellp": {"label": "🚨 متلازمة HELLP", "color": "#991B1B"},
    "eclampsia": {"label": "⚡ إرجاج (Eclampsia)", "color": "#7F1D1D"},
}


def get_severity_meta(level):
    return SEVERITY_LEVELS.get(level, {"label": "—", "color": "#94A3B8"})


# ============================================
# CORE EVALUATION
# ============================================

def evaluate_preeclampsia(
    systolic,
    diastolic,
    proteinuria=None,
    platelets=None,
    liver_enzymes=None,
    creatinine=None,
    symptoms=None,
):
    """
    Comprehensive preeclampsia evaluation.

    Args:
        systolic: BP systolic (mmHg)
        diastolic: BP diastolic (mmHg)
        proteinuria: '+' / '+' / '++' / '+++' / '++++' OR mg/dL
        platelets: platelets count (/μL)
        liver_enzymes: AST/ALT (multiple of normal)
        creatinine: mg/dL
        symptoms: list of [headache, visual, epigastric, edema]

    Returns:
        {level, label, color, criteria_met, recommendation, urgent, details}
    """
    symptoms = symptoms or []
    criteria = []
    severity_score = 0

    # 1. Blood pressure evaluation
    if systolic and diastolic:
        if systolic >= 160 or diastolic >= 110:
            criteria.append("🔴 ضغط شديد (≥160/110)")
            severity_score += 30
        elif systolic >= 140 or diastolic >= 90:
            criteria.append("🟡 ارتفاع ضغط (≥140/90)")
            severity_score += 15

    # 2. Proteinuria
    protein_severity = _proteinuria_level(proteinuria)
    if protein_severity == "severe":
        criteria.append("🔴 بروتين البول شديد")
        severity_score += 25
    elif protein_severity == "moderate":
        criteria.append("🟠 بروتين البول متوسط")
        severity_score += 15
    elif protein_severity == "mild":
        criteria.append("🟡 بروتين البول خفيف")
        severity_score += 5

    # 3. Platelets
    if platelets is not None:
        try:
            plt = float(platelets)
            if plt < 100000:
                criteria.append("🔴 صفائح دموية منخفضة ({:,}/μL)".format(int(plt)))
                severity_score += 25
            elif plt < 150000:
                criteria.append("🟡 صفائح منخفضة قليلاً ({:,}/μL)".format(int(plt)))
                severity_score += 10
        except Exception:
            pass

    # 4. Liver enzymes
    if liver_enzymes is not None:
        try:
            le = float(liver_enzymes)
            if le >= 2.0:
                criteria.append("🔴 إنزيمات كبد مرتفعة (×{})".format(le))
                severity_score += 20
            elif le >= 1.5:
                criteria.append("🟠 إنزيمات كبد مرتفعة قليلاً (×{})".format(le))
                severity_score += 10
        except Exception:
            pass

    # 5. Creatinine
    if creatinine is not None:
        try:
            cr = float(creatinine)
            if cr >= 1.1:
                criteria.append("🔴 كرياتينين مرتفع ({})".format(cr))
                severity_score += 15
        except Exception:
            pass

    # 6. Symptoms
    if "headache" in symptoms:
        criteria.append("⚠️ صداع شديد")
        severity_score += 10
    if "visual" in symptoms:
        criteria.append("⚠️ اضطرابات بصرية")
        severity_score += 10
    if "epigastric" in symptoms:
        criteria.append("⚠️ ألم شرسوفي")
        severity_score += 10
    if "edema" in symptoms:
        criteria.append("⚠️ تورم مفاجئ")
        severity_score += 5

    # ============ CLASSIFICATION ============
    has_bp_problem = systolic and diastolic and (systolic >= 140 or diastolic >= 90)
    has_proteinuria = protein_severity in ("mild", "moderate", "severe")

    # HELLP: Hemolysis + Elevated Liver + Low Platelets
    has_low_plt = platelets and float(platelets) < 100000
    has_high_liver = liver_enzymes and float(liver_enzymes) >= 2.0
    if has_low_plt and has_high_liver:
        level = "hellp"
        recommendation = [
            "🚨 حالة طارئة — نقل فوري للمستشفى",
            "تقييم فوري للولادة",
            "ستيرويدات لتسريع نضج رئة الجنين",
            "مراقبة دقيقة للصفائح",
        ]
        urgent = True
    # Severe preeclampsia
    elif (has_bp_problem and protein_severity == "severe") or severity_score >= 50:
        level = "severe_preeclampsia"
        recommendation = [
            "⚠️ تحويل فوري للمستشفى",
            "بدء أدوية خافضة للضغط (لابيتالول/نيفيديبين)",
            "كبريتات المغنيسيوم للوقاية من الإرجاج",
            "تقييم التوقيت المناسب للولادة",
        ]
        urgent = True
    # Mild preeclampsia
    elif has_bp_problem and has_proteinuria:
        level = "mild_preeclampsia"
        recommendation = [
            "مراقبة أسبوعية على الأقل",
            "فحوصات دم كاملة (CBC, وظائف كبد)",
            "قياس الضغط مرتين يومياً",
            "فحص حركة الجنين يومياً",
        ]
        urgent = False
    # Gestational hypertension (no protein)
    elif has_bp_problem:
        level = "gestational_htn"
        recommendation = [
            "مراقبة الضغط أسبوعياً",
            "فحص بروتين البول",
            "مراقبة نمو الجنين",
        ]
        urgent = False
    else:
        level = "none"
        recommendation = ["متابعة روتينية"]
        urgent = False

    meta = get_severity_meta(level)

    return {
        "level": level,
        "label": meta["label"],
        "color": meta["color"],
        "criteria_met": criteria,
        "recommendation": recommendation,
        "urgent": urgent,
        "score": severity_score,
    }


def _proteinuria_level(value):
    """Classify proteinuria"""
    if not value:
        return "none"
    v = str(value).strip().upper()
    if v in ("+", "+1"):
        return "mild"
    if v in ("++", "+2"):
        return "moderate"
    if v in ("+++", "+3", "++++", "+4"):
        return "severe"
    if v in ("NEG", "NEGATIVE", "TRACE", "-"):
        return "none"
    # Try numeric (mg/dL)
    try:
        n = float(v)
        if n >= 300:
            return "severe"
        elif n >= 100:
            return "moderate"
        elif n >= 30:
            return "mild"
    except Exception:
        pass
    return "none"


# ============================================
# FETCH FROM DATABASE
# ============================================

def get_preeclampsia_data(clinic_id, patient_id):
    """Fetch latest BP + proteinuria + symptoms + labs"""
    from core.db import db

    result = {
        "systolic": None,
        "diastolic": None,
        "proteinuria": None,
        "platelets": None,
        "liver_enzymes": None,
        "creatinine": None,
        "symptoms": [],
        "date": None,
    }

    try:
        # Latest visit BP
        visits = (
            db().table("visits").select(
                "visit_date,bp_systolic,bp_diastolic,notes"
            ).eq("clinic_id", clinic_id).eq("patient_id", patient_id)
            .order("visit_date", desc=True).limit(1).execute().data or []
        )

        if visits:
            v = visits[0]
            result["systolic"] = v.get("bp_systolic")
            result["diastolic"] = v.get("bp_diastolic")
            result["date"] = v.get("visit_date")
    except Exception:
        pass

    try:
        # Latest CBC + urine
        labs = (
            db().table("lab_tests").select(
                "test_date,test_type,result_value"
            ).eq("clinic_id", clinic_id).eq("patient_id", patient_id)
            .in_("test_type", ["urine", "cbc"])
            .order("test_date", desc=True).limit(5).execute().data or []
        )

        for lab in labs:
            rv = lab.get("result_value") or {}
            if not isinstance(rv, dict):
                continue

            if lab.get("test_type") == "urine":
                if not result["proteinuria"]:
                    result["proteinuria"] = rv.get("protein")

            if lab.get("test_type") == "cbc":
                if not result["platelets"]:
                    result["platelets"] = rv.get("plt")
    except Exception:
        pass

    return result


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Preeclampsia Screening Test")
    print("=" * 60)

    test_cases = [
        # (systolic, diastolic, protein, platelets, liver, creat, symptoms, expected)
        (120, 80, "NEG", 250000, 1.0, 0.8, [], "none"),
        (145, 92, "NEG", 220000, 1.0, 0.9, [], "gestational_htn"),
        (150, 95, "++", 180000, 1.2, 0.9, ["headache"], "mild_preeclampsia"),
        (165, 115, "+++", 90000, 2.5, 1.3, ["headache", "visual"], "severe_preeclampsia"),
        (170, 115, "++++", 85000, 3.0, 1.4, ["headache"], "hellp"),
    ]

    for i, tc in enumerate(test_cases, 1):
        sys_bp, dia_bp, prot, plt, liver, creat, sym, expected = tc
        r = evaluate_preeclampsia(
            sys_bp, dia_bp, prot, plt, liver, creat, sym
        )
        ok = "✅" if r["level"] == expected else "❌"
        print("\n{}. Case: BP={}/{}, protein={}, plt={}".format(
            i, sys_bp, dia_bp, prot, plt))
        print("   {} Expected: {}, Got: {}".format(ok, expected, r["level"]))
        print("   {}".format(r["label"]))
        for c in r["criteria_met"]:
            print("   - {}".format(c))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
