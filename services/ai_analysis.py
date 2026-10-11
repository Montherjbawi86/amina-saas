# -*- coding: utf-8 -*-
import os as _os
_os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
_os.environ.setdefault('LANG', 'en_US.UTF-8')
_os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

"""AI-powered risk analysis using Groq"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from groq import Groq

from core.config import settings
from core.db import insert, select, update, DBError


class AIError(Exception):
    pass


# Model configuration
DEFAULT_MODEL = "openai/gpt-oss-20b"      # fast
DEEP_MODEL = "openai/gpt-oss-120b"        # thorough


def _get_client():
    if not settings.GROQ_API_KEY:
        raise AIError("GROQ_API_KEY missing in .env")
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LANG", "en_US.UTF-8")
    os.environ.setdefault("LC_ALL", "en_US.UTF-8")
    return Groq(api_key=settings.GROQ_API_KEY)


# ============================================
# Prompt building
# ============================================
SYSTEM_PROMPT = """أنت طبيب نساء وولادة عربي خبير. يجب أن تكون كل ردودك باللغة العربية الفصحى حصراً.

قواعد إلزامية:
1. كل النصوص (summary, issue, action, positives, recommendations) بالعربية
2. لا تستخدم أي كلمة إنجليزية إلا للمصطلحات الطبية الضرورية
3. اتبع صيغة JSON المطلوبة بدقة

Schema:
{
  "risk_level": "low"|"medium"|"high",
  "summary": "ملخص بالعربية (سطرين كحد أقصى)",
  "concerns": [
    {"issue": "المشكلة بالعربية", "severity": "high|medium|low", "action": "الإجراء بالعربية"}
  ],
  "positives": ["نقطة إيجابية بالعربية"],
  "recommendations": ["توصية بالعربية"],
  "next_visit_days": 7,
  "urgent": false
}

قيود:
- concerns: 3 كحد أقصى
- positives: 3 كحد أقصى
- recommendations: 5 كحد أقصى
- urgent: true فقط للحالات الحرجة جداً

مهم جداً: أجب بالعربية فقط. أي كلمة إنجليزية (غير المصطلحات الطبية) ستعتبر خطأ.

JSON صالح فقط."""


def build_patient_context(patient: Dict, visits: List[Dict]) -> str:
    """Build a detailed prompt with patient data"""
    lines = []
    lines.append("=== بيانات الحامل ===")
    lines.append("الاسم: {}".format(patient.get("full_name", "-")))
    lines.append("العمر: {}".format(_calculate_age(patient.get("date_of_birth"))))
    lines.append("فصيلة الدم: {}".format(patient.get("blood_type") or "-"))
    lines.append("عدد الحملات: {} | الولادات: {}".format(
        patient.get("gravida", 0), patient.get("para", 0)))

    # Gestational age
    weeks = patient.get("gestational_weeks", 0)
    lines.append("عمر الحمل الحالي: {} أسبوع".format(weeks))
    lines.append("EDD: {}".format(patient.get("edd") or "-"))
    lines.append("LMP: {}".format(patient.get("lmp") or "-"))

    if patient.get("notes"):
        lines.append("ملاحظات: {}".format(patient["notes"]))

    lines.append("")
    lines.append("=== الزيارات ({} زيارة) ===".format(len(visits)))

    if not visits:
        lines.append("لا توجد زيارات مسجلة")
    else:
        for i, v in enumerate(visits[:10], 1):
            lines.append("زيارة {}:".format(i))
            lines.append("  التاريخ: {}".format((v.get("visit_date") or "-")[:10]))
            if v.get("weight_kg"):
                lines.append("  الوزن: {} كغ".format(v["weight_kg"]))
            if v.get("bp_systolic") and v.get("bp_diastolic"):
                lines.append("  الضغط: {}/{}".format(
                    v["bp_systolic"], v["bp_diastolic"]))
            if v.get("fetal_heart_rate"):
                lines.append("  نبض الجنين: {} bpm".format(v["fetal_heart_rate"]))
            if v.get("fundal_height_cm"):
                lines.append("  ارتفاع الرحم: {} سم".format(v["fundal_height_cm"]))
            if v.get("notes"):
                lines.append("  ملاحظات: {}".format(v["notes"]))

    # Weight trend
    weights = [v["weight_kg"] for v in visits if v.get("weight_kg")]
    if len(weights) >= 2:
        lines.append("")
        lines.append("=== اتجاه الوزن ===")
        lines.append("الوزن الأول: {} كغ".format(weights[-1]))
        lines.append("الوزن الأخير: {} كغ".format(weights[0]))
        lines.append("الفرق: {:.1f} كغ".format(weights[0] - weights[-1]))

    # BP trend
    bps = [(v["bp_systolic"], v["bp_diastolic"]) for v in visits
           if v.get("bp_systolic") and v.get("bp_diastolic")]
    if bps:
        lines.append("")
        lines.append("=== اتجاه الضغط ===")
        lines.append("أول قياس: {}/{}".format(bps[-1][0], bps[-1][1]))
        lines.append("آخر قياس: {}/{}".format(bps[0][0], bps[0][1]))

    return "\n".join(lines)


def _calculate_age(dob_str):
    if not dob_str:
        return "-"
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d")
        age = (datetime.now() - dob).days // 365
        return "{} سنة".format(age)
    except Exception:
        return "-"


# ============================================
# Main analysis function
# ============================================
def _normalize_concerns(concerns):
    """Convert various AI output formats to consistent dicts"""
    if not isinstance(concerns, list):
        return []
    normalized = []
    for c in concerns:
        if isinstance(c, dict):
            normalized.append({
                "issue": c.get("issue", c.get("problem", c.get("title", str(c)))),
                "severity": c.get("severity", c.get("level", "medium")),
                "action": c.get("action", c.get("recommendation", c.get("advice", "-")))
            })
        elif isinstance(c, str):
            normalized.append({"issue": c, "severity": "medium", "action": "-"})
        else:
            normalized.append({"issue": str(c), "severity": "medium", "action": "-"})
    return normalized


def _normalize_recommendations(recs):
    """Ensure recommendations are list of strings"""
    if not isinstance(recs, list):
        return []
    out = []
    for r in recs:
        if isinstance(r, str):
            out.append(r)
        elif isinstance(r, dict):
            out.append(r.get("text", r.get("recommendation", str(r))))
        else:
            out.append(str(r))
    return out


def _normalize_positives(pos):
    """Ensure positives are list of strings"""
    if not isinstance(pos, list):
        return []
    out = []
    for p in pos:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            out.append(p.get("text", p.get("positive", str(p))))
        else:
            out.append(str(p))
    return out


def analyze_patient(patient: Dict, visits: List[Dict], model: str = DEFAULT_MODEL) -> Dict:
    """
    Analyze a patient's data with AI.
    Returns: dict with risk_level, summary, concerns, etc.
    Raises: AIError on failure.
    """
    if not patient:
        raise AIError("Patient data required")

    client = _get_client()
    context = build_patient_context(patient, visits)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context + "\n\nقدم تحليل JSON."}
    ]

    raw = None
    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            if raw:
                break
        except Exception as e:
            last_error = e
            err_str = str(e)
            # If JSON validation failed, retry with simpler prompt
            if "json_validate_failed" in err_str or "400" in err_str:
                messages[1]["content"] = messages[1]["content"] + chr(10) + chr(10) + "كن موجزاً جداً."
                continue
            else:
                raise AIError("AI call failed: " + err_str)
    if not raw:
        raise AIError("AI failed after 3 attempts: " + str(last_error))

    # Parse JSON
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            raise AIError("AI returned invalid JSON: " + raw[:200])

    # Validate & enrich
    result.setdefault("risk_level", "low")
    result.setdefault("summary", "")
    result.setdefault("next_visit_days", 7)
    result.setdefault("urgent", False)
    result["concerns"] = _normalize_concerns(result.get("concerns", []))
    result["positives"] = _normalize_positives(result.get("positives", []))
    result["recommendations"] = _normalize_recommendations(result.get("recommendations", []))
    result["model"] = model
    result["analyzed_at"] = datetime.utcnow().isoformat()

    return result


# ============================================
# Save analysis to DB
# ============================================
def save_analysis(clinic_id: str, patient_id: str, visit_id: Optional[str],
                  analysis: Dict) -> Dict:
    """Save analysis result to visits table (ai_risk_analysis column) or standalone"""
    # If we have a visit_id, attach there
    if visit_id:
        try:
            update("visits", {"id": visit_id, "clinic_id": clinic_id},
                   {"ai_risk_analysis": analysis})
            return analysis
        except DBError:
            pass
    # Otherwise save as standalone record (in visits table with only ai_risk_analysis)
    return analysis


def get_saved_analysis(clinic_id: str, patient_id: str) -> Optional[Dict]:
    """Fetch the most recent AI analysis for a patient"""
    try:
        rows = (
            __import__("core.db", fromlist=["db"]).db()
            .table("visits")
            .select("ai_risk_analysis, visit_date")
            .eq("clinic_id", clinic_id)
            .eq("patient_id", patient_id)
            .not_.is_("ai_risk_analysis", "null")
            .order("visit_date", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if rows and rows[0].get("ai_risk_analysis"):
            return rows[0]["ai_risk_analysis"]
    except Exception:
        pass
    return None


# ============================================
# Test
# ============================================
if __name__ == "__main__":
    from services.patients import create_patient, get_patient_summary
    from services.visits import create_visit
    from core.tenant import create_clinic
    from core.auth import create_user
    from core.db import delete as db_delete
    from datetime import date, timedelta
    import uuid

    print("=" * 50)
    print("AI Analysis Module Test")
    print("=" * 50)

    suffix = uuid.uuid4().hex[:6]
    clinic = create_clinic("AI Test " + suffix, "Dr. AI", "ai-{}@t.com".format(suffix))
    user = create_user(clinic["id"], "doc-{}@t.com".format(suffix), "secret123", "Dr. AI", "doctor")

    lmp = (date.today() - timedelta(days=200)).isoformat()
    patient = create_patient(clinic["id"], "سارة محمد", "+9647700", lmp=lmp)

    # Create 2 visits with concerning values
    create_visit(clinic["id"], patient["id"], user["id"],
                 weight_kg=72.5, bp_systolic=150, bp_diastolic=95,
                 fetal_heart_rate=105, fundal_height_cm=26,
                 notes="صداع مستمر وتورم في القدمين")
    create_visit(clinic["id"], patient["id"], user["id"],
                 weight_kg=68.0, bp_systolic=130, bp_diastolic=85,
                 fetal_heart_rate=140, fundal_height_cm=24)

    p = get_patient_summary(clinic["id"], patient["id"])
    from services.visits import list_visits
    visits = list_visits(clinic["id"], patient["id"])

    print("\nPatient: {} ({})".format(p["full_name"], p["gestational_display"]))
    print("Visits: {}".format(len(visits)))

    print("\n🤖 Running AI analysis...")
    try:
        result = analyze_patient(p, visits)
        print("\n📊 النتيجة:")
        print("Risk Level: {}".format(result["risk_level"]))
        print("Summary: {}".format(result["summary"]))
        print("\nConcerns:")
        for c in result["concerns"]:
            print("  [{}] {} → {}".format(c.get("severity"), c.get("issue"), c.get("action")))
        print("\nPositives:")
        for pos in result["positives"]:
            print("  ✓ {}".format(pos))
        print("\nRecommendations:")
        for r in result["recommendations"]:
            print("  → {}".format(r))
        print("\nNext visit in: {} days".format(result["next_visit_days"]))
        print("Urgent: {}".format(result["urgent"]))
    except AIError as e:
        print("❌ AI Error: {}".format(e))

    # Cleanup
    db_delete("clinics", id=clinic["id"])
    print("\n" + "=" * 50)
    print("Done")
    print("=" * 50)
