# -*- coding: utf-8 -*-
"""
Fetal growth measurements + WHO percentile calculations
قياسات نمو الجنين + معايير منظمة الصحة العالمية
"""
from datetime import datetime, date
from typing import Dict, List, Optional

from core.db import db, insert, select, update, DBError
from services.who_growth_standards import (
    BPD_REFERENCE, HC_REFERENCE, AC_REFERENCE, FL_REFERENCE, EFW_REFERENCE,
    lookup, analyze_bpd, analyze_hc, analyze_ac, analyze_fl, analyze_efw,
    diagnose,
)


class GrowthError(Exception):
    pass


def _to_iso_date(v):
    """Convert date/datetime/string to ISO date string"""
    if v is None:
        return None
    if isinstance(v, str):
        return v[:10]
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    return str(v)[:10]


def _to_num(v):
    """Convert to float or None"""
    if v is None or v == "" or v == 0 or v == 0.0:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _to_int(v):
    """Convert to int or None"""
    if v is None or v == "" or v == 0:
        return None
    try:
        return int(v)
    except Exception:
        return None


# ============================================
# FUNDAL HEIGHT (still used as a secondary measure)
# ============================================
FUNDAL_HEIGHT_REFERENCE = {
    20: (17, 20, 23), 22: (19, 22, 25), 24: (21, 24, 27),
    26: (23, 26, 29), 28: (25, 28, 31), 30: (27, 30, 33),
    32: (28, 31, 34), 34: (30, 33, 36), 36: (31, 34, 37),
    38: (32, 35, 38), 40: (33, 36, 39),
}


# ============================================
# CRUD
# ============================================

def create_measurement(clinic_id, patient_id, **fields):
    if not patient_id:
        raise GrowthError("patient_id required")
    if not fields.get("gestational_week"):
        raise GrowthError("gestational_week required")

    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "visit_id": fields.get("visit_id"),
        "measured_at": _to_iso_date(fields.get("measured_at")) or date.today().isoformat(),
        "gestational_week": int(fields["gestational_week"]),
        "fundal_height_cm": _to_num(fields.get("fundal_height_cm")),
        "estimated_fetal_weight_g": _to_int(fields.get("estimated_fetal_weight_g")),
        "biparietal_diameter_mm": _to_num(fields.get("biparietal_diameter_mm")),
        "femur_length_mm": _to_num(fields.get("femur_length_mm")),
        "abdominal_circumference_mm": _to_num(fields.get("abdominal_circumference_mm")),
        "head_circumference_mm": _to_num(fields.get("head_circumference_mm")),
        "amniotic_fluid_index": _to_num(fields.get("amniotic_fluid_index")),
        "notes": fields.get("notes"),
    }

    try:
        return insert("growth_measurements", data)
    except DBError as e:
        raise GrowthError("Failed: " + str(e))


def update_measurement(clinic_id, measurement_id, **fields):
    allowed = {
        "measured_at", "gestational_week", "fundal_height_cm",
        "estimated_fetal_weight_g", "biparietal_diameter_mm",
        "femur_length_mm", "abdominal_circumference_mm",
        "head_circumference_mm", "amniotic_fluid_index", "notes",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise GrowthError("No fields to update")
    return update("growth_measurements", {"id": measurement_id, "clinic_id": clinic_id}, clean)


def list_measurements(clinic_id, patient_id, limit=50):
    return (
        db().table("growth_measurements")
        .select("*")
        .eq("clinic_id", clinic_id)
        .eq("patient_id", patient_id)
        .order("gestational_week")
        .limit(limit)
        .execute()
        .data or []
    )


def delete_measurement(clinic_id, measurement_id):
    return (
        db().table("growth_measurements")
        .delete()
        .eq("id", measurement_id)
        .eq("clinic_id", clinic_id)
        .execute()
        .data
    )


# ============================================
# PERCENTILE ANALYSIS
# ============================================

def get_fundal_height_percentile(week, value_cm):
    """Fundal height percentile using FH reference"""
    if not value_cm or not week:
        return None

    p10, p50, p90 = lookup(FUNDAL_HEIGHT_REFERENCE, int(week))

    if value_cm < p10:
        return {"percentile": "<10", "label": "🟠 أقل من الطبيعي (SGA محتمل)",
                "color": "#F59E0B", "deviation": round(value_cm - p50, 1)}
    elif value_cm > p90:
        return {"percentile": ">90", "label": "🟡 أعلى من الطبيعي (LGA محتمل)",
                "color": "#F59E0B", "deviation": round(value_cm - p50, 1)}
    return {"percentile": "10-90", "label": "🟢 طبيعي",
            "color": "#10B981", "deviation": round(value_cm - p50, 1)}


def get_fetal_weight_percentile(week, weight_g):
    """EFW percentile"""
    return analyze_efw(week, weight_g)


def analyze_measurement(measurement):
    """
    Comprehensive analysis of a single measurement.
    Returns: {
        week, efw_analysis, bpd_analysis, hc_analysis, ac_analysis, fl_analysis,
        fh_analysis, diagnosis
    }
    """
    week = measurement.get("gestational_week")
    if not week:
        return None

    result = {
        "week": week,
        "measured_at": measurement.get("measured_at"),
    }

    # Individual analyses
    if measurement.get("fundal_height_cm"):
        result["fh_analysis"] = get_fundal_height_percentile(week, measurement["fundal_height_cm"])

    if measurement.get("estimated_fetal_weight_g"):
        result["efw_analysis"] = analyze_efw(week, measurement["estimated_fetal_weight_g"])

    if measurement.get("biparietal_diameter_mm"):
        result["bpd_analysis"] = analyze_bpd(week, measurement["biparietal_diameter_mm"])

    if measurement.get("head_circumference_mm"):
        result["hc_analysis"] = analyze_hc(week, measurement["head_circumference_mm"])

    if measurement.get("abdominal_circumference_mm"):
        result["ac_analysis"] = analyze_ac(week, measurement["abdominal_circumference_mm"])

    if measurement.get("femur_length_mm"):
        result["fl_analysis"] = analyze_fl(week, measurement["femur_length_mm"])

    # Comprehensive diagnosis
    if measurement.get("estimated_fetal_weight_g"):
        result["diagnosis"] = diagnose(week, {
            "efw": measurement["estimated_fetal_weight_g"],
            "bpd": measurement.get("biparietal_diameter_mm"),
            "hc": measurement.get("head_circumference_mm"),
            "ac": measurement.get("abdominal_circumference_mm"),
            "fl": measurement.get("femur_length_mm"),
        })

    return result


# ============================================
# CHART DATA
# ============================================

def get_reference_curve():
    """Return reference curves for plotting"""
    weeks = sorted(FUNDAL_HEIGHT_REFERENCE.keys())
    return {
        "weeks": weeks,
        "fh_p10": [FUNDAL_HEIGHT_REFERENCE[w][0] for w in weeks],
        "fh_p50": [FUNDAL_HEIGHT_REFERENCE[w][1] for w in weeks],
        "fh_p90": [FUNDAL_HEIGHT_REFERENCE[w][2] for w in weeks],
    }


def get_who_curve(measure_type="efw"):
    """
    Get WHO reference curve for plotting.
    measure_type: 'bpd', 'hc', 'ac', 'fl', 'efw'
    Returns: {weeks, p10, p50, p90}
    """
    ref = {
        "bpd": BPD_REFERENCE,
        "hc": HC_REFERENCE,
        "ac": AC_REFERENCE,
        "fl": FL_REFERENCE,
        "efw": EFW_REFERENCE,
    }.get(measure_type)

    if not ref:
        return None

    weeks = sorted(ref.keys())
    return {
        "weeks": weeks,
        "p10": [ref[w][0] for w in weeks],
        "p50": [ref[w][1] for w in weeks],
        "p90": [ref[w][2] for w in weeks],
    }


def get_patient_chart_data(clinic_id, patient_id):
    """
    All measurement data for a patient, formatted for plotting.
    Returns: {weeks, fh, efw, bpd, hc, ac, fl}
    """
    measurements = list_measurements(clinic_id, patient_id, limit=100)

    result = {
        "weeks": [m["gestational_week"] for m in measurements],
        "fh": [m.get("fundal_height_cm") for m in measurements],
        "efw": [m.get("estimated_fetal_weight_g") for m in measurements],
        "bpd": [m.get("biparietal_diameter_mm") for m in measurements],
        "hc": [m.get("head_circumference_mm") for m in measurements],
        "ac": [m.get("abdominal_circumference_mm") for m in measurements],
        "fl": [m.get("femur_length_mm") for m in measurements],
        "dates": [m.get("measured_at") for m in measurements],
    }

    return result


def get_patient_summary(clinic_id, patient_id):
    """Latest measurement summary"""
    measurements = list_measurements(clinic_id, patient_id, limit=100)
    if not measurements:
        return None

    latest = measurements[-1]
    analysis = analyze_measurement(latest)

    return {
        "total": len(measurements),
        "latest": latest,
        "latest_analysis": analysis,
        "first_week": measurements[0].get("gestational_week"),
        "last_week": measurements[-1].get("gestational_week"),
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Growth Module Test — Enhanced")
    print("=" * 60)

    # Test percentile
    print("\n1. Fundal height (28cm @ week 28):")
    r = get_fundal_height_percentile(28, 28)
    print("   {}".format(r["label"]))

    print("\n2. BPD analysis (55mm @ week 24):")
    r = analyze_bpd(24, 55)
    print("   {}".format(r["label"]))

    print("\n3. WHO curve (EFW):")
    curve = get_who_curve("efw")
    print("   Weeks: {} total".format(len(curve["weeks"])))
    print("   P50 samples: {}".format(curve["p50"][:5]))

    print("\n4. Full diagnosis (IUGR):")
    d = diagnose(32, {"efw": 1500})
    print("   {}".format(d["label"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
