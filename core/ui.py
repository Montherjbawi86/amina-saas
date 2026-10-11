# -*- coding: utf-8 -*-
"""Modern Medical SaaS — Blue theme"""
import streamlit as st


COLORS = {
    "primary":       "#16A34A",
    "primary_dark":  "#166534",
    "primary_soft":  "#F0FDF4",
    "primary_hover": "#15803D",

    "success": "#10B981",
    "warning": "#F59E0B",
    "danger":  "#EF4444",
    "info":    "#22C55E",

    "bg":        "#F8FAFC",
    "card":      "#FFFFFF",
    "border":    "#E2E8F0",
    "text":      "#0F172A",
    "text_muted": "#64748B",
}

RISK_COLORS = {
    "low":    {"bg": "#ECFDF5", "fg": "#047857", "icon": "🟢", "label": "منخفض"},
    "medium": {"bg": "#FFFBEB", "fg": "#B45309", "icon": "🟡", "label": "متوسط"},
    "high":   {"bg": "#FEF2F2", "fg": "#B91C1C", "icon": "🔴", "label": "عالي"},
}


def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* { font-family: 'Inter', -apple-system, 'SF Pro Display', system-ui, sans-serif !important; }

.main .block-container {
    padding: 1.5rem 2rem 3rem 2rem;
    max-width: 1500px;
}

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stSidebarNav"] { display: none !important; }

.stApp { background: #F8FAFC; }

h1, h2, h3, h4 {
    color: #0F172A;
    font-weight: 700;
    letter-spacing: -0.02em;
}
h1 { font-size: 1.6rem !important; margin: 0 0 0.5rem 0 !important; font-weight: 800; }
h2 { font-size: 1.25rem !important; margin: 1.25rem 0 0.75rem 0 !important; }
h3 { font-size: 1.05rem !important; font-weight: 600; }

p, li { color: #334155; line-height: 1.6; }

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    border: 1px solid #E2E8F0 !important;
    background: #FFFFFF !important;
    color: #334155 !important;
    padding: 0.5rem 0.9rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    border-color: #16A34A !important;
    color: #16A34A !important;
    background: #F8FAFC !important;
    box-shadow: 0 2px 8px rgba(22, 163, 74, 0.08) !important;
}
.stButton > button[kind="primary"] {
    background: #16A34A !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 2px 6px rgba(22, 163, 74, 0.24) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #15803D !important;
    box-shadow: 0 4px 14px rgba(22, 163, 74, 0.32) !important;
    color: white !important;
}

.stLinkButton > a {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    text-decoration: none !important;
    padding: 0.5rem 0.9rem !important;
    border: 1px solid #E2E8F0 !important;
    background: white !important;
    color: #334155 !important;
    transition: all 0.15s ease !important;
}
.stLinkButton > a:hover {
    border-color: #16A34A !important;
    color: #16A34A !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    background: #FFFFFF !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 0.75rem !important;
    transition: all 0.15s ease !important;
    color: #0F172A !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #16A34A !important;
    box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1) !important;
    outline: none !important;
}

.stSelectbox > div > div > div {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    background: white !important;
    font-size: 0.9rem !important;
}

.stTextInput > label, .stNumberInput > label, .stSelectbox > label,
.stTextArea > label, .stDateInput > label, .stTimeInput > label {
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    color: #475569 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    background: #FFFFFF !important;
    padding: 4px !important;
    border-radius: 10px !important;
    border: 1px solid #E2E8F0 !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 600 !important;
    padding: 8px 14px !important;
    color: #64748B !important;
    font-size: 0.85rem !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #16A34A !important;
    background: #F8FAFC !important;
}
.stTabs [aria-selected="true"] {
    background: #F0FDF4 !important;
    color: #16A34A !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: white;
    padding: 0.9rem 1rem;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
[data-testid="stMetricValue"] {
    color: #0F172A;
    font-weight: 700;
    font-size: 1.4rem;
}
[data-testid="stMetricLabel"] {
    color: #64748B;
    font-weight: 500;
    font-size: 0.78rem;
}

/* KPI Card */
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    display: flex;
    align-items: center;
    gap: 0.85rem;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    transition: all 0.15s ease;
    height: 100%;
}
.kpi-card:hover {
    border-color: #CBD5E1;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}
.kpi-icon {
    font-size: 1.4rem;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    background: #F0FDF4;
    flex-shrink: 0;
}
.kpi-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.1;
    margin: 0;
}
.kpi-label {
    font-size: 0.75rem;
    color: #64748B;
    font-weight: 500;
    margin-top: 0.2rem;
}

/* Patient Card */
.patient-card {
    background: white;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border: 1px solid #E2E8F0;
    border-right: 3px solid #16A34A;
    transition: all 0.15s ease;
}
.patient-card:hover {
    border-color: #16A34A;
    box-shadow: 0 2px 8px rgba(22, 163, 74, 0.08);
}
.patient-card.risk-low { border-right-color: #10B981; }
.patient-card.risk-medium { border-right-color: #F59E0B; }
.patient-card.risk-high { border-right-color: #EF4444; }

/* Badges */
.status-badge {
    display: inline-block;
    padding: 0.22rem 0.6rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-low { background: #ECFDF5; color: #047857; }
.badge-medium { background: #FFFBEB; color: #B45309; }
.badge-high { background: #FEF2F2; color: #B91C1C; }
.badge-info { background: #F0FDF4; color: #166534; }

/* Risk Banner */
.risk-banner {
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border: 1px solid;
}
.risk-banner.risk-low { background: #ECFDF5; border-color: #A7F3D0; }
.risk-banner.risk-medium { background: #FFFBEB; border-color: #FDE68A; }
.risk-banner.risk-high { background: #FEF2F2; border-color: #FECACA; }

/* Hero */
.hero {
    background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    color: white;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(22, 163, 74, 0.2);
}
.hero h1 { color: white !important; font-size: 2rem !important; margin: 0 !important; }
.hero p { color: rgba(255,255,255,0.95); margin-top: 0.5rem; }

/* Concern */
.concern-item {
    background: white;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.5rem;
    border: 1px solid #E2E8F0;
    border-right: 3px solid #CBD5E1;
}
.concern-item.sev-high { border-right-color: #EF4444; }
.concern-item.sev-medium { border-right-color: #F59E0B; }
.concern-item.sev-low { border-right-color: #F97316; }

.recommendation {
    background: #F0FDF4;
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.4rem;
    border-right: 3px solid #16A34A;
    font-size: 0.9rem;
    color: #14532D;
}
.positive-item {
    background: #ECFDF5;
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.4rem;
    border-right: 3px solid #10B981;
    font-size: 0.9rem;
    color: #047857;
}

.stAlert { border-radius: 10px !important; }

.streamlit-expanderHeader {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    background: white !important;
    border: 1px solid #E2E8F0 !important;
}
.streamlit-expanderHeader:hover {
    border-color: #16A34A !important;
    color: #16A34A !important;
}

[data-testid="stForm"] { border: none; padding: 0; }

hr { border-color: #E2E8F0 !important; margin: 1.25rem 0 !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-left: 1px solid #E2E8F0 !important;
}
section[data-testid="stSidebar"] > div { padding-top: 1rem; }

section[data-testid="stSidebar"] .stButton > button {
    text-align: right !important;
    justify-content: flex-start !important;
    padding: 0.55rem 0.85rem !important;
    background: transparent !important;
    color: #334155 !important;
    border: 1px solid transparent !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #F1F5F9 !important;
    color: #16A34A !important;
    border-color: transparent !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #F0FDF4 !important;
    color: #16A34A !important;
    border: none !important;
    box-shadow: none !important;
    font-weight: 600 !important;
}

section[data-testid="stSidebar"] h3 {
    font-size: 0.72rem !important;
    color: #94A3B8 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 1rem !important;
    margin-bottom: 0.4rem !important;
    font-weight: 700 !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F1F5F9; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
/* ============ NUCLEAR PRIMARY BUTTON FIX ============ */
    /* Force white text on ALL primary buttons */
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:focus,
    .stButton > button[kind="primary"]:active,
    .stButton > button[kind="primary"]:visited {
        color: #FFFFFF !important;
        background-color: #16A34A !important;
        font-weight: 700 !important;
    }

    /* ALL descendants */
    .stButton > button[kind="primary"] *,
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span,
    .stButton > button[kind="primary"] div,
    .stButton > button[kind="primary"] svg,
    .stButton > button[kind="primary"] i {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Streamlit's internal wrappers */
    .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"],
    .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] *,
    .stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Hover state */
    .stButton > button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover * {
        color: #FFFFFF !important;
        background-color: #15803D !important;
    }

    /* Link buttons (styled as primary) */
    .stLinkButton > a[data-testid="stBaseLinkButton-primary"],
    .stLinkButton > a[data-testid="stBaseLinkButton-primary"] *,
    .stLinkButton > a[data-testid="stBaseLinkButton-primary"] p,
    .stLinkButton > a[data-testid="stBaseLinkButton-primary"] span {
        color: #FFFFFF !important;
        background-color: #16A34A !important;
        font-weight: 700 !important;
    }

    /* Download button primary */
    .stDownloadButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] *,
    .stDownloadButton > button[kind="primary"] p,
    .stDownloadButton > button[kind="primary"] span {
        color: #FFFFFF !important;
        background-color: #16A34A !important;
        font-weight: 700 !important;
    }

    /* Form submit button (primary) */
    [data-testid="stFormSubmitButton"] button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] *,
    [data-testid="stFormSubmitButton"] button[kind="primary"] p,
    [data-testid="stFormSubmitButton"] button[kind="primary"] span {
        color: #FFFFFF !important;
        background-color: #16A34A !important;
        font-weight: 700 !important;
    }

    /* Global anti-black override inside any primary button */
    button[kind="primary"] {
        color: #FFFFFF !important;
    }
    button[kind="primary"] > * {
        color: #FFFFFF !important;
    }
    button[kind="primary"] > * > * {
        color: #FFFFFF !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #16A34A !important;
        box-shadow: 0 1px 3px rgba(15,23,42,0.08) !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span {
        color: #16A34A !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #475569 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
    }


    /* ============ TABS BLUE VARIANT ============ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background: #F1F5F9 !important;
        padding: 5px !important;
        border-radius: 10px !important;
        border: 1px solid #E2E8F0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 18px !important;
        color: #475569 !important;
        font-size: 0.95rem !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #16A34A !important;
        background: #FFFFFF !important;
    }

    /* ACTIVE: blue bg + white text */
    .stTabs [aria-selected="true"],
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #16A34A !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(22, 163, 74, 0.25) !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] div,
    .stTabs [aria-selected="true"] svg {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        font-weight: 700 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }


    /* ============ SIDEBAR ACTIVE ITEM ============ */
    /* Active sidebar button: blue bg + white text (high contrast) */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #16A34A !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(22, 163, 74, 0.25) !important;
        font-weight: 700 !important;
    }

    /* Force ALL descendants to white */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] span,
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] div {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Hover state */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #15803D !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover * {
        color: #FFFFFF !important;
    }

    /* ============ TOP TABS ACTIVE ============ */
    /* Active tab: white bg + blue text (clean) */
    .stTabs [aria-selected="true"],
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #FFFFFF !important;
        color: #16A34A !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1) !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] div {
        color: #16A34A !important;
        font-weight: 700 !important;
        background: transparent !important;
    }

    /* Non-active tabs: gray on light */
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) {
        color: #64748B !important;
        background: transparent !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {
        color: #16A34A !important;
        background: #F8FAFC !important;
    }
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) *,
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) p,
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) span {
        color: #64748B !important;
        font-weight: 600 !important;
    }

    /* Hide tab highlight */
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }


    /* ============ BUTTON WRAP FIX ============ */
    /* Prevent text wrapping in 3 lines */
    .stButton > button {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        min-height: 2.5rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        white-space: nowrap !important;
        line-height: 1 !important;
        overflow: visible !important;
    }

    /* Better column ratio for filters */
    [data-testid="stHorizontalBlock"] {
        gap: 0.75rem !important;
    }


    /* ============ FOREST GREEN BUTTONS — WHITE TEXT ============ */
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:focus,
    .stButton > button[kind="primary"]:active {
        background-color: #16A34A !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(22, 163, 74, 0.24) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #15803D !important;
        box-shadow: 0 4px 14px rgba(22, 163, 74, 0.32) !important;
    }
    .stButton > button[kind="primary"] *,
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span,
    .stButton > button[kind="primary"] div {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Sidebar primary (active nav) */
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #16A34A !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(22, 163, 74, 0.25) !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"] *,
    section[data-testid="stSidebar"] button[kind="primary"] p,
    section[data-testid="stSidebar"] button[kind="primary"] span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Tabs active */
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #16A34A !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span {
        color: #16A34A !important;
        font-weight: 700 !important;
    }

    /* Focus rings green */
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #16A34A !important;
        box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1) !important;
    }

    /* Progress bar green */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #16A34A 0%, #22C55E 100%) !important;
    }

    /* Hero green */
    .hero {
        background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%) !important;
        box-shadow: 0 10px 30px rgba(22, 163, 74, 0.2) !important;
    }


    /* ============ ADVANCED ANIMATIONS ============ */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeInLeft {
        from { opacity: 0; transform: translateX(-40px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeInRight {
        from { opacity: 0; transform: translateX(40px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes scaleIn {
        from { opacity: 0; transform: scale(0.85); }
        to { opacity: 1; transform: scale(1); }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
        40% { transform: translateY(-10px); }
        60% { transform: translateY(-5px); }
    }
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    @keyframes slideInUp {
        from { opacity: 0; transform: translateY(60px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes heartbeat {
        0%, 100% { transform: scale(1); }
        10%, 30% { transform: scale(1.1); }
        20%, 40% { transform: scale(1); }
    }

    /* Hero enhancements */
    .hero {
        background: linear-gradient(135deg, #16A34A 0%, #22C55E 25%, #4ADE80 50%, #22C55E 75%, #16A34A 100%) !important;
        background-size: 200% 200% !important;
        animation: gradientShift 8s ease infinite, fadeInUp 0.8s ease-out !important;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%);
        animation: rotate 30s linear infinite;
        pointer-events: none;
    }
    .hero::after {
        content: '';
        position: absolute;
        bottom: -100px;
        left: -100px;
        width: 200px;
        height: 200px;
        background: rgba(255,255,255,0.08);
        border-radius: 50%;
        animation: float 6s ease-in-out infinite;
        pointer-events: none;
    }
    .hero > * {
        animation: fadeInUp 1s ease-out;
        animation-fill-mode: both;
    }
    .hero > *:nth-child(1) { animation-delay: 0.1s; }
    .hero > *:nth-child(2) { animation-delay: 0.2s; }
    .hero > *:nth-child(3) { animation-delay: 0.3s; }

    /* Feature cards */
    .feature-card {
        background: white;
        border-radius: 16px;
        padding: 1.75rem 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: fadeInUp 0.6s ease-out;
        animation-fill-mode: both;
        position: relative;
        overflow: hidden;
    }
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #16A34A 0%, #22C55E 100%);
        transform: scaleX(0);
        transform-origin: right;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 40px rgba(22, 163, 74, 0.15);
        border-color: #86EFAC;
    }
    .feature-card:hover::before {
        transform: scaleX(1);
    }
    .feature-card:nth-child(1) { animation-delay: 0.1s; }
    .feature-card:nth-child(2) { animation-delay: 0.2s; }
    .feature-card:nth-child(3) { animation-delay: 0.3s; }
    .feature-card:nth-child(4) { animation-delay: 0.4s; }

    .feature-icon {
        font-size: 2rem;
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 14px;
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    .feature-card:hover .feature-icon {
        transform: scale(1.1) rotate(-3deg);
    }

    .feature-title {
        font-weight: 700;
        font-size: 1.1rem;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        color: #64748B;
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* Stats section */
    .stat-box {
        text-align: center;
        padding: 1.5rem 1rem;
        background: white;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        transition: all 0.3s ease;
        animation: scaleIn 0.5s ease-out;
        animation-fill-mode: both;
    }
    .stat-box:hover {
        transform: scale(1.05);
        border-color: #16A34A;
        box-shadow: 0 8px 24px rgba(22, 163, 74, 0.15);
    }
    .stat-box:nth-child(1) { animation-delay: 0.1s; }
    .stat-box:nth-child(2) { animation-delay: 0.2s; }
    .stat-box:nth-child(3) { animation-delay: 0.3s; }
    .stat-box:nth-child(4) { animation-delay: 0.4s; }

    .stat-number {
        font-size: 2.25rem;
        font-weight: 800;
        background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1;
        margin-bottom: 0.4rem;
    }
    .stat-label {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* CTA section */
    .cta-section {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        text-align: center;
        border: 2px dashed #86EFAC;
        animation: fadeInUp 0.8s ease-out;
        margin: 2rem 0;
    }
    .cta-section h2 {
        color: #15803D !important;
        margin-bottom: 0.75rem !important;
    }
    .cta-section p {
        color: #475569;
        margin-bottom: 1.25rem;
    }

    /* Pulsing dot */
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        margin-right: 0.4rem;
        animation: pulse 1.5s ease-in-out infinite;
    }

    /* Floating badge */
    .floating-badge {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: #22C55E;
        color: white;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        animation: float 3s ease-in-out infinite;
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
    }

    /* Heartbeat icon */
    .heartbeat {
        animation: heartbeat 1.5s ease-in-out infinite;
        display: inline-block;
    }

    /* Bounce arrow */
    .bounce-arrow {
        display: inline-block;
        animation: bounce 2s infinite;
    }

    /* Fade in class utilities */
    .fade-in { animation: fadeIn 0.6s ease-out; }
    .fade-up { animation: fadeInUp 0.6s ease-out; }
    .fade-left { animation: fadeInLeft 0.6s ease-out; }
    .fade-right { animation: fadeInRight 0.6s ease-out; }

    /* Delay utilities */
    .delay-1 { animation-delay: 0.1s; animation-fill-mode: both; }
    .delay-2 { animation-delay: 0.2s; animation-fill-mode: both; }
    .delay-3 { animation-delay: 0.3s; animation-fill-mode: both; }
    .delay-4 { animation-delay: 0.4s; animation-fill-mode: both; }
    .delay-5 { animation-delay: 0.5s; animation-fill-mode: both; }

    /* About section */
    .about-section {
        background: white;
        border-radius: 20px;
        padding: 2.5rem 2rem;
        border: 1px solid #E2E8F0;
        animation: fadeInUp 0.8s ease-out;
        margin: 2rem 0;
    }

    .about-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        align-items: center;
    }

    @media (max-width: 768px) {
        .about-grid {
            grid-template-columns: 1fr;
        }
    }

    .about-image {
        text-align: center;
        font-size: 8rem;
        animation: float 4s ease-in-out infinite;
    }


    /* ============ PERFORMANCE OPTIMIZATIONS ============ */
    /* Reduce animations that use high CPU */

    /* Simplify hero gradient (no continuous animation) */
    .hero {
        background: linear-gradient(135deg, #16A34A 0%, #22C55E 100%) !important;
        animation: fadeInUp 0.6s ease-out !important;
        background-size: auto !important;
    }
    .hero::before {
        animation: none !important;
    }
    .hero::after {
        animation: none !important;
    }

    /* Kill the float animations on stat boxes (keep hover) */
    .stat-box {
        animation: fadeInUp 0.4s ease-out !important;
    }
    .stat-box:hover {
        transform: translateY(-2px) !important;
    }

    /* Simpler feature card animation */
    .feature-card {
        animation: fadeInUp 0.4s ease-out !important;
    }

    /* Kill float on floating badge */
    .floating-badge {
        animation: none !important;
    }

    /* Kill rotation animation */
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(0deg); }
    }

    /* ============ Reduce animations on slow devices ============ */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }

    /* Better performance: use transform/opacity only */
    .kpi-card, .patient-card, .feature-card, .stat-box {
        will-change: transform, box-shadow;
    }


    /* ============ PREVENT BUTTON CLIPPING ============ */
    /* Ensure buttons never get cut off */
    .stButton,
    .stButton > button,
    .stDownloadButton,
    .stDownloadButton > button,
    .stLinkButton,
    .stLinkButton > a {
        overflow: visible !important;
        clip-path: none !important;
    }

    .stButton > button {
        min-height: 2.6rem !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        text-overflow: clip !important;
    }

    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        white-space: nowrap !important;
        overflow: visible !important;
        line-height: 1.2 !important;
        margin: 0 !important;
    }

    /* Horizontal block (row) never clips children */
    [data-testid="stHorizontalBlock"] {
        overflow: visible !important;
        align-items: stretch !important;
    }

    [data-testid="column"] {
        overflow: visible !important;
        min-width: 0 !important;
    }

    /* Buttons in columns: fill height */
    [data-testid="column"] .stButton {
        height: 100% !important;
    }
    [data-testid="column"] .stButton > button {
        height: 100% !important;
    }

</style>
    """, unsafe_allow_html=True)


def inject_sidebar_styles():
    pass

def inject_sidebar_decorations():
    pass


def kpi_card(icon, value, label, color=None):
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div style="flex:1; min-width:0;">
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
    </div>
    """.format(icon=icon, value=value, label=label), unsafe_allow_html=True)


def status_badge(text, level="info"):
    return '<span class="status-badge badge-{level}">{text}</span>'.format(level=level, text=text)


def risk_badge(risk_level):
    cfg = RISK_COLORS.get(risk_level, RISK_COLORS["low"])
    return '<span class="status-badge badge-{level}">{icon} {label}</span>'.format(
        level=risk_level, icon=cfg["icon"], label=cfg["label"])


def risk_banner(risk_level, summary, urgent=False):
    cfg = RISK_COLORS.get(risk_level, RISK_COLORS["low"])
    urgent_html = ""
    if urgent:
        urgent_html = ('<div style="margin-top:0.75rem; padding:0.65rem 0.9rem; '
                       'background:white; border-radius:8px; '
                       'color:#991B1B; font-weight:600; border-right:3px solid #DC2626; font-size:0.9rem;">'
                       '🚨 حالة عاجلة — يُنصح بالتدخل الطبي الفوري</div>')
    st.markdown("""
    <div class="risk-banner risk-{level}">
        <div style="font-size: 2.25rem;">{icon}</div>
        <div style="flex:1;">
            <div style="font-weight:700; color:{fg}; font-size:1.1rem;">{title}</div>
            <p style="margin:0.4rem 0 0 0; color:#334155; font-size:0.9rem; line-height:1.5;">{summary}</p>
            {urgent}
        </div>
    </div>
    """.format(level=risk_level, icon=cfg["icon"], fg=cfg["fg"],
               title="خطر {} — {}".format(cfg["label"], risk_level.upper()),
               summary=summary, urgent=urgent_html), unsafe_allow_html=True)


def concern_card(issue, severity, action):
    sev_icons = {"high": "🔴", "medium": "🟡", "low": "🟠"}
    st.markdown("""
    <div class="concern-item sev-{sev}">
        <div style="display:flex; gap:0.6rem;">
            <span style="font-size:1.2rem;">{icon}</span>
            <div style="flex:1;">
                <div style="font-weight:600; color:#0F172A; font-size:0.95rem;">{issue}</div>
                <div style="color:#64748B; font-size:0.85rem; margin-top:0.25rem;">💡 {action}</div>
            </div>
        </div>
    </div>
    """.format(sev=severity, icon=sev_icons.get(severity, "⚪"), issue=issue, action=action), unsafe_allow_html=True)


def recommendation_card(text):
    st.markdown('<div class="recommendation">→ {}</div>'.format(text), unsafe_allow_html=True)


def positive_card(text):
    st.markdown('<div class="positive-item">✓ {}</div>'.format(text), unsafe_allow_html=True)


def hero(title, subtitle, icon="👶"):
    st.markdown("""
    <div class="hero">
        <div style="font-size: 3rem; margin-bottom: 0.4rem;">{icon}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """.format(icon=icon, title=title, subtitle=subtitle), unsafe_allow_html=True)


def page_header(title, subtitle=None, icon="📋"):
    subtitle_html = ""
    if subtitle:
        subtitle_html = '<p style="margin:0.2rem 0 0 0; color:#64748B; font-size:0.85rem;">{}</p>'.format(subtitle)
    st.markdown("""
    <div style="display:flex; align-items:center; gap:0.85rem; margin-bottom:1.25rem; padding-bottom:0.9rem; border-bottom:1px solid #E2E8F0;">
        <div style="width:48px; height:48px; border-radius:10px; background:#F0FDF4; display:flex; align-items:center; justify-content:center; font-size:1.4rem; border:1px solid #DCFCE7;">
            {icon}
        </div>
        <div>
            <h1 style="margin:0 !important; font-size:1.4rem !important; color:#0F172A;">{title}</h1>
            {subtitle_html}
        </div>
    </div>
    """.format(icon=icon, title=title, subtitle_html=subtitle_html), unsafe_allow_html=True)


def section_header(title, subtitle=None, icon="📋"):
    st.markdown("### {} {}".format(icon, title))
    if subtitle:
        st.caption(subtitle)


def spacer(height=1):
    for _ in range(height):
        st.write("")


def modern_navbar(user, clinic, alert_count=0, on_logout=None):
    alert_html = ""
    if alert_count > 0:
        alert_html = ('<div style="background:#DC2626; color:white; padding:0.3rem 0.7rem; '
                      'border-radius:6px; font-size:0.75rem; font-weight:700;">🔔 {}</div>'
                     ).format(alert_count)

    st.markdown(
        '<div style="background:white; padding:0.85rem 1.25rem; border-radius:12px; '
        'border:1px solid #E2E8F0; display:flex; align-items:center; justify-content:space-between; '
        'box-shadow:0 1px 3px rgba(15,23,42,0.04); margin-bottom:1.25rem;">'
        '<div style="display:flex; align-items:center; gap:0.75rem;">'
        '<div style="width:38px; height:38px; border-radius:10px; background:#16A34A; '
        'display:flex; align-items:center; justify-content:center; font-size:1.2rem;">👶</div>'
        '<div>'
        '<div style="font-weight:700; font-size:0.95rem; color:#0F172A;">أمينة SaaS</div>'
        '<div style="font-size:0.72rem; color:#64748B;">' + clinic.get("name", "") + '</div>'
        '</div></div>'
        '<div style="display:flex; align-items:center; gap:0.85rem;">'
        + alert_html +
        '<div style="text-align:right;">'
        '<div style="font-weight:600; font-size:0.85rem; color:#0F172A;">' + user.get("full_name", "") + '</div>'
        '<div style="font-size:0.7rem; color:#64748B;">' + clinic.get("plan", "").upper() + '</div>'
        '</div>'
        '<div style="width:38px; height:38px; border-radius:50%; background:#F0FDF4; '
        'display:flex; align-items:center; justify-content:center; font-size:1rem; '
        'border:2px solid #DCFCE7;">👩‍⚕️</div>'
        '</div></div>',
        unsafe_allow_html=True
    )


def render_sidebar(clinic, user, active="dashboard"):
    """Sidebar with high-contrast active button"""
    with st.sidebar:
        # Header
        st.markdown(
            '<div style="padding:0.75rem 0.5rem 1rem 0.5rem; border-bottom:1px solid #F1F5F9; margin-bottom:0.5rem;">'
            '<div style="display:flex; align-items:center; gap:0.6rem;">'
            '<div style="width:36px; height:36px; border-radius:10px; background:#16A34A; '
            'display:flex; align-items:center; justify-content:center; font-size:1.1rem;">👶</div>'
            '<div>'
            '<div style="font-weight:700; font-size:0.95rem; color:#0F172A;">أمينة SaaS</div>'
            '<div style="font-size:0.68rem; color:#64748B;">نظام إدارة العيادات</div>'
            '</div></div></div>',
            unsafe_allow_html=True
        )

        # User card
        st.markdown(
            '<div style="padding:0.6rem 0.75rem; border-radius:8px; background:#F8FAFC; '
            'margin-bottom:0.75rem; display:flex; align-items:center; gap:0.6rem;">'
            '<div style="width:32px; height:32px; border-radius:50%; background:#F0FDF4; '
            'display:flex; align-items:center; justify-content:center; font-size:0.95rem;">👩‍⚕️</div>'
            '<div style="flex:1; min-width:0;">'
            '<div style="font-weight:600; color:#0F172A; font-size:0.8rem; '
            'overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">' +
            user.get("full_name", "") + '</div>'
            '<div style="color:#64748B; font-size:0.68rem;">' +
            clinic.get("plan", "").upper() + '</div>'
            '</div></div>',
            unsafe_allow_html=True
        )

        st.markdown("### 🧭 التنقل")

        # ========== NAV ITEMS ==========
        nav_items = [
            ("dashboard", "📊 لوحة التحكم"),
            ("appointments", "📅 المواعيد"),
            ("patients", "👩 الحوامل"),
            ("medical", "📋 السجل الطبي"),
            ("ai", "🤖 تحليل AI"),
            ("admin", "⚙️ الإدارة"),
        ]

        for key, label in nav_items:
            is_active = (key == active)

            if is_active:
                # ACTIVE — primary button (blue bg, white text)
                if st.button("▶  " + label, key="navbtn_" + key,
                             use_container_width=True, type="primary"):
                    st.session_state["nav_section"] = key
                    st.rerun()
            else:
                # INACTIVE — secondary
                if st.button(label, key="navbtn_" + key,
                             use_container_width=True):
                    st.session_state["nav_section"] = key
                    st.rerun()

        # ========== QUICK ACTIONS ==========
        st.markdown("### ⚡ إجراءات سريعة")

        if st.button("➕ حامل جديدة", use_container_width=True, key="sb_np"):
            st.session_state["patient_view"] = "new"
            st.session_state["nav_section"] = "patients"
            st.session_state["selected_patient_id"] = None
            st.rerun()

        if st.button("🩺 زيارة جديدة", use_container_width=True, key="sb_nv"):
            pid = st.session_state.get("selected_patient_id")
            if pid:
                st.session_state["patient_view"] = "new_visit"
                st.session_state["nav_section"] = "patients"
                st.rerun()
            else:
                st.warning("اختر حاملاً أولاً")

        st.markdown("---")

        if st.button("🚪 تسجيل الخروج", use_container_width=True, key="sb_lo"):
            return "__logout__"

        st.markdown(
            '<div style="text-align:center; font-size:0.65rem; color:#94A3B8; padding:0.75rem 0;">'
            '© 2026 أمينة SaaS</div>', unsafe_allow_html=True)

    return None



def top_navbar(*args, **kwargs):
    pass

def sidebar_header():
    pass

def sidebar_user_card(*args, **kwargs):
    pass

def sidebar_logout_button():
    return False

def sidebar_footer():
    pass


def landing_hero():
    """Beautiful animated landing hero"""
    st.markdown("""
    <div class="hero" style="padding: 4rem 2rem; text-align:center; border-radius: 24px; margin-bottom: 2rem;">
        <div style="font-size: 5rem; margin-bottom: 0.75rem; position:relative; z-index:1;">
            <span class="heartbeat">👶</span>
        </div>
        <h1 style="font-size: 2.75rem !important; color: white !important; margin: 0 0 0.75rem 0 !important; position:relative; z-index:1; font-weight: 900; letter-spacing: -0.03em;">
            أمينة SaaS
        </h1>
        <p style="font-size: 1.15rem; color: rgba(255,255,255,0.95) !important; margin: 0 0 1.5rem 0; position:relative; z-index:1; max-width: 600px; margin-left:auto; margin-right:auto; line-height: 1.6;">
            نظام إدارة عيادات النساء والولادة<br>
            مدعوم بالذكاء الاصطناعي · عربي بالكامل · آمن
        </p>
        <div style="display:flex; gap:0.75rem; justify-content:center; flex-wrap:wrap; position:relative; z-index:1;">
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 999px; color: white; font-size: 0.85rem; font-weight: 600; backdrop-filter: blur(10px);">🇮🇶 عربي 100%</span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 999px; color: white; font-size: 0.85rem; font-weight: 600; backdrop-filter: blur(10px);">🤖 AI متقدم</span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 999px; color: white; font-size: 0.85rem; font-weight: 600; backdrop-filter: blur(10px);">📱 WhatsApp</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def feature_card(icon, title, description):
    """Animated feature card"""
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">{icon}</div>
        <div class="feature-title">{title}</div>
        <div class="feature-desc">{description}</div>
    </div>
    """.format(icon=icon, title=title, description=description), unsafe_allow_html=True)


def stat_box(number, label):
    """Animated stat"""
    st.markdown("""
    <div class="stat-box">
        <div class="stat-number">{number}</div>
        <div class="stat-label">{label}</div>
    </div>
    """.format(number=number, label=label), unsafe_allow_html=True)


def about_section():
    """About product section"""
    st.markdown("""
    <div class="about-section">
        <div class="about-grid">
            <div>
                <div style="font-size: 0.85rem; font-weight: 700; color: #16A34A; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.75rem;">
                    <span class="pulse-dot"></span> عن المنتج
                </div>
                <h2 style="color: #0F172A !important; margin: 0 0 1rem 0 !important; font-size: 1.75rem !important;">
                    لماذا أمينة SaaS؟
                </h2>
                <p style="color: #475569; line-height: 1.8; font-size: 1rem; margin-bottom: 1rem;">
                    <strong style="color: #16A34A;">أمينة SaaS</strong> هو نظام إدارة عيادات متكامل مصمم خصيصاً لعيادات النساء والولادة في العالم العربي.
                </p>
                <p style="color: #475569; line-height: 1.8; font-size: 1rem; margin-bottom: 1rem;">
                    يجمع بين سهولة الاستخدام، القوة الطبية، والذكاء الاصطناعي لتقديم أفضل رعاية للحوامل.
                </p>
                <div style="display:flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1.25rem;">
                    <span style="background: #F0FDF4; color: #15803D; padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid #BBF7D0;">✓ عربي بالكامل</span>
                    <span style="background: #F0FDF4; color: #15803D; padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid #BBF7D0;">✓ آمن ومشفر</span>
                    <span style="background: #F0FDF4; color: #15803D; padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid #BBF7D0;">✓ سريع</span>
                    <span style="background: #F0FDF4; color: #15803D; padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid #BBF7D0;">✓ سهل</span>
                </div>
            </div>
            <div class="about-image">🏥</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def cta_section():
    """Call to action"""
    st.markdown("""
    <div class="cta-section">
        <h2 style="font-size: 1.75rem !important;">🚀 ابدأ الآن مجاناً</h2>
        <p style="font-size: 1.05rem;">14 يوم تجريبي · بدون بطاقة ائتمان · إعداد في دقيقتين</p>
        <div style="display:flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">
            <span style="background: #16A34A; color: white; padding: 0.75rem 1.5rem; border-radius: 10px; font-weight: 700; box-shadow: 0 4px 12px rgba(22,163,74,0.3);">
                🏥 سجّل عيادتك الآن
            </span>
            <span class="bounce-arrow" style="font-size: 1.5rem; align-self: center;">👉</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def footer_landing():
    """Footer for landing page"""
    st.markdown("""
    <div style="text-align:center; padding: 2rem 1rem; color: #94A3B8; font-size: 0.85rem; border-top: 1px solid #E2E8F0; margin-top: 3rem;">
        <div style="margin-bottom: 0.75rem;">
            <strong style="color: #16A34A;">👶 أمينة SaaS</strong> — نظام إدارة عيادات النساء والولادة
        </div>
        <div style="display:flex; gap: 1.5rem; justify-content: center; flex-wrap: wrap; margin-bottom: 0.75rem;">
            <span>📧 info@amina-saas.com</span>
            <span>🌍 العراق</span>
            <span>📱 +964 770 000 0000</span>
        </div>
        <div style="font-size: 0.75rem; opacity: 0.7;">
            © 2026 أمينة SaaS · كل الحقوق محفوظة
        </div>
    </div>
    """, unsafe_allow_html=True)
