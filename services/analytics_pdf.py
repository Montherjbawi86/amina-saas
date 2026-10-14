# -*- coding: utf-8 -*-
"""
Analytics PDF Export
تقرير إداري شامل PDF
"""
from datetime import datetime, date
from io import BytesIO
import os
import urllib.request

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ============================================
# ARABIC FONT
# ============================================

def _register_font():
    import os
    here = os.path.dirname(os.path.abspath(__file__))

    project_fonts = [
        os.path.normpath(os.path.join(here, "..", "assets/fonts/Amiri-Regular.ttf")),
        os.path.normpath(os.path.join(here, "..", "assets/fonts/NotoNaskhArabic-Regular.ttf")),
    ]
    for abs_path in project_fonts:
        if os.path.exists(abs_path):
            try:
                pdfmetrics.registerFont(TTFont("Arabic", abs_path))
                print("[AnalyticsPDF] Using: {}".format(abs_path))
                return "Arabic"
            except Exception as e:
                print("[AnalyticsPDF] Failed {}: {}".format(abs_path, str(e)[:80]))

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
        "title": ParagraphStyle("title", fontName=ARABIC_FONT,
            fontSize=20, leading=26, textColor=colors.white, alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", fontName=ARABIC_FONT,
            fontSize=14, leading=18, textColor=colors.HexColor("#15803D"),
            alignment=TA_RIGHT, spaceBefore=10, spaceAfter=6),
        "label": ParagraphStyle("label", fontName=ARABIC_FONT,
            fontSize=9, leading=12, textColor=colors.HexColor("#64748B"),
            alignment=TA_RIGHT),
        "value": ParagraphStyle("value", fontName=ARABIC_FONT,
            fontSize=11, leading=14, textColor=colors.HexColor("#0F172A"),
            alignment=TA_RIGHT),
        "body": ParagraphStyle("body", fontName=ARABIC_FONT,
            fontSize=9, leading=13, alignment=TA_RIGHT),
        "small": ParagraphStyle("small", fontName=ARABIC_FONT,
            fontSize=7, leading=10, textColor=colors.HexColor("#94A3B8"),
            alignment=TA_CENTER),
    }


# ============================================
# COMPONENTS
# ============================================

def _build_header(clinic, user, date_from, date_to):
    styles = _styles()

    # Title bar
    left = Table([[Paragraph("📊", ParagraphStyle("logo",
        fontName=ARABIC_FONT, fontSize=28, alignment=TA_CENTER))]],
        colWidths=[2.5*cm])
    left.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1.5, colors.HexColor("#16A34A")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))

    right_data = [
        [Paragraph(_ar(clinic.get("name", "العيادة")), ParagraphStyle(
            "cname", fontName=ARABIC_FONT, fontSize=16, leading=20,
            textColor=colors.HexColor("#16A34A"), alignment=TA_RIGHT))],
        [Paragraph(_ar("د. " + user.get("full_name", "")), styles["label"])],
        [Paragraph(_ar("📅 {} → {}".format(date_from or "البداية", date_to or "الآن")),
            styles["label"])],
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

    story = [header, Spacer(1, 12)]

    # Title bar
    title_data = [[Paragraph(_ar("تقرير الأداء الشامل"), styles["title"])]]
    title_t = Table(title_data, colWidths=[13*cm])
    title_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#16A34A")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(title_t)
    story.append(Spacer(1, 8))

    # Generated at
    story.append(Paragraph(
        _ar("تم الإنشاء: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M"))),
        styles["small"]
    ))
    story.append(Spacer(1, 12))

    return story


def _build_kpi_table(overview):
    """KPI grid"""
    styles = _styles()

    kpis = [
        ("👩", "الحوامل النشطات", overview.get("total_patients", 0)),
        ("🆕", "جديدات في الفترة", overview.get("new_patients", 0)),
        ("🩺", "الزيارات", overview.get("total_visits", 0)),
        ("💊", "الوصفات", overview.get("total_prescriptions", 0)),
        ("🔬", "التحاليل", overview.get("total_lab_tests", 0)),
        ("⚠️", "تحاليل غير طبيعية", overview.get("abnormal_lab_tests", 0)),
        ("📸", "صور سونار", overview.get("total_ultrasound", 0)),
        ("📄", "شهادات صادرة", overview.get("total_certificates", 0)),
    ]

    rows = []
    for i in range(0, len(kpis), 4):
        chunk = kpis[i:i+4]
        row_cells = []
        for icon, label, value in chunk:
            cell_data = [[
                Paragraph(icon, ParagraphStyle("icon",
                    fontName=ARABIC_FONT, fontSize=18, alignment=TA_CENTER)),
            ], [
                Paragraph(str(value), ParagraphStyle("val",
                    fontName=ARABIC_FONT, fontSize=16, leading=18,
                    textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER)),
            ], [
                Paragraph(_ar(label), ParagraphStyle("lbl",
                    fontName=ARABIC_FONT, fontSize=8, leading=10,
                    textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)),
            ]]
            cell_t = Table(cell_data, colWidths=[3.1*cm])
            cell_t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), colors.white),
                ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))
            row_cells.append(cell_t)

        # Fill remaining cells
        while len(row_cells) < 4:
            row_cells.append("")

        rows.append(row_cells)

    if not rows:
        return []

    t = Table(rows, colWidths=[3.25*cm]*4)
    t.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))

    return [t, Spacer(1, 12)]


def _build_bar_chart(data, title, color="#16A34A"):
    """Vertical bar chart as Drawing"""
    if not data:
        return None

    drawing = Drawing(13*cm, 6*cm)

    chart = VerticalBarChart()
    chart.x = 1.5*cm
    chart.y = 1*cm
    chart.height = 4*cm
    chart.width = 11*cm
    chart.data = [[d.get("count", 0) for d in data]]
    chart.categoryAxis.categoryNames = [d.get("label", "") for d in data]
    chart.bars[0].fillColor = colors.HexColor(color)
    chart.bars[0].strokeColor = None
    chart.valueAxis.valueMin = 0
    chart.categoryAxis.labels.fontName = ARABIC_FONT
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = ARABIC_FONT
    chart.valueAxis.labels.fontSize = 7

    drawing.add(chart)
    return drawing


def _build_lab_summary_table(labs):
    """Abnormal labs summary"""
    styles = _styles()
    if not labs:
        return [Paragraph(_ar("✅ لا توجد تحاليل غير طبيعية"), styles["body"]), Spacer(1, 8)]

    rows = [[
        Paragraph(_ar("التاريخ"), styles["body"]),
        Paragraph(_ar("الحامل"), styles["body"]),
        Paragraph(_ar("التحليل"), styles["body"]),
        Paragraph(_ar("الخطورة"), styles["body"]),
    ]]
    for t in labs[:10]:
        sev = t.get("severity", "moderate")
        sev_text = {"severe": "🔴 شديد", "moderate": "🟠 متوسط", "mild": "🟡 خفيف"}.get(sev, "—")
        rows.append([
            Paragraph(_ar((t.get("test_date") or "—")[:10]), styles["small"]),
            Paragraph(_ar((t.get("_patient_name") or "—")[:20]), styles["small"]),
            Paragraph(_ar((t.get("test_name") or "—")[:25]), styles["small"]),
            Paragraph(_ar(sev_text), styles["small"]),
        ])

    t = Table(rows, colWidths=[2.5*cm, 3.5*cm, 5*cm, 2*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#16A34A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    return [t, Spacer(1, 12)]


def _build_patient_summary_table(patients):
    """Top patients table"""
    styles = _styles()
    if not patients:
        return []

    rows = [[
        Paragraph(_ar("الحامل"), styles["body"]),
        Paragraph(_ar("الخطر"), styles["body"]),
        Paragraph(_ar("زيارات"), styles["body"]),
        Paragraph(_ar("تحاليل"), styles["body"]),
        Paragraph(_ar("غير طبيعية"), styles["body"]),
    ]]
    for p in patients[:10]:
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(p.get("risk_level", "low"), "⚪")
        rows.append([
            Paragraph(_ar((p.get("name") or "—")[:22]), styles["small"]),
            Paragraph(_ar(risk_icon), styles["small"]),
            Paragraph(str(p.get("visits", 0)), styles["small"]),
            Paragraph(str(p.get("labs", 0)), styles["small"]),
            Paragraph(str(p.get("abnormal_labs", 0)), styles["small"]),
        ])

    t = Table(rows, colWidths=[5*cm, 2*cm, 2*cm, 2*cm, 2*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), ARABIC_FONT),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#16A34A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    return [t, Spacer(1, 12)]


def _build_qr_section(clinic):
    """QR for verification"""
    if not HAS_QR:
        return []
    try:
        site = os.getenv("SITE_URL", "https://amina-saas.onrender.com").rstrip("/")
        content = "{}/?report={}&date={}".format(
            site, str(clinic.get("id", ""))[:8], date.today().strftime("%Y%m%d")
        )
        qr = qrcode.QRCode(version=None, box_size=6, border=2,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return [RLImage(buf, width=3*cm, height=3*cm)]
    except Exception:
        return []


def _page_footer(canvas, doc, clinic):
    canvas.saveState()
    canvas.setFont(ARABIC_FONT, 8)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    text = _ar("{} — تقرير الأداء — {}".format(
        clinic.get("name", ""), date.today().strftime("%Y-%m-%d")))
    canvas.drawCentredString(A4[0] / 2, 1*cm, text)
    canvas.restoreState()


# ============================================
# PUBLIC API
# ============================================

def generate_analytics_pdf(clinic, user, overview, trends,
                             abnormal_labs=None, patients_report=None,
                             date_from=None, date_to=None):
    """
    Generate comprehensive analytics PDF report.

    Args:
        clinic: dict
        user: dict
        overview: from services.reports.get_overview()
        trends: from services.reports.get_monthly_trends()
        abnormal_labs: from services.reports.get_abnormal_labs()
        patients_report: from services.reports.get_patients_report()
        date_from, date_to: date objects or None

    Returns:
        bytes (PDF)
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
        title="Analytics Report - {}".format(clinic.get("name", "")),
    )

    story = []

    # Header
    story += _build_header(clinic, user, date_from, date_to)

    # KPIs
    story.append(Paragraph(_ar("📊 المؤشرات الرئيسية"), _styles()["h1"]))
    story += _build_kpi_table(overview)

    # Trends
    if trends:
        story.append(Paragraph(_ar("📈 الزيارات (آخر 6 أشهر)"), _styles()["h1"]))
        visits_data = [{"label": t["label"], "count": t["visits"]} for t in trends]
        chart = _build_bar_chart(visits_data, "الزيارات", "#16A34A")
        if chart:
            story.append(chart)
        story.append(Spacer(1, 8))

        story.append(Paragraph(_ar("👩 الحوامل الجديدات"), _styles()["h1"]))
        patients_data = [{"label": t["label"], "count": t["patients"]} for t in trends]
        chart = _build_bar_chart(patients_data, "حوامل", "#22C55E")
        if chart:
            story.append(chart)
        story.append(Spacer(1, 12))

    # Abnormal labs
    story.append(Paragraph(_ar("⚠️ التحاليل غير الطبيعية"), _styles()["h1"]))
    story += _build_lab_summary_table(abnormal_labs or [])

    # Top patients
    if patients_report:
        story.append(Paragraph(_ar("👩 تقرير الحوامل"), _styles()["h1"]))
        story += _build_patient_summary_table(patients_report)

    # QR
    qr_list = _build_qr_section(clinic)
    if qr_list:
        story.append(Spacer(1, 12))
        qr_data = [[
            qr_list[0],
            Paragraph(_ar("<b>للتحقق من التقرير</b><br/>امسحي الرمز"),
                ParagraphStyle("qr", fontName=ARABIC_FONT, fontSize=9,
                    leading=13, textColor=colors.HexColor("#15803D"),
                    alignment=TA_RIGHT))
        ]]
        qr_t = Table(qr_data, colWidths=[3.5*cm, 9.5*cm])
        qr_t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
            ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#16A34A")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(qr_t)

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
    print("=" * 60)
    print("Analytics PDF Test")
    print("=" * 60)

    clinic = {"id": "test-123", "name": "عيادة النور للنساء والولادة"}
    user = {"full_name": "د. أمينة محمد"}
    overview = {
        "total_patients": 15, "new_patients": 3, "total_visits": 42,
        "total_prescriptions": 18, "total_lab_tests": 25,
        "abnormal_lab_tests": 7, "total_ultrasound": 12, "total_certificates": 5,
    }
    trends = [
        {"label": "Aug 2026", "patients": 2, "visits": 5, "labs": 3, "ultrasounds": 1},
        {"label": "Sep 2026", "patients": 4, "visits": 12, "labs": 8, "ultrasounds": 3},
        {"label": "Oct 2026", "patients": 3, "visits": 15, "labs": 10, "ultrasounds": 4},
    ]
    labs = [
        {"test_date": "2026-10-10", "_patient_name": "فاطمة أحمد", "test_name": "CBC", "severity": "moderate"},
        {"test_date": "2026-10-08", "_patient_name": "زينب علي", "test_name": "Glucose", "severity": "severe"},
    ]
    patients = [
        {"name": "فاطمة أحمد", "risk_level": "high", "visits": 8, "labs": 5, "abnormal_labs": 2},
        {"name": "زينب علي", "risk_level": "low", "visits": 4, "labs": 3, "abnormal_labs": 0},
    ]

    pdf = generate_analytics_pdf(clinic, user, overview, trends, labs, patients)
    with open("test_analytics.pdf", "wb") as f:
        f.write(pdf)

    print("✅ PDF generated: test_analytics.pdf ({:,} bytes)".format(len(pdf)))
    print("=" * 60)
