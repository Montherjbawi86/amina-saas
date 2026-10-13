# -*- coding: utf-8 -*-
"""
Lab Tests Service
إدارة التحاليل المخبرية — 12 نوع مع حقول مخصصة
"""
from datetime import datetime, date
from typing import Optional, Dict, List, Any

from core.db import db, insert, update, delete, select


# ============================================
# TEST CATALOG — 12 تحليل
# ============================================

LAB_TEST_TYPES = {
    "cbc": {
        "name_ar": "تعداد الدم الكامل (CBC)",
        "name_en": "Complete Blood Count",
        "icon": "🩸",
        "fields": [
            {"key": "hgb", "label": "الهيموغلوبين (Hgb)", "unit": "g/dL",
             "range": "12.0 - 16.0", "min": 12.0, "max": 16.0},
            {"key": "wbc", "label": "كريات الدم البيضاء (WBC)", "unit": "/μL",
             "range": "4000 - 11000", "min": 4000, "max": 11000},
            {"key": "plt", "label": "الصفائح الدموية (PLT)", "unit": "/μL",
             "range": "150000 - 450000", "min": 150000, "max": 450000},
            {"key": "rbc", "label": "كريات الدم الحمراء (RBC)", "unit": "million/μL",
             "range": "4.2 - 5.4", "min": 4.2, "max": 5.4},
            {"key": "hct", "label": "الهيماتوكريت (HCT)", "unit": "%",
             "range": "36 - 46", "min": 36, "max": 46},
            {"key": "mcv", "label": "حجم الكرية (MCV)", "unit": "fL",
             "range": "80 - 100", "min": 80, "max": 100},
        ],
    },
    "glucose": {
        "name_ar": "سكر الدم (Glucose)",
        "name_en": "Blood Glucose",
        "icon": "🍬",
        "fields": [
            {"key": "fasting", "label": "صائم (Fasting)", "unit": "mg/dL",
             "range": "70 - 100", "min": 70, "max": 100},
            {"key": "random", "label": "عشوائي (Random)", "unit": "mg/dL",
             "range": "70 - 140", "min": 70, "max": 140},
            {"key": "hba1c", "label": "HbA1c", "unit": "%",
             "range": "4.0 - 5.6", "min": 4.0, "max": 5.6},
        ],
    },
    "urine": {
        "name_ar": "تحليل البول (Urine Analysis)",
        "name_en": "Urine Analysis",
        "icon": "💧",
        "fields": [
            {"key": "protein", "label": "البروتين", "unit": "",
             "range": "Negative", "type": "text"},
            {"key": "glucose", "label": "السكر", "unit": "",
             "range": "Negative", "type": "text"},
            {"key": "ketones", "label": "الكيتونات", "unit": "",
             "range": "Negative", "type": "text"},
            {"key": "blood", "label": "الدم", "unit": "",
             "range": "Negative", "type": "text"},
            {"key": "wbc", "label": "كريات بيضاء", "unit": "/HPF",
             "range": "0 - 5", "min": 0, "max": 5},
            {"key": "rbc", "label": "كريات حمراء", "unit": "/HPF",
             "range": "0 - 2", "min": 0, "max": 2},
            {"key": "ph", "label": "pH", "unit": "",
             "range": "4.5 - 8.0", "min": 4.5, "max": 8.0},
            {"key": "bacteria", "label": "بكتيريا", "unit": "",
             "range": "None", "type": "text"},
        ],
    },
    "tsh": {
        "name_ar": "الغدة الدرقية (TSH)",
        "name_en": "Thyroid Stimulating Hormone",
        "icon": "🦋",
        "fields": [
            {"key": "tsh", "label": "TSH", "unit": "mIU/L",
             "range": "0.4 - 4.0", "min": 0.4, "max": 4.0},
            {"key": "t3", "label": "T3", "unit": "ng/dL",
             "range": "80 - 200", "min": 80, "max": 200},
            {"key": "t4", "label": "T4", "unit": "μg/dL",
             "range": "5.0 - 12.0", "min": 5.0, "max": 12.0},
        ],
    },
    "ferritin": {
        "name_ar": "مخزون الحديد (Ferritin)",
        "name_en": "Ferritin",
        "icon": "⚙️",
        "fields": [
            {"key": "ferritin", "label": "Ferritin", "unit": "ng/mL",
             "range": "15 - 150", "min": 15, "max": 150},
        ],
    },
    "blood_group": {
        "name_ar": "فصيلة الدم",
        "name_en": "Blood Group",
        "icon": "🅰️",
        "fields": [
            {"key": "abo", "label": "ABO", "unit": "",
             "range": "A/B/AB/O", "type": "text"},
            {"key": "rh", "label": "Rh", "unit": "",
             "range": "+/-", "type": "text"},
        ],
    },
    "hepatitis_b": {
        "name_ar": "التهاب الكبد B",
        "name_en": "Hepatitis B",
        "icon": "🦠",
        "fields": [
            {"key": "hbsag", "label": "HBsAg", "unit": "",
             "range": "Negative", "type": "text"},
            {"key": "anti_hbs", "label": "Anti-HBs", "unit": "",
             "range": "Positive", "type": "text"},
        ],
    },
    "hepatitis_c": {
        "name_ar": "التهاب الكبد C",
        "name_en": "Hepatitis C",
        "icon": "🦠",
        "fields": [
            {"key": "anti_hcv", "label": "Anti-HCV", "unit": "",
             "range": "Negative", "type": "text"},
        ],
    },
    "hiv": {
        "name_ar": "فيروس نقص المناعة (HIV)",
        "name_en": "HIV",
        "icon": "🛡️",
        "fields": [
            {"key": "hiv", "label": "HIV Ab", "unit": "",
             "range": "Negative", "type": "text"},
        ],
    },
    "rubella": {
        "name_ar": "الحصبة الألمانية (Rubella)",
        "name_en": "Rubella IgG",
        "icon": "🧬",
        "fields": [
            {"key": "igg", "label": "IgG", "unit": "IU/mL",
             "range": "> 10 (immune)", "min": 10, "max": 999999},
            {"key": "igm", "label": "IgM", "unit": "",
             "range": "Negative", "type": "text"},
        ],
    },
    "vitamin_d": {
        "name_ar": "فيتامين D",
        "name_en": "Vitamin D (25-OH)",
        "icon": "☀️",
        "fields": [
            {"key": "vit_d", "label": "25-OH Vitamin D", "unit": "ng/mL",
             "range": "30 - 100", "min": 30, "max": 100},
        ],
    },
    "calcium": {
        "name_ar": "الكالسيوم",
        "name_en": "Calcium",
        "icon": "🦴",
        "fields": [
            {"key": "total", "label": "Total Calcium", "unit": "mg/dL",
             "range": "8.5 - 10.5", "min": 8.5, "max": 10.5},
            {"key": "ionized", "label": "Ionized Calcium", "unit": "mg/dL",
             "range": "4.5 - 5.3", "min": 4.5, "max": 5.3},
        ],
    },
}


def get_test_catalog():
    return LAB_TEST_TYPES


def get_test_info(test_type):
    return LAB_TEST_TYPES.get(test_type)


def get_test_label(test_type):
    info = LAB_TEST_TYPES.get(test_type)
    if not info:
        return test_type
    return "{} {}".format(info.get("icon", ""), info.get("name_ar", test_type))


def check_abnormality(test_type, result_value):
    info = LAB_TEST_TYPES.get(test_type)
    if not info or not result_value:
        return False, "normal", []

    abnormal_fields = []
    severities = []

    for field in info.get("fields", []):
        key = field["key"]
        val = result_value.get(key)
        if val is None or val == "":
            continue

        field_type = field.get("type", "numeric")

        if field_type == "text":
            expected = field.get("range", "").lower()
            actual = str(val).lower().strip()
            if expected and expected not in actual and actual not in expected:
                abnormal_fields.append({
                    "key": key, "label": field["label"],
                    "value": val, "expected": field.get("range"),
                    "severity": "moderate"
                })
                severities.append("moderate")
        else:
            try:
                v = float(val)
                mn = field.get("min")
                mx = field.get("max")
                if mn is None or mx is None:
                    continue

                if v < mn:
                    deviation = (mn - v) / mn if mn > 0 else 1
                    severity = _severity_from_deviation(deviation, "low")
                    abnormal_fields.append({
                        "key": key, "label": field["label"],
                        "value": val, "expected": field.get("range"),
                        "direction": "low", "severity": severity
                    })
                    severities.append(severity)
                elif v > mx:
                    deviation = (v - mx) / mx if mx > 0 else 1
                    severity = _severity_from_deviation(deviation, "high")
                    abnormal_fields.append({
                        "key": key, "label": field["label"],
                        "value": val, "expected": field.get("range"),
                        "direction": "high", "severity": severity
                    })
                    severities.append(severity)
            except (ValueError, TypeError):
                continue

    is_abnormal = len(abnormal_fields) > 0

    if "severe" in severities:
        overall = "severe"
    elif "moderate" in severities:
        overall = "moderate"
    elif "mild" in severities:
        overall = "mild"
    else:
        overall = "normal"

    return is_abnormal, overall, abnormal_fields


def _severity_from_deviation(deviation, direction):
    if deviation < 0.05:
        return "mild"
    elif deviation < 0.20:
        return "moderate"
    else:
        return "severe"


def get_severity_label(severity):
    return {
        "normal": "🟢 طبيعي",
        "mild": "🟡 خفيف",
        "moderate": "🟠 متوسط",
        "severe": "🔴 شديد",
    }.get(severity, "—")


def create_lab_test(clinic_id, patient_id, test_type, result_value,
                    doctor_id=None, visit_id=None, test_date=None,
                    lab_name=None, notes=None, attachment_url=None):
    info = LAB_TEST_TYPES.get(test_type)
    if not info:
        raise ValueError("Unknown test type: " + str(test_type))

    is_abnormal, severity, abnormal_fields = check_abnormality(test_type, result_value)

    row = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "visit_id": visit_id,
        "doctor_id": doctor_id,
        "test_type": test_type,
        "test_name": info["name_ar"],
        "test_date": str(test_date) if test_date else str(date.today()),
        "result_value": result_value or {},
        "is_abnormal": is_abnormal,
        "severity": severity,
        "lab_name": lab_name,
        "notes": notes,
        "attachment_url": attachment_url,
        "status": "completed",
    }

    return insert("lab_tests", row)


def get_lab_test(clinic_id, test_id):
    rows = (
        db().table("lab_tests")
        .select("*")
        .eq("clinic_id", clinic_id)
        .eq("id", test_id)
        .limit(1)
        .execute()
        .data or []
    )
    return rows[0] if rows else None


def list_lab_tests(clinic_id, patient_id=None, test_type=None,
                   date_from=None, date_to=None, only_abnormal=False,
                   limit=500):
    try:
        q = db().table("lab_tests").select("*").eq("clinic_id", clinic_id)

        if patient_id:
            q = q.eq("patient_id", patient_id)
        if test_type:
            q = q.eq("test_type", test_type)
        if date_from:
            q = q.gte("test_date", str(date_from))
        if date_to:
            q = q.lte("test_date", str(date_to))
        if only_abnormal:
            q = q.eq("is_abnormal", True)

        q = q.order("test_date", desc=True).limit(limit)
        return q.execute().data or []
    except Exception as e:
        print("[lab_tests] list error: {}".format(e))
        return []


def list_patient_tests(clinic_id, patient_id, limit=100):
    return list_lab_tests(clinic_id, patient_id=patient_id, limit=limit)


def update_lab_test(clinic_id, test_id, **fields):
    allowed = {
        "test_date", "result_value", "lab_name", "notes",
        "attachment_url", "status", "visit_id",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}

    if "result_value" in clean:
        test = get_lab_test(clinic_id, test_id)
        if test:
            is_abn, sev, _ = check_abnormality(test["test_type"], clean["result_value"])
            clean["is_abnormal"] = is_abn
            clean["severity"] = sev

    clean["updated_at"] = datetime.utcnow().isoformat()

    if not clean:
        raise ValueError("No valid fields")

    return update("lab_tests", {"id": test_id, "clinic_id": clinic_id}, clean)


def delete_lab_test(clinic_id, test_id):
    return delete("lab_tests", id=test_id, clinic_id=clinic_id)


def get_patient_lab_summary(clinic_id, patient_id):
    tests = list_patient_tests(clinic_id, patient_id, limit=200)
    total = len(tests)
    abnormal = sum(1 for t in tests if t.get("is_abnormal"))
    by_type = {}
    for t in tests:
        tt = t.get("test_type", "other")
        by_type.setdefault(tt, {"total": 0, "abnormal": 0})
        by_type[tt]["total"] += 1
        if t.get("is_abnormal"):
            by_type[tt]["abnormal"] += 1

    return {
        "total": total,
        "abnormal": abnormal,
        "normal": total - abnormal,
        "by_type": by_type,
        "latest_date": tests[0]["test_date"] if tests else None,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Lab Tests Service Test")
    print("=" * 60)

    print("\n📋 Catalog: {} test types".format(len(LAB_TEST_TYPES)))
    for key, info in LAB_TEST_TYPES.items():
        print("   {} {} — {} fields".format(
            info["icon"], info["name_ar"], len(info["fields"])))

    print("\n🔬 Abnormality test (CBC):")
    test_values = {"hgb": 9.5, "wbc": 7500, "plt": 250000, "rbc": 4.5}
    is_abn, sev, fields = check_abnormality("cbc", test_values)
    print("   is_abnormal: {}".format(is_abn))
    print("   severity: {}".format(sev))
    for f in fields:
        print("     - {} = {} (expected {})".format(
            f["label"], f["value"], f["expected"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
