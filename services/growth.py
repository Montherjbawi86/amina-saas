# -*- coding: utf-8 -*-
"""Fetal growth measurements + WHO percentile calculations"""
from datetime import datetime, date
from typing import Dict, List, Optional

from core.db import db, insert, select, update, DBError


class GrowthError(Exception):
    pass


# ============================================
# WHO Fetal Growth Reference (approximate)
# Fundal Height (cm) by gestational week
# Source: WHO + INTERGROWTH-21st simplified
# ============================================
FUNDAL_HEIGHT_REFERENCE = {
    # week: (p10, p50, p90)
    20: (17, 20, 23),
    22: (19, 22, 25),
    24: (21, 24, 27),
    26: (23, 26, 29),
    28: (25, 28, 31),
    30: (27, 30, 33),
    32: (28, 31, 34),
    34: (30, 33, 36),
    36: (31, 34, 37),
    38: (32, 35, 38),
    40: (33, 36, 39),
}

# Estimated fetal weight (grams) by week — p10/p50/p90
FETAL_WEIGHT_REFERENCE = {
    20: (240, 300, 380),
    22: (390, 480, 590),
    24: (560, 670, 800),
    26: (760, 900, 1060),
    28: (1000, 1150, 1350),
    30: (1300, 1500, 1750),
    32: (1650, 1900, 2200),
    34: (2100, 2400, 2750),
    36: (2600, 2900, 3300),
    38: (3000, 3300, 3700),
    40: (3300, 3600, 4000),
}


def _lookup(ref, week):
    """Find nearest week entry"""
    if week in ref:
        return ref[week]
    keys = sorted(ref.keys())
    # find closest
    closest = min(keys, key=lambda k: abs(k - week))
    return ref[closest]


def get_fundal_height_percentile(week, value_cm):
    """
    Returns percentile label based on WHO reference.
    Returns: {percentile, label, color, deviation}
    """
    if not value_cm or not week:
        return None

    p10, p50, p90 = _lookup(FUNDAL_HEIGHT_REFERENCE, int(week))

    if value_cm < p10:
        return {
            "percentile": "<10",
            "label": "🟠 أقل من الطبيعي (SGA محتمل)",
            "color": "#F59E0B",
            "deviation": round(value_cm - p50, 1),
        }
    elif value_cm > p90:
        return {
            "percentile": ">90",
            "label": "🟡 أعلى من الطبيعي (LGA محتمل)",
            "color": "#F59E0B",
            "deviation": round(value_cm - p50, 1),
        }
    else:
        return {
            "percentile": "10-90",
            "label": "🟢 طبيعي",
            "color": "#10B981",
            "deviation": round(value_cm - p50, 1),
        }


def get_fetal_weight_percentile(week, weight_g):
    if not weight_g or not week:
        return None

    p10, p50, p90 = _lookup(FETAL_WEIGHT_REFERENCE, int(week))

    if weight_g < p10:
        return {"percentile": "<10", "label": "🟠 وزن أقل من الطبيعي", "color": "#F59E0B"}
    elif weight_g > p90:
        return {"percentile": ">90", "label": "🟡 وزن أعلى من الطبيعي", "color": "#F59E0B"}
    return {"percentile": "10-90", "label": "🟢 طبيعي", "color": "#10B981"}


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
        "measured_at": fields.get("measured_at") or date.today().isoformat(),
        "gestational_week": int(fields["gestational_week"]),
        "fundal_height_cm": fields.get("fundal_height_cm"),
        "estimated_fetal_weight_g": fields.get("estimated_fetal_weight_g"),
        "biparietal_diameter_mm": fields.get("biparietal_diameter_mm"),
        "femur_length_mm": fields.get("femur_length_mm"),
        "abdominal_circumference_mm": fields.get("abdominal_circumference_mm"),
        "amniotic_fluid_index": fields.get("amniotic_fluid_index"),
        "notes": fields.get("notes"),
    }

    try:
        return insert("growth_measurements", data)
    except DBError as e:
        raise GrowthError("Failed: " + str(e))


def list_measurements(clinic_id, patient_id, limit=50):
    return (db().table("growth_measurements").select("*")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .order("gestational_week")
            .limit(limit)
            .execute().data)


def delete_measurement(clinic_id, measurement_id):
    q = db().table("growth_measurements").delete().eq("id", measurement_id).eq("clinic_id", clinic_id)
    return q.execute().data


def get_reference_curve():
    """Return reference curves for plotting"""
    weeks = sorted(FUNDAL_HEIGHT_REFERENCE.keys())
    return {
        "weeks": weeks,
        "fh_p10": [FUNDAL_HEIGHT_REFERENCE[w][0] for w in weeks],
        "fh_p50": [FUNDAL_HEIGHT_REFERENCE[w][1] for w in weeks],
        "fh_p90": [FUNDAL_HEIGHT_REFERENCE[w][2] for w in weeks],
        "fw_p10": [FETAL_WEIGHT_REFERENCE[w][0] for w in weeks],
        "fw_p50": [FETAL_WEIGHT_REFERENCE[w][1] for w in weeks],
        "fw_p90": [FETAL_WEIGHT_REFERENCE[w][2] for w in weeks],
    }


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from services.patients import create_patient
    from core.db import delete as db_delete

    print("=" * 50)
    print("Growth Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Growth Test " + suffix, "Dr. G", "g-{}@t.com".format(suffix))
    patient = create_patient(clinic["id"], "نور محمد", "+9647700")

    print("\n1. Create measurement at week 28:")
    m = create_measurement(
        clinic["id"], patient["id"],
        gestational_week=28,
        fundal_height_cm=28,
        estimated_fetal_weight_g=1150,
    )
    print("   OK: {}".format(m["id"][:8]))

    print("\n2. Percentile analysis (FH=28 @ wk 28):")
    p = get_fundal_height_percentile(28, 28)
    print("   {}".format(p["label"]))
    print("   Deviation from median: {} cm".format(p["deviation"]))

    print("\n3. SGA case (FH=23 @ wk 28):")
    p2 = get_fundal_height_percentile(28, 23)
    print("   {}".format(p2["label"]))

    print("\n4. LGA case (FH=34 @ wk 28):")
    p3 = get_fundal_height_percentile(28, 34)
    print("   {}".format(p3["label"]))

    print("\n5. Fetal weight percentile (1150g @ wk28):")
    fw = get_fetal_weight_percentile(28, 1150)
    print("   {}".format(fw["label"]))

    print("\n6. List measurements:")
    ms = list_measurements(clinic["id"], patient["id"])
    print("   Total: {}".format(len(ms)))

    print("\n7. Reference curve:")
    ref = get_reference_curve()
    print("   Weeks: {}".format(ref["weeks"][:5]))
    print("   FH median: {}".format(ref["fh_p50"][:5]))

    print("\n8. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Growth module OK")
    print("=" * 50)
