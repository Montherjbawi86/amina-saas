# -*- coding: utf-8 -*-
"""Medical files management (Supabase Storage + DB)"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid as _uuid

from core.db import db, insert, select, update, delete, DBError


class FileError(Exception):
    pass


BUCKET = "medical-files"

CATEGORY_LABELS = {
    "ultrasound": "📷 صورة سونار",
    "lab_result": "🔬 نتيجة تحليل",
    "prescription": "💊 وصفة خارجية",
    "report": "📄 تقرير",
    "other": "📎 أخرى",
}


def _safe_name(name):
    """Sanitize file name"""
    import re
    s = str(name).strip()
    s = re.sub(r"[^a-zA-Z0-9\u0600-\u06FF._-]+", "_", s)
    return s[:120] or "file"


def upload_file(clinic_id, patient_id, uploaded_by, file_bytes, file_name, **kwargs):
    """
    Upload file to Supabase Storage + register in DB.
    file_bytes: bytes
    file_name: original name
    kwargs: category, notes, visit_id, content_type
    """
    if not file_bytes:
        raise FileError("File is empty")
    if not file_name:
        raise FileError("File name required")

    # Path: clinic_id/patient_id/uuid_filename
    file_uuid = _uuid.uuid4().hex[:12]
    safe = _safe_name(file_name)
    storage_path = "{}/{}/{}_{}".format(clinic_id, patient_id, file_uuid, safe)

    content_type = kwargs.get("content_type") or "application/octet-stream"

    try:
        db().storage.from_(BUCKET).upload(
            storage_path, file_bytes,
            {"content-type": content_type, "upsert": "false"}
        )
    except Exception as e:
        raise FileError("فشل الرفع: " + str(e)[:150])

    # Register in DB
    data = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "visit_id": kwargs.get("visit_id"),
        "uploaded_by": uploaded_by,
        "file_name": file_name,
        "storage_path": storage_path,
        "file_type": content_type,
        "file_size_bytes": len(file_bytes),
        "category": kwargs.get("category", "other"),
        "notes": kwargs.get("notes"),
    }

    if data["category"] not in CATEGORY_LABELS:
        data["category"] = "other"

    try:
        rec = insert("medical_files", data)
    except DBError as e:
        # Rollback storage
        try:
            db().storage.from_(BUCKET).remove([storage_path])
        except Exception:
            pass
        raise FileError("فشل حفظ السجل: " + str(e)[:150])

    return rec


def list_files(clinic_id, patient_id=None, category=None, limit=100):
    q = db().table("medical_files").select("*").eq("clinic_id", clinic_id)
    if patient_id:
        q = q.eq("patient_id", patient_id)
    if category:
        q = q.eq("category", category)
    return q.order("uploaded_at", desc=True).limit(limit).execute().data


def get_file(clinic_id, file_id):
    rows = select("medical_files", "*", id=file_id, clinic_id=clinic_id)
    return rows[0] if rows else None


def download_file(clinic_id, file_id):
    """Download file bytes from storage"""
    rec = get_file(clinic_id, file_id)
    if not rec:
        raise FileError("الملف غير موجود")
    try:
        data = db().storage.from_(BUCKET).download(rec["storage_path"])
        return data, rec
    except Exception as e:
        raise FileError("فشل التحميل: " + str(e)[:150])


def delete_file(clinic_id, file_id):
    """Delete from storage + DB"""
    rec = get_file(clinic_id, file_id)
    if not rec:
        raise FileError("الملف غير موجود")

    # Storage first
    try:
        db().storage.from_(BUCKET).remove([rec["storage_path"]])
    except Exception:
        pass

    # DB
    q = db().table("medical_files").delete().eq("id", file_id).eq("clinic_id", clinic_id)
    q.execute()
    return True


def count_files(clinic_id, patient_id=None):
    q = db().table("medical_files").select("id", count="exact").eq("clinic_id", clinic_id)
    if patient_id:
        q = q.eq("patient_id", patient_id)
    return q.execute().count or 0


def count_files_cached(clinic_id, patient_id=None):
    try:
        import streamlit as st
    except ImportError:
        return count_files(clinic_id, patient_id)

    @st.cache_data(ttl=60, show_spinner=False)
    def _cached(cid, pid):
        return count_files(cid, pid)

    return _cached(clinic_id, patient_id)


def format_size(bytes_val):
    if not bytes_val:
        return "—"
    b = float(bytes_val)
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return "{:.1f} {}".format(b, unit)
        b /= 1024
    return "{:.1f} TB".format(b)


def get_signed_url(clinic_id, file_id, expires=3600):
    """Generate signed URL for a file (1 hour default)"""
    rec = get_file(clinic_id, file_id)
    if not rec:
        raise FileError("الملف غير موجود")
    try:
        res = db().storage.from_(BUCKET).create_signed_url(rec["storage_path"], expires)
        return res.get("signedURL") or res.get("signed_url") or res
    except Exception as e:
        raise FileError("فشل إنشاء الرابط: " + str(e)[:150])


# Cached
def list_files_cached(clinic_id, patient_id=None):
    try:
        import streamlit as st
    except ImportError:
        return list_files(clinic_id, patient_id=patient_id)

    @st.cache_data(ttl=60, show_spinner=False)
    def _cached(cid, pid):
        return list_files(cid, patient_id=pid)

    return _cached(clinic_id, patient_id)


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    import uuid
    from core.tenant import create_clinic
    from core.auth import create_user
    from services.patients import create_patient
    from core.db import delete as db_delete

    print("=" * 50)
    print("Files Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("Files Test " + suffix, "Dr. F", "f-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "u-{}@t.com".format(suffix), "secret123", "Dr", "doctor")
    patient = create_patient(clinic["id"], "نور محمد", "+9647700")

    print("\n1. Upload test file:")
    content = b"test ultrasound report - sample content"
    rec = upload_file(
        clinic["id"], patient["id"], user["id"],
        content, "ultrasound_week20.txt",
        category="ultrasound",
        notes="سونار الأسبوع 20",
        content_type="text/plain"
    )
    print("   OK: {}".format(rec["id"][:8]))
    print("   Path: {}".format(rec["storage_path"]))

    print("\n2. List files:")
    files = list_files(clinic["id"], patient_id=patient["id"])
    print("   Total: {}".format(len(files)))
    for f in files:
        print("   - [{}] {} ({})".format(
            f["category"], f["file_name"], format_size(f["file_size_bytes"])))

    print("\n3. Download:")
    data, rec2 = download_file(clinic["id"], rec["id"])
    print("   Downloaded {} bytes".format(len(data)))
    print("   Matches original: {}".format(data == content))

    print("\n4. Count:")
    print("   {}".format(count_files(clinic["id"], patient["id"])))

    print("\n5. Delete:")
    delete_file(clinic["id"], rec["id"])
    files_after = list_files(clinic["id"], patient_id=patient["id"])
    print("   Files after: {}".format(len(files_after)))

    print("\n6. Cleanup:")
    db_delete("clinics", id=clinic["id"])
    print("   OK")

    print("\n" + "=" * 50)
    print("Files module OK")
    print("=" * 50)
