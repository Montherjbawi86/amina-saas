# -*- coding: utf-8 -*-
"""PDF report generation for Amina SaaS"""
from datetime import datetime, date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle

# Arabic support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

# ============================================
# ARABIC FONT
# ============================================
def _register_arabic_font():
    """Try to register an Arabic-capable font"""
    import os
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", path))
                return "Arabic"
            except Exception:
                continue
    return "Helvetica"


ARABIC_FONT = _register_arabic_font()


def _ar(text):
    """Prepare Arabic text for reportlab: reshape + bidi"""
    if text is None:
        return ""
    text = str(text)
    if not HAS_ARABIC:
        return text
    try:
        # Reshape Arabic letters (connect them)
        reshaped = arabic_reshaper.reshape(text)
        # Apply bidi for correct RTL order
        return get_display(reshaped)
    except Exception:
        return text


# ============================================
# STYLES
# ============================================
def _styles():
    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=ss["Title"],
            fontName=ARABIC_FONT, fontSize=22, leading=28,
            textColor=colors.HexColor("#7B2D8E"), alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1", parent=ss["Heading1"],
            fontName=ARABIC_FONT, fontSize=16, leading=22,
            textColor=colors.HexColor("#7B2D8E"), alignment=TA_RIGHT,
        ),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"],
            fontName=ARABIC_FONT, fontSize=13, leading=18,
            textColor=colors.HexColor("#5A1F6B"), alignment=TA_RIGHT,
        ),
        "normal": ParagraphStyle(
            "normal", parent=ss["BodyText"],
            fontName=ARABIC_FONT, fontSize=10, leading=14,
            alignment=TA_RIGHT,
        ),
        "small": ParagraphStyle(
            "small", parent=ss["BodyText"],
            fontName=ARABIC_FONT, fontSize=8, leading=12,
            alignment=TA_RIGHT, textColor=colors.HexColor("#6B7280"),
        ),
        "center": ParagraphStyle(
            "center", parent=ss["BodyText"],
            fontName=ARABIC_FONT, fontSize=10, leading=14,
            alignment=TA_CENTER,
        ),
    }
    return styles


# ============================================
# PDF BUILDER
# ============================================
class PatientReportBuilder:
    def __init__(self, patient, visits, alerts=None, ai_result=None, clinic=None):
        self.patient = patient or {}
        self.visits = visits or []
        self.alerts = alerts or []
        self.ai_result = ai_result
        self.clinic = clinic or {}
        self.styles = _styles()
        self.buffer = BytesIO()

    # ---------- components ----------
    def _header(self):
        """Report header with brand + patient name"""
        story = []
        # Brand bar
        brand = Table([[
            Paragraph("<b>أمينة SaaS</b>", ParagraphStyle(
                "brand", fontName=ARABIC_FONT, fontSize=14, leading=18,
                textColor=colors.white, alignment=TA_LEFT)),
            Paragraph("{}".format(self.clinic.get("name", "")), ParagraphStyle(
                "clinic", fontName=ARABIC_FONT, fontSize=10, leading=14,
                textColor=colors.white, alignment=TA_RIGHT)),
        ]], colWidths=[8*cm, 8*cm])
        brand.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#7B2D8E")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))
        story.append(brand)
        story.append(Spacer(1, 10))

        # Title
        story.append(Paragraph(_ar("تقرير الحامل"), self.styles["title"]))
        story.append(Paragraph(
            _ar("تاريخ التقرير: {}".format(date.today().strftime("%Y-%m-%d"))),
            self.styles["center"]
        ))
        story.append(Spacer(1, 12))

        return story

    def _patient_card(self):
        """Patient basic info table"""
        p = self.patient
        story = []
        story.append(Paragraph(_ar("معلومات الحامل"), self.styles["h1"]))
        story.append(Spacer(1, 6))

        data = [
            [_ar("الاسم"), _ar(p.get("full_name", "—")), _ar("الهاتف"), _ar(p.get("phone", "—"))],
            [_ar("العمر"), _ar(self._age(p.get("date_of_birth"))), _ar("فصيلة الدم"), _ar(p.get("blood_type") or "—")],
            [_ar("G / P"), _ar("{} / {}".format(p.get("gravida", 0), p.get("para", 0))),
             _ar("عمر الحمل"), _ar(p.get("gestational_display", "—"))],
            [_ar("LMP"), _ar(p.get("lmp") or "—"), _ar("EDD"), _ar(p.get("edd") or "—")],
            [_ar("المخاطر"), _ar(self._risk_label(p.get("risk_level", "low"))), _ar("عدد الزيارات"), _ar(str(len(self.visits)))],
        ]

        t = Table(data, colWidths=[3*cm, 4.5*cm, 3*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F5F0F7")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F5F0F7")),
            ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#5A1F6B")),
            ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#5A1F6B")),
            ("ALIGN", (0,0), (-1,-1), "RIGHT"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
        return story

    def _alerts_section(self):
        """Alerts table"""
        if not self.alerts:
            return []
        story = []
        story.append(Paragraph(_ar("🔔 التنبيهات الطبية ({})".format(len(self.alerts))), self.styles["h1"]))
        story.append(Spacer(1, 6))

        colors_map = {
            "critical": "#DC2626",
            "high": "#EF4444",
            "medium": "#F59E0B",
            "low": "#10B981",
        }

        for a in self.alerts:
            hexc = colors_map.get(a.get("level", "low"), "#6B7280")
            icon = a.get("icon", "•")
            data = [[
                Paragraph(_ar("<b>{}</b>".format(a.get("title", ""))), ParagraphStyle(
                    "alert_title", fontName=ARABIC_FONT, fontSize=10, leading=14,
                    textColor=colors.white, alignment=TA_RIGHT)),
                Paragraph("{}".format(icon), ParagraphStyle(
                    "alert_icon", fontName=ARABIC_FONT, fontSize=14, leading=18,
                    textColor=colors.white, alignment=TA_CENTER)),
            ], [
                Paragraph(_ar("{}".format(a.get("message", ""))), ParagraphStyle(
                    "alert_msg", fontName=ARABIC_FONT, fontSize=9, leading=13,
                    alignment=TA_RIGHT)),
                "",
            ], [
                Paragraph(_ar("الإجراء: {}".format(a.get("action", "—"))), ParagraphStyle(
                    "alert_action", fontName=ARABIC_FONT, fontSize=9, leading=13,
                    textColor=colors.HexColor("#4B5563"), alignment=TA_RIGHT)),
                "",
            ]]
            t = Table(data, colWidths=[13*cm, 2*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (1,0), colors.HexColor(hexc)),
                ("SPAN", (0,1), (1,1)),
                ("SPAN", (0,2), (1,2)),
                ("ALIGN", (0,0), (-1,-1), "RIGHT"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("RIGHTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#E5E7EB")),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 6))
        return story

    def _visits_section(self):
        """Visits history table"""
        if not self.visits:
            return []
        story = []
        story.append(Paragraph(_ar("📋 تاريخ الزيارات ({})".format(len(self.visits))), self.styles["h1"]))
        story.append(Spacer(1, 6))

        header = [_ar("التاريخ"), _ar("الوزن"), _ar("الضغط"), _ar("النبض"), _ar("الارتفاع"), _ar("ملاحظات")]
        rows = [header]
        for v in self.visits[:30]:
            rows.append([
                _ar((v.get("visit_date") or "—")[:10]),
                _ar(str(v.get("weight_kg") or "—")),
                _ar("{}/{}".format(v.get("bp_systolic") or "-", v.get("bp_diastolic") or "-")),
                _ar(str(v.get("fetal_heart_rate") or "—")),
                _ar(str(v.get("fundal_height_cm") or "—")),
                _ar((v.get("notes") or "—")[:40]),
            ])

        t = Table(rows, colWidths=[2.5*cm, 2*cm, 2.5*cm, 2*cm, 2*cm, 4*cm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#7B2D8E")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
        return story

    def _ai_section(self):
        """AI analysis"""
        if not self.ai_result:
            return []
        r = self.ai_result
        story = []
        story.append(Paragraph(_ar("🤖 تحليل AI"), self.styles["h1"]))
        story.append(Spacer(1, 6))

        risk = r.get("risk_level", "low")
        colors_map = {"high": "#EF4444", "medium": "#F59E0B", "low": "#10B981"}
        hexc = colors_map.get(risk, "#6B7280")

        summary = r.get("summary", "")
        data = [[
            Paragraph(_ar("مستوى الخطر: {}".format(risk.upper())), ParagraphStyle(
                "ai_risk", fontName=ARABIC_FONT, fontSize=12, leading=16,
                textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph("🤖", ParagraphStyle(
                "ai_icon", fontName=ARABIC_FONT, fontSize=14,
                textColor=colors.white, alignment=TA_CENTER)),
        ], [
            Paragraph(_ar(summary), self.styles["normal"]),
            "",
        ]]
        t = Table(data, colWidths=[13*cm, 2*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (1,0), colors.HexColor(hexc)),
            ("SPAN", (0,1), (1,1)),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

        concerns = r.get("concerns", [])
        if concerns:
            story.append(Paragraph(_ar("المخاوف:"), self.styles["h2"]))
            for c in concerns:
                story.append(Paragraph(
                    _ar("• [{}] {}".format(c.get("severity", ""), c.get("issue", ""))),
                    self.styles["normal"]))
                story.append(Paragraph(
                    _ar("  الإجراء: {}".format(c.get("action", "—"))),
                    self.styles["small"]))
            story.append(Spacer(1, 6))

        recs = r.get("recommendations", [])
        if recs:
            story.append(Paragraph(_ar("التوصيات:"), self.styles["h2"]))
            for rec in recs:
                story.append(Paragraph(_ar("• {}".format(rec)), self.styles["normal"]))

        story.append(Spacer(1, 12))
        return story

    def _footer(self, canvas, doc):
        """Page footer"""
        canvas.saveState()
        canvas.setFont(ARABIC_FONT, 8)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        canvas.drawString(2*cm, 1*cm, "أمينة SaaS — {} — {}".format(
            self.clinic.get("name", ""), date.today().strftime("%Y-%m-%d")))
        canvas.drawRightString(A4[0] - 2*cm, 1*cm, "Page {}".format(doc.page))
        canvas.restoreState()

    # ---------- helpers ----------
    def _age(self, dob_str):
        if not dob_str:
            return "—"
        try:
            dob = datetime.strptime(str(dob_str)[:10], "%Y-%m-%d")
            return "{} سنة".format((date.today() - dob.date()).days // 365)
        except Exception:
            return "—"

    def _risk_label(self, risk):
        return {"low": "🟢 منخفض", "medium": "🟡 متوسط", "high": "🔴 عالي"}.get(risk, "—")

    # ---------- build ----------
    def build(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm,
            title="تقرير {}".format(self.patient.get("full_name", "")),
        )
        story = []
        story += self._header()
        story += self._patient_card()
        story += self._alerts_section()
        story += self._visits_section()
        story += self._ai_section()

        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf


# ============================================
# PUBLIC API
# ============================================
def generate_patient_report(patient, visits, alerts=None, ai_result=None, clinic=None):
    """
    Generate a patient report PDF.
    Returns: bytes (PDF content)
    """
    builder = PatientReportBuilder(
        patient=patient, visits=visits,
        alerts=alerts or [], ai_result=ai_result, clinic=clinic or {}
    )
    return builder.build()


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("PDF Reports Test")
    print("=" * 50)

    patient = {
        "full_name": "فاطمة أحمد محمد",
        "phone": "+9647701234567",
        "date_of_birth": "1995-03-15",
        "blood_type": "O+",
        "gravida": 2, "para": 1,
        "gestational_display": "28 أسبوع + 4 يوم",
        "lmp": "2026-03-20", "edd": "2026-12-25",
        "risk_level": "high",
    }

    visits = [
        {"visit_date": "2026-10-10T10:00:00", "weight_kg": 72.5,
         "bp_systolic": 155, "bp_diastolic": 95, "fetal_heart_rate": 105,
         "fundal_height_cm": 32, "notes": "صداع وتورم"},
        {"visit_date": "2026-10-03T10:00:00", "weight_kg": 70.0,
         "bp_systolic": 130, "bp_diastolic": 85, "fetal_heart_rate": 145,
         "fundal_height_cm": 27, "notes": "زيارة روتينية"},
        {"visit_date": "2026-09-20T10:00:00", "weight_kg": 68.0,
         "bp_systolic": 120, "bp_diastolic": 80, "fetal_heart_rate": 140,
         "fundal_height_cm": 24, "notes": ""},
    ]

    alerts = [
        {"level": "high", "icon": "🔴", "title": "ضغط دم مرتفع",
         "message": "ضغط 155/95", "action": "قياس كل 4 ساعات"},
        {"level": "medium", "icon": "🟡", "title": "تباطؤ نبض الجنين",
         "message": "نبض 105 bpm", "action": "فحص CTG"},
    ]

    ai = {
        "risk_level": "high",
        "summary": "ارتفاع ضغط مع تباطؤ نبض الجنين يحتاج تقييم فوري.",
        "concerns": [
            {"issue": "ارتفاع ضغط الدم", "severity": "high", "action": "مراجعة فورية"},
        ],
        "positives": ["الالتزام بالمتابعة"],
        "recommendations": ["مراجعة عاجلة", "فحص بروتين البول"],
    }

    clinic = {"name": "عيادة النور للنساء والولادة"}

    try:
        pdf_bytes = generate_patient_report(patient, visits, alerts, ai, clinic)
        out = "test_report.pdf"
        with open(out, "wb") as f:
            f.write(pdf_bytes)
        print("✅ PDF generated: {}".format(out))
        print("   Size: {:,} bytes".format(len(pdf_bytes)))
        print("\n👉 افتحه: open {}".format(out))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ Failed: {}".format(e))
