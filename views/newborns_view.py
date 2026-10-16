# -*- coding: utf-8 -*-
"""
Newborns View
واجهة سجل المواليد
"""
from datetime import date, datetime, time
import streamlit as st
import pandas as pd

from core.db import db
from core.ui import page_header_v2, kpi_card_v2, empty_state, section_header_v2
from services.newborns import (
    create_newborn, list_newborns, get_newborn, update_newborn,
    delete_newborn, get_clinic_summary, get_mother_newborns,
    DELIVERY_TYPES, DELIVERY_PLACES, HEALTH_STATUS, GENDERS,
    get_delivery_type_label, get_delivery_place_label,
    get_health_status_label, get_gender_label,
    apgar_color, apgar_label,
)


# ============================================
# HELPERS
# ============================================

def _fetch_mothers(clinic_id):
    """Fetch active patients (mothers)"""
    try:
        return (
            db().table("patients")
            .select("id,full_name,phone,lmp,edd")
            .eq("clinic_id", clinic_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
            .data or []
        )
    except Exception:
        return []


def _format_date(v):
    if not v:
        return "—"
    return str(v)[:10]


def _format_weight(g):
    if not g:
        return "—"
    try:
        return "{:,} غرام".format(int(g))
    except Exception:
        return "—"


# ============================================
# TAB 1: LIST
# ============================================

def _render_list_tab(clinic, user):
    """List all newborns"""

    mothers = _fetch_mothers(clinic["id"])

    # Filters
    c1, c2, c3 = st.columns(3)

    with c1:
        mmap = {"": "الكل"}
        for m in mothers:
            mmap[m["id"]] = m.get("full_name", "—")

        mother_filter = st.selectbox(
            "الأم",
            options=list(mmap.keys()),
            format_func=lambda x: mmap[x],
            key="nb_mother_filter"
        )

    with c2:
        gender_filter = st.selectbox(
            "الجنس",
            options=["", "male", "female"],
            format_func=lambda x: "الكل" if x == "" else GENDERS[x],
            key="nb_gender_filter"
        )

    with c3:
        days = st.selectbox(
            "الفترة",
            options=[0, 30, 90, 365],
            format_func=lambda x: {
                0: "الكل",
                30: "آخر 30 يوم",
                90: "آخر 3 أشهر",
                365: "آخر سنة",
            }[x],
            key="nb_days_filter"
        )

    date_from = None
    if days > 0:
        date_from = date.today() - __import__("datetime").timedelta(days=days)

    # Fetch
    newborns = list_newborns(
        clinic["id"],
        mother_id=mother_filter if mother_filter else None,
        gender=gender_filter if gender_filter else None,
        date_from=date_from,
        limit=200,
    )

    if not newborns:
        empty_state(
            "👶",
            "لا توجد سجلات",
            "أضف أول ولادة من تبويب '➕ ولادة جديدة'"
        )
        return

    st.caption("📊 {} سجل".format(len(newborns)))
    st.write("")

    # Render cards
    for nb in newborns:
        gender_icon = "👦" if nb.get("gender") == "male" else "👧"
        health = nb.get("health_status", "healthy")
        health_color = {
            "healthy": "#10B981",
            "needs_care": "#F59E0B",
            "nicu": "#EF4444",
            "critical": "#DC2626",
        }.get(health, "#94A3B8")

        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                    padding:1rem 1.25rem;margin-bottom:0.5rem;
                    border-right:4px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:700;color:#0F172A;font-size:1.05rem;">
                        {icon} {baby_name}
                    </div>
                    <div style="color:#64748B;font-size:0.85rem;margin-top:0.35rem;">
                        👩 {mother} · 📅 {date} · 🏥 {delivery}
                    </div>
                </div>
                <div style="background:{color};color:white;padding:0.25rem 0.7rem;
                            border-radius:999px;font-size:0.72rem;font-weight:700;">
                    {health_label}
                </div>
            </div>
            <div style="display:flex;gap:1rem;margin-top:0.6rem;flex-wrap:wrap;">
                {details}
            </div>
        </div>
        """.format(
            color=health_color,
            icon=gender_icon,
            baby_name=nb.get("baby_name") or "مولود بدون اسم",
            mother=nb.get("_mother_name", "—"),
            date=_format_date(nb.get("delivery_date")),
            delivery=get_delivery_type_label(nb.get("delivery_type", "normal")),
            health_label=get_health_status_label(health),
            details="".join([
                '<span style="background:#F1F5F9;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.8rem;">⚖️ {}</span>'.format(_format_weight(nb.get("weight_grams"))) if nb.get("weight_grams") else "",
                '<span style="background:#F1F5F9;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.8rem;">📏 {} سم</span>'.format(nb.get("length_cm")) if nb.get("length_cm") else "",
                '<span style="background:#F1F5F9;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.8rem;">APGAR: {}</span>'.format(nb.get("apgar_5min")) if nb.get("apgar_5min") else "",
            ])
        ), unsafe_allow_html=True)

        # Actions
        c1, c2, c3, c4 = st.columns([1, 1, 1, 4])
        with c1:
            if st.button("📄", key="nb_cert_{}".format(nb["id"]),
                         help="شهادة ميلاد", use_container_width=True):
                st.session_state["nb_cert_id"] = nb["id"]
                st.rerun()
        with c2:
            if st.button("✏️", key="nb_edit_{}".format(nb["id"]),
                         help="تعديل", use_container_width=True):
                st.session_state["nb_edit_id"] = nb["id"]
                st.rerun()
        with c3:
            if st.button("🗑️", key="nb_del_{}".format(nb["id"]),
                         help="حذف", use_container_width=True):
                if st.session_state.get("nb_del_confirm") == nb["id"]:
                    delete_newborn(clinic["id"], nb["id"])
                    st.session_state.pop("nb_del_confirm", None)
                    st.success("🗑️ تم الحذف")
                    st.rerun()
                else:
                    st.session_state["nb_del_confirm"] = nb["id"]
                    st.warning("اضغط مرة أخرى للتأكيد")

        st.write("")


# ============================================
# TAB 2: ADD
# ============================================

def _render_add_tab(clinic, user):
    """Add new newborn"""

    mothers = _fetch_mothers(clinic["id"])
    if not mothers:
        empty_state("👩", "لا يوجد حوامل", "سجّل حاملاً أولاً")
        return

    mmap = {m["id"]: "{} — {}".format(m.get("full_name", ""), m.get("phone", "")) for m in mothers}

    st.markdown("#### 👶 تسجيل ولادة جديدة")

    # Select mother outside form (for reactivity)
    selected_mother = st.selectbox(
        "👩 الأم *",
        options=list(mmap.keys()),
        format_func=lambda x: mmap[x],
        key="nb_add_mother"
    )

    # Form
    with st.form("newborn_form", clear_on_submit=True):
        st.markdown("##### 📅 بيانات الولادة")

        c1, c2, c3 = st.columns(3)
        with c1:
            delivery_date = st.date_input(
                "تاريخ الولادة *",
                value=date.today(),
                max_value=date.today(),
                key="nb_del_date"
            )
        with c2:
            delivery_time = st.time_input(
                "الوقت",
                value=time(12, 0),
                key="nb_del_time"
            )
        with c3:
            delivery_type = st.selectbox(
                "نوع الولادة",
                options=list(DELIVERY_TYPES.keys()),
                format_func=lambda x: DELIVERY_TYPES[x],
                key="nb_del_type"
            )

        delivery_place = st.selectbox(
            "مكان الولادة",
            options=[""] + list(DELIVERY_PLACES.keys()),
            format_func=lambda x: "— اختر —" if x == "" else DELIVERY_PLACES[x],
            key="nb_del_place"
        )

        st.divider()
        st.markdown("##### 👶 بيانات المولود")

        c4, c5 = st.columns(2)
        with c4:
            baby_name = st.text_input(
                "اسم المولود",
                placeholder="اختياري — يمكن تركه فارغاً",
                key="nb_baby_name"
            )
        with c5:
            gender = st.radio(
                "الجنس *",
                options=["male", "female"],
                format_func=lambda x: GENDERS[x],
                horizontal=True,
                key="nb_gender"
            )

        c6, c7, c8 = st.columns(3)
        with c6:
            weight = st.number_input(
                "⚖️ الوزن (غرام)",
                min_value=500, max_value=6000,
                value=3200, step=50,
                key="nb_weight"
            )
        with c7:
            length = st.number_input(
                "📏 الطول (سم)",
                min_value=20.0, max_value=70.0,
                value=50.0, step=0.5,
                key="nb_length"
            )
        with c8:
            head_circ = st.number_input(
                "🧠 محيط الرأس (سم)",
                min_value=20.0, max_value=45.0,
                value=34.0, step=0.5,
                key="nb_head"
            )

        st.divider()
        st.markdown("##### 📊 APGAR Score (اختياري)")
        st.caption("0-10: 7+ طبيعي، 4-6 متوسط، 0-3 منخفض")

        c9, c10, c11 = st.columns(3)
        with c9:
            apgar_1 = st.number_input("1 دقيقة", min_value=0, max_value=10, value=0, key="nb_apgar1")
        with c10:
            apgar_5 = st.number_input("5 دقائق", min_value=0, max_value=10, value=0, key="nb_apgar5")
        with c11:
            apgar_10 = st.number_input("10 دقائق", min_value=0, max_value=10, value=0, key="nb_apgar10")

        st.divider()
        st.markdown("##### 💚 الحالة")

        c12, c13 = st.columns(2)
        with c12:
            health_status = st.selectbox(
                "الحالة الصحية",
                options=list(HEALTH_STATUS.keys()),
                format_func=lambda x: HEALTH_STATUS[x],
                key="nb_health"
            )
        with c13:
            complications = st.text_input(
                "مضاعفات (إن وجدت)",
                placeholder="اختياري",
                key="nb_complications"
            )

        notes = st.text_area(
            "ملاحظات",
            placeholder="أي ملاحظات إضافية...",
            height=80,
            key="nb_notes"
        )

        submitted = st.form_submit_button(
            "💾 حفظ الولادة",
            use_container_width=True,
            type="primary"
        )

    if submitted:
        try:
            data = {
                "delivery_date": delivery_date,
                "delivery_time": delivery_time.strftime("%H:%M") if delivery_time else None,
                "delivery_type": delivery_type,
                "delivery_place": delivery_place or None,
                "baby_name": baby_name or None,
                "gender": gender,
                "weight_grams": weight if weight > 0 else None,
                "length_cm": length if length > 0 else None,
                "head_circumference_cm": head_circ if head_circ > 0 else None,
                "apgar_1min": apgar_1 if apgar_1 > 0 else None,
                "apgar_5min": apgar_5 if apgar_5 > 0 else None,
                "apgar_10min": apgar_10 if apgar_10 > 0 else None,
                "health_status": health_status,
                "complications": complications or None,
                "notes": notes or None,
            }

            result = create_newborn(
                clinic_id=clinic["id"],
                mother_id=selected_mother,
                data=data,
                doctor_id=user.get("id") if user else None,
            )

            if result:
                # Audit log
                try:
                    from services.audit_log import log_action
                    log_action(
                        clinic_id=clinic["id"],
                        user_id=user.get("id") if user else None,
                        action="create",
                        entity_type="newborn",
                        entity_id=result.get("id"),
                        details={"baby_name": baby_name, "gender": gender, "weight": weight}
                    )
                except Exception:
                    pass

                st.success("✅ تم حفظ الولادة!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ فشل الحفظ")
        except Exception as e:
            st.error("❌ {}".format(str(e)[:200]))


# ============================================
# TAB 3: STATS
# ============================================

def _render_stats_tab(clinic, user):
    """Statistics"""

    summary = get_clinic_summary(clinic["id"])

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card_v2("👶", summary["total"], "إجمالي المواليد")
    with c2:
        kpi_card_v2("📅", summary["this_month"], "هذا الشهر")
    with c3:
        kpi_card_v2("👦", summary["males"], "ذكور")
    with c4:
        kpi_card_v2("👧", summary["females"], "إناث")
    with c5:
        kpi_card_v2("⚖️", "{:,}".format(summary["avg_weight"]), "متوسط الوزن (غ)")

    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        kpi_card_v2("🏥", "{}%".format(summary["c_section_pct"]), "نسبة القيصرية")
    with c2:
        cs = summary["c_section_count"]
        normal = summary["total"] - cs
        kpi_card_v2("🩺", "{} / {}".format(normal, cs), "طبيعية / قيصرية")

    st.divider()

    # Weight range
    if summary["total"] > 0:
        section_header_v2("⚖️", "نطاق الوزن")

        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                    padding:1rem 1.25rem;">
            <div style="display:flex;justify-content:space-between;">
                <div>
                    <div style="color:#64748B;font-size:0.8rem;">الحد الأدنى</div>
                    <div style="font-weight:700;color:#0F172A;font-size:1.1rem;">
                        {min:,} غرام
                    </div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#64748B;font-size:0.8rem;">المتوسط</div>
                    <div style="font-weight:700;color:#16A34A;font-size:1.1rem;">
                        {avg:,} غرام
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#64748B;font-size:0.8rem;">الحد الأقصى</div>
                    <div style="font-weight:700;color:#0F172A;font-size:1.1rem;">
                        {max:,} غرام
                    </div>
                </div>
            </div>
        </div>
        """.format(
            min=summary["min_weight"],
            avg=summary["avg_weight"],
            max=summary["max_weight"],
        ), unsafe_allow_html=True)

        st.divider()

    # Health status distribution
    section_header_v2("💚", "الحالة الصحية")

    status = summary.get("status_counts", {})
    if not status:
        st.info("لا توجد بيانات")
    else:
        for s, count in sorted(status.items(), key=lambda x: -x[1]):
            label = HEALTH_STATUS.get(s, s)
            st.markdown("""
            <div style="display:flex;justify-content:space-between;
                        padding:0.5rem 0.85rem;border-bottom:1px solid #F1F5F9;">
                <span>{label}</span>
                <span style="font-weight:700;color:#0F172A;">{count}</span>
            </div>
            """.format(label=label, count=count), unsafe_allow_html=True)


# ============================================
# MAIN RENDER
# ============================================

def render(clinic, user):
    """Main render"""
    page_header_v2(
        title="سجل المواليد",
        subtitle="تسجيل ومتابعة مواليد العيادة",
        icon="👶",
    )

    # Modals for edit/cert (handled by other components)
    if st.session_state.get("nb_edit_id"):
        _render_edit_modal(clinic, user)
    if st.session_state.get("nb_cert_id"):
        _render_cert_modal(clinic, user)

    tab1, tab2, tab3 = st.tabs([
        "📋 القائمة",
        "➕ ولادة جديدة",
        "📊 إحصائيات",
    ])

    with tab1:
        _render_list_tab(clinic, user)
    with tab2:
        _render_add_tab(clinic, user)
    with tab3:
        _render_stats_tab(clinic, user)


def _render_edit_modal(clinic, user):
    nb_id = st.session_state.get("nb_edit_id")
    nb = get_newborn(clinic["id"], nb_id)
    if not nb:
        st.session_state.pop("nb_edit_id", None)
        return

    with st.expander("✏️ تعديل بيانات المولود", expanded=True):
        with st.form("edit_newborn"):
            c1, c2 = st.columns(2)
            with c1:
                baby_name = st.text_input("اسم المولود", value=nb.get("baby_name") or "")
            with c2:
                weight = st.number_input("الوزن (غ)", min_value=500, max_value=6000,
                    value=int(nb.get("weight_grams") or 3200), step=50)

            c3, c4 = st.columns(2)
            with c3:
                health = st.selectbox("الحالة",
                    options=list(HEALTH_STATUS.keys()),
                    index=list(HEALTH_STATUS.keys()).index(nb.get("health_status", "healthy")),
                    format_func=lambda x: HEALTH_STATUS[x])
            with c4:
                delivery_type = st.selectbox("نوع الولادة",
                    options=list(DELIVERY_TYPES.keys()),
                    index=list(DELIVERY_TYPES.keys()).index(nb.get("delivery_type", "normal")),
                    format_func=lambda x: DELIVERY_TYPES[x])

            notes = st.text_area("ملاحظات", value=nb.get("notes") or "", height=80)

            c5, c6 = st.columns(2)
            with c5:
                save = st.form_submit_button("💾 حفظ", type="primary", use_container_width=True)
            with c6:
                cancel = st.form_submit_button("❌ إلغاء", use_container_width=True)

            if save:
                try:
                    update_newborn(clinic["id"], nb_id,
                        baby_name=baby_name or None,
                        weight_grams=weight,
                        health_status=health,
                        delivery_type=delivery_type,
                        notes=notes or None,
                    )
                    st.session_state.pop("nb_edit_id", None)
                    st.success("✅ تم الحفظ")
                    st.rerun()
                except Exception as e:
                    st.error("❌ {}".format(str(e)[:150]))

            if cancel:
                st.session_state.pop("nb_edit_id", None)
                st.rerun()


def _render_cert_modal(clinic, user):
    """Generate birth certificate PDF"""
    nb_id = st.session_state.get("nb_cert_id")
    nb = get_newborn(clinic["id"], nb_id)
    if not nb:
        st.session_state.pop("nb_cert_id", None)
        return

    with st.expander("📄 شهادة ميلاد", expanded=True):
        st.info("👶 سيتم إنشاء شهادة ميلاد رسمية PDF")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 توليد الشهادة", type="primary", use_container_width=True,
                         key="nb_gen_cert"):
                with st.spinner("⏳ جاري التوليد..."):
                    try:
                        from services.newborn_certificate_pdf import generate_birth_certificate
                        # Fetch mother info
                        mom_rows = db().table("patients").select("*").eq("id", nb["mother_id"]).limit(1).execute().data
                        mom = mom_rows[0] if mom_rows else {}

                        pdf = generate_birth_certificate(nb, mom, clinic, user.get("full_name", "") if user else "")
                        st.session_state["_nb_cert_pdf"] = pdf
                        st.session_state["_nb_cert_name"] = "birth_cert_{}.pdf".format(str(nb_id)[:8])
                        st.success("✅ جاهزة!")
                        st.rerun()
                    except Exception as e:
                        st.error("❌ {}".format(str(e)[:200]))

        with c2:
            if st.button("❌ إغلاق", use_container_width=True, key="nb_close_cert"):
                st.session_state.pop("nb_cert_id", None)
                st.rerun()

        if "_nb_cert_pdf" in st.session_state:
            pdf = st.session_state["_nb_cert_pdf"]
            st.download_button(
                "⬇️ تحميل PDF",
                data=pdf,
                file_name=st.session_state.get("_nb_cert_name", "cert.pdf"),
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="nb_download_cert"
            )
