# -*- coding: utf-8 -*-
"""
Audit Log Service
سجل التغييرات والإجراءات
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from core.db import db


# ============================================
# CONSTANTS
# ============================================

ACTION_ICONS = {
    "create": "➕",
    "update": "✏️",
    "delete": "🗑️",
    "login": "🔓",
    "logout": "🔒",
    "signup": "🆕",
    "view": "👁️",
    "export": "📥",
    "print": "🖨️",
    "enable_2fa": "🛡️",
    "disable_2fa": "⚠️",
}

ACTION_LABELS = {
    "create": "إنشاء",
    "update": "تعديل",
    "delete": "حذف",
    "login": "تسجيل دخول",
    "logout": "تسجيل خروج",
    "signup": "إنشاء حساب",
    "view": "عرض",
    "export": "تصدير",
    "print": "طباعة",
    "enable_2fa": "تفعيل 2FA",
    "disable_2fa": "إلغاء 2FA",
}

ACTION_COLORS = {
    "create": "#10B981",
    "update": "#F59E0B",
    "delete": "#EF4444",
    "login": "#22C55E",
    "logout": "#64748B",
    "signup": "#8B5CF6",
    "view": "#94A3B8",
    "export": "#0EA5E9",
    "print": "#6366F1",
}

ENTITY_LABELS = {
    "patient": "👩 حامل",
    "visit": "🩺 زيارة",
    "prescription": "💊 وصفة",
    "lab_test": "🔬 تحليل",
    "vaccination": "💉 تحصين",
    "ultrasound": "📸 سونار",
    "certificate": "📄 شهادة",
    "user": "👤 مستخدم",
    "clinic": "🏥 عيادة",
    "session": "🔐 جلسة",
    "share_link": "🔗 رابط",
    "medical_file": "📎 ملف",
}


def get_action_icon(action):
    return ACTION_ICONS.get(action, "•")


def get_action_label(action):
    return ACTION_LABELS.get(action, action)


def get_action_color(action):
    return ACTION_COLORS.get(action, "#94A3B8")


def get_entity_label(entity_type):
    return ENTITY_LABELS.get(entity_type, entity_type)


# ============================================
# WRITE
# ============================================

def log_action(clinic_id, user_id, action, entity_type, entity_id=None,
               details=None, ip_address=None, user_agent=None):
    """
    Log an action. Silently fails (never breaks main flow).
    Returns: created row or None
    """
    try:
        row = {
            "clinic_id": clinic_id,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        result = db().table("audit_log").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        # Silent fail — audit must never break the app
        print("[audit] log failed: {}".format(str(e)[:100]))
        return None


def log_from_session(clinic_id, user_id, action, entity_type, entity_id=None, details=None):
    """Log with auto-timestamp (uses current context)"""
    return log_action(
        clinic_id=clinic_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


# ============================================
# READ
# ============================================

def list_logs(clinic_id, user_id=None, action=None, entity_type=None,
              date_from=None, date_to=None, search=None, limit=200):
    """List audit logs with filters"""
    try:
        q = db().table("audit_log").select(
            "id,clinic_id,user_id,action,entity_type,entity_id,details,created_at"
        ).eq("clinic_id", clinic_id)

        if user_id:
            q = q.eq("user_id", user_id)
        if action:
            q = q.eq("action", action)
        if entity_type:
            q = q.eq("entity_type", entity_type)
        if date_from:
            q = q.gte("created_at", str(date_from) + "T00:00:00")
        if date_to:
            q = q.lte("created_at", str(date_to) + "T23:59:59")

        q = q.order("created_at", desc=True).limit(limit)
        rows = q.execute().data or []

        # Enrich with user names
        uids = list({r["user_id"] for r in rows if r.get("user_id")})
        if uids:
            users = db().table("users").select(
                "id,full_name,role"
            ).in_("id", uids).execute().data or []
            umap = {u["id"]: u for u in users}
            for r in rows:
                u = umap.get(r.get("user_id"), {})
                r["_user_name"] = u.get("full_name", "—")
                r["_user_role"] = u.get("role", "—")

        # Search in details
        if search:
            s = search.lower()
            rows = [
                r for r in rows
                if s in str(r.get("details", "")).lower()
                or s in str(r.get("_user_name", "")).lower()
                or s in str(r.get("entity_type", "")).lower()
            ]

        return rows
    except Exception as e:
        print("[audit] list failed: {}".format(e))
        return []


def get_user_activity(clinic_id, user_id, days=30):
    """Activity summary for a specific user"""
    try:
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = db().table("audit_log").select(
            "id,action,entity_type,created_at"
        ).eq("clinic_id", clinic_id).eq("user_id", user_id).gte(
            "created_at", since
        ).execute().data or []

        from collections import Counter
        actions = Counter(r.get("action", "?") for r in rows)
        entities = Counter(r.get("entity_type", "?") for r in rows)

        return {
            "total": len(rows),
            "actions": dict(actions),
            "entities": dict(entities),
            "days": days,
        }
    except Exception as e:
        print("[audit] user_activity failed: {}".format(e))
        return {"total": 0, "actions": {}, "entities": {}, "days": days}


def get_summary(clinic_id, days=30):
    """Overall audit summary for clinic"""
    try:
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = db().table("audit_log").select(
            "id,user_id,action,entity_type,created_at"
        ).eq("clinic_id", clinic_id).gte("created_at", since).execute().data or []

        from collections import Counter
        actions = Counter(r.get("action", "?") for r in rows)
        users = Counter(r.get("user_id") for r in rows if r.get("user_id"))
        entities = Counter(r.get("entity_type", "?") for r in rows)

        # Get user names
        uids = list(users.keys())
        umap = {}
        if uids:
            urows = db().table("users").select("id,full_name").in_(
                "id", uids
            ).execute().data or []
            umap = {u["id"]: u.get("full_name", "—") for u in urows}

        top_users = [
            {"user_id": uid, "name": umap.get(uid, "—"), "count": cnt}
            for uid, cnt in users.most_common(5)
        ]

        return {
            "total": len(rows),
            "days": days,
            "actions": dict(actions),
            "entities": dict(entities),
            "top_users": top_users,
        }
    except Exception as e:
        print("[audit] summary failed: {}".format(e))
        return {"total": 0, "actions": {}, "entities": {}, "top_users": [], "days": days}


def get_available_actions():
    """Return list of action keys"""
    return list(ACTION_LABELS.keys())


def get_available_entities():
    """Return list of entity type keys"""
    return list(ENTITY_LABELS.keys())


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Audit Log Service Test")
    print("=" * 60)

    from core.db import db
    clinics = db().table("clinics").select("id,name").limit(1).execute().data
    if not clinics:
        print("❌ لا توجد عيادات")
        exit(1)

    cid = clinics[0]["id"]
    print("\n✅ العيادة: {}".format(clinics[0]["name"]))

    # Test write
    result = log_action(
        clinic_id=cid,
        user_id=None,
        action="create",
        entity_type="patient",
        entity_id=None,
        details={"test": True, "source": "audit_test"}
    )
    print("\n✅ log_action: {}".format("OK" if result else "FAILED"))

    # Test read
    logs = list_logs(cid, limit=5)
    print("✅ list_logs: {} نتيجة".format(len(logs)))

    # Test summary
    summary = get_summary(cid, days=30)
    print("✅ summary: total={}".format(summary["total"]))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
