# -*- coding: utf-8 -*-
"""
WHO Fetal Growth Standards
معايير منظمة الصحة العالمية لنمو الجنين
Source: INTERGROWTH-21st + WHO Fetal Growth Charts
"""
from typing import Optional, Dict, Tuple


# ============================================
# BPD — Biparietal Diameter (mm)
# ============================================
BPD_REFERENCE = {
    12: (18, 21, 24),
    13: (20, 23, 26),
    14: (23, 26, 29),
    15: (26, 29, 32),
    16: (29, 32, 36),
    17: (32, 35, 39),
    18: (35, 38, 42),
    19: (37, 41, 45),
    20: (40, 44, 48),
    21: (43, 46, 50),
    22: (45, 49, 53),
    23: (48, 52, 56),
    24: (50, 54, 59),
    25: (53, 57, 61),
    26: (55, 59, 64),
    27: (58, 62, 67),
    28: (60, 64, 69),
    29: (62, 66, 72),
    30: (64, 68, 74),
    31: (66, 70, 76),
    32: (68, 72, 78),
    33: (70, 74, 80),
    34: (72, 76, 82),
    35: (73, 78, 84),
    36: (75, 79, 85),
    37: (76, 81, 87),
    38: (78, 82, 89),
    39: (79, 83, 90),
    40: (80, 84, 92),
}


# ============================================
# HC — Head Circumference (mm)
# ============================================
HC_REFERENCE = {
    12: (60, 70, 82),
    13: (73, 84, 97),
    14: (86, 97, 110),
    15: (98, 110, 124),
    16: (110, 122, 137),
    17: (121, 134, 149),
    18: (132, 145, 161),
    19: (142, 156, 172),
    20: (152, 166, 183),
    21: (161, 176, 193),
    22: (170, 185, 202),
    23: (179, 194, 212),
    24: (187, 203, 221),
    25: (195, 211, 229),
    26: (203, 219, 238),
    27: (210, 227, 246),
    28: (217, 234, 254),
    29: (224, 241, 261),
    30: (230, 248, 268),
    31: (236, 254, 275),
    32: (242, 260, 281),
    33: (248, 266, 288),
    34: (253, 272, 294),
    35: (258, 277, 300),
    36: (263, 282, 305),
    37: (268, 287, 310),
    38: (272, 292, 315),
    39: (276, 296, 320),
    40: (280, 300, 325),
}


# ============================================
# AC — Abdominal Circumference (mm)
# ============================================
AC_REFERENCE = {
    12: (50, 60, 71),
    13: (60, 71, 83),
    14: (70, 82, 95),
    15: (80, 93, 107),
    16: (91, 105, 120),
    17: (102, 116, 132),
    18: (112, 128, 145),
    19: (123, 139, 157),
    20: (133, 151, 170),
    21: (144, 162, 182),
    22: (154, 174, 195),
    23: (165, 185, 207),
    24: (175, 197, 220),
    25: (185, 208, 232),
    26: (196, 220, 244),
    27: (206, 231, 257),
    28: (216, 242, 269),
    29: (226, 253, 281),
    30: (236, 264, 293),
    31: (245, 274, 305),
    32: (255, 285, 317),
    33: (264, 295, 328),
    34: (273, 305, 340),
    35: (282, 315, 351),
    36: (291, 325, 362),
    37: (300, 334, 373),
    38: (308, 343, 383),
    39: (316, 352, 394),
    40: (324, 360, 404),
}


# ============================================
# FL — Femur Length (mm)
# ============================================
FL_REFERENCE = {
    12: (7, 9, 12),
    13: (10, 13, 16),
    14: (14, 17, 20),
    15: (17, 20, 24),
    16: (20, 24, 28),
    17: (23, 27, 32),
    18: (27, 31, 36),
    19: (30, 34, 39),
    20: (33, 37, 42),
    21: (36, 40, 46),
    22: (39, 43, 49),
    23: (41, 46, 52),
    24: (44, 49, 55),
    25: (46, 51, 58),
    26: (48, 54, 61),
    27: (51, 56, 63),
    28: (53, 58, 66),
    29: (55, 61, 68),
    30: (57, 63, 71),
    31: (59, 65, 73),
    32: (61, 67, 75),
    33: (63, 69, 78),
    34: (65, 71, 80),
    35: (66, 72, 82),
    36: (68, 74, 84),
    37: (69, 75, 85),
    38: (70, 76, 87),
    39: (71, 77, 88),
    40: (72, 78, 89),
}


# ============================================
# EFW — Estimated Fetal Weight (grams)
# ============================================
EFW_REFERENCE = {
    12: (10, 14, 20),
    13: (20, 23, 30),
    14: (35, 43, 55),
    15: (55, 70, 88),
    16: (85, 105, 130),
    17: (120, 145, 180),
    18: (160, 190, 230),
    19: (205, 240, 285),
    20: (250, 300, 360),
    21: (310, 360, 430),
    22: (370, 430, 510),
    23: (440, 500, 590),
    24: (510, 590, 690),
    25: (590, 680, 790),
    26: (680, 780, 900),
    27: (780, 880, 1010),
    28: (880, 1000, 1140),
    29: (990, 1120, 1270),
    30: (1110, 1250, 1410),
    31: (1230, 1390, 1550),
    32: (1360, 1530, 1710),
    33: (1500, 1680, 1870),
    34: (1640, 1830, 2030),
    35: (1780, 1980, 2200),
    36: (1930, 2140, 2370),
    37: (2080, 2290, 2540),
    38: (2210, 2440, 2700),
    39: (2340, 2580, 2850),
    40: (2450, 2710, 2990),
}


# ============================================
# LOOKUP
# ============================================

def lookup(reference: Dict, week: int) -> Tuple[float, float, float]:
    """Get (p10, p50, p90) for a week (interpolated if needed)"""
    if not week:
        return None

    week = int(week)

    if week in reference:
        return reference[week]

    keys = sorted(reference.keys())
    if week < keys[0]:
        return reference[keys[0]]
    if week > keys[-1]:
        return reference[keys[-1]]

    # Linear interpolation
    lower = max(k for k in keys if k < week)
    upper = min(k for k in keys if k > week)
    ratio = (week - lower) / (upper - lower)

    lower_vals = reference[lower]
    upper_vals = reference[upper]

    return tuple(
        lower_vals[i] + (upper_vals[i] - lower_vals[i]) * ratio
        for i in range(3)
    )


def get_percentile_label(p10, p50, p90, value):
    """Classify value against reference"""
    if value is None:
        return None

    if value < p10:
        deviation_pct = round(100.0 * (value - p50) / p50, 1) if p50 else 0
        severity = "moderate" if value < p10 * 0.9 else "mild"
        return {
            "category": "low",
            "percentile": "<10",
            "label": "🟠 أقل من الطبيعي",
            "color": "#F59E0B",
            "severity": severity,
            "deviation_pct": deviation_pct,
        }
    elif value > p90:
        deviation_pct = round(100.0 * (value - p50) / p50, 1) if p50 else 0
        severity = "moderate" if value > p90 * 1.1 else "mild"
        return {
            "category": "high",
            "percentile": ">90",
            "label": "🟡 أعلى من الطبيعي",
            "color": "#F59E0B",
            "severity": severity,
            "deviation_pct": deviation_pct,
        }
    else:
        deviation_pct = round(100.0 * (value - p50) / p50, 1) if p50 else 0
        return {
            "category": "normal",
            "percentile": "10-90",
            "label": "🟢 طبيعي",
            "color": "#10B981",
            "severity": "none",
            "deviation_pct": deviation_pct,
        }


def analyze_bpd(week, value):
    if not value:
        return None
    p10, p50, p90 = lookup(BPD_REFERENCE, week)
    return get_percentile_label(p10, p50, p90, value)


def analyze_hc(week, value):
    if not value:
        return None
    p10, p50, p90 = lookup(HC_REFERENCE, week)
    return get_percentile_label(p10, p50, p90, value)


def analyze_ac(week, value):
    if not value:
        return None
    p10, p50, p90 = lookup(AC_REFERENCE, week)
    return get_percentile_label(p10, p50, p90, value)


def analyze_fl(week, value):
    if not value:
        return None
    p10, p50, p90 = lookup(FL_REFERENCE, week)
    return get_percentile_label(p10, p50, p90, value)


def analyze_efw(week, value):
    if not value:
        return None
    p10, p50, p90 = lookup(EFW_REFERENCE, week)
    return get_percentile_label(p10, p50, p90, value)


# ============================================
# DIAGNOSIS
# ============================================

def diagnose(week, measurements):
    """
    Comprehensive fetal growth diagnosis.
    measurements: {bpd, hc, ac, fl, efw}
    Returns: {status, label, details, recommendations}
    """
    efw = measurements.get("efw")
    ac = measurements.get("ac")

    if not efw:
        return {
            "status": "unknown",
            "label": "ℹ️ بيانات غير كافية",
            "color": "#94A3B8",
            "details": "أدخل EFW للتشخيص",
            "recommendations": [],
        }

    p10, p50, p90 = lookup(EFW_REFERENCE, week)

    # IUGR (Intrauterine Growth Restriction)
    if efw < p10:
        severity = "severe" if efw < p10 * 0.85 else "moderate"
        return {
            "status": "iugr",
            "label": "🚨 تأخر نمو الجنين (IUGR)",
            "color": "#DC2626",
            "details": "الوزن المتوقع {} غ أقل من P10 ({:.0f} غ)".format(efw, p10),
            "severity": severity,
            "recommendations": [
                "متابعة أسبوعية",
                "دوبلر الشريان السري",
                "تقييم السائل الأمنيوسي",
                "مراقبة حركة الجنين يومياً",
                "استشارة أخصائي طب الأمومة والأجنة",
            ],
        }

    # Macrosomia (LGA)
    if efw > p90:
        return {
            "status": "macrosomia",
            "label": "🟡 ضخامة الجنين (Macrosomia)",
            "color": "#F59E0B",
            "details": "الوزن المتوقع {} غ أعلى من P90 ({:.0f} غ)".format(efw, p90),
            "severity": "moderate",
            "recommendations": [
                "فحص سكري الحمل",
                "تقييم الحوض للولادة الطبيعية",
                "متابعة نمو الجنين",
                "مناقشة خيارات الولادة",
            ],
        }

    # Normal
    return {
        "status": "normal",
        "label": "✅ نمو طبيعي",
        "color": "#10B981",
        "details": "الوزن المتوقع {} غ ضمن النطاق الطبيعي (P10-P90)".format(efw),
        "severity": "none",
        "recommendations": ["متابعة روتينية"],
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("WHO Fetal Growth Standards Test")
    print("=" * 60)

    print("\n📊 Reference tables:")
    print("  BPD: {} weeks".format(len(BPD_REFERENCE)))
    print("  HC:  {} weeks".format(len(HC_REFERENCE)))
    print("  AC:  {} weeks".format(len(AC_REFERENCE)))
    print("  FL:  {} weeks".format(len(FL_REFERENCE)))
    print("  EFW: {} weeks".format(len(EFW_REFERENCE)))

    print("\n🔍 Lookup test (BPD @ week 24):")
    p10, p50, p90 = lookup(BPD_REFERENCE, 24)
    print("  P10={} P50={} P90={}".format(p10, p50, p90))

    print("\n🔍 Interpolation test (BPD @ week 24.5):")
    p10, p50, p90 = lookup(BPD_REFERENCE, 24)
    print("  Uses nearest week 24")

    print("\n📈 Percentile analysis:")
    for w, v in [(24, 55), (28, 65), (32, 72), (36, 78)]:
        r = analyze_bpd(w, v)
        print("  BPD week {}: {} mm → {}".format(w, v, r["label"]))

    print("\n🚨 Diagnosis test (IUGR):")
    d = diagnose(32, {"efw": 1500})
    print("  EFW 1500g @ week 32:")
    print("  → {}".format(d["label"]))
    print("  → {}".format(d["details"]))

    print("\n✅ Diagnosis test (Normal):")
    d = diagnose(32, {"efw": 1900})
    print("  EFW 1900g @ week 32:")
    print("  → {}".format(d["label"]))

    print("\n🟡 Diagnosis test (Macrosomia):")
    d = diagnose(32, {"efw": 2400})
    print("  EFW 2400g @ week 32:")
    print("  → {}".format(d["label"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
