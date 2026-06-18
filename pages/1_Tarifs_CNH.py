# -*- coding: utf-8 -*-
"""
Page Streamlit : Tarifs CNH -> Excel / CSV
Transforme les fichiers tarif Case / New Holland (réplique du PowerQuery)
avec comparaison Case/NH, préfixe "CASE", et 3 modes d'export.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Permet d'importer theme.py / tarif_core.py situés à la racine du projet
sys.path.append(str(Path(__file__).resolve().parent.parent))

from theme import apply_theme, page_header          # noqa: E402
import tarif_core as tc                              # noqa: E402

st.set_page_config(page_title="Tarifs CNH → Excel", page_icon="📑", layout="wide")
apply_theme()
page_header(
    "Tarifs CNH → Excel / CSV",
    "Transformation des tarifs Case & New Holland — réplique fidèle du PowerQuery",
    "📑",
)

# ==================== 1. CHARGEMENT DES FICHIERS ====================
st.markdown('<div class="section-title">📂 Fichiers tarif (.txt)</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    case_file = st.file_uploader("Tarif **Case** (.txt)", type=["txt"], key="up_case")
with c2:
    nh_file = st.file_uploader("Tarif **New Holland** (.txt)", type=["txt"], key="up_nh")

# ==================== 2. TABLE DES REMISES ====================
with st.expander("⚙️ Table des remises (Code CNH → Taux)  —  0.5 = 50 %"):
    st.caption(
        "Modifiable. Sert au calcul du **Prix net** = Prix tarif × (1 − taux). "
        "Un code absent de la table laisse le Prix net vide."
    )
    default_rem = pd.DataFrame(
        {"Code CNH": list(tc.DEFAULT_REMISE.keys()),
         "Taux de remise": list(tc.DEFAULT_REMISE.values())}
    )
    rem_edit = st.data_editor(
        default_rem, num_rows="dynamic", use_container_width=True, key="rem_editor",
        column_config={
            "Taux de remise": st.column_config.NumberColumn(format="%.2f", min_value=0.0, max_value=1.0)
        },
    )

# ==================== 3. MODE D'EXPORT ====================
st.markdown('<div class="section-title">🎯 Contenu à exporter</div>', unsafe_allow_html=True)
mode = st.radio(
    "Mode",
    ["Case uniquement", "New Holland uniquement", "Tous cumulé (Case + New Holland)"],
    horizontal=True, label_visibility="collapsed",
)

prefix_case = False
if mode == "Case uniquement":
    prefix_case = st.checkbox(
        "Préfixer « CASE » les désignations des références présentes **uniquement** "
        "dans le tarif Case (comparaison Case ↔ New Holland — nécessite les 2 fichiers)"
    )

generate = st.button("🚀 Générer le fichier", type="primary")

# ==================== 4. TRAITEMENT ====================
def _read(file):
    return file.getvalue().decode("utf-8", errors="replace")

if generate:
    remise_map = {
        str(r["Code CNH"]).strip(): float(r["Taux de remise"])
        for _, r in rem_edit.iterrows()
        if str(r["Code CNH"]).strip() != "" and pd.notna(r["Taux de remise"])
    }

    nb_prefixes = None
    df = None
    fname = "TARIF"

    try:
        with st.spinner("Transformation en cours…"):
            if mode == "New Holland uniquement":
                if nh_file is None:
                    st.error("⚠️ Chargez le fichier **New Holland**.")
                    st.stop()
                df = tc.parse_tarif_txt(_read(nh_file), remise_map)
                fname = "TARIF_NewHolland"

            elif mode == "Case uniquement":
                if case_file is None:
                    st.error("⚠️ Chargez le fichier **Case**.")
                    st.stop()
                df = tc.parse_tarif_txt(_read(case_file), remise_map)
                fname = "TARIF_Case"
                if prefix_case:
                    if nh_file is None:
                        st.error("⚠️ Le préfixe « CASE » nécessite aussi le fichier **New Holland**.")
                        st.stop()
                    nh_refs = set(tc.parse_tarif_txt(_read(nh_file), remise_map)["Référence pièce"])
                    df, nb_prefixes = tc.apply_case_prefix(df, nh_refs)
                    fname = "TARIF_Case_prefixe"

            else:  # Tous cumulé (sans comparaison)
                parts = []
                if case_file is not None:
                    parts.append(tc.parse_tarif_txt(_read(case_file), remise_map))
                if nh_file is not None:
                    parts.append(tc.parse_tarif_txt(_read(nh_file), remise_map))
                if not parts:
                    st.error("⚠️ Chargez au moins un fichier (Case et/ou New Holland).")
                    st.stop()
                df = pd.concat(parts, ignore_index=True)
                fname = "TARIF_cumule"

            # Sérialisation — CSV toujours ; xlsx seulement si sous la limite Excel
            csv_bytes = tc.to_csv_bytes(df)
            xlsx_bytes = None
            if len(df) <= 1_048_576:
                xlsx_bytes = tc.to_xlsx_bytes(df)
            else:
                st.warning(
                    f"{len(df):,} lignes dépassent la limite Excel (1 048 576). "
                    "Export xlsx désactivé — utilisez le CSV.".replace(",", " ")
                )

        st.session_state["tarif_result"] = {
            "df_head": df.head(300),
            "n_rows": len(df),
            "nb_prefixes": nb_prefixes,
            "xlsx": xlsx_bytes,
            "csv": csv_bytes,
            "fname": fname,
        }
    except Exception as e:
        st.error(f"Erreur pendant la transformation : {e}")

# ==================== 5. RÉSULTAT + TÉLÉCHARGEMENT ====================
res = st.session_state.get("tarif_result")
if res:
    st.success("✅ Fichier généré.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Lignes", f"{res['n_rows']:,}".replace(",", " "))
    m2.metric("Colonnes", len(tc.COLS))
    if res["nb_prefixes"] is not None:
        m3.metric("Réf. préfixées « CASE »", f"{res['nb_prefixes']:,}".replace(",", " "))

    st.markdown('<div class="section-title">👁️ Aperçu (300 premières lignes)</div>', unsafe_allow_html=True)
    st.dataframe(res["df_head"], use_container_width=True, height=380)

    st.markdown('<div class="section-title">⬇️ Téléchargement</div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    if res["xlsx"] is not None:
        d1.download_button(
            "📊 Télécharger en Excel (.xlsx)",
            data=res["xlsx"], file_name=f"{res['fname']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        d1.button("📊 Excel indisponible (trop de lignes)", disabled=True, use_container_width=True)
    d2.download_button(
        "📄 Télécharger en CSV (.csv)",
        data=res["csv"], file_name=f"{res['fname']}.csv",
        mime="text/csv", use_container_width=True,
    )
else:
    st.info("Chargez un fichier, choisissez le mode d'export, puis cliquez sur **Générer**.")
