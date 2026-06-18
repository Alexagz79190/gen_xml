# -*- coding: utf-8 -*-
"""
Thème graphique partagé pour l'application Streamlit.
Palette Groupe Dubreuil : bleu marine (#003660) + jaune (#FFDD32).

apply_theme()  -> injecte le CSS moderne (à appeler après st.set_page_config)
page_header()  -> en-tête "hero" stylisé en haut de chaque page
"""

import streamlit as st

# ---------- Palette Groupe Dubreuil ----------
BLEU = "#003660"          # bleu marine principal
BLEU_CLAIR = "#053784"    # bleu secondaire (dégradé)
JAUNE = "#FFDD32"         # jaune accent
JAUNE_DORE = "#FCC300"    # jaune doré (hover)
BLEU_SOFT = "#eaf1f7"     # fond bleuté très clair


def apply_theme():
    """Injecte le CSS global. À appeler une fois par page, après set_page_config."""
    st.markdown(
        f"""
        <style>
        /* ---------- Base ---------- */
        html, body, [class*="css"] {{
            font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
        }}
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        div[data-testid="stDecoration"] {{display: none;}}

        /* ---------- Hero ---------- */
        .hero {{
            background: linear-gradient(120deg, {BLEU} 0%, {BLEU_CLAIR} 100%);
            border-radius: 18px;
            border-bottom: 5px solid {JAUNE};
            padding: 26px 30px;
            margin-bottom: 22px;
            color: #fff;
            box-shadow: 0 10px 30px rgba(0,54,96,.22);
        }}
        .hero h1 {{
            color: #fff; font-size: 1.7rem; font-weight: 700;
            margin: 0; line-height: 1.2;
        }}
        .hero p {{
            color: rgba(255,255,255,.88); margin: 6px 0 0 0; font-size: .98rem;
        }}
        .hero .hero-icon {{ font-size: 2.1rem; margin-right: 10px; }}

        /* ---------- Cartes ---------- */
        .card {{
            background: #ffffff;
            border: 1px solid #e4e8ee;
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,.03);
        }}
        .section-title {{
            font-weight: 700; font-size: 1.05rem; color: {BLEU};
            margin: 14px 0 10px 0; padding-left: 10px;
            border-left: 4px solid {JAUNE};
            display:flex; align-items:center; gap:8px;
        }}

        /* ---------- Boutons ---------- */
        .stButton > button, .stDownloadButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid {BLEU};
            transition: all .15s ease;
        }}
        .stButton > button[kind="primary"], .stDownloadButton > button {{
            background: {BLEU}; color: #fff; border: none;
        }}
        .stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {{
            background: {BLEU_CLAIR}; color: #fff;
            box-shadow: 0 0 0 3px rgba(255,221,50,.45);
        }}

        /* ---------- Uploaders ---------- */
        section[data-testid="stFileUploaderDropzone"] {{
            background: {BLEU_SOFT};
            border: 1.5px dashed {BLEU};
            border-radius: 12px;
        }}

        /* ---------- Métriques ---------- */
        div[data-testid="stMetric"] {{
            background: #fff; border: 1px solid #e4e8ee;
            border-left: 4px solid {JAUNE};
            border-radius: 12px; padding: 12px 16px;
        }}

        /* ---------- Radios / widgets : accent bleu ---------- */
        div[data-baseweb="radio"] svg {{ color: {BLEU}; fill: {BLEU}; }}

        /* ---------- Tableaux ---------- */
        div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background: #fbfcfd;
            border-right: 1px solid #e4e8ee;
        }}
        section[data-testid="stSidebar"] a[aria-current="page"] {{
            border-left: 3px solid {JAUNE};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", icon: str = "🛠️"):
    """Affiche un en-tête 'hero' en haut de page (palette Dubreuil)."""
    st.markdown(
        f"""
        <div class="hero">
            <h1><span class="hero-icon">{icon}</span>{title}</h1>
            {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
