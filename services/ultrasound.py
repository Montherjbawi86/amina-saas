# -*- coding: utf-8 -*-
"""
Ultrasound Gallery Service
إدارة صور السونار — رفع، عرض، حذف
"""
from datetime import datetime, date
from io import BytesIO
from typing import Optional, List, Dict, Any
import uuid

from core.db import db, insert, update, delete


BUCKET_NAME = "ultrasound-images"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"]


# ============================================
# UPLOAD
# ============================================

def upload_image(clinic_id, patient_id, file_bytes, file_name, mime_type,
                 doctor_id=None, visit_id=None, image_date=None,
                 gestational_weeks=None, caption=None, notes=None):
    """
    Upload an ultrasound image to Supabase Storage + create DB record.

    Returns: created row dict, or raises Exception.
    """
    # Validate
    if not file_bytes:
        raise ValueError("الملف فارغ")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("الملف كبير جداً (الحد 10 MB)")
    if mime_type not in ALLOWED_TYPES:
        raise ValueError("نوع الملف غير مدعوم: {}".format(mime_type))

    # Build unique storage path
    ext = _ext_from_mime(mime_type, file_name)
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_path = "{}/{}/{}_{}.{}".format(
        clinic_id, patient_id, timestamp, unique_id, ext
    )

    # Upload to Supabase Storage
    try:
        result = db().storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type, "upsert": "true"}
        )
    except Exception as e:
        raise Exception("فشل رفع الصورة: {}".format(str(e)[:200]))

    # Get public URL
    try:
        url_resp = db().storage.from_(BUCKET_NAME).get_public_url(storage_path)
        public_url = url_resp if isinstance(url_resp, str) else url_resp.get("publicURL", "")
    except Exception:
        public_url = ""

    # Insert DB row
    row = {
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "visit_id": visit_id,
        "doctor_id": doctor_id,
        "storage_path": storage_path,
        "public_url": public_url,
        "file_name": file_name or "ultrasound",
        "file_size": len(file_bytes),
        "mime_type": mime_type,
        "gestational_weeks": gestational_weeks,
        "image_date": str(image_date) if image_date else str(date.today()),
        "caption": caption,
        "notes": notes,
    }

    return insert("ultrasound_images", row)


def _ext_from_mime(mime, original_name):
    """Determine file extension"""
    m = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
    }
    if mime in m:
        return m[mime]
    # Fallback: from filename
    if original_name and "." in original_name:
        return original_name.rsplit(".", 1)[-1].lower()[:5]
    return "jpg"


# ============================================
# READ
# ============================================

def get_image(clinic_id, image_id):
    """Fetch a single image row"""
    try:
        rows = (
            db().table("ultrasound_images")
            .select("*")
            .eq("clinic_id", clinic_id)
            .eq("id", image_id)
            .limit(1)
            .execute()
            .data or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def list_images(clinic_id, patient_id=None, date_from=None, date_to=None,
                min_weeks=None, max_weeks=None, limit=500):
    """List images with filters"""
    try:
        q = db().table("ultrasound_images").select("*").eq("clinic_id", clinic_id)

        if patient_id:
            q = q.eq("patient_id", patient_id)
        if date_from:
            q = q.gte("image_date", str(date_from))
        if date_to:
            q = q.lte("image_date", str(date_to))
        if min_weeks is not None:
            q = q.gte("gestational_weeks", min_weeks)
        if max_weeks is not None:
            q = q.lte("gestational_weeks", max_weeks)

        q = q.order("image_date", desc=True).limit(limit)
        return q.execute().data or []
    except Exception as e:
        print("[ultrasound] list error: {}".format(e))
        return []


def list_patient_images(clinic_id, patient_id, limit=200):
    """All images for one patient"""
    return list_images(clinic_id, patient_id=patient_id, limit=limit)


# ============================================
# UPDATE
# ============================================

def update_image(clinic_id, image_id, **fields):
    """Update caption/notes/etc"""
    allowed = {"caption", "notes", "gestational_weeks", "image_date", "visit_id"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        raise ValueError("لا توجد حقول للتحديث")
    return update("ultrasound_images", {"id": image_id, "clinic_id": clinic_id}, clean)


# ============================================
# DELETE
# ============================================

def delete_image(clinic_id, image_id):
    """Delete from Storage + DB"""
    img = get_image(clinic_id, image_id)
    if not img:
        return False

    # Delete from Storage
    try:
        db().storage.from_(BUCKET_NAME).remove([img["storage_path"]])
    except Exception as e:
        print("[ultrasound] storage delete failed: {}".format(e))

    # Delete DB row
    try:
        delete("ultrasound_images", id=image_id, clinic_id=clinic_id)
        return True
    except Exception as e:
        print("[ultrasound] db delete failed: {}".format(e))
        return False


# ============================================
# STATS
# ============================================

def get_patient_summary(clinic_id, patient_id):
    """Summary of patient's ultrasound images"""
    imgs = list_patient_images(clinic_id, patient_id, limit=500)
    total = len(imgs)

    if total == 0:
        return {
            "total": 0,
            "first_date": None,
            "last_date": None,
            "total_size_mb": 0.0,
            "weeks_range": None,
        }

    total_size = sum(i.get("file_size", 0) or 0 for i in imgs)
    dates = [i.get("image_date") for i in imgs if i.get("image_date")]
    weeks = [i.get("gestational_weeks") for i in imgs if i.get("gestational_weeks")]

    return {
        "total": total,
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
        "total_size_mb": total_size / (1024.0 * 1024.0),
        "weeks_range": (min(weeks), max(weeks)) if weeks else None,
    }


def get_clinic_summary(clinic_id):
    """Overall stats for the clinic"""
    try:
        r = db().table("ultrasound_images").select("id", count="exact").eq("clinic_id", clinic_id).execute()
        return {"total": r.count or 0}
    except Exception:
        return {"total": 0}


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Ultrasound Service Test")
    print("=" * 60)

    from core.db import db

    # Check bucket
    try:
        buckets = db().storage.list_buckets()
        names = [b.name for b in buckets]
        print("✅ Buckets: {}".format(names))
        if BUCKET_NAME not in names:
            print("❌ Bucket '{}' غير موجود!".format(BUCKET_NAME))
        else:
            print("✅ Bucket '{}' متاح".format(BUCKET_NAME))
    except Exception as e:
        print("⚠️ storage check: {}".format(str(e)[:150]))

    # Check table
    try:
        r = db().table("ultrasound_images").select("id", count="exact").execute()
        print("✅ جدول ultrasound_images — rows: {}".format(r.count or 0))
    except Exception as e:
        print("❌ table: {}".format(str(e)[:150]))

    print("=" * 60)
