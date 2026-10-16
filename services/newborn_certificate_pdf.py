# -*- coding: utf-8 -*-
"""
Birth Certificate PDF
شهادة ميلاد رسمية مع QR
"""
from datetime import datetime, date
from io import BytesIO
import os
import uuid

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ============================================
# FONT
# ============================================

def _register_font():
    here = os.path.dirname(os.path.abspath(__file__))
    project_fonts = [
        os.path.normpath(os.path.join(here, "..", "assets/fonts/Amiri-Regular.ttf")),
        os.path.normpath(os.path.join(here, "..", "assets/fonts/NotoNaskhArabic-Regular.ttf")),
    ]
    for path in project_fonts:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", path))
                return "Arabic"
            except Exception:
                pass

    system_fonts = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in system_fonts:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", path))
                return "Arabic"
            except Exception:
                continue
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
            fontSize=18, leading=22, textColor=colors.HexColor("#16A34A"),
            alignment=TA_RIGHT),
        "clinic_info": ParagraphStyle("clinic_info", fontName=ARABIC_FONT,
            fontSize=10, leading=14, textColor=colors.HexColor("#475569"),
            alignment=TA_RIGHT),
        "title": ParagraphStyle("title", fontName=ARABIC_FONT,
            fontSize=20, leading=26, textColor=colors.white, alignment=TA_CENTER),
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

def _fmt_date(v):
    if not v:
        return "—"
    return str(v)[:10]


def _fmt_weight(g):
    if not g:
        return "—"
    try:
        return "{:,} غرام".format(int(g))
    except Exception:
        return "—"


def _gender_label(g):
    return {"male": "ذكر 👦", "female": "أنثى 👧"}.get(g, "—")


def _delivery_label(t):
    return {
        "normal": "طبيعية",
        "c_section": "قيصرية",
        "assisted": "بمساعدة",
        "breech": "مقعدية",
    }.get(t, t or "—")


def _health_label(h):
    return {
        "healthy": "سليم ✅",
        "needs_care": "يحتاج رعاية",
        "nicu": "في الحاضنة",
        "critical": "حرج",
    }.get(h, h or "—")


# ============================================
# COMPONENTS
# ============================================

def _build_header(clinic, doctor_name):
    styles = _styles()

    left = Table([[Paragraph("👶", ParagraphStyle("logo",
        fontName=ARABIC_FONT, fontSize=32, alignment=TA_CENTER))]],
        colWidths=[2.5*cm])
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
    t = Table([[Paragraph(_ar("شهادة ميلاد رسمية"), styles["title"])]],
        colWidths=[13*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#16A34A")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    return t


def _build_newborn_section(nb):
    styles = _styles()
    data = [
        [Paragraph(_ar("اسم المولود:"), styles["label"]),
         Paragraph(_ar(nb.get("baby_name") or "—"), styles["value"]),
         Paragraph(_ar("الجنس:"), styles["label"]),
         Paragraph(_ar(_gender_label(nb.get("gender"))), styles["value"])],

        [Paragraph(_ar("تاريخ الولادة:"), styles["label"]),
         Paragraph(_ar(_fmt_date(nb.get("delivery_date"))), styles["value"]),
         Paragraph(_ar("وقت الولادة:"), styles["label"]),
         Paragraph(_ar(str(nb.get("delivery_time") or "—")[:5]), styles["value"])],

        [Paragraph(_ar("نوع الولادة:"), styles["label"]),
         Paragraph(_ar(_delivery_label(nb.get("delivery_type"))), styles["value"]),
         Paragraph(_ar("مكان الولادة:"), styles["label"]),
         Paragraph(_ar(nb.get("delivery_place") or "—"), styles["value"])],
    ]
    t = Table(data, colWidths=[3*cm, 3.5*cm, 3*cm, 3.5*cm])
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


def _build_measurements_section(nb):
    styles = _styles()
    data = [
        [Paragraph(_ar("الوزن:"), styles["label"]),
         Paragraph(_ar(_fmt_weight(nb.get("weight_grams"))), styles["value"]),
         Paragraph(_ar("الطول:"), styles["label"]),
         Paragraph(_ar("{} سم".format(nb.get("length_cm") or "—")), styles["value"])],

        [Paragraph(_ar("محيط الرأس:"), styles["label"]),
         Paragraph(_ar("{} سم".format(nb.get("head_circumference_cm") or "—")), styles["value"]),
         Paragraph(_ar("الحالة:"), styles["label"]),
         Paragraph(_ar(_health_label(nb.get("health_status"))), styles["value"])],
    ]
    t = Table(data, colWidths=[3*cm, 3.5*cm, 3*cm, 3.5*cm])
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


def _build_mother_section(mom):
    styles = _styles()
    data = [
        [Paragraph(_ar("اسم الأم:"), styles["label"]),
         Paragraph(_ar(mom.get("full_name", "—")), styles["value"]),
         Paragraph(_ar("الهاتف:"), styles["label"]),
         Paragraph(_ar(mom.get("phone") or "—"), styles["value"])],

        [Paragraph(_ar("الرقم الوطني:"), styles["label"]),
         Paragraph(_ar(mom.get("national_id") or "—"), styles["value"]),
         Paragraph(_ar("فصيلة الدم:"), styles["label"]),
         Paragraph(_ar(mom.get("blood_type") or "—"), styles["value"])],
    ]
    t = Table(data, colWidths=[3*cm, 3.5*cm, 3*cm, 3.5*cm])
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


def _build_apgar_section(nb):
    styles = _styles()
    a1 = nb.get("apgar_1min")
    a5 = nb.get("apgar_5min")
    a10 = nb.get("apgar_10min")

    if not any([a1, a5, a10]):
        return None

    data = [[
        Paragraph(_ar("APGAR Score"), ParagraphStyle("apgar_h",
            fontName=ARABIC_FONT, fontSize=11, textColor=colors.white,
            alignment=TA_CENTER)),
        "", "",
    ], [
        Paragraph(_ar("1 دقيقة"), styles["label"]),
        Paragraph(_ar("5 دقائق"), styles["label"]),
        Paragraph(_ar("10 دقائق"), styles["label"]),
    ], [
        Paragraph(_ar(str(a1) if a1 else "—"), styles["value"]),
        Paragraph(_ar(str(a5) if a5 else "—"), styles["value"]),
        Paragraph(_ar(str(a10) if a10 else "—"), styles["value"]),
    ]]
    t = Table(data, colWidths=[4.3*cm, 4.3*cm, 4.4*cm])
    t.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#16A34A")),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F0FDF4")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    return t


def _build_notes_section(notes, complications):
    styles = _styles()
    story = []

    if complications:
        story.append(Paragraph(_ar("⚠️ مضاعفات:"), styles["section"]))
        t = Table([[Paragraph(_ar(complications), styles["body"])]],
            colWidths=[13*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FEF3C7")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#FDE68A")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    if notes:
        story.append(Paragraph(_ar("📝 ملاحظات:"), styles["section"]))
        t = Table([[Paragraph(_ar(notes), styles["body"])]],
            colWidths=[13*cm])
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

    return story


def _build_qr_image(cert_id, baby_name):
    if not HAS_QR:
        return None
    try:
        site = os.getenv("SITE_URL", "https://amina-saas.onrender.com").rstrip("/")
        content = "{}/?birth={}".format(site, cert_id)
        qr = qrcode.QRCode(version=None, box_size=8, border=2,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=3*cm, height=3*cm)
    except Exception:
        return None


def _build_signature_section(cert_id, baby_name, doctor_name):
    styles = _styles()
    qr_img = _build_qr_image(cert_id, baby_name)

    sig_data = [
        [Paragraph(_ar("ختم العيادة"), ParagraphStyle("cs",
            fontName=ARABIC_FONT, fontSize=9, leading=12,
            textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)),
         Paragraph(_ar("توقيع الطبيبة"), ParagraphStyle("ds",
            fontName=ARABIC_FONT, fontSize=9, leading=12,
            textColor=colors.HexColor("#64748B"), alignment=TA_CENTER))],
        [Paragraph("", styles["body"]), Paragraph("", styles["body"])],
        [Paragraph("____________________", ParagraphStyle("l1",
            fontName="Helvetica", fontSize=10, alignment=TA_CENTER)),
         Paragraph("____________________", ParagraphStyle("l2",
            fontName="Helvetica", fontSize=10, alignment=TA_CENTER))],
        [Paragraph("", styles["body"]),
         Paragraph(_ar("د. " + doctor_name) if doctor_name else "",
            ParagraphStyle("dn", fontName=ARABIC_FONT, fontSize=10,
                leading=13, textColor=colors.HexColor("#0F172A"),
                alignment=TA_CENTER))],
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
    text = _ar("{} — شهادة ميلاد — {}".format(
        clinic.get("name", ""), date.today().strftime("%Y-%m-%d")))
    canvas.drawCentredString(A4[0] / 2, 1*cm, text)
    canvas.restoreState()


# ============================================
# PUBLIC API
# ============================================

def generate_birth_certificate(newborn, mother, clinic, doctor_name="", cert_id=None):
    """
    Generate birth certificate PDF.

    Args:
        newborn: dict
        mother: dict
        clinic: dict
        doctor_name: str
        cert_id: optional UUID string

    Returns:
        bytes (PDF)
    """
    cert_id = cert_id or str(uuid.uuid4())

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
        title="Birth Certificate - {}".format(newborn.get("baby_name", "Newborn")),
    )

    styles = _styles()
    story = []

    story.append(_build_header(clinic, doctor_name))
    story.append(Spacer(1, 14))
    story.append(_build_title_bar())
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        _ar("تاريخ الإصدار: {}".format(date.today().strftime("%Y-%m-%d"))),
        styles["subtitle"]
    ))
    story.append(Spacer(1, 14))

    # Newborn info
    story.append(Paragraph(_ar("👶 معلومات المولود"), styles["section"]))
    story.append(_build_newborn_section(newborn))
    story.append(Spacer(1, 12))

    # Measurements
    story.append(Paragraph(_ar("📊 القياسات"), styles["section"]))
    story.append(_build_measurements_section(newborn))
    story.append(Spacer(1, 12))

    # APGAR
    apgar_t = _build_apgar_section(newborn)
    if apgar_t:
        story.append(Paragraph(_ar("💚 تقييم APGAR"), styles["section"]))
        story.append(apgar_t)
        story.append(Spacer(1, 12))

    # Mother
    story.append(Paragraph(_ar("👩 معلومات الأم"), styles["section"]))
    story.append(_build_mother_section(mother))
    story.append(Spacer(1, 12))

    # Notes + complications
    story += _build_notes_section(newborn.get("notes"), newborn.get("complications"))
    story.append(Spacer(1, 20))

    # Signature + QR
    story.append(_build_signature_section(cert_id, newborn.get("baby_name"), doctor_name))

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
    print("=" * 60)
    print("Birth Certificate PDF Test")
    print("=" * 60)

    newborn = {
        "baby_name": "أحمد محمد",
        "gender": "male",
        "delivery_date": "2026-10-15",
        "delivery_time": "14:30",
        "delivery_type": "normal",
        "delivery_place": "مستشفى بغداد",
        "weight_grams": 3200,
        "length_cm": 50,
        "head_circumference_cm": 34,
        "apgar_1min": 8,
        "apgar_5min": 9,
        "apgar_10min": 10,
        "health_status": "healthy",
        "notes": "الحمد لله، الولادة سلسة",
    }

    mother = {
        "full_name": "Mona2",
        "phone": "1629014596",
        "national_id": "972598723",
        "blood_type": "AB+",
    }

    clinic = {
        "name": "عيادة النور للنساء والولادة",
        "phone": "+964 770 000 0000",
    }

    pdf = generate_birth_certificate(newborn, mother, clinic, "أمينة محمد")
    with open("test_birth_certificate.pdf", "wb") as f:
        f.write(pdf)

    print("✅ PDF generated: test_birth_certificate.pdf ({:,} bytes)".format(len(pdf)))
    print("=" * 60)
