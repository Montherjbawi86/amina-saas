"""Integration test for Day 2"""
import uuid
from core.config import settings, validate_config
from core.db import db, health_check, insert, delete, select

print("=" * 50)
print("Day 2 Integration Test")
print("=" * 50)

# 1. Config
print("\n1. Config:")
ok, errors = validate_config()
print("   Valid: {}".format("OK" if ok else "FAIL"))
if errors:
    for e in errors:
        print("   " + e)

# 2. DB Health
print("\n2. DB Health:")
h = health_check()
print("   Status: {}".format("OK" if h['ok'] else "FAIL"))

# 3. Full cycle
print("\n3. INSERT -> SELECT -> DELETE:")
try:
    test_slug = "test-day2-" + uuid.uuid4().hex[:8]
    test_email = "test-{}@test.com".format(uuid.uuid4().hex[:8])

    clinic = insert("clinics", {
        "name": "Test Clinic Day 2",
        "slug": test_slug,
        "doctor_name": "Dr. Test",
        "email": test_email
    })
    print("   INSERT: {}...".format(clinic['id'][:8]))

    rows = select("clinics", "*", id=clinic["id"])
    assert len(rows) == 1, "Expected 1 row"
    print("   SELECT: {}".format(rows[0]['name']))

    delete("clinics", id=clinic["id"])
    rows = select("clinics", "*", id=clinic["id"])
    assert len(rows) == 0, "Expected 0 rows after delete"
    print("   DELETE: cleaned up")

except Exception as e:
    print("   FAIL: {}".format(e))

print("\n" + "=" * 50)
print("Day 2 COMPLETE!")
print("=" * 50)
