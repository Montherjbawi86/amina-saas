# -*- coding: utf-8 -*-
"""
اختبار سريع لـ Excel Export
يُشغَّل محلياً أو على Render Shell
"""
import sys
from core.db import db


def main():
    print("=" * 60)
    print("Excel Export - Test")
    print("=" * 60)

    # 1. Get first clinic
    try:
        clinics = db().table("clinics").select("id, name").limit(1).execute().data
        if not clinics:
            print("ERROR: No clinic in database")
            return 1
        clinic = clinics[0]
        clinic_id = clinic["id"]
        print("OK Clinic: {}".format(clinic["name"]))
    except Exception as e:
        print("ERROR connection: {}".format(e))
        return 1

    # 2. Test each export
    from services.excel_export import (
        export_patients, export_visits, export_prescriptions,
        export_vaccinations, export_all
    )

    tests = [
        ("Patients", export_patients),
        ("Visits", export_visits),
        ("Prescriptions", export_prescriptions),
        ("Vaccinations", export_vaccinations),
        ("All", export_all),
    ]

    for name, func in tests:
        try:
            data = func(clinic_id)
            size_kb = len(data) / 1024.0
            print("OK {}: {:.1f} KB".format(name, size_kb))
        except Exception as e:
            print("ERROR {}: {}".format(name, str(e)[:120]))
            return 1

    print("=" * 60)
    print("OK All tests passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
