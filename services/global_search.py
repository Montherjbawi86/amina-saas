# -*- coding: utf-8 -*-
"""
Global Search Service
بحث شامل في كل بيانات العيادة
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from core.db import db


# ============================================
# HELPERS
# ============================================

def _safe(s):
    """Normalize string for search"""
    if not s:
        return ""
    return str(s).lower().strip()


def _match(text, query):
    """Simple contains match (case-insensitive)"""
    if not query:
        return True
    return _safe(query) in _safe(text)


def _highlight(text, query, max_len=100):
    """Truncate text around query match"""
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# ============================================
# SEARCH: PATIENTS
# ============================================

def search_patients(clinic_id, query, limit=20):
    """Search patients by name, phone, or national_id"""
    if not query or len(query) < 2:
        return []

    try:
        q = _safe(query)

        # Get all active patients
        rows = (
            db().table("patients")
            .select("id,full_name,phone,national_id,risk_level,lmp,edd,is_active")
            .eq("clinic_id", clinic_id)
            .limit(200)
            .execute()
            .data or []
        )

        results = []
        for p in rows:
            if not p.get("is_active", True):
                continue

            name = _safe(p.get("full_name"))
            phone = _safe(p.get("phone"))
            nid = _safe(p.get("national_id"))

            if q in name or q in phone or q in nid:
                results.append({
                    "type": "patient",
                    "id": p["id"],
                    "title": p.get("full_name", "—"),
                    "subtitle": "📞 {}".format(p.get("phone", "—")),
                    "meta": "مخاطر: {}".format(p.get("risk_level", "low")),
                    "icon": "👩",
                    "color": "#16A34A",
                    "nav": "patients",
                    "extra": {"patient_id": p["id"]},
                })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        print("[global_search] patients error: {}".format(e))
        return []


# ============================================
# SEARCH: VISITS
# ============================================

def search_visits(clinic_id, query, limit=20):
    """Search visits by notes"""
    if not query or len(query) < 2:
        return []

    try:
        q = _safe(query)

        rows = (
            db().table("visits")
            .select("id,patient_id,visit_date,notes,gestational_age_weeks")
            .eq("clinic_id", clinic_id)
            .order("visit_date", desc=True)
            .limit(200)
            .execute()
            .data or []
        )

        # Enrich patient names
        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p.get("full_name", "—") for p in pats}

        results = []
        for v in rows:
            notes = _safe(v.get("notes"))
            if q in notes:
                results.append({
                    "type": "visit",
                    "id": v["id"],
                    "title": "🩺 زيارة — {}".format(
                        pmap.get(v.get("patient_id"), "—")),
                    "subtitle": "📅 {}".format(
                        str(v.get("visit_date", ""))[:10]),
                    "meta": _highlight(v.get("notes"), query),
                    "icon": "🩺",
                    "color": "#0EA5A0",
                    "nav": "patients",
                    "extra": {"patient_id": v.get("patient_id")},
                })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        print("[global_search] visits error: {}".format(e))
        return []


# ============================================
# SEARCH: LAB TESTS
# ============================================

def search_labs(clinic_id, query, limit=20):
    """Search lab tests by test name or patient name"""
    if not query or len(query) < 2:
        return []

    try:
        q = _safe(query)

        rows = (
            db().table("lab_tests")
            .select("id,patient_id,test_name,test_type,test_date,is_abnormal,severity")
            .eq("clinic_id", clinic_id)
            .order("test_date", desc=True)
            .limit(200)
            .execute()
            .data or []
        )

        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p.get("full_name", "—") for p in pats}

        results = []
        for t in rows:
            name = _safe(t.get("test_name"))
            pname = _safe(pmap.get(t.get("patient_id"), ""))
            if q in name or q in pname:
                is_abn = t.get("is_abnormal", False)
                badge = " ⚠️" if is_abn else ""
                results.append({
                    "type": "lab",
                    "id": t["id"],
                    "title": "🔬 {}{}".format(t.get("test_name", "—"), badge),
                    "subtitle": "👩 {} · 📅 {}".format(
                        pmap.get(t.get("patient_id"), "—"),
                        str(t.get("test_date", ""))[:10]),
                    "meta": "الخطورة: {}".format(t.get("severity", "normal")),
                    "icon": "🔬",
                    "color": "#F59E0B" if is_abn else "#10B981",
                    "nav": "lab_tests",
                    "extra": {"patient_id": t.get("patient_id")},
                })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        print("[global_search] labs error: {}".format(e))
        return []


# ============================================
# SEARCH: CERTIFICATES
# ============================================

def search_certificates(clinic_id, query, limit=20):
    """Search certificates by patient name or ID"""
    if not query or len(query) < 2:
        return []

    try:
        q = _safe(query)

        rows = (
            db().table("certificates")
            .select("id,patient_id,issued_at,is_active")
            .eq("clinic_id", clinic_id)
            .order("issued_at", desc=True)
            .limit(200)
            .execute()
            .data or []
        )

        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p.get("full_name", "—") for p in pats}

        results = []
        for c in rows:
            pname = _safe(pmap.get(c.get("patient_id"), ""))
            cid = _safe(str(c.get("id", ""))[:8])
            if q in pname or q in cid:
                results.append({
                    "type": "certificate",
                    "id": c["id"],
                    "title": "📄 شهادة حمل",
                    "subtitle": "👩 {} · 📅 {}".format(
                        pmap.get(c.get("patient_id"), "—"),
                        str(c.get("issued_at", ""))[:10]),
                    "meta": "المعرف: {}".format(cid.upper()),
                    "icon": "📄",
                    "color": "#7B2D8E",
                    "nav": "certificate",
                    "extra": {"patient_id": c.get("patient_id")},
                })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        print("[global_search] certs error: {}".format(e))
        return []


# ============================================
# SEARCH: PRESCRIPTIONS
# ============================================

def search_prescriptions(clinic_id, query, limit=20):
    """Search prescriptions by diagnosis"""
    if not query or len(query) < 2:
        return []

    try:
        q = _safe(query)

        rows = (
            db().table("prescriptions")
            .select("id,patient_id,issued_at,diagnosis")
            .eq("clinic_id", clinic_id)
            .order("issued_at", desc=True)
            .limit(200)
            .execute()
            .data or []
        )

        pids = list({r["patient_id"] for r in rows if r.get("patient_id")})
        pmap = {}
        if pids:
            pats = (
                db().table("patients")
                .select("id,full_name")
                .in_("id", pids)
                .execute()
                .data or []
            )
            pmap = {p["id"]: p.get("full_name", "—") for p in pats}

        results = []
        for p in rows:
            diag = _safe(p.get("diagnosis"))
            pname = _safe(pmap.get(p.get("patient_id"), ""))
            if q in diag or q in pname:
                results.append({
                    "type": "prescription",
                    "id": p["id"],
                    "title": "💊 وصفة — {}".format(
                        p.get("diagnosis", "—")[:40] or "بدون تشخيص"),
                    "subtitle": "👩 {} · 📅 {}".format(
                        pmap.get(p.get("patient_id"), "—"),
                        str(p.get("issued_at", ""))[:10]),
                    "meta": _highlight(p.get("diagnosis"), query),
                    "icon": "💊",
                    "color": "#0EA5E9",
                    "nav": "medical",
                    "extra": {"patient_id": p.get("patient_id")},
                })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        print("[global_search] prescriptions error: {}".format(e))
        return []


# ============================================
# MASTER SEARCH
# ============================================

def search_all(clinic_id, query):
    """Search across all entity types"""
    if not query or len(query.strip()) < 2:
        return {
            "query": query,
            "total": 0,
            "patients": [],
            "visits": [],
            "labs": [],
            "certificates": [],
            "prescriptions": [],
        }

    query = query.strip()

    patients = search_patients(clinic_id, query, limit=15)
    visits = search_visits(clinic_id, query, limit=15)
    labs = search_labs(clinic_id, query, limit=15)
    certs = search_certificates(clinic_id, query, limit=10)
    presc = search_prescriptions(clinic_id, query, limit=10)

    return {
        "query": query,
        "total": len(patients) + len(visits) + len(labs) + len(certs) + len(presc),
        "patients": patients,
        "visits": visits,
        "labs": labs,
        "certificates": certs,
        "prescriptions": presc,
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Global Search Service Test")
    print("=" * 60)

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if not clinics:
        print("❌ لا توجد عيادات")
        exit(1)

    cid = clinics[0]["id"]
    print("\n✅ العيادة: {}".format(clinics[0]["name"]))

    # Test queries
    for q in ["فاطمة", "CBC", "964"]:
        print("\n🔍 البحث عن: '{}'".format(q))
        r = search_all(cid, q)
        print("   إجمالي: {}".format(r["total"]))
        for k in ["patients", "visits", "labs", "certificates", "prescriptions"]:
            if r[k]:
                print("   - {}: {}".format(k, len(r[k])))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
