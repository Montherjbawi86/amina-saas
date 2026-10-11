# -*- coding: utf-8 -*-
"""Automatic medical alerts based on patient data"""
from datetime import datetime, timedelta, date
from typing import Dict, List


def analyze_patient_alerts(patient, visits):
    """Analyze a patient and return list of alerts."""
    alerts = []

    if not patient:
        return alerts

    weeks = patient.get("gestational_weeks", 0)
    recent_visits = visits[:5]

    # ============ 1. Blood pressure alerts ============
    for v in recent_visits[:2]:
        sys_bp = v.get("bp_systolic")
        dia_bp = v.get("bp_diastolic")
        if sys_bp and dia_bp:
            if sys_bp >= 160 or dia_bp >= 110:
                alerts.append({
                    "level": "critical",
                    "icon": "🚨",
                    "title": "ضغط دم حرج",
                    "message": "ضغط {}/{} — يحتاج تدخل فوري".format(sys_bp, dia_bp),
                    "action": "تحقق من بروتين البول، قيّم لتسمم الحمل"
                })
            elif sys_bp >= 140 or dia_bp >= 90:
                alerts.append({
                    "level": "high",
                    "icon": "🔴",
                    "title": "ضغط دم مرتفع",
                    "message": "ضغط {}/{} — يحتاج متابعة".format(sys_bp, dia_bp),
                    "action": "قياس كل 4 ساعات، تقييم الأعراض"
                })

    # ============ 2. Fetal heart rate alerts ============
    for v in recent_visits[:2]:
        fhr = v.get("fetal_heart_rate")
        if fhr:
            if fhr < 100:
                alerts.append({
                    "level": "critical",
                    "icon": "🚨",
                    "title": "تباطؤ حاد في نبض الجنين",
                    "message": "نبض {} bpm — أقل من 100".format(fhr),
                    "action": "فحص CTG فوري، استشارة طارئة"
                })
            elif fhr < 110:
                alerts.append({
                    "level": "high",
                    "icon": "🟡",
                    "title": "تباطؤ نبض الجنين",
                    "message": "نبض {} bpm — أقل من الطبيعي".format(fhr),
                    "action": "مراقبة، فحص CTG"
                })
            elif fhr > 170:
                alerts.append({
                    "level": "high",
                    "icon": "🟡",
                    "title": "تسارع نبض الجنين",
                    "message": "نبض {} bpm — أعلى من الطبيعي".format(fhr),
                    "action": "استبعاد العدوى، فحص CTG"
                })

    # ============ 3. Weight gain alerts ============
    weights = [(v.get("visit_date"), v.get("weight_kg"))
               for v in visits if v.get("weight_kg")]
    if len(weights) >= 2:
        last_weight = weights[0][1]
        prev_weight = weights[1][1]
        try:
            last_date = datetime.fromisoformat(weights[0][0][:19]) if weights[0][0] else None
            prev_date = datetime.fromisoformat(weights[1][0][:19]) if weights[1][0] else None
            if last_date and prev_date:
                days_diff = abs((last_date - prev_date).days)
                if 0 < days_diff <= 14:
                    gain_per_week = (last_weight - prev_weight) / (days_diff / 7.0)
                    if gain_per_week > 1.5:
                        alerts.append({
                            "level": "high",
                            "icon": "🟡",
                            "title": "زيادة وزن سريعة",
                            "message": "زيادة {:.1f} كغ/أسبوع".format(gain_per_week),
                            "action": "تقييم غذائي، استبعاد احتباس السوائل"
                        })
                    elif gain_per_week < -0.5:
                        alerts.append({
                            "level": "medium",
                            "icon": "🟠",
                            "title": "فقدان وزن",
                            "message": "فقدان {:.1f} كغ/أسبوع".format(abs(gain_per_week)),
                            "action": "تقييم غذائي"
                        })
        except Exception:
            pass

    # ============ 4. Fundal height alerts ============
    for v in visits[:1]:
        fh = v.get("fundal_height_cm")
        ga = v.get("gestational_age_weeks") or weeks
        if fh and ga and ga > 20:
            expected = ga
            diff = abs(fh - expected)
            if diff > 4:
                alerts.append({
                    "level": "high",
                    "icon": "🟡",
                    "title": "ارتفاع رحم غير طبيعي",
                    "message": "قياس {} سم في الأسبوع {} (المتوقع ~{} سم)".format(fh, ga, expected),
                    "action": "سونار لتقييم نمو الجنين"
                })

    # ============ 5. Visit gap alerts ============
    if visits:
        last_visit_date_str = visits[0].get("visit_date")
        if last_visit_date_str:
            try:
                last = datetime.fromisoformat(last_visit_date_str[:19]).date()
                days_since = (date.today() - last).days
                expected_max_days = 30 if weeks < 28 else 14
                if days_since > expected_max_days:
                    alerts.append({
                        "level": "medium",
                        "icon": "🟠",
                        "title": "انقطاع عن المتابعة",
                        "message": "آخر زيارة منذ {} يوم".format(days_since),
                        "action": "التواصل مع الحامل"
                    })
            except Exception:
                pass

    return alerts


def get_clinic_alerts(clinic_id, patients, visits_by_patient):
    """Get all alerts across all patients in a clinic."""
    results = []
    for p in patients:
        visits = visits_by_patient.get(p["id"], [])
        alerts = analyze_patient_alerts(p, visits)
        if alerts:
            results.append({
                "patient_id": p["id"],
                "patient_name": p["full_name"],
                "phone": p.get("phone"),
                "risk_level": p.get("risk_level", "low"),
                "alerts": alerts
            })

    def severity_score(item):
        levels = [a["level"] for a in item["alerts"]]
        if "critical" in levels: return 0
        if "high" in levels: return 1
        if "medium" in levels: return 2
        return 3

    results.sort(key=severity_score)
    return results


def count_alerts_by_level(alerts_list):
    """Count alerts by severity"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in alerts_list:
        for a in item["alerts"]:
            lvl = a.get("level", "low")
            counts[lvl] = counts.get(lvl, 0) + 1
    return counts


if __name__ == "__main__":
    print("Alerts Module Test")
    patient = {"full_name": "فاطمة أحمد", "gestational_weeks": 28, "risk_level": "high"}
    visits = [
        {"visit_date": "2026-10-10T10:00:00", "bp_systolic": 155, "bp_diastolic": 95,
         "fetal_heart_rate": 105, "weight_kg": 72.5, "fundal_height_cm": 32,
         "gestational_age_weeks": 28},
        {"visit_date": "2026-10-03T10:00:00", "bp_systolic": 130, "bp_diastolic": 85,
         "fetal_heart_rate": 145, "weight_kg": 70.0, "fundal_height_cm": 27,
         "gestational_age_weeks": 27},
    ]
    alerts = analyze_patient_alerts(patient, visits)
    print("Alerts: {}".format(len(alerts)))
    for a in alerts:
        print("  {} [{}] {}".format(a["icon"], a["level"], a["title"]))
        print("     {}".format(a["message"]))
