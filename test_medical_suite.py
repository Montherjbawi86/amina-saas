# -*- coding: utf-8 -*-
"""
Test Medical Suite — 4 features
اختبار شامل للرعاية الطبية المتقدمة
"""
import sys
from datetime import date, timedelta

from core.db import db
from services.medical_suite import (
    calculate_risk_score, get_risk_level_meta, calculate_age,
    get_antenatal_plan, classify_anemia, get_anemia_thresholds,
    WHO_ANTENATAL_SCHEDULE, get_patient_medical_summary,
)
from services.drug_interactions_db import (
    check_interactions, get_severity_label, get_severity_color,
    search_drugs, COMMON_DRUGS, DRUG_INTERACTIONS,
)


PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def test(name, condition, detail=""):
    icon = PASS if condition else FAIL
    print("  {} {}".format(icon, name))
    if detail:
        print("     {}".format(detail))
    return condition


def main():
    all_passed = True

    # ============ 1. RISK SCORE ============
    section("1. Risk Score Calculator")

    # Test age
    age = calculate_age("1995-03-15")
    all_passed &= test(
        "Age calculation (1995-03-15)",
        age is not None and age > 28 and age < 35,
        "Age: {}".format(age)
    )

    # Test high-risk
    patient = {
        "date_of_birth": "1985-01-01",
        "gravida": 5, "para": 4,
        "risk_level": "high",
        "blood_type": "O-",
        "lmp": "2026-03-15",
        "edd": "2026-12-20",
    }
    visits = [{"bp_systolic": 165, "bp_diastolic": 115, "fetal_heart_rate": 100}]
    risk = calculate_risk_score(patient, visits)
    all_passed &= test(
        "High-risk score calculated",
        risk is not None and risk["level"] == "high",
        "Score: {} / Level: {}".format(risk["score"], risk["level"])
    )
    all_passed &= test(
        "Factors detected",
        len(risk["factors"]) >= 5,
        "Found {} factors".format(len(risk["factors"]))
    )
    all_passed &= test(
        "Recommendations provided",
        len(risk["recommendations"]) >= 2,
        "{} recommendations".format(len(risk["recommendations"]))
    )

    # Test low-risk
    patient_low = {
        "date_of_birth": "1998-01-01",
        "gravida": 1, "para": 0,
        "risk_level": "low",
        "blood_type": "O+",
        "lmp": "2026-03-15",
    }
    risk_low = calculate_risk_score(patient_low, [])
    all_passed &= test(
        "Low-risk score calculated",
        risk_low is not None and risk_low["level"] == "low",
        "Score: {} / Level: {}".format(risk_low["score"], risk_low["level"])
    )

    # ============ 2. ANTENATAL CARE PLAN ============
    section("2. Antenatal Care Plan (WHO 8 visits)")

    all_passed &= test(
        "WHO schedule has 8 visits",
        len(WHO_ANTENATAL_SCHEDULE) == 8,
        "Found: {}".format(len(WHO_ANTENATAL_SCHEDULE))
    )

    plan = get_antenatal_plan(patient)
    all_passed &= test(
        "Plan generated",
        plan is not None,
        "Visits: {}".format(len(plan["visits"]) if plan else 0)
    )
    if plan:
        all_passed &= test(
            "Current week calculated",
            plan["current_week"] > 0,
            "Week: {}".format(plan["current_week"])
        )
        all_passed &= test(
            "LMP present",
            plan["lmp"] is not None,
            "LMP: {}".format(plan["lmp"])
        )
        all_passed &= test(
            "EDD present",
            plan["edd"] is not None,
            "EDD: {}".format(plan["edd"])
        )

        statuses = [v["status"] for v in plan["visits"]]
        all_passed &= test(
            "Statuses assigned",
            all(s in ["past", "current", "upcoming"] for s in statuses),
            "past={}, current={}, upcoming={}".format(
                statuses.count("past"),
                statuses.count("current"),
                statuses.count("upcoming"),
            )
        )

    # ============ 3. ANEMIA CLASSIFICATION ============
    section("3. Anemia Screening (WHO)")

    thresholds = get_anemia_thresholds()
    all_passed &= test(
        "3 trimester thresholds",
        len(thresholds) == 3,
        "Found: {}".format(list(thresholds.keys()))
    )

    # Test cases
    test_cases = [
        (12.0, 20, "normal", "🟢"),
        (10.2, 20, "mild", "🟡"),
        (8.5, 20, "moderate", "🟠"),
        (6.5, 20, "severe", "🔴"),
        (11.5, 5, "normal", "🟢"),  # 1st trimester
        (10.0, 5, "mild", "🟡"),  # 1st trimester
    ]

    for hb, week, expected_cat, expected_icon in test_cases:
        r = classify_anemia(hb, week)
        is_correct = r and r["category"] == expected_cat
        all_passed &= test(
            "Hb {} @ week {} → {}".format(hb, week, expected_cat),
            is_correct,
            "Result: {}".format(r["severity"] if r else "None")
        )

    # ============ 4. DRUG INTERACTIONS ============
    section("4. Drug Interactions")

    all_passed &= test(
        "Database has drugs",
        len(COMMON_DRUGS) >= 20,
        "{} drugs".format(len(COMMON_DRUGS))
    )
    all_passed &= test(
        "Database has interactions",
        len(DRUG_INTERACTIONS) >= 20,
        "{} interactions".format(len(DRUG_INTERACTIONS))
    )

    # Test iron + calcium
    meds = [{"name": "حديد"}, {"name": "كالسيوم"}]
    results = check_interactions(meds)
    all_passed &= test(
        "Iron + Calcium interaction detected",
        len(results) >= 1,
        "Found: {}".format(len(results))
    )

    # Test oxytocin + misoprostol (severe)
    meds = [{"name": "أوكسيتوسين"}, {"name": "ميزوبروستول"}]
    results = check_interactions(meds)
    has_severe = any(r["severity"] == "severe" for r in results)
    all_passed &= test(
        "Severe interaction flagged",
        has_severe,
        "Severity: {}".format(results[0]["severity"] if results else "None")
    )

    # Test 3 drugs
    meds = [{"name": "حديد"}, {"name": "كالسيوم"}, {"name": "فيتامين D"}]
    results = check_interactions(meds)
    all_passed &= test(
        "3-drug interaction check",
        len(results) >= 2,
        "Found: {}".format(len(results))
    )

    # Test search
    results = search_drugs("حديد")
    all_passed &= test(
        "Drug search works",
        len(results) >= 1,
        "Found: {}".format(len(results))
    )

    # Test no interaction
    meds = [{"name": "باراسيتامول"}]
    results = check_interactions(meds)
    all_passed &= test(
        "Single drug → no interactions",
        len(results) == 0,
        "Found: {}".format(len(results))
    )

    # ============ 5. DATABASE CONNECTION ============
    section("5. Database Connection")

    try:
        clinics = db().table("clinics").select("id,name").limit(1).execute().data
        all_passed &= test(
            "Supabase connection",
            len(clinics) > 0,
            "Clinic: {}".format(clinics[0]["name"] if clinics else "None")
        )

        if clinics:
            cid = clinics[0]["id"]
            patients = db().table("patients").select("id,full_name").eq(
                "clinic_id", cid
            ).limit(1).execute().data

            if patients:
                pid = patients[0]["id"]
                all_passed &= test(
                    "Patient fetch",
                    True,
                    "Patient: {}".format(patients[0]["full_name"])
                )

                # Test full summary
                summary = get_patient_medical_summary(cid, pid)
                all_passed &= test(
                    "Medical summary generated",
                    summary is not None,
                    "Keys: {}".format(list(summary.keys()) if summary else [])
                )
    except Exception as e:
        all_passed &= test(
            "Database connection",
            False,
            "Error: {}".format(str(e)[:100])
        )

    # ============ SUMMARY ============
    section("SUMMARY")

    if all_passed:
        print()
        print("  🎉 ALL TESTS PASSED!")
        print()
        print("  ✅ Risk Score Calculator")
        print("  ✅ Antenatal Care Plan")
        print("  ✅ Anemia Screening")
        print("  ✅ Drug Interactions")
        print("  ✅ Database Connection")
        print()
        return 0
    else:
        print()
        print("  ⚠️ SOME TESTS FAILED")
        print("  Check details above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
