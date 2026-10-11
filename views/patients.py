# -*- coding: utf-8 -*-
"""Patients view v3 — faster actions via sub-views"""
import time
from datetime import date, datetime
import streamlit as st

from services.patients import (
    list_patients_cached, create_patient, get_patient_summary_cached,
    calculate_edd, calculate_gestational_age, get_risk_color,
    update_patient, PatientError,
)
from services.visits import (
    create_visit, analyze_bp, list_visits_cached, VisitError,
)
from core.cache import clear_all, show_cache_status


def render(clinic, user):
    """Main router"""
    view = st.session_state.get("patient_view", "list")

    if view == "list":
        _render_list(clinic)
    elif view == "new":
        _render_new(clinic)
    elif view == "detail":
        _render_detail(clinic, user)
    elif view == "edit":
        _render_edit(clinic, user)
    elif view == "new_visit":
        _render_new_visit(clinic, user)
    elif view == "portal":
        _render_portal(clinic)
    elif view == "wa":
        _render_wa(clinic, user)
    elif view == "appt":
        _render_appt(clinic, user)
    elif view == "ai":
        st.session_state["patient_view"] = "detail"
        st.info("👉 اذهب لتبويب **⚙️ الإدارة → 🤖 تحليل AI**")


# ============================================
# LIST
# ============================================
def _render_list(clinic):
    st.markdown("### 👩 قائمة الحوامل")

    # ============ TOP ACTIONS BAR ============
    c1, c2, c3 = st.columns([4, 1, 1])
    with c2:
        if st.button("➕ حامل جديدة", use_container_width=True, type="primary", key="new_btn"):
            st.session_state["patient_view"] = "new"
            st.rerun()
    with c3:
        if st.button("🔄 تحديث", use_container_width=True, key="refresh_btn"):
            from core.cache import clear_all
            clear_all()
            st.rerun()

    # ============ FILTERS ============
    c1, c2 = st.columns([3, 2])
    with c1:
        search = st.text_input("🔍 بحث بالاسم", placeholder="اكتبي اسماً...", key="lst_search")
    with c2:
        risk_filter = st.selectbox("مستوى المخاطر", ["الكل", "low", "medium", "high"], key="lst_risk")

    # Refresh button (small)
    c1, c2 = st.columns([5, 1])
    with c2:
        show_cache_status("patients_list")

    with st.spinner("جاري التحميل..."):
        patients = list_patients_cached(
            clinic["id"],
            search=search if search else None,
            risk_level=None if risk_filter == "الكل" else risk_filter,
        )

    if not patients:
        st.info("لا توجد حوامل. اضغط **➕ حامل جديدة** للبدء.")
        return

    st.markdown("**العدد: {}**".format(len(patients)))

    for p in patients:
        risk = p.get("risk_level", "low")
        weeks, days = calculate_gestational_age(p.get("lmp"))
        ga_text = "{}أ + {}ي".format(weeks, days) if weeks else "—"

        st.markdown("""
        <div class="patient-card risk-{risk}">
            <div style="font-size: 2.5rem;">👩</div>
            <div style="flex:1;">
                <div style="font-weight:700; font-size:1.15rem; color:#1F2937;">
                    {icon} {name}
                </div>
                <div style="color:#6B7280; font-size:0.85rem;">
                    📞 {phone} &nbsp;|&nbsp; 💓 {ga} &nbsp;|&nbsp; 📅 EDD: {edd}
                </div>
            </div>
        </div>
        """.format(
            risk=risk,
            icon={"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪"),
            name=p["full_name"], phone=p["phone"],
            ga=ga_text, edd=p.get("edd") or "—"
        ), unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 5])
        with c1:
            if st.button("📋 فتح", key="open_" + p["id"], use_container_width=True):
                st.session_state["selected_patient_id"] = p["id"]
                st.session_state["patient_view"] = "detail"
                st.rerun()
        with c2:
            if st.button("✏️ تعديل", key="edit_" + p["id"], use_container_width=True):
                st.session_state["selected_patient_id"] = p["id"]
                st.session_state["patient_view"] = "edit"
                st.rerun()
        st.write("")


# ============================================
# DETAIL (compact, with sub-page navigation)
# ============================================
def _render_detail(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    if not pid:
        st.session_state["patient_view"] = "list"
        st.rerun()

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.error("الملف غير موجود")
        if st.button("رجوع"):
            st.session_state["patient_view"] = "list"
            st.rerun()
        return

    # Header with compact buttons
    c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
    with c1:
        st.markdown("### {} {}".format(get_risk_color(p["risk_level"]), p["full_name"]))
        st.caption("📞 {} | {}".format(p["phone"], p["gestational_display"]))
    with c2:
        st.write("")
        if st.button("✏️ تعديل", use_container_width=True, key="det_edit"):
            st.session_state["patient_view"] = "edit"
            st.rerun()
    with c3:
        st.write("")
        if st.button("🩺 زيارة", use_container_width=True, type="primary", key="det_visit"):
            st.session_state["patient_view"] = "new_visit"
            st.rerun()
    with c4:
        st.write("")
        if st.button("📱 WA", use_container_width=True, key="det_wa"):
            st.session_state["patient_view"] = "wa"
            st.rerun()
    with c5:
        st.write("")
        if st.button("📅 موعد", use_container_width=True, key="det_appt"):
            st.session_state["patient_view"] = "appt"
            st.rerun()
    with c6:
        st.write("")
        if st.button("📲 بوابة", use_container_width=True, key="det_portal"):
            st.session_state["patient_view"] = "portal"
            st.rerun()

    st.divider()

    # Compact KPI row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("عمر الحمل", p["gestational_display"])
    m2.metric("EDD", p.get("edd") or "—")
    m3.metric("G / P", "{} / {}".format(p.get("gravida", 0), p.get("para", 0)))
    m4.metric("المخاطر", p.get("risk_level", "—").upper())

    # Alerts (only if any)
    try:
        from services.visits import list_visits_cached as _lvc
        from views.alerts_view import render_patient_alerts
        visits_for_alerts = _lvc(clinic["id"], pid, limit=10)
        alerts = None
        try:
            from services.alerts import analyze_patient_alerts
            alerts = analyze_patient_alerts(p, visits_for_alerts)
        except Exception:
            pass
        if alerts:
            render_patient_alerts(p, visits_for_alerts)
    except Exception:
        pass

    st.divider()

    # Basic info (2 columns)
    c1, c2 = st.columns(2)
    with c1:
        st.write("- **الهاتف:** {}".format(p["phone"]))
        st.write("- **الرقم الوطني:** {}".format(p.get("national_id") or "—"))
        st.write("- **فصيلة الدم:** {}".format(p.get("blood_type") or "—"))
    with c2:
        st.write("- **LMP:** {}".format(p.get("lmp") or "—"))
        st.write("- **EDD:** {}".format(p.get("edd") or "—"))
        st.write("- **تاريخ الإنشاء:** {}".format((p.get("created_at") or "—")[:10]))

    if p.get("notes"):
        st.info("📝 {}".format(p["notes"]))

    st.divider()

    # Actions row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📥 PDF", use_container_width=True, key="det_pdf_btn"):
            st.session_state["patient_view"] = "pdf"
            st.rerun()
    with c2:
        if st.button("⬅️ القائمة", use_container_width=True, key="det_back"):
            st.session_state["patient_view"] = "list"
            st.rerun()

    # Recent visits (compact)
    st.markdown("#### 🩺 آخر الزيارات")
    try:
        visits = list_visits_cached(clinic["id"], pid, limit=3)
        if not visits:
            st.info("لا توجد زيارات")
        else:
            for v in visits:
                _render_visit_row(v)
    except Exception:
        pass


def _render_visit_row(v):
    try:
        dt = datetime.fromisoformat(v["visit_date"].replace("Z", ""))
        date_str = dt.strftime("%Y-%m-%d")
    except Exception:
        date_str = (v.get("visit_date") or "—")[:10]

    bp = "{}/{}".format(v.get("bp_systolic") or "-", v.get("bp_diastolic") or "-")
    weight = "{} كغ".format(v.get("weight_kg") or "—")
    fhr = "{} bpm".format(v.get("fetal_heart_rate") or "—")

    st.markdown("""
    <div style="background:white; border-radius:10px; padding:0.6rem 1rem; margin-bottom:0.35rem; border-right:4px solid #0EA5A0;">
        <div style="display:flex; align-items:center; gap:1rem;">
            <div style="font-weight:700; color:#0EA5A0; min-width:90px;">{date}</div>
            <div style="color:#6B7280; font-size:0.85rem;">
                ⚖️ {w} | 💓 {bp} | 👶 {fhr}
            </div>
        </div>
    </div>
    """.format(date=date_str, w=weight, bp=bp, fhr=fhr), unsafe_allow_html=True)


# ============================================
# WHATSAPP (sub-page — faster)
# ============================================
def _render_wa(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.session_state["patient_view"] = "detail"
        st.rerun()

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### 📱 إرسال WhatsApp — {}".format(p["full_name"]))
        st.caption("📞 {}".format(p.get("phone") or "—"))
    with c2:
        if st.button("⬅️ رجوع", use_container_width=True, key="wa_back"):
            st.session_state["patient_view"] = "detail"
            st.rerun()

    try:
        from views.messaging_view import render_send_dialog
        render_send_dialog(clinic, p, key_prefix="wa_" + str(pid)[:8])
    except Exception as e:
        st.error("فشل تحميل: {}".format(e))


# ============================================
# APPOINTMENT (sub-page — faster)
# ============================================
def _render_appt(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.session_state["patient_view"] = "detail"
        st.rerun()

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### 📅 حجز موعد — {}".format(p["full_name"]))
    with c2:
        if st.button("⬅️ رجوع", use_container_width=True, key="appt_back"):
            st.session_state["patient_view"] = "detail"
            st.rerun()

    try:
        from views.appointments_view import quick_book_appointment
        quick_book_appointment(clinic, user, pid)
    except Exception as e:
        st.error("فشل تحميل: {}".format(e))


# ============================================
# EDIT
# ============================================
def _render_edit(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    if not pid:
        st.session_state["patient_view"] = "list"
        st.rerun()

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.error("الملف غير موجود")
        return

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### ✏️ تعديل — {}".format(p["full_name"]))
    with c2:
        if st.button("⬅️ رجوع", key="edit_back", use_container_width=True):
            st.session_state["patient_view"] = "detail"
            st.rerun()

    with st.form("edit_patient_full"):
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("الاسم الكامل *", value=p["full_name"])
            phone = st.text_input("الهاتف *", value=p["phone"])
        with c2:
            national_id = st.text_input("الرقم الوطني", value=p.get("national_id") or "")
            blood_type = st.selectbox(
                "فصيلة الدم",
                ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                index=["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].index(p.get("blood_type") or "")
            )

        dob_val = None
        if p.get("date_of_birth"):
            try:
                dob_val = datetime.strptime(p["date_of_birth"][:10], "%Y-%m-%d").date()
            except Exception:
                pass
        date_of_birth = st.date_input("تاريخ الميلاد", value=dob_val, min_value=date(1950, 1, 1))

        c1, c2, c3 = st.columns(3)
        with c1:
            lmp_val = None
            if p.get("lmp"):
                try:
                    lmp_val = datetime.strptime(p["lmp"][:10], "%Y-%m-%d").date()
                except Exception:
                    pass
            lmp = st.date_input("آخر دورة (LMP)", value=lmp_val)
        with c2:
            gravida = st.number_input("Gravida", min_value=0, value=int(p.get("gravida", 0)))
        with c3:
            para = st.number_input("Para", min_value=0, value=int(p.get("para", 0)))

        risk_level = st.selectbox(
            "مستوى المخاطر",
            ["low", "medium", "high"],
            index=["low", "medium", "high"].index(p.get("risk_level", "low")),
            format_func=lambda x: {
                "low": "🟢 منخفض", "medium": "🟡 متوسط", "high": "🔴 عالي"}[x]
        )
        notes = st.text_area("ملاحظات", value=p.get("notes") or "", height=80)

        if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True, type="primary"):
            try:
                update_patient(
                    clinic["id"], pid,
                    full_name=full_name, phone=phone,
                    national_id=national_id or None,
                    date_of_birth=date_of_birth.isoformat() if date_of_birth else None,
                    blood_type=blood_type or None,
                    lmp=lmp.isoformat() if lmp else None,
                    gravida=int(gravida), para=int(para),
                    risk_level=risk_level, notes=notes or None,
                )
                clear_all()
                st.success("✅ تم الحفظ")
                st.balloons()
                time.sleep(0.8)
                st.session_state["patient_view"] = "detail"
                st.rerun()
            except PatientError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))


# ============================================
# NEW
# ============================================
def _render_new(clinic):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### ➕ إضافة حامل جديدة")
    with c2:
        if st.button("⬅️ رجوع", key="new_back", use_container_width=True):
            st.session_state["patient_view"] = "list"
            st.rerun()

    with st.form("new_patient_form"):
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("الاسم الكامل *")
            phone = st.text_input("الهاتف *", placeholder="+964...")
        with c2:
            national_id = st.text_input("الرقم الوطني")
            blood_type = st.selectbox("فصيلة الدم", ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])

        date_of_birth = st.date_input("تاريخ الميلاد", value=None, min_value=date(1950, 1, 1))

        c1, c2, c3 = st.columns(3)
        with c1:
            lmp = st.date_input("LMP", value=None, key="new_lmp")
        with c2:
            gravida = st.number_input("Gravida", min_value=0, value=0)
        with c3:
            para = st.number_input("Para", min_value=0, value=0)

        if lmp:
            st.info("📅 EDD: **{}**".format(calculate_edd(lmp.isoformat())))

        risk_level = st.selectbox(
            "مستوى المخاطر",
            ["low", "medium", "high"],
            format_func=lambda x: {
                "low": "🟢 منخفض", "medium": "🟡 متوسط", "high": "🔴 عالي"}[x]
        )
        notes = st.text_area("ملاحظات", height=80)

        if st.form_submit_button("💾 حفظ", use_container_width=True, type="primary"):
            if not full_name or not phone:
                st.error("الاسم والهاتف مطلوبان")
            else:
                try:
                    new_p = create_patient(
                        clinic_id=clinic["id"], full_name=full_name, phone=phone,
                        national_id=national_id or None,
                        date_of_birth=date_of_birth.isoformat() if date_of_birth else None,
                        blood_type=blood_type or None,
                        lmp=lmp.isoformat() if lmp else None,
                        gravida=gravida, para=para,
                        risk_level=risk_level, notes=notes or None,
                    )
                    clear_all()
                    st.success("✅ {}".format(new_p["full_name"]))
                    st.session_state["selected_patient_id"] = new_p["id"]
                    st.session_state["patient_view"] = "detail"
                    time.sleep(0.8)
                    st.rerun()
                except PatientError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error("خطأ: {}".format(e))


# ============================================
# NEW VISIT
# ============================================
def _render_new_visit(clinic, user):
    pid = st.session_state.get("selected_patient_id")
    p = get_patient_summary_cached(clinic["id"], pid)

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### 🩺 زيارة جديدة — {}".format(p["full_name"]))
    with c2:
        if st.button("⬅️ رجوع", key="visit_back", use_container_width=True):
            st.session_state["patient_view"] = "detail"
            st.rerun()

    with st.form("new_visit_form"):
        c1, c2 = st.columns(2)
        with c1:
            weight_kg = st.number_input("الوزن (كغ)", min_value=30.0, max_value=200.0, value=65.0, step=0.1)
        with c2:
            visit_date = st.date_input("تاريخ الزيارة", value=date.today())

        c1, c2 = st.columns(2)
        with c1:
            bp_systolic = st.number_input("الضغط الانقباضي", min_value=50, max_value=250, value=120)
        with c2:
            bp_diastolic = st.number_input("الضغط الانبساطي", min_value=30, max_value=150, value=80)

        bp = analyze_bp(bp_systolic, bp_diastolic)
        if bp:
            if bp["level"] == "high":
                st.error("{} - {}".format(bp["label"], bp.get("warning", "")))
            elif bp["level"] == "normal":
                st.success(bp["label"])

        c1, c2 = st.columns(2)
        with c1:
            fhr = st.number_input("نبض الجنين (bpm)", min_value=60, max_value=220, value=140)
        with c2:
            fundal = st.number_input("ارتفاع الرحم (سم)", min_value=5.0, max_value=60.0, value=20.0, step=0.5)

        notes = st.text_area("ملاحظات", height=80)

        if st.form_submit_button("💾 حفظ الزيارة", use_container_width=True, type="primary"):
            try:
                create_visit(
                    clinic_id=clinic["id"], patient_id=pid, doctor_id=user["id"],
                    visit_date=datetime.combine(visit_date, datetime.now().time()).isoformat(),
                    gestational_age_weeks=p.get("gestational_weeks"),
                    weight_kg=weight_kg, bp_systolic=bp_systolic, bp_diastolic=bp_diastolic,
                    fetal_heart_rate=fhr, fundal_height_cm=fundal, notes=notes or None
                )
                clear_all()
                st.success("✅ تم حفظ الزيارة")
                st.session_state["patient_view"] = "detail"
                time.sleep(0.8)
                st.rerun()
            except VisitError as e:
                st.error(str(e))
            except Exception as e:
                st.error("خطأ: {}".format(e))


# ============================================
# PORTAL (PWA) INVITE
# ============================================
def _render_portal(clinic, patient_id=None):
    pid = patient_id or st.session_state.get("selected_patient_id")
    if not pid:
        st.session_state["patient_view"] = "list"
        st.rerun()

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.error("الملف غير موجود")
        return

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown("### 📲 بوابة الحامل — {}".format(p["full_name"]))
    with c2:
        if st.button("⬅️ رجوع", key="portal_back", use_container_width=True):
            st.session_state["patient_view"] = "detail"
            st.rerun()

    # Create or get account
    try:
        from services.patient_portal import get_or_create_account
        account = get_or_create_account(
            clinic_id=clinic["id"],
            patient_id=pid,
            phone=p.get("phone", "")
        )
        st.success("✅ الحساب جاهز")
    except Exception as e:
        st.error("خطأ: {}".format(str(e)))
        return

    # ============ SEND OTP VIA WHATSAPP ============
    st.markdown("### 📱 إرسال رمز التحقق")
    st.caption("يُنشئ النظام رمزاً فريداً ويرسله للحامل عبر واتساب")

    if st.button("🔐 إنشاء وإرسال OTP", key="gen_send_otp", type="primary", use_container_width=True):
        try:
            from services.patient_portal import generate_otp
            from services.messaging import build_whatsapp_link

            result = generate_otp(p.get("phone", ""))
            if isinstance(result, tuple) and len(result) == 3:
                code, _acct, sent_via = result
            elif isinstance(result, tuple):
                code, _acct = result
                sent_via = None
            else:
                code = result
                sent_via = None

            st.session_state["doctor_otp_" + str(pid)[:8]] = code
            st.success("✅ تم إنشاء الرمز")

            st.markdown("""
            <div style="background:#F0FDF4; border:2px solid #16A34A; border-radius:12px; padding:1rem; text-align:center; margin:0.5rem 0;">
                <div style="font-size:0.8rem; color:#64748B;">رمز التحقق</div>
                <div style="font-family:monospace; font-size:2rem; font-weight:800; color:#16A34A; letter-spacing:0.2em;">
                    {}
                </div>
            </div>
            """.format(code), unsafe_allow_html=True)

            # WhatsApp send
            _phone = p.get("phone", "")
            if not _phone.startswith("+"):
                _phone = "+" + _phone.lstrip("0")

            wa_msg = (
                "*بوابة أمينة SaaS* 👶" + chr(10) +
                "━━━━━━━━━━━━━━━" + chr(10) +
                "السلام عليكم *{}* 🌸".format(p["full_name"]) + chr(10) + chr(10) +
                "🔐 رمز التحقق الخاص بك:" + chr(10) + chr(10) +
                "*{}*".format(code) + chr(10) + chr(10) +
                "⏰ صالح 10 دقائق" + chr(10) + chr(10) +
                "📱 ادخلي البوابة:" + chr(10) +
                "http://192.168.1.189:8501/?pwa=1" + chr(10) + chr(10) +
                "_مع تمنياتنا بالصحة والعافية_ 💜"
            )
            wa_link = build_whatsapp_link(_phone, wa_msg)

            st.link_button(
                "📱 إرسال الرمز عبر واتساب",
                wa_link,
                use_container_width=True
            )
            st.caption("سيُفتح واتساب مع الرمز جاهز — اضغط Send")

        except Exception as e:
            st.error("خطأ: {}".format(str(e)[:200]))

    st.divider()

    # PWA URL
    base_url = st.session_state.get("_public_base_url", "http://192.168.1.189:8501")
    pwa_url = "{}/?pwa=1".format(base_url.rstrip("/"))

    st.markdown("### 🔗 رابط البوابة")
    st.code(pwa_url, language=None)

    # QR Code
    try:
        import qrcode
        from io import BytesIO

        qr = qrcode.QRCode(version=None, box_size=8, border=2)
        qr.add_data(pwa_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#16A34A", back_color="white")
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)

        qc1, qc2 = st.columns([1, 2])
        with qc1:
            st.image(buf.getvalue(), width=200, caption="امسحي للدخول")
        with qc2:
            st.markdown("**اطلبي من الحامل:**")
            st.markdown("""
            1. 📱 امسحي الرمز بكاميرا الجوال
            2. 🔢 أدخلي رقم هاتفك
            3. 🔐 استلمي رمز OTP
            4. ✅ ادخلي وشاهدي بياناتك
            """)

            if p.get("phone"):
                from services.messaging import build_whatsapp_link
                wa_msg = (
                    "*بوابة الحامل* 📱" + chr(10) +
                    "━━━━━━━━━━━━━━━" + chr(10) +
                    "السلام عليكم *{}* 🌸".format(p["full_name"]) + chr(10) + chr(10) +
                    "بوابتك الخاصة جاهزة!" + chr(10) +
                    "اضغطي الرابط لمشاهدة مواعيدك ووصفاتك:" + chr(10) +
                    pwa_url + chr(10) + chr(10) +
                    "🔐 سيصلك رمز تحقق على رقمك." + chr(10) + chr(10) +
                    "_مع تمنياتنا بالصحة والعافية_ 💜"
                )
                wa_link = build_whatsapp_link(p["phone"], wa_msg)
                st.link_button("📱 إرسال الرابط عبر واتساب", wa_link, use_container_width=True)
    except Exception as e:
        st.warning("QR: {}".format(str(e)[:80]))
