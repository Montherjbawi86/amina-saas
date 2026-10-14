# -*- coding: utf-8 -*-
"""
Vaccination Schedule View
جدول التطعيمات القياسي — عرض شامل لكل الحوامل
"""
from datetime import date, timedelta, datetime
import streamlit as st
import pandas as pd

from core.db import db
from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from services.vaccinations import (
    DEFAULT_SCHEDULE, list_vaccinations, auto_schedule_defaults,
    mark_given, update_vaccination, create_vaccination,
    get_status_label, get_status_color,
)


# ============================================
# HELPERS
# ============================================

def _fetch_patients(clinic_id):
    try:
        return (
            db().table("patients")
            .select("id, full_name, phone, lmp, edd, blood_type, is_active")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _fetch_all_vaccinations(clinic_id):
    """Fetch all vaccinations for the clinic"""
    try:
        return (
            db().table("vaccinations")
            .select("*")
            .eq("clinic_id", clinic_id)
            .order("scheduled_for")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _gestational_age(lmp):
    """Returns (weeks, days) or (None, None)"""
    if not lmp:
        return None, None
    try:
        if isinstance(lmp, str):
            lmp_d = datetime.strptime(lmp[:10], "%Y-%m-%d").date()
        else:
            lmp_d = lmp
        days = (date.today() - lmp_d).days
        if days < 0:
            return None, None
        return days // 7, days % 7
    except Exception:
        return None, None


def _weeks_label(weeks):
    if weeks is None:
        return "—"
    return "أسبوع {}".format(weeks)


# ============================================
# TAB 1: OVERVIEW
# ============================================

def _render_overview_tab(clinic, patients, vaccinations):
    """KPIs + auto-schedule for all"""

    # Categorize by status
    total = len(vaccinations)
    pending = sum(1 for v in vaccinations if v.get("status") == "pending")
    given = sum(1 for v in vaccinations if v.get("status") == "given")
    missed = sum(1 for v in vaccinations if v.get("status") == "missed")

    # Upcoming 30 days
    today = date.today()
    in_30 = today + timedelta(days=30)
    upcoming = [
        v for v in vaccinations
        if v.get("status") == "pending"
        and v.get("scheduled_for")
        and today <= datetime.strptime(v["scheduled_for"][:10], "%Y-%m-%d").date() <= in_30
    ]

    # Overdue
    overdue = [
        v for v in vaccinations
        if v.get("status") == "pending"
        and v.get("scheduled_for")
        and datetime.strptime(v["scheduled_for"][:10], "%Y-%m-%d").date() < today
    ]

    # Row 1: KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card_v2("👩", len(patients), "الحوامل النشطات")
    with c2:
        kpi_card_v2("💉", total, "إجمالي التطعيمات")
    with c3:
        kpi_card_v2("⏳", pending, "منتظرة")
    with c4:
        kpi_card_v2("✅", given, "تم إعطاؤها")
    with c5:
        kpi_card_v2("❌", missed, "فائتة")

    st.write("")

    # Row 2: Alerts
    c1, c2 = st.columns(2)

    with c1:
        if overdue:
            st.markdown("""
            <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;
                        padding:1rem 1.25rem;">
                <div style="font-size:1.5rem;">🚨</div>
                <div style="font-weight:700;color:#B91C1C;margin-top:0.3rem;">
                    {} تطعيم متأخر
                </div>
                <div style="color:#7F1D1D;font-size:0.85rem;margin-top:0.2rem;">
                    يحتاج متابعة فورية
                </div>
            </div>
            """.format(len(overdue)), unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:12px;
                        padding:1rem 1.25rem;">
                <div style="font-size:1.5rem;">✅</div>
                <div style="font-weight:700;color:#15803D;margin-top:0.3rem;">
                    لا توجد تطعيمات متأخرة
                </div>
                <div style="color:#166534;font-size:0.85rem;margin-top:0.2rem;">
                    كل التطعيمات في موعدها
                </div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;
                    padding:1rem 1.25rem;">
            <div style="font-size:1.5rem;">📅</div>
            <div style="font-weight:700;color:#1E40AF;margin-top:0.3rem;">
                {} تطعيم خلال 30 يوم
            </div>
            <div style="color:#1E3A8A;font-size:0.85rem;margin-top:0.2rem;">
                قادمة قريباً
            </div>
        </div>
        """.format(len(upcoming)), unsafe_allow_html=True)

    st.divider()

    # === Auto-schedule section ===
    section_header_v2("⚡", "توليد الجدول التلقائي")

    st.caption("""
    يولّد الجدول القياسي (8 عناصر: 6 تطعيمات + 2 مكملات) لكل حامل لديها EDD.
    التواريخ تُحسب تلقائياً حسب أسابيع الحمل.
    """)

    # Patients without any schedule
    scheduled_pids = {v.get("patient_id") for v in vaccinations}
    patients_without = [p for p in patients if p["id"] not in scheduled_pids]

    c1, c2 = st.columns([2, 1])

    with c1:
        if patients_without:
            st.warning("⚠️ {} حامل بدون جدول تطعيمات".format(len(patients_without)))
            with st.expander("عرض القائمة"):
                for p in patients_without:
                    weeks, _ = _gestational_age(p.get("lmp"))
                    st.write("- **{}** — {}".format(
                        p.get("full_name", "—"),
                        _weeks_label(weeks) if weeks else "لا يوجد LMP"
                    ))
        else:
            st.success("✅ كل الحوامل لديهن جدول تطعيمات")

    with c2:
        if st.button("⚡ توليد لكل الحوامل", type="primary",
                     use_container_width=True, key="auto_all_sched"):
            with st.spinner("⏳ جاري التوليد..."):
                total_created = 0
                failed = 0
                for p in patients:
                    if not p.get("edd"):
                        failed += 1
                        continue
                    try:
                        created = auto_schedule_defaults(
                            clinic["id"], p["id"], p["edd"]
                        )
                        total_created += len(created)
                    except Exception:
                        failed += 1

                if total_created:
                    st.success("✅ تم إنشاء {} تطعيم".format(total_created))
                    st.rerun()
                else:
                    st.info("لم يُنشأ جديد")

                if failed:
                    st.warning("⚠️ {} حامل بدون EDD".format(failed))


# ============================================
# TAB 2: ALL VACCINATIONS
# ============================================

def _render_all_tab(clinic, patients, vaccinations):
    """Full list of all vaccinations with filters"""

    # Filters
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        pmap = {"all": "كل الحوامل"}
        for p in patients:
            pmap[p["id"]] = p.get("full_name", "—")

        patient_filter = st.selectbox(
            "الحامل",
            options=list(pmap.keys()),
            format_func=lambda x: pmap[x],
            key="sched_patient_filter"
        )

    with c2:
        status_filter = st.selectbox(
            "الحالة",
            options=["all", "pending", "given", "missed", "skipped"],
            format_func=lambda x: {
                "all": "الكل",
                "pending": "⏳ منتظرة",
                "given": "✅ تم",
                "missed": "❌ فائتة",
                "skipped": "⏭️ متجاوزة",
            }[x],
            key="sched_status_filter"
        )

    with c3:
        only_overdue = st.checkbox("متأخرة فقط", value=False, key="sched_overdue_only")

    # Apply filters
    filtered = vaccinations

    if patient_filter != "all":
        filtered = [v for v in filtered if v.get("patient_id") == patient_filter]

    if status_filter != "all":
        filtered = [v for v in filtered if v.get("status") == status_filter]

    if only_overdue:
        today = date.today()
        filtered = [
            v for v in filtered
            if v.get("scheduled_for")
            and datetime.strptime(v["scheduled_for"][:10], "%Y-%m-%d").date() < today
            and v.get("status") == "pending"
        ]

    if not filtered:
        empty_state("💉", "لا توجد تطعيمات", "جرب تغيير الفلاتر")
        return

    st.caption("📊 {} نتيجة".format(len(filtered)))

    # Table
    pmap_names = {p["id"]: p.get("full_name", "—") for p in patients}

    rows = []
    for v in filtered:
        scheduled = v.get("scheduled_for") or ""
        try:
            sched_date = datetime.strptime(scheduled[:10], "%Y-%m-%d").date()
        except Exception:
            sched_date = None

        days_diff = ""
        if sched_date and v.get("status") == "pending":
            diff = (sched_date - date.today()).days
            if diff < 0:
                days_diff = "متأخر {} يوم".format(abs(diff))
            elif diff == 0:
                days_diff = "اليوم"
            elif diff <= 7:
                days_diff = "بعد {} يوم".format(diff)
            else:
                days_diff = "بعد {} يوم".format(diff)

        rows.append({
            "الحامل": pmap_names.get(v.get("patient_id"), "—"),
            "التطعيم": v.get("vaccine_name", "—"),
            "الجرعة": v.get("dose_number", 1),
            "الحالة": get_status_label(v.get("status", "pending")),
            "مجدول": scheduled[:10] if scheduled else "—",
            "الوقت": days_diff,
            "أُعطي": (v.get("given_at") or "—")[:10],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export CSV
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 تصدير CSV",
        csv,
        "vaccination_schedule_{}.csv".format(date.today().strftime("%Y%m%d")),
        "text/csv",
        key="sched_csv_export"
    )


# ============================================
# TAB 3: BY PATIENT
# ============================================

def _render_by_patient_tab(clinic, patients, vaccinations):
    """Timeline view per patient"""

    if not patients:
        empty_state("👩", "لا يوجد حوامل", "")
        return

    pmap = {p["id"]: p for p in patients}

    selected_id = st.selectbox(
        "اختر حاملاً",
        options=list(pmap.keys()),
        format_func=lambda x: "{} — {}".format(
            pmap[x].get("full_name", "—"),
            _weeks_label(_gestational_age(pmap[x].get("lmp"))[0])
        ),
        key="sched_patient_view"
    )

    if not selected_id:
        return

    patient = pmap[selected_id]
    weeks, days = _gestational_age(patient.get("lmp"))

    # Patient header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#F0FDF4 0%,#DCFCE7 100%);
                border-radius:14px;padding:1.25rem 1.5rem;border:1px solid #BBF7D0;
                margin-bottom:1rem;">
        <div style="font-weight:700;color:#0F172A;font-size:1.15rem;">
            👩 {name}
        </div>
        <div style="color:#166534;font-size:0.9rem;margin-top:0.3rem;">
            {weeks} &nbsp;|&nbsp; 📅 EDD: {edd}
        </div>
    </div>
    """.format(
        name=patient.get("full_name", "—"),
        weeks=_weeks_label(weeks) if weeks else "لا يوجد LMP",
        edd=patient.get("edd", "—")[:10] if patient.get("edd") else "—",
    ), unsafe_allow_html=True)

    # Patient vaccinations
    pvax = [v for v in vaccinations if v.get("patient_id") == selected_id]

    if not pvax:
        st.info("📭 لا يوجد جدول لهذه الحامل")
        if st.button("⚡ توليد الجدول", key="gen_one", type="primary"):
            if not patient.get("edd"):
                st.error("لا يوجد EDD")
            else:
                created = auto_schedule_defaults(clinic["id"], selected_id, patient["edd"])
                st.success("تم إنشاء {}".format(len(created)))
                st.rerun()
        return

    # Sort by scheduled date
    pvax.sort(key=lambda x: x.get("scheduled_for") or "")

    # Timeline
    st.markdown("#### 📅 الجدول الزمني")

    for v in pvax:
        status = v.get("status", "pending")
        color = get_status_color(status)
        scheduled = (v.get("scheduled_for") or "")[:10]
        given = (v.get("given_at") or "")[:10]

        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                    padding:0.9rem 1.15rem;margin-bottom:0.5rem;
                    border-right:4px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:700;color:#0F172A;">
                    💉 {name}
                </div>
                <div style="background:{color};color:white;padding:0.2rem 0.6rem;
                            border-radius:6px;font-size:0.72rem;font-weight:700;">
                    {status}
                </div>
            </div>
            <div style="color:#64748B;font-size:0.85rem;margin-top:0.4rem;">
                📅 مجدول: {scheduled} {given}
            </div>
        </div>
        """.format(
            color=color,
            name=v.get("vaccine_name", "—"),
            status=get_status_label(status),
            scheduled=scheduled or "—",
            given=" &nbsp;|&nbsp; ✅ أُعطي: {}".format(given) if given else "",
        ), unsafe_allow_html=True)

        # Actions
        c1, c2, c3 = st.columns([1, 1, 5])
        with c1:
            if status != "given":
                if st.button("✅ أُعطي", key="pv_given_{}".format(v["id"]),
                             use_container_width=True):
                    mark_given(clinic["id"], v["id"])
                    st.success("✅ تم")
                    st.rerun()
        with c2:
            if status == "pending":
                if st.button("❌ فائت", key="pv_miss_{}".format(v["id"]),
                             use_container_width=True):
                    update_vaccination(clinic["id"], v["id"], status="missed")
                    st.rerun()
        st.markdown("")


# ============================================
# TAB 4: STANDARD SCHEDULE
# ============================================

def _render_standard_tab():
    """Show the standard schedule template"""

    section_header_v2("📋", "الجدول القياسي — WHO + CDC + وزارة الصحة")

    st.caption("هذا هو الجدول الذي يُطبَّق تلقائياً على كل حامل عند التوليد.")

    vaccines = [x for x in DEFAULT_SCHEDULE if x.get("category") == "vaccine"]
    supplements = [x for x in DEFAULT_SCHEDULE if x.get("category") == "supplement"]

    # Vaccines
    st.markdown("##### 💉 التطعيمات ({})".format(len(vaccines)))

    for item in vaccines:
        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                    padding:0.75rem 1rem;margin-bottom:0.4rem;
                    border-right:3px solid #16A34A;">
            <div style="font-weight:700;color:#0F172A;">
                💉 {name}
            </div>
            <div style="color:#64748B;font-size:0.85rem;margin-top:0.3rem;">
                📅 الأسبوع: <b>{week}</b> &nbsp;|&nbsp; الجرعة: {dose}
            </div>
            {notes}
        </div>
        """.format(
            name=item["name"],
            week=item["week"],
            dose=item["dose"],
            notes='<div style="color:#94A3B8;font-size:0.8rem;margin-top:0.25rem;">💡 {}</div>'.format(item["notes"]) if item.get("notes") else "",
        ), unsafe_allow_html=True)

    st.write("")
    st.markdown("##### 💊 المكملات ({})".format(len(supplements)))

    for item in supplements:
        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
                    padding:0.75rem 1rem;margin-bottom:0.4rem;
                    border-right:3px solid #F59E0B;">
            <div style="font-weight:700;color:#0F172A;">
                💊 {name}
            </div>
            <div style="color:#64748B;font-size:0.85rem;margin-top:0.3rem;">
                📅 من الأسبوع: <b>{week}</b>
            </div>
            {notes}
        </div>
        """.format(
            name=item["name"],
            week=item["week"],
            notes='<div style="color:#94A3B8;font-size:0.8rem;margin-top:0.25rem;">💡 {}</div>'.format(item["notes"]) if item.get("notes") else "",
        ), unsafe_allow_html=True)

    st.divider()
    st.info("""
    ℹ️ **ملاحظة:**
    - الجدول قد يحتاج تعديلاً حسب البروتوكول المحلي
    - بعض التطعيمات (مثل Rh) تُعطى فقط لحالات معينة
    - المكملات تُوصف لحوامل محددات
    - يمكن تعديل الجدول في `services/vaccinations.py`
    """)


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="جدول التطعيمات",
        subtitle="متابعة شاملة للتطعيمات القياسية لكل الحوامل",
        icon="💉",
        badge="{} حامل".format(len(_fetch_patients(clinic["id"])))
    )

    patients = _fetch_patients(clinic["id"])
    vaccinations = _fetch_all_vaccinations(clinic["id"])

    if not patients:
        empty_state(
            "👩",
            "لا توجد حوامل",
            "سجّل حاملاً أولاً من قسم 'الحوامل'"
        )
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 نظرة عامة",
        "📋 كل التطعيمات",
        "👩 حسب الحامل",
        "📖 الجدول القياسي",
    ])

    with tab1:
        _render_overview_tab(clinic, patients, vaccinations)
    with tab2:
        _render_all_tab(clinic, patients, vaccinations)
    with tab3:
        _render_by_patient_tab(clinic, patients, vaccinations)
    with tab4:
        _render_standard_tab()
