# -*- coding: utf-8 -*-
import streamlit as st
from services.patients import get_patient_summary_cached
from services.visits import list_visits_cached, analyze_bp


def render(clinic, user):
    """Render visits history tab"""
    st.markdown("### 🩺 تاريخ الزيارات والقياسات")

    pid = st.session_state.get("selected_patient_id")
    if not pid:
        st.info("👉 اختر حاملاً من تبويب **👩 الحوامل** أولاً")
        return

    p = get_patient_summary_cached(clinic["id"], pid)
    if not p:
        st.info("👉 اختر حاملاً من تبويب **👩 الحوامل** أولاً")
        return

    st.caption("الحامل: **{}** — {}".format(p["full_name"], p["gestational_display"]))

    visits = list_visits_cached(clinic["id"], pid, limit=100)

    if not visits:
        st.info("لا توجد زيارات بعد. اذهب لتبويب **👩 الحوامل** → افتح الملف → زيارة جديدة")
        return

    import pandas as pd
    import plotly.express as px

    st.metric("إجمالي الزيارات", len(visits))
    st.divider()

    df = pd.DataFrame(visits)
    df["visit_date"] = pd.to_datetime(df["visit_date"])
    df = df.sort_values("visit_date")

    tab_w, tab_bp, tab_f, tab_t = st.tabs(["📈 الوزن", "💓 الضغط", "👶 الجنين", "📋 الجدول"])

    with tab_w:
        if df["weight_kg"].notna().any():
            wdf = df[df["weight_kg"].notna()][["visit_date", "weight_kg"]]
            fig = px.line(wdf, x="visit_date", y="weight_kg", markers=True,
                labels={"visit_date": "التاريخ", "weight_kg": "الوزن (كغ)"})
            fig.update_traces(line_color="#0EA5A0", marker_size=10)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد قياسات وزن")

    with tab_bp:
        bpdf = df[df["bp_systolic"].notna() & df["bp_diastolic"].notna()]
        if not bpdf.empty:
            bplong = bpdf[["visit_date", "bp_systolic", "bp_diastolic"]].melt(
                id_vars=["visit_date"], var_name="type", value_name="value")
            bplong["type"] = bplong["type"].map(
                {"bp_systolic": "انقباضي", "bp_diastolic": "انبساطي"})
            fig = px.line(bplong, x="visit_date", y="value", color="type", markers=True,
                labels={"visit_date": "التاريخ", "value": "mmHg", "type": "النوع"})
            fig.add_hline(y=140, line_dash="dash", line_color="red",
                annotation_text="حد الخطر 140")
            st.plotly_chart(fig, use_container_width=True)

            last = df.iloc[-1]
            if pd.notna(last["bp_systolic"]):
                a = analyze_bp(int(last["bp_systolic"]), int(last["bp_diastolic"]))
                if a:
                    if a["level"] == "high":
                        st.error("🚨 آخر قياس: {}".format(a["label"]))
                    elif a["level"] == "normal":
                        st.success("آخر قياس: {}".format(a["label"]))
                    else:
                        st.warning("آخر قياس: {}".format(a["label"]))
        else:
            st.info("لا توجد قياسات ضغط")

    with tab_f:
        c1, c2 = st.columns(2)
        with c1:
            fdf = df[df["fetal_heart_rate"].notna()]
            if not fdf.empty:
                fig = px.line(fdf, x="visit_date", y="fetal_heart_rate", markers=True,
                    labels={"visit_date": "التاريخ", "fetal_heart_rate": "bpm"})
                fig.update_traces(line_color="#E91E63", marker_size=10)
                fig.add_hrect(y0=110, y1=160, fillcolor="green",
                    opacity=0.1, annotation_text="النطاق الطبيعي")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("لا توجد قياسات نبض")
        with c2:
            hdf = df[df["fundal_height_cm"].notna()]
            if not hdf.empty:
                fig = px.line(hdf, x="visit_date", y="fundal_height_cm", markers=True,
                    labels={"visit_date": "التاريخ", "fundal_height_cm": "سم"})
                fig.update_traces(line_color="#00ACC1", marker_size=10)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("لا توجد قياسات ارتفاع")

    with tab_t:
        cols = {
            "visit_date": "التاريخ",
            "weight_kg": "الوزن",
            "bp_systolic": "انقباضي",
            "bp_diastolic": "انبساطي",
            "fetal_heart_rate": "نبض",
            "fundal_height_cm": "ارتفاع",
            "notes": "ملاحظات"
        }
        tdf = df[[c for c in cols.keys() if c in df.columns]].copy()
        tdf.columns = [cols[c] for c in tdf.columns]
        if "التاريخ" in tdf.columns:
            tdf["التاريخ"] = pd.to_datetime(tdf["التاريخ"]).dt.strftime("%Y-%m-%d")
        st.dataframe(tdf, use_container_width=True, hide_index=True)

        csv = tdf.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 تحميل CSV", csv, "visits.csv", "text/csv")
