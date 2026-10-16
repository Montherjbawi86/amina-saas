# -*- coding: utf-8 -*-
"""
Drug Interactions Database
قاعدة بيانات تفاعلات الأدوية — شاملة للأدوية الشائعة في النساء والولادة
"""
from typing import List, Dict, Optional


# ============================================
# DRUG CATEGORIES
# ============================================

DRUG_CATEGORIES = {
    "supplements": "💊 مكملات",
    "analgesics": "🩹 مسكنات",
    "antibiotics": "🦠 مضادات حيوية",
    "antihypertensives": "💓 خافضات ضغط",
    "diabetes": "🍬 أدوية سكري",
    "uterotonics": "🤰 أدوية الرحم",
    "anticoagulants": "🩸 مضادات تخثر",
    "antiemetics": "🤢 مضادات قيء",
    "hormones": "⚗️ هرمونات",
    "thyroid": "🦋 أدوية الغدة",
}


# ============================================
# COMMON DRUGS (for autocomplete)
# ============================================

COMMON_DRUGS = [
    # Supplements
    {"name": "فوليك أسيد", "name_en": "Folic Acid", "category": "supplements"},
    {"name": "حديد", "name_en": "Ferrous Sulfate", "category": "supplements"},
    {"name": "فيتامين D", "name_en": "Vitamin D", "category": "supplements"},
    {"name": "كالسيوم", "name_en": "Calcium", "category": "supplements"},
    {"name": "فيتامين B12", "name_en": "Vitamin B12", "category": "supplements"},

    # Analgesics
    {"name": "باراسيتامول", "name_en": "Paracetamol", "category": "analgesics"},
    {"name": "ايبوبروفين", "name_en": "Ibuprofen", "category": "analgesics"},
    {"name": "أسبرين", "name_en": "Aspirin", "category": "analgesics"},

    # Antibiotics
    {"name": "أموكسيسيلين", "name_en": "Amoxicillin", "category": "antibiotics"},
    {"name": "سيفترياكسون", "name_en": "Ceftriaxone", "category": "antibiotics"},
    {"name": "أزيثرومايسين", "name_en": "Azithromycin", "category": "antibiotics"},
    {"name": "ميترونيدازول", "name_en": "Metronidazole", "category": "antibiotics"},
    {"name": "نيتروفورانتوين", "name_en": "Nitrofurantoin", "category": "antibiotics"},

    # Antihypertensives
    {"name": "ميثيلدوبا", "name_en": "Methyldopa", "category": "antihypertensives"},
    {"name": "لابيتالول", "name_en": "Labetalol", "category": "antihypertensives"},
    {"name": "نيفيديبين", "name_en": "Nifedipine", "category": "antihypertensives"},
    {"name": "هيدرالازين", "name_en": "Hydralazine", "category": "antihypertensives"},

    # Diabetes
    {"name": "ميتفورمين", "name_en": "Metformin", "category": "diabetes"},
    {"name": "إنسولين", "name_en": "Insulin", "category": "diabetes"},
    {"name": "جليبنكلاميد", "name_en": "Glibenclamide", "category": "diabetes"},

    # Uterotonics
    {"name": "أوكسيتوسين", "name_en": "Oxytocin", "category": "uterotonics"},
    {"name": "ميزوبروستول", "name_en": "Misoprostol", "category": "uterotonics"},
    {"name": "ميثيل إرغومترين", "name_en": "Methylergometrine", "category": "uterotonics"},

    # Anticoagulants
    {"name": "هيبارين", "name_en": "Heparin", "category": "anticoagulants"},
    {"name": "إنوكسابارين", "name_en": "Enoxaparin", "category": "anticoagulants"},
    {"name": "وارفارين", "name_en": "Warfarin", "category": "anticoagulants"},

    # Antiemetics
    {"name": "ميتوكلوبراميد", "name_en": "Metoclopramide", "category": "antiemetics"},
    {"name": "أوندانسيترون", "name_en": "Ondansetron", "category": "antiemetics"},
    {"name": "دوكسيلامين", "name_en": "Doxylamine", "category": "antiemetics"},

    # Hormones
    {"name": "بروجستيرون", "name_en": "Progesterone", "category": "hormones"},
    {"name": "إستروجين", "name_en": "Estrogen", "category": "hormones"},
    {"name": "ثيروكسين", "name_en": "Levothyroxine", "category": "thyroid"},
]


# ============================================
# DRUG INTERACTIONS
# ============================================

# Format: (drug1_key, drug2_key, severity, description_ar, recommendation_ar)
DRUG_INTERACTIONS = [
    # Iron interactions
    ("حديد", "كالسيوم", "moderate",
     "الحديد + الكالسيوم: انخفاض امتصاص الحديد بنسبة 40%",
     "خذ الحديد والكالسيوم بفاصل ساعتين على الأقل"),

    ("حديد", "مضاد حموضة", "moderate",
     "الحديد + مضادات الحموضة: انخفاض امتصاص الحديد",
     "خذ الحديد قبل ساعتين من مضادات الحموضة"),

    ("حديد", "شاي", "mild",
     "الشاي يُقلل امتصاص الحديد",
     "تجنّب الشاي مع الحديد"),

    ("حديد", "قهوة", "mild",
     "القهوة تُقلل امتصاص الحديد",
     "تجنّب القهوة مع الحديد"),

    # Vitamin D
    ("فيتامين D", "كالسيوم", "info",
     "فيتامين D يُحسّن امتصاص الكالسيوم (تفاعل إيجابي)",
     "من الجيد أخذهما معاً"),

    # NSAIDs
    ("ايبوبروفين", "هيبارين", "severe",
     "ايبوبروفين + هيبارين: خطر نزيف كبير (تأثير مضاعف على تخثر الدم)",
     "⚠️ تجنّب الجمع — استخدم باراسيتامول بدلاً من ايبوبروفين"),

    ("ايبوبروفين", "أسبرين", "moderate",
     "ايبوبروفين + أسبرين: يقلل تأثير الأسبرين على القلب",
     "استخدم أحدهما فقط"),

    ("ايبوبروفين", "ميثيلدوبا", "moderate",
     "ايبوبروفين قد يُقلل تأثير خافضات الضغط",
     "راقب ضغط الدم"),

    ("أسبرين", "هيبارين", "severe",
     "أسبرين + هيبارين: خطر نزيف",
     "⚠️ يحتاج مراقبة دقيقة INR"),

    ("أسبرين", "وارفارين", "severe",
     "أسبرين + وارفارين: خطر نزيف كبير",
     "⚠️ ممنوع الجمع بدون إشراف مختص"),

    # Antibiotics
    ("ميترونيدازول", "وارفارين", "severe",
     "ميترونيدازول يُضاعف تأثير وارفارين → خطر نزيف",
     "⚠️ قلل جرعة وارفارين وراقب INR يومياً"),

    ("أزيثرومايسين", "وارفارين", "moderate",
     "أزيثرومايسين يُقوّي تأثير وارفارين",
     "راقب INR"),

    ("سيبروفلوكساسين", "وارفارين", "severe",
     "سيبروفلوكساسين + وارفارين: خطر نزيف",
     "راقب INR"),

    # Diabetes
    ("ميتفورمين", "إنسولين", "moderate",
     "ميتفورمين + إنسولين: خطر هبوط سكر",
     "راقب السكر قبل الوجبات"),

    ("ميتفورمين", "جليبنكلاميد", "moderate",
     "خطر هبوط سكر مضاعف",
     "قلل الجرعات"),

    # Antihypertensives
    ("ميثيلدوبا", "لابيتالول", "moderate",
     "تأثير خافض ضغط مضاعف — قد يُسبب هبوط",
     "راقب الضغط بعناية"),

    ("نيفيديبين", "ميثيلدوبا", "mild",
     "تأثير خافض ضغط مضاعف",
     "راقب الضغط"),

    ("نيفيديبين", "مغنيسيوم", "moderate",
     "نيفيديبين + كبريتات المغنيسيوم: هبوط ضغط شديد",
     "⚠️ يحتاج مراقبة دقيقة في حالة تسمم الحمل"),

    # Uterotonics
    ("أوكسيتوسين", "ميزوبروستول", "severe",
     "⚠️ استخدام أوكسيتوسين + ميزوبروستول معاً = فرط تحفيز الرحم (خطر انفجار الرحم)",
     "لا تستخدمهما معاً — انتظر 4 ساعات بينهما"),

    ("أوكسيتوسين", "ميثيل إرغومترين", "moderate",
     "تأثير متزامن على الرحم",
     "استخدم أحدهما فقط في نفس الوقت"),

    ("ميزوبروستول", "ميثيل إرغومترين", "moderate",
     "تأثير متزامن على الرحم",
     "احترس من فرط انقباض الرحم"),

    # Antiemetics
    ("ميتوكلوبراميد", "أوندانسيترون", "mild",
     "قد يُسببان prolongation QT",
     "راقب تخطيط القلب للحالات القلبية"),

    # Thyroid
    ("ثيروكسين", "كالسيوم", "moderate",
     "الكالسيوم يُقلل امتصاص الثيروكسين",
     "خذ الثيروكسين على معدة فارغة، وبفاصل 4 ساعات عن الكالسيوم"),

    ("ثيروكسين", "حديد", "moderate",
     "الحديد يُقلل امتصاص الثيروكسين",
     "بفاصل 4 ساعات على الأقل"),

    ("ثيروكسين", "مضاد حموضة", "moderate",
     "مضادات الحموضة تُقلل امتصاص الثيروكسين",
     "بفاصل 4 ساعات"),

    # Hormones
    ("بروجستيرون", "إستروجين", "info",
     "شائع في حبوب منع الحمل والعلاج الهرموني",
     "لا تفاعل ضار"),

    # Antibiotics + Supplements
    ("نيتروفورانتوين", "حديد", "mild",
     "الحديد قد يُقلل امتصاص نيتروفورانتوين",
     "بفاصل ساعتين"),

    # Food interactions
    ("وارفارين", "خضروات ورقية", "moderate",
     "فيتامين K في الخضروات الورقية يُقلل تأثير وارفارين",
     "حافظ على كمية ثابتة يومياً"),

    ("ميتفورمين", "كحول", "severe",
     "خطر الحماض اللبني (lactic acidosis)",
     "⚠️ تجنّب الكحول تماماً مع ميتفورمين"),
]


# ============================================
# NORMALIZATION
# ============================================

def _normalize(name):
    """Normalize drug name for matching"""
    if not name:
        return ""
    n = str(name).strip().lower()
    # Remove common suffixes
    for suffix in [" 5mg", " 10mg", " 500mg", " 65mg", " حبوب", " أقراص", " شراب", " كبسولات"]:
        n = n.replace(suffix, "")
    return n


def _find_drug_by_name(name):
    """Find drug in COMMON_DRUGS by name (Arabic or English)"""
    if not name:
        return None
    norm = _normalize(name)
    for d in COMMON_DRUGS:
        if _normalize(d["name"]) in norm or _normalize(d.get("name_en", "")) in norm:
            return d
        if norm in _normalize(d["name"]) or norm in _normalize(d.get("name_en", "")):
            return d
    return None


# ============================================
# INTERACTION CHECK
# ============================================

def check_interactions(medications):
    """
    Check interactions in a list of medications.
    medications: [{"name": "...", "dose": "...", ...}]

    Returns: list of interaction dicts, sorted by severity.
    """
    if not medications:
        return []

    # Extract drug names
    names = []
    for m in medications:
        if isinstance(m, dict):
            n = m.get("name") or m.get("drug") or ""
            if n:
                names.append(n.strip())
        elif isinstance(m, str):
            names.append(m.strip())

    if len(names) < 1:
        return []

    found = []

    # Check all pairs
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1 = _normalize(names[i])
            n2 = _normalize(names[j])

            for interaction in DRUG_INTERACTIONS:
                d1, d2, severity, desc, rec = interaction
                d1n = _normalize(d1)
                d2n = _normalize(d2)

                # Check both orders
                if (d1n in n1 and d2n in n2) or (d1n in n2 and d2n in n1):
                    found.append({
                        "drug1": names[i],
                        "drug2": names[j],
                        "severity": severity,
                        "description": desc,
                        "recommendation": rec,
                    })

    # Sort by severity
    severity_order = {"severe": 0, "moderate": 1, "mild": 2, "info": 3}
    found.sort(key=lambda x: severity_order.get(x["severity"], 99))

    return found


def get_severity_label(severity):
    return {
        "severe": "🔴 خطير",
        "moderate": "🟠 متوسط",
        "mild": "🟡 خفيف",
        "info": "ℹ️ معلومة",
    }.get(severity, "—")


def get_severity_color(severity):
    return {
        "severe": "#DC2626",
        "moderate": "#F97316",
        "mild": "#F59E0B",
        "info": "#0EA5E9",
    }.get(severity, "#94A3B8")


def get_severity_icon(severity):
    return {
        "severe": "🚨",
        "moderate": "⚠️",
        "mild": "🟡",
        "info": "ℹ️",
    }.get(severity, "•")


# ============================================
# PREGNANCY-SPECIFIC WARNINGS
# ============================================

PREGNANCY_WARNINGS = {
    "warfarin": {
        "category": "X",
        "warning": "⚠️ ممنوع في الحمل — يُسبب تشوهات جنينية",
        "alternative": "استخدم هيبارين/إنوكسابارين",
    },
    "ace_inhibitors": {
        "category": "X",
        "warning": "⚠️ ممنوع في الحمل — خطر على الكلى الجنينية",
        "alternative": "استخدم ميثيلدوبا أو لابيتالول",
    },
    "nsaids_third_trimester": {
        "category": "D",
        "warning": "⚠️ تجنّب في الثلث الثالث — يُسبب إغلاق القناة الشريانية",
        "alternative": "استخدم باراسيتامول",
    },
    "isotretinoin": {
        "category": "X",
        "warning": "⚠️ ممنوع تماماً — تشوهات شديدة",
        "alternative": "إيقاف قبل الحمل بفترة",
    },
    "methotrexate": {
        "category": "X",
        "warning": "⚠️ ممنوع — إجهاض وتشوهات",
        "alternative": "بديل حسب الحالة",
    },
    "ciprofloxacin": {
        "category": "C",
        "warning": "⚠️ تجنّب إلا للضرورة — خطر على الغضاريف",
        "alternative": "أموكسيسيلين أو سيفالوسبورين",
    },
    "tetracycline": {
        "category": "D",
        "warning": "⚠️ تصبغ أسنان الجنين",
        "alternative": "بديل مناسب",
    },
}


def check_pregnancy_warning(drug_name):
    """Check if a drug has pregnancy warning"""
    if not drug_name:
        return None

    norm = _normalize(drug_name)

    for key, warning in PREGNANCY_WARNINGS.items():
        if key.replace("_", " ") in norm or key in norm:
            return warning

    return None


# ============================================
# SEARCH
# ============================================

def search_drugs(query, limit=20):
    """Search drugs by name"""
    if not query:
        return COMMON_DRUGS[:limit]

    q = _normalize(query)
    results = []
    for d in COMMON_DRUGS:
        if q in _normalize(d["name"]) or q in _normalize(d.get("name_en", "")):
            results.append(d)
    return results[:limit]


def get_drugs_by_category(category):
    """Get drugs filtered by category"""
    if not category or category == "all":
        return COMMON_DRUGS
    return [d for d in COMMON_DRUGS if d.get("category") == category]


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Drug Interactions DB Test")
    print("=" * 60)

    print("\n📊 Database:")
    print("  الأدوية: {}".format(len(COMMON_DRUGS)))
    print("  التفاعلات: {}".format(len(DRUG_INTERACTIONS)))
    print("  التصنيفات: {}".format(len(DRUG_CATEGORIES)))

    print("\n🔍 Test 1: حديد + كالسيوم")
    meds = [{"name": "حديد"}, {"name": "كالسيوم"}]
    results = check_interactions(meds)
    for r in results:
        print("  {} {} — {}".format(
            get_severity_icon(r["severity"]),
            get_severity_label(r["severity"]),
            r["description"][:60]))

    print("\n🔍 Test 2: أوكسيتوسين + ميزوبروستول")
    meds = [{"name": "أوكسيتوسين"}, {"name": "ميزوبروستول"}]
    results = check_interactions(meds)
    for r in results:
        print("  {} {}".format(
            get_severity_icon(r["severity"]),
            r["description"][:80]))

    print("\n🔍 Test 3: 3 أدوية")
    meds = [{"name": "حديد"}, {"name": "كالسيوم"}, {"name": "فيتامين D"}]
    results = check_interactions(meds)
    print("  وجد {} تفاعل".format(len(results)))
    for r in results:
        print("  - {}".format(r["description"][:60]))

    print("\n🔍 Test 4: pregnancy warning")
    w = check_pregnancy_warning("وارفارين")
    if w:
        print("  {}".format(w["warning"]))

    print("\n🔍 Test 5: search")
    r = search_drugs("حديد")
    print("  نتائج البحث: {}".format(len(r)))

    print("\n" + "=" * 60)
    print("OK")
    print("=" * 60)
