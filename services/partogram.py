# -*- coding: utf-8 -*-
"""
Partogram Service
مخطط المخاض — WHO + Modified WHO
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from core.db import db, insert, update


# ============================================
# CONSTANTS
# ============================================

LABOR_STATUS = {
    "active": {"label": "🔵 نشط", "color": "#0EA5E9"},
    "completed": {"label": "✅ مكتمل", "color": "#10B981"},
    "transferred": {"label": "🚑 محوّل", "color": "#F59E0B"},
    "cancelled": {"label": "❌ ملغى", "color": "#94A3B8"},
}

AMNIOTIC_FLUID = {
    "intact": "🟢 سليم (Intact)",
    "clear": "💧 صافي (Clear)",
    "meconium_thin": "🟡 عقي (خفيف)",
    "meconium_thick": "🟠 عقي (كثيف)",
    "blood": "🔴 دموي",
}


# ============================================
# FETCH ACTIVE LABOR
# ============================================

def get_active_labor(clinic_id, patient_id):
    """Get current active labor for a patient"""
    try:
        rows = (
            db().table("labor_records")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .eq("status", "active")
            .order("labor_start", desc=True)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def list_active_labors(clinic_id):
    """List all active labors in clinic"""
    try:
        return (
            db().table("labor_records")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("status", "active")
            .order("labor_start", desc=True)
            .execute()
            .data or []
        )
    except Exception:
        return []


def start_labor(clinic_id, patient_id, doctor_id=None):
    """Start a new labor record"""
    existing = get_active_labor(clinic_id, patient_id)
    if existing:
        return existing

    return insert("labor_records", {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "status": "active",
        "labor_start": datetime.utcnow().isoformat(),
    })


def end_labor(clinic_id, labor_id, status="completed", newborn_id=None):
    """End a labor record"""
    try:
        return update("labor_records", {"id": labor_id, "clinic_id": clinic_id}, {
            "status": status,
            "labor_end": datetime.utcnow().isoformat(),
            "newborn_id": newborn_id,
            "updated_at": datetime.utcnow().isoformat(),
        })
    except Exception:
        return None


# ============================================
# PARTogram ENTRIES
# ============================================

def add_entry(clinic_id, labor_id, data):
    """Add a partogram entry"""
    entry = {
        "labor_id": labor_id,
        "clinic_id": clinic_id,
        "recorded_at": data.get("recorded_at") or datetime.utcnow().isoformat(),
        "cervical_dilatation_cm": _num(data.get("cervical_dilatation_cm")),
        "fetal_station": _int(data.get("fetal_station")),
        "effacement_percent": _int(data.get("effacement_percent")),
        "cervix_consistency": data.get("cervix_consistency"),
        "cervix_position": data.get("cervix_position"),
        "bp_systolic": _int(data.get("bp_systolic")),
        "bp_diastolic": _int(data.get("bp_diastolic")),
        "maternal_pulse": _int(data.get("maternal_pulse")),
        "temperature": _num(data.get("temperature")),
        "fetal_heart_rate": _int(data.get("fetal_heart_rate")),
        "amniotic_fluid": data.get("amniotic_fluid"),
        "contractions_per_10min": _int(data.get("contractions_per_10min")),
        "contraction_duration_sec": _int(data.get("contraction_duration_sec")),
        "oxytocin_units": _num(data.get("oxytocin_units")),
        "notes": data.get("notes"),
    }
    return insert("partogram_entries", entry)


def list_entries(clinic_id, labor_id, limit=100):
    """List all entries for a labor"""
    try:
        return (
            db().table("partogram_entries")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("labor_id", labor_id)
            .order("recorded_at")
            .limit(limit)
            .execute()
            .data or []
        )
    except Exception:
        return []


def get_latest_entry(clinic_id, labor_id):
    """Get latest entry"""
    entries = list_entries(clinic_id, labor_id, limit=1)
    if entries:
        return entries[-1]
    return None


# ============================================
# HELPERS
# ============================================

def _num(v):
    if v is None or v == "" or v == 0:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except Exception:
        return None


# ============================================
# ANALYSIS
# ============================================

def analyze_labor(clinic_id, labor_id):
    """
    Comprehensive labor analysis.
    Returns: {status, alerts, progress, recommendation}
    """
    labor = None
    try:
        rows = db().table("labor_records").select("*").eq("id", labor_id).eq("clinic_id", clinic_id).limit(1).execute().data or []
        labor = rows[0] if rows else None
    except Exception:
        pass

    if not labor:
        return {"error": "Labor record not found"}

    entries = list_entries(clinic_id, labor_id, limit=100)

    if not entries:
        return {
            "status": "no_data",
            "alerts": [],
            "progress": "no_data",
            "recommendation": ["سجّل قياسات المخاض"],
        }

    alerts = []

    # Labor duration
    start = labor.get("labor_start")
    duration_hours = 0
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            now = datetime.utcnow()
            if start_dt.tzinfo:
                now = now.replace(tzinfo=start_dt.tzinfo)
            duration_hours = (now - start_dt).total_seconds() / 3600.0
        except Exception:
            pass

    # Prolonged labor (> 12 hours)
    if duration_hours > 12:
        alerts.append({
            "level": "critical",
            "message": "⚠️ مخاض مطوّل: {:.1f} ساعة".format(duration_hours),
            "recommendation": "تقييم فوري — قد يحتاج تدخل جراحي",
        })
    elif duration_hours > 8:
        alerts.append({
            "level": "warning",
            "message": "⏰ مخاض طويل: {:.1f} ساعة".format(duration_hours),
            "recommendation": "مراقبة دقيقة",
        })

    # Latest measurements
    latest = entries[-1]
    first = entries[0]

    # Fetal distress (FHR)
    fhr = latest.get("fetal_heart_rate")
    if fhr:
        if fhr < 110:
            alerts.append({
                "level": "critical",
                "message": "🚨 تباطؤ نبض الجنين: {} bpm".format(fhr),
                "recommendation": "أوكسجين + تقييم فوري (CTG)",
            })
        elif fhr > 160:
            alerts.append({
                "level": "critical",
                "message": "🚨 تسارع نبض الجنين: {} bpm".format(fhr),
                "recommendation": "أوكسجين + تقييم فوري",
            })

    # Maternal BP (elevated)
    bp_sys = latest.get("bp_systolic")
    bp_dia = latest.get("bp_diastolic")
    if bp_sys and bp_dia:
        if bp_sys >= 160 or bp_dia >= 110:
            alerts.append({
                "level": "critical",
                "message": "🚨 ضغط الأم شديد: {}/{}".format(bp_sys, bp_dia),
                "recommendation": "خافض ضغط فوري",
            })
        elif bp_sys >= 140 or bp_dia >= 90:
            alerts.append({
                "level": "warning",
                "message": "⚠️ ارتفاع ضغط الأم: {}/{}".format(bp_sys, bp_dia),
                "recommendation": "مراقبة",
            })

    # Meconium
    af = latest.get("amniotic_fluid")
    if af == "meconium_thick":
        alerts.append({
            "level": "critical",
            "message": "🚨 عقي كثيف (Meconium)",
            "recommendation": "تقييم فوري — خطر شفط عقي",
        })
    elif af == "meconium_thin":
        alerts.append({
            "level": "warning",
            "message": "⚠️ عقي خفيف",
            "recommendation": "مراقبة دقيقة",
        })

    # Progress analysis
    progress = "normal"
    if len(entries) >= 2:
        first_dil = first.get("cervical_dilatation_cm")
        last_dil = latest.get("cervical_dilatation_cm")

        if first_dil is not None and last_dil is not None:
            # Time between
            t_first = _parse_dt(first.get("recorded_at"))
            t_last = _parse_dt(latest.get("recorded_at"))

            if t_first and t_last:
                hours_elapsed = (t_last - t_first).total_seconds() / 3600.0

                if hours_elapsed > 0:
                    # Active phase: from ≥ 4 cm, expect 1 cm/hour
                    if last_dil >= 4 and first_dil >= 4:
                        rate = (last_dil - first_dil) / hours_elapsed
                        if rate < 0.5:
                            progress = "arrest"
                            alerts.append({
                                "level": "critical",
                                "message": "🚨 توقف المخاض (Active Phase Arrest)",
                                "recommendation": "تقييم للقيصرية أو الأوكسيتوسين",
                            })
                        elif rate < 1.0:
                            progress = "slow"
                            alerts.append({
                                "level": "warning",
                                "message": "⚠️ مخاض بطيء ({} سم/ساعة)".format(round(rate, 2)),
                                "recommendation": "متابعة أو تحفيز",
                            })
                        else:
                            progress = "normal"

    # Recommendation
    recs = []
    if alerts:
        recs = [a["recommendation"] for a in alerts]
    else:
        recs = ["متابعة روتينية — تقدم طبيعي"]

    return {
        "status": "ok",
        "labor": labor,
        "duration_hours": round(duration_hours, 1),
        "entries_count": len(entries),
        "alerts": alerts,
        "progress": progress,
        "recommendation": recs,
        "latest": latest,
    }


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Partogram Service Test")
    print("=" * 60)

    from core.db import db

    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if not clinics:
        print("❌ لا توجد عيادات")
        exit(1)

    cid = clinics[0]["id"]
    print("\n✅ العيادة: {}".format(clinics[0]["name"]))

    # Test active labors
    labors = list_active_labors(cid)
    print("📋 Active labors: {}".format(len(labors)))

    # Test analysis if there's data
    if labors:
        labor = labors[0]
        analysis = analyze_labor(cid, labor["id"])
        print("\n📊 Analysis:")
        print("  Duration: {} hours".format(analysis.get("duration_hours", 0)))
        print("  Alerts: {}".format(len(analysis.get("alerts", []))))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
