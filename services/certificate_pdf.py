# -*- coding: utf-8 -*-
"""
Pregnancy Certificate PDF
شهادة حمل رسمية مع QR code
"""
from datetime import datetime, date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import qrcode


# ============================================
# FONT REGISTRATION
# ============================================

def _register_font():
    """Register Arabic font — assets first, then system fonts"""
    import os
    project_fonts = [
        "assets/fonts/Amiri-Regular.ttf",
        "assets/fonts/NotoNaskhArabic-Regular.ttf",
    ]
    for rel_path in project_fonts:
        abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", rel_path)
        abs_path = os.path.normpath(abs_path)
        if os.path.exists(abs_path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", abs_path))
                print("[CertPDF] Font: {}".format(abs_path))
                return "Arabic"
            except Exception as e:
                print("[CertPDF] Failed {}: {}".format(abs_path, e))

    system_fonts = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in system_fonts:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", path))
                print("[CertPDF] System font: {}".format(path))
                return "Arabic"
            except Exception:
                continue

    print("[CertPDF] WARNING: No Arabic font — using Helvetica")
    return "Helvetica"


ARABIC_FONT = _register_font()

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False


def _ar(text):
    if text is None:
        return ""
    text = str(text)
    if not HAS_ARABIC:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


# ============================================
# STYLES
# ============================================

def _styles():
    return {
        "clinic_name": ParagraphStyle("clinic_name", fontName=ARABIC_FONT,
            fontSize=20, leading=24, textColor=colors.HexColor("#16A34A"),
            alignment=TA_RIGHT, spaceAfter=4),
        "clinic_info": ParagraphStyle("clinic_info", fontName=ARABIC_FONT,
            fontSize=10, leading=14, textColor=colors.HexColor("#475569"),
            alignment=TA_RIGHT),
        "title": ParagraphStyle("title", fontName=ARABIC_FONT,
            fontSize=18, leading=24, textColor=colors.white,
            alignment=TA_CENTER, spaceBefore=6, spaceAfter=6),
        "subtitle": ParagraphStyle("subtitle", fontName=ARABIC_FONT,
            fontSize=11, leading=15, textColor=colors.HexColor("#15803D"),
            alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName=ARABIC_FONT,
            fontSize=12, leading=16, textColor=colors.HexColor("#15803D"),
            alignment=TA_RIGHT, spaceAfter=6, spaceBefore=10),
        "label": ParagraphStyle("label", fontName=ARABIC_FONT,
            fontSize=10, leading=14, textColor=colors.HexColor("#64748B"),
            alignment=TA_RIGHT),
        "value": ParagraphStyle("value", fontName=ARABIC_FONT,
            fontSize=11, leading=15, textColor=colors.HexColor("#0F172A"),
            alignment=TA_RIGHT),
        "body": ParagraphStyle("body", fontName=ARABIC_FONT,
            fontSize=10, leading=15, alignment=TA_RIGHT),
        "footer": ParagraphStyle("footer", fontName=ARABIC_FONT,
            fontSize=8, leading=12, textColor=colors.HexColor("#94A3B8"),
            alignment=TA_CENTER),
    }


# ============================================
# HELPERS
# ============================================

def _calc_age(dob_str):
    if not dob_str:
        return "—"
    try:
        dob = datetime.strptime(str(dob_str)[:10], "%Y-%m-%d")
        return "{} سنة".format((date.today() - dob.date()).days // 365)
    except Exception:
        return "—"


def _calc_gestational_weeks(lmp, ref_date=None):
    """Returns (weeks, days) from LMP"""
    if not lmp:
        return None, None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        elif isinstance(lmp, date):
            lmp_d = lmp
        else:
            return None, None

        if ref_date:
            if isinstance(ref_date, str):
                ref = datetime.strptime(ref_date[:10], "%Y-%m-%d").date()
            elif isinstance(ref_date, date):
                ref = ref_date
            else:
                ref = date.today()
        else:
            ref = date.today()

        days = (ref - lmp_d).days
        if days < 0:
            return None, None
        return days // 7, days % 7
    except Exception:
        return None, None


def _format_gestational(lmp, ref_date=None):
    weeks, days = _calc_gestational_weeks(lmp, ref_date)
    if weeks is None:
        return "—"
    return "{} أسبوع + {} يوم".format(weeks, days)


def _format_date(v):
    if not v:
        return "—"
    try:
        if isinstance(v, str):
            return v[:10]
        return v.strftime("%Y-%m-%d")
    except Exception:
        return str(v)


# ============================================
# COMPONENTS
# ============================================

def _build_header(clinic, doctor_name):
    styles = _styles()
    left = Table([[Paragraph("👶", ParagraphStyle("logo", fontName=ARABIC_FONT,
        fontSize=32, alignment=TA_CENTER))]], colWidths=[2.5*cm])
    left.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1.5, colors.HexColor("#16A34A")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))

    right_data = [
        [Paragraph(_ar(clinic.get("name", "العيادة")), styles["clinic_name"])],
        [Paragraph(_ar("د. " + doctor_name) if doctor_name else "", styles["clinic_info"])],
        [Paragraph(_ar("📞 " + (clinic.get("phone") or "—")), styles["clinic_info"])],
        [Paragraph(_ar("📍 " + (clinic.get("address") or "—")) if clinic.get("address") else "", styles["clinic_info"])],
    ]
    right = Table(right_data, colWidths=[10.5*cm])
    right.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))

    header = Table([[left, right]], colWidths=[2.5*cm, 10.5*cm])
    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    return header


def _build_title_bar():
    styles = _styles()
    data = [[Paragraph(_ar("شهادة حمل رسمية"), styles["title"])]]
    t = Table(data, colWidths=[13*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#16A34A")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    return t


def _build_patient_section(patient):
    styles = _styles()
    data = [
        [Paragraph(_ar("اسم الحامل:"), styles["label"]),
         Paragraph(_ar(patient.get("full_name", "—")), styles["value"]),
         Paragraph(_ar("العمر:"), styles["label"]),
         Paragraph(_ar(_calc_age(patient.get("date_of_birth"))), styles["value"])],

        [Paragraph(_ar("الرقم الوطني:"), styles["label"]),
         Paragraph(_ar(patient.get("national_id") or "—"), styles["value"]),
         Paragraph(_ar("فصيلة الدم:"), styles["label"]),
         Paragraph(_ar(patient.get("blood_type") or "—"), styles["value"])],

        [Paragraph(_ar("رقم الهاتف:"), styles["label"]),
         Paragraph(_ar(patient.get("phone") or "—"), styles["value"]),
         Paragraph(_ar("مستوى الخطر:"), styles["label"]),
         Paragraph(_ar(_risk_label(patient.get("risk_level"))), styles["value"])],
    ]
    t = Table(data, colWidths=[2.8*cm, 3.7*cm, 2.8*cm, 3.7*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F0FDF4")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F0FDF4")),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def _build_pregnancy_section(patient):
    styles = _styles()
    lmp = patient.get("lmp")
    edd = patient.get("edd")
    gest = _format_gestational(lmp)

    data = [
        [Paragraph(_ar("تاريخ آخر دورة (LMP):"), styles["label"]),
         Paragraph(_ar(_format_date(lmp)), styles["value"]),
         Paragraph(_ar("تاريخ الولادة المتوقع (EDD):"), styles["label"]),
         Paragraph(_ar(_format_date(edd)), styles["value"])],

        [Paragraph(_ar("عمر الحمل الحالي:"), styles["label"]),
         Paragraph(_ar(gest), styles["value"]),
         Paragraph(_ar("عدد مرات الحمل (G/P):"), styles["label"]),
         Paragraph(_ar("{}/{}".format(patient.get("gravida") or 0, patient.get("para") or 0)), styles["value"])],
    ]
    t = Table(data, colWidths=[3.3*cm, 3.2*cm, 3.3*cm, 3.2*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F0FDF4")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F0FDF4")),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def _build_visits_summary(visits):
    styles = _styles()
    if not visits:
        data = [[Paragraph(_ar("لا توجد زيارات مسجلة"), styles["body"])]]
        t = Table(data, colWidths=[13*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        return t

    last_visit = visits[0] if visits else {}
    first_visit = visits[-1] if visits else {}

    data = [
        [Paragraph(_ar("عدد الزيارات:"), styles["label"]),
         Paragraph(_ar(str(len(visits))), styles["value"]),
         Paragraph(_ar("آخر زيارة:"), styles["label"]),
         Paragraph(_ar(_format_date(last_visit.get("visit_date"))), styles["value"])],
        [Paragraph(_ar("أول زيارة:"), styles["label"]),
         Paragraph(_ar(_format_date(first_visit.get("visit_date"))), styles["value"]),
         Paragraph(_ar("الطبيبة المشرفة:"), styles["label"]),
         Paragraph(_ar(visits[0].get("_doctor_name") or "—"), styles["value"])],
    ]
    t = Table(data, colWidths=[3.3*cm, 3.2*cm, 3.3*cm, 3.2*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F0FDF4")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F0FDF4")),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def _build_recommendations_section(notes):
    styles = _styles()
    if not notes:
        notes = "المتابعة الدورية مع الطبيبة المختصة، الراحة الكافية، التغذية السليمة."
    data = [
        [Paragraph(_ar("📋 توصيات الطبيبة:"), ParagraphStyle("rec_head",
            fontName=ARABIC_FONT, fontSize=11, leading=15,
            textColor=colors.HexColor("#15803D"), alignment=TA_RIGHT))],
        [Paragraph(_ar(notes), styles["body"])],
    ]
    t = Table(data, colWidths=[13*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#86EFAC")),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    return t


def _build_qr_image(certificate_id, patient):
    try:
        qr_content = "CERT:{}|{}|{}".format(
            str(certificate_id)[:8],
            patient.get("full_name", ""),
            date.today().strftime("%Y-%m-%d")
        )
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=8, border=2)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=3*cm, height=3*cm)
    except Exception as e:
        print("[CertPDF] QR failed: {}".format(e))
        return None


def _build_signature_section(certificate_id, patient, doctor_name):
    styles = _styles()
    qr_img = _build_qr_image(certificate_id, patient)

    sig_data = [
        [Paragraph(_ar("ختم العيادة"), ParagraphStyle("cs", fontName=ARABIC_FONT,
            fontSize=9, leading=12, textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER)),
         Paragraph(_ar("توقيع الطبيبة"), ParagraphStyle("ds", fontName=ARABIC_FONT,
            fontSize=9, leading=12, textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER))],
        [Paragraph("", styles["body"]), Paragraph("", styles["body"])],
        [Paragraph("____________________", ParagraphStyle("l1",
            fontName="Helvetica", fontSize=10, alignment=TA_CENTER)),
         Paragraph("____________________", ParagraphStyle("l2",
            fontName="Helvetica", fontSize=10, alignment=TA_CENTER))],
        [Paragraph("", styles["body"]),
         Paragraph(_ar("د. " + doctor_name) if doctor_name else "", ParagraphStyle("dn",
            fontName=ARABIC_FONT, fontSize=10, leading=13,
            textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER))],
    ]
    sig = Table(sig_data, colWidths=[5*cm, 5*cm])
    sig.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    if qr_img:
        qr_data = [[
            qr_img,
            Paragraph(_ar("<b>للتحقق من الشهادة</b><br/>امسحي الرمز بكاميرا الجوال"),
                ParagraphStyle("qr_label", fontName=ARABIC_FONT, fontSize=9,
                    leading=13, textColor=colors.HexColor("#15803D"),
                    alignment=TA_RIGHT))
        ]]
        qr_t = Table(qr_data, colWidths=[3.5*cm, 6.5*cm])
        qr_t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
            ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#16A34A")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))
        combined = Table([[sig, qr_t]], colWidths=[6*cm, 7*cm])
        combined.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ]))
        return combined

    return sig


def _page_footer(canvas, doc, clinic):
    canvas.saveState()
    canvas.setFont(ARABIC_FONT, 8)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    text = _ar("{} — شهادة حمل — {}".format(
        clinic.get("name", ""), date.today().strftime("%Y-%m-%d")))
    canvas.drawCentredString(A4[0] / 2, 1*cm, text)
    canvas.restoreState()


def _risk_label(risk):
    return {
        "low": "🟢 منخفض",
        "medium": "🟡 متوسط",
        "high": "🔴 عالي",
    }.get(risk, "—")


# ============================================
# PUBLIC API
# ============================================

def generate_certificate_pdf(patient, visits=None, clinic=None,
                              doctor_name="", certificate_id=None):
    """
    Generate pregnancy certificate PDF.

    Args:
        patient: dict (full row from patients table)
        visits: list of visit dicts (optional, for summary)
        clinic: dict (clinic row)
        doctor_name: str
        certificate_id: uuid string (for QR)

    Returns:
        bytes (PDF)
    """
    import uuid

    patient = patient or {}
    visits = visits or []
    clinic = clinic or {}
    cert_id = certificate_id or str(uuid.uuid4())

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
        title="Pregnancy Certificate - {}".format(patient.get("full_name", ""))
    )

    styles = _styles()
    story = []

    # Header
    story.append(_build_header(clinic, doctor_name))
    story.append(Spacer(1, 14))

    # Title bar
    story.append(_build_title_bar())
    story.append(Spacer(1, 8))

    # Date line
    story.append(Paragraph(
        _ar("تاريخ الإصدار: {}".format(date.today().strftime("%Y-%m-%d"))),
        styles["subtitle"]
    ))
    story.append(Spacer(1, 14))

    # Patient info
    story.append(Paragraph(_ar("معلومات الحامل"), styles["section"]))
    story.append(_build_patient_section(patient))
    story.append(Spacer(1, 12))

    # Pregnancy info
    story.append(Paragraph(_ar("تفاصيل الحمل"), styles["section"]))
    story.append(_build_pregnancy_section(patient))
    story.append(Spacer(1, 12))

    # Visits summary
    story.append(Paragraph(_ar("ملخص المتابعة"), styles["section"]))
    story.append(_build_visits_summary(visits))
    story.append(Spacer(1, 12))

    # Recommendations
    story.append(_build_recommendations_section(patient.get("notes")))
    story.append(Spacer(1, 20))

    # Signature + QR
    story.append(_build_signature_section(cert_id, patient, doctor_name))

    # Build
    doc.build(story,
        onFirstPage=lambda c, d: _page_footer(c, d, clinic),
        onLaterPages=lambda c, d: _page_footer(c, d, clinic))

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Pregnancy Certificate Test")
    print("=" * 50)

    patient = {
        "full_name": "فاطمة أحمد محمد",
        "phone": "+9647701234567",
        "national_id": "972598723",
        "date_of_birth": "1995-03-15",
        "blood_type": "AB+",
        "gravida": 1,
        "para": 1,
        "risk_level": "low",
        "lmp": "2026-08-04",
        "edd": "2027-05-11",
        "notes": "المتابعة الدورية كل 4 أسابيع",
    }

    visits = [
        {"visit_date": "2026-10-10", "_doctor_name": "د. أمينة محمد"},
        {"visit_date": "2026-10-03", "_doctor_name": "د. أمينة محمد"},
    ]

    clinic = {
        "name": "عيادة النور للنساء والولادة",
        "phone": "+964 770 000 0000",
    }

    pdf = generate_certificate_pdf(patient, visits, clinic, "أمينة محمد")
    with open("test_certificate.pdf", "wb") as f:
        f.write(pdf)
    print("✅ PDF: test_certificate.pdf ({:,} bytes)".format(len(pdf)))
