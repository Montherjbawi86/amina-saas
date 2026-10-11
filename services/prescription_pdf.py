# -*- coding: utf-8 -*-
"""Prescription PDF with QR code"""
from datetime import datetime, date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import qrcode


def _register_font():
    """Register Arabic font — local assets first, then system fonts"""
    import os

    # 1. Local font in project (works on Render/Linux)
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
                print("[PDF] Using font: {}".format(abs_path))
                return "Arabic"
            except Exception as e:
                print("[PDF] Failed {}: {}".format(abs_path, e))

    # 2. System fonts (macOS local)
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
                print("[PDF] Using system font: {}".format(path))
                return "Arabic"
            except Exception:
                continue

    print("[PDF] WARNING: No Arabic font found — using Helvetica")
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


def _styles():
    return {
        "clinic_name": ParagraphStyle("clinic_name", fontName=ARABIC_FONT,
            fontSize=18, leading=22, textColor=colors.HexColor("#16A34A"),
            alignment=TA_RIGHT, spaceAfter=4),
        "clinic_info": ParagraphStyle("clinic_info", fontName=ARABIC_FONT,
            fontSize=9, leading=13, textColor=colors.HexColor("#475569"),
            alignment=TA_RIGHT),
        "title": ParagraphStyle("title", fontName=ARABIC_FONT,
            fontSize=16, leading=20, textColor=colors.white, alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName=ARABIC_FONT,
            fontSize=11, leading=15, textColor=colors.HexColor("#15803D"),
            alignment=TA_RIGHT, spaceAfter=4, spaceBefore=8),
        "body": ParagraphStyle("body", fontName=ARABIC_FONT,
            fontSize=10, leading=14, alignment=TA_RIGHT),
    }


def _build_qr_image(prescription, patient):
    try:
        meds_list = [m.get("name", "") for m in prescription.get("medications", [])[:5]]
        qr_content = "Rx: {} | {} | {} | Meds: {}".format(
            str(prescription.get("id", ""))[:8],
            patient.get("full_name", ""),
            date.today().strftime("%Y-%m-%d"),
            ", ".join(meds_list)
        )
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=8, border=2)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        rl_img = RLImage(buf, width=3*cm, height=3*cm)
        print("✅ QR generated")
        return rl_img
    except Exception as e:
        print("QR failed: {}".format(e))
        return None


def _build_header(clinic, doctor_name):
    styles = _styles()
    left = Table([[Paragraph("👩‍⚕️", ParagraphStyle("logo", fontName=ARABIC_FONT,
        fontSize=28, alignment=TA_CENTER))]], colWidths=[2.5*cm])
    left.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1.5, colors.HexColor("#16A34A")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    right_data = [
        [Paragraph(_ar(clinic.get("name", "العيادة")), styles["clinic_name"])],
        [Paragraph(_ar("د. " + doctor_name) if doctor_name else "", styles["clinic_info"])],
        [Paragraph(_ar("📞 " + (clinic.get("phone") or "—")), styles["clinic_info"])],
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
    data = [[Paragraph(_ar("وصفة طبية — Prescription"), _styles()["title"])]]
    t = Table(data, colWidths=[13*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#16A34A")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    return t


def _calc_age(dob_str):
    if not dob_str:
        return "—"
    try:
        dob = datetime.strptime(str(dob_str)[:10], "%Y-%m-%d")
        return "{} سنة".format((date.today() - dob.date()).days // 365)
    except Exception:
        return "—"


def _build_patient_info(patient, prescription):
    styles = _styles()
    data = [
        [Paragraph(_ar("اسم المريضة:"), styles["body"]),
         Paragraph(_ar(patient.get("full_name", "—")), styles["body"]),
         Paragraph(_ar("التاريخ:"), styles["body"]),
         Paragraph(_ar(date.today().strftime("%Y-%m-%d")), styles["body"])],
        [Paragraph(_ar("الهاتف:"), styles["body"]),
         Paragraph(_ar(patient.get("phone", "—")), styles["body"]),
         Paragraph(_ar("العمر:"), styles["body"]),
         Paragraph(_ar(_calc_age(patient.get("date_of_birth"))), styles["body"])],
        [Paragraph(_ar("رقم الوصفة:"), styles["body"]),
         Paragraph(_ar(str(prescription["id"])[:8].upper()), styles["body"]),
         Paragraph(_ar("فصيلة الدم:"), styles["body"]),
         Paragraph(_ar(patient.get("blood_type") or "—"), styles["body"])],
    ]
    t = Table(data, colWidths=[2.5*cm, 4*cm, 2.5*cm, 4*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F0FDF4")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F0FDF4")),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return t


def _build_diagnosis(diagnosis):
    if not diagnosis:
        return None
    styles = _styles()
    data = [
        [Paragraph(_ar("📋 التشخيص:"), ParagraphStyle("dl", fontName=ARABIC_FONT,
            fontSize=11, leading=15, textColor=colors.HexColor("#15803D"),
            alignment=TA_RIGHT))],
        [Paragraph(_ar(diagnosis), styles["body"])],
    ]
    t = Table(data, colWidths=[13*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#86EFAC")),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    return t


def _build_medications(medications):
    styles = _styles()
    header = [
        Paragraph(_ar("#"), ParagraphStyle("h", fontName=ARABIC_FONT, fontSize=10,
            textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(_ar("الدواء"), ParagraphStyle("h2", fontName=ARABIC_FONT, fontSize=10,
            textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph(_ar("الجرعة"), ParagraphStyle("h3", fontName=ARABIC_FONT, fontSize=10,
            textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(_ar("التكرار"), ParagraphStyle("h4", fontName=ARABIC_FONT, fontSize=10,
            textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(_ar("المدة"), ParagraphStyle("h5", fontName=ARABIC_FONT, fontSize=10,
            textColor=colors.white, alignment=TA_CENTER)),
    ]
    data = [header]
    for i, med in enumerate(medications, 1):
        data.append([
            Paragraph(str(i), styles["body"]),
            Paragraph(_ar(med.get("name", "—")), styles["body"]),
            Paragraph(_ar(med.get("dose") or "—"), styles["body"]),
            Paragraph(_ar(med.get("frequency") or "—"), styles["body"]),
            Paragraph(_ar(med.get("duration") or "—"), styles["body"]),
        ])
    t = Table(data, colWidths=[0.8*cm, 5.2*cm, 2.2*cm, 2.4*cm, 2.4*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#16A34A")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def _build_instructions(instructions, notes):
    story = []
    styles = _styles()
    if instructions:
        story.append(Paragraph(_ar("📝 تعليمات:"), styles["section"]))
        data = [[Paragraph(_ar(instructions), styles["body"])]]
        t = Table(data, colWidths=[13*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#BBF7D0")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))
    if notes:
        story.append(Paragraph(_ar("💬 ملاحظات:"), styles["section"]))
        data = [[Paragraph(_ar(notes), styles["body"])]]
        t = Table(data, colWidths=[13*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFFBEB")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#FDE68A")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))
    return story


def _build_signature(doctor_name):
    styles = _styles()
    story = [Spacer(1, 20)]
    sig = [
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
         Paragraph(_ar("د. " + doctor_name), ParagraphStyle("dn",
            fontName=ARABIC_FONT, fontSize=10, leading=13,
            textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER))],
    ]
    t = Table(sig, colWidths=[6.5*cm, 6.5*cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(t)
    return story


def _build_qr_section(prescription, patient):
    qr_img = _build_qr_image(prescription, patient)
    if not qr_img:
        return []
    story = [Spacer(1, 15)]
    qr_data = [[
        qr_img,
        Paragraph(
            _ar("<b>للتحقق من الوصفة</b><br/>امسحي الرمز بكاميرا الجوال"),
            ParagraphStyle("qr_label", fontName=ARABIC_FONT, fontSize=9,
                leading=13, textColor=colors.HexColor("#15803D"),
                alignment=TA_RIGHT))
    ]]
    t = Table(qr_data, colWidths=[3.5*cm, 9.5*cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#16A34A")),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(t)
    return story


def _page_footer(canvas, doc, clinic):
    canvas.saveState()
    canvas.setFont(ARABIC_FONT, 8)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    text = _ar("{} — {}".format(clinic.get("name", ""), date.today().strftime("%Y-%m-%d")))
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, text)
    canvas.drawString(2*cm, 1*cm, "Page {}".format(doc.page))
    canvas.restoreState()


def generate_prescription_pdf(prescription, patient, clinic, doctor_name=""):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
        title="Prescription {}".format(str(prescription.get("id", ""))[:8]))

    story = []
    story.append(_build_header(clinic, doctor_name))
    story.append(Spacer(1, 12))
    story.append(_build_title_bar())
    story.append(Spacer(1, 12))
    story.append(_build_patient_info(patient, prescription))
    story.append(Spacer(1, 12))

    diag = _build_diagnosis(prescription.get("diagnosis"))
    if diag:
        story.append(diag)
        story.append(Spacer(1, 12))

    story.append(Paragraph(_ar("💊 الأدوية الموصوفة:"), _styles()["section"]))
    story.append(_build_medications(prescription.get("medications", [])))
    story.append(Spacer(1, 10))

    story += _build_instructions(prescription.get("instructions"), prescription.get("notes"))
    story += _build_signature(doctor_name)
    story += _build_qr_section(prescription, patient)

    doc.build(story,
        onFirstPage=lambda c, d: _page_footer(c, d, clinic),
        onLaterPages=lambda c, d: _page_footer(c, d, clinic))

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


if __name__ == "__main__":
    print("=" * 50)
    print("Prescription PDF + QR Test")
    print("=" * 50)

    prescription = {
        "id": "abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "diagnosis": "فقر دم خفيف مع حمل",
        "medications": [
            {"name": "حمض الفوليك 5mg", "dose": "1 قرص", "frequency": "يومياً", "duration": "3 أشهر"},
            {"name": "حديد 65mg", "dose": "1 قرص", "frequency": "مرتين يومياً", "duration": "شهرين"},
        ],
        "instructions": "يُؤخذ مع الطعام",
        "notes": "الإكثار من الخضروات",
    }

    patient = {
        "full_name": "فاطمة أحمد محمد",
        "phone": "+9647701234567",
        "date_of_birth": "1995-03-15",
        "blood_type": "O+",
    }

    clinic = {
        "name": "عيادة النور للنساء والولادة",
        "phone": "+964 770 000 0000",
    }

    pdf_bytes = generate_prescription_pdf(prescription, patient, clinic, "أمينة محمد")
    with open("test_prescription.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("✅ PDF: test_prescription.pdf ({:,} bytes)".format(len(pdf_bytes)))
