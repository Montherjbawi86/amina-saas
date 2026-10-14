# -*- coding: utf-8 -*-
"""
Print Mode — وضع الطباعة
يحوّل الصفحة إلى تنسيق مناسب للطباعة (A4)
"""
import streamlit as st


def is_print_mode():
    """Check if print mode is active"""
    return st.session_state.get("_print_mode", False)


def enable_print_mode():
    """Activate print mode"""
    st.session_state["_print_mode"] = True


def disable_print_mode():
    """Deactivate print mode"""
    st.session_state["_print_mode"] = False


def toggle_print_mode():
    """Toggle print mode"""
    st.session_state["_print_mode"] = not st.session_state.get("_print_mode", False)


def inject_print_css():
    """Inject CSS that hides UI chrome when printing"""
    st.markdown("""
    <style>
    /* ============ PRINT MODE ============ */
    @media print {
        /* Hide Streamlit chrome */
        header[data-testid="stHeader"] { display: none !important; }
        #MainMenu, footer { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stDeployButton { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }

        /* Hide buttons, forms, inputs */
        .stButton, .stDownloadButton, .stFormSubmitButton,
        .stLinkButton, .stForm, .stTextInput, .stNumberInput,
        .stTextArea, .stSelectbox, .stMultiSelect, .stFileUploader,
        [data-testid="stFileUploaderDropzone"] {
            display: none !important;
        }

        /* Hide tabs (they'd be useless in print) */
        .stTabs [data-baseweb="tab-list"] { display: none !important; }

        /* Full width for content */
        .main .block-container {
            padding: 0.5cm 1cm !important;
            max-width: 100% !important;
        }

        /* Body background */
        body, .stApp {
            background: white !important;
        }

        /* Bigger fonts for readability */
        body {
            font-size: 11pt !important;
        }
        h1 { font-size: 18pt !important; }
        h2 { font-size: 14pt !important; }
        h3 { font-size: 12pt !important; }

        /* Avoid page breaks inside cards */
        .kpi-card-v2, .glass-card, .info-card, .patient-card,
        .empty-state, table, tr {
            page-break-inside: avoid !important;
        }

        /* Cards: solid border for print */
        .kpi-card-v2, .glass-card {
            box-shadow: none !important;
            border: 1px solid #94A3B8 !important;
        }

        /* Print header (only visible in print) */
        .print-header { display: block !important; }

        /* Print footer */
        .print-footer { display: block !important; }

        /* Hide on-screen only elements */
        .no-print { display: none !important; }
    }

    /* ============ PRINT MODE (screen preview) ============ */
    .print-mode-active .main .block-container {
        max-width: 21cm !important;
        margin: 0 auto !important;
        background: white !important;
        padding: 1.5cm 1.5cm !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.1) !important;
        border-radius: 4px !important;
    }
    .print-mode-active section[data-testid="stSidebar"] {
        display: none !important;
    }
    .print-mode-active header[data-testid="stHeader"] {
        display: none !important;
    }
    .print-mode-active .stButton,
    .print-mode-active .stDownloadButton,
    .print-mode-active .stFormSubmitButton,
    .print-mode-active .stLinkButton,
    .print-mode-active .stForm,
    .print-mode-active .stTextInput,
    .print-mode-active .stNumberInput,
    .print-mode-active .stTextArea,
    .print-mode-active .stSelectbox,
    .print-mode-active .stMultiSelect,
    .print-mode-active .stFileUploader {
        display: none !important;
    }
    .print-mode-active .stTabs [data-baseweb="tab-list"] {
        display: none !important;
    }

    /* Print header (hidden on screen, visible on print) */
    .print-header {
        display: none;
        text-align: center;
        padding: 0.5cm 0 0.5cm 0;
        border-bottom: 2px solid #16A34A;
        margin-bottom: 1cm;
    }
    .print-header .ph-clinic {
        font-size: 14pt;
        font-weight: 800;
        color: #0F172A;
    }
    .print-header .ph-meta {
        font-size: 9pt;
        color: #64748B;
        margin-top: 0.2cm;
    }
    .print-footer {
        display: none;
        text-align: center;
        padding: 0.5cm 0 0 0;
        margin-top: 1cm;
        border-top: 1px solid #E2E8F0;
        font-size: 8pt;
        color: #94A3B8;
    }

    /* Print preview banner (visible only in print mode) */
    .print-preview-banner {
        background: #FEF3C7;
        border: 1px solid #FDE68A;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.85rem;
        color: #92400E;
    }
    </style>
    """, unsafe_allow_html=True)


def inject_print_mode_class():
    """Add print-mode class to body if active (screen preview)"""
    if is_print_mode():
        st.markdown("""
        <script>
        (function() {
            const app = window.parent.document.querySelector('.stApp');
            if (app) app.classList.add('print-mode-active');
        })();
        </script>
        """, unsafe_allow_html=True)


def render_print_controls(clinic=None, user=None, title=None):
    """
    Render print controls (top-right): Print mode toggle + Print button.
    Call this on any page that wants print support.
    """
    # Inject CSS once
    inject_print_css()
    inject_print_mode_class()

    # Controls (hidden in print mode itself)
    c1, c2, c3 = st.columns([6, 1, 1])
    with c2:
        if is_print_mode():
            if st.button("❌ إلغاء الطباعة", key="print_cancel", use_container_width=True):
                disable_print_mode()
                st.rerun()
        else:
            if st.button("🖨️ طباعة", key="print_start", use_container_width=True):
                enable_print_mode()
                st.rerun()

    with c3:
        if is_print_mode():
            # Browser print button (uses window.print via JS)
            st.markdown("""
            <button onclick="window.parent.print()" 
                    style="width:100%; background:#16A34A; color:white; border:none;
                           border-radius:8px; padding:0.5rem; font-weight:700;
                           font-size:0.85rem; cursor:pointer;">
                🖨️ اطبع الآن
            </button>
            """, unsafe_allow_html=True)

    # Print header (visible only when printing)
    if is_print_mode() and clinic:
        _render_print_header(clinic, user, title)


def _render_print_header(clinic, user, title=None):
    """Print header (clinic name + date + title)"""
    from datetime import date
    clinic_name = clinic.get("name", "العيادة")
    doctor_name = user.get("full_name", "") if user else ""

    title_html = ""
    if title:
        title_html = '<div style="font-size:12pt; font-weight:700; color:#16A34A; margin-top:0.3cm;">{}</div>'.format(title)

    st.markdown("""
    <div class="print-header">
        <div class="ph-clinic">🏥 {clinic}</div>
        <div class="ph-meta">
            {doctor} &nbsp;|&nbsp; 📅 {date}
        </div>
        {title}
    </div>
    """.format(
        clinic=clinic_name,
        doctor="د. " + doctor_name if doctor_name else "",
        date=date.today().strftime("%Y-%m-%d"),
        title=title_html,
    ), unsafe_allow_html=True)


def render_print_footer():
    """Print footer (page info + branding)"""
    if is_print_mode():
        from datetime import date
        st.markdown("""
        <div class="print-footer">
            أمينة SaaS — نظام إدارة عيادات النساء والولادة &nbsp;|&nbsp;
            © {year} &nbsp;|&nbsp; طُبع في {date}
        </div>
        """.format(
            year=date.today().year,
            date=date.today().strftime("%Y-%m-%d %H:%M"),
        ), unsafe_allow_html=True)


def print_button_only():
    """Just a print button (for pages that already have header)"""
    if is_print_mode():
        c1, c2, c3 = st.columns([7, 1, 1])
        with c2:
            if st.button("❌ إلغاء", key="pbtn_cancel", use_container_width=True):
                disable_print_mode()
                st.rerun()
        with c3:
            st.markdown("""
            <button onclick="window.parent.print()" 
                    style="width:100%; background:#16A34A; color:white; border:none;
                           border-radius:8px; padding:0.5rem; font-weight:700;
                           font-size:0.85rem; cursor:pointer;">
                🖨️ اطبع
            </button>
            """, unsafe_allow_html=True)
    else:
        c1, c2, c3 = st.columns([8, 1, 1])
        with c3:
            if st.button("🖨️ طباعة", key="pbtn_start", use_container_width=True):
                enable_print_mode()
                st.rerun()


if __name__ == "__main__":
    print("=" * 50)
    print("Print Mode Module")
    print("=" * 50)
    print("✅ Module loads OK")
    print("")
    print("Functions:")
    print("  - is_print_mode()")
    print("  - enable_print_mode()")
    print("  - disable_print_mode()")
    print("  - toggle_print_mode()")
    print("  - render_print_controls(clinic, user, title)")
    print("  - render_print_footer()")
    print("  - print_button_only()")
    print("=" * 50)
