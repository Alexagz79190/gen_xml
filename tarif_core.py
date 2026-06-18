# -*- coding: utf-8 -*-
"""
Moteur de transformation des tarifs CNH (Case / New Holland).

Réplique fidèle du PowerQuery existant (requête "tariff") :
  - découpage en largeur fixe (offsets ci-dessous, 15 colonnes, UTF-8)
  - Prix tarif = colonne brute / 100
  - Poids kg   = colonne brute / 1000
  - Famille Mistral = 3 premiers caractères du MPC
  - suppression de la ligne d'en-tête (référence commençant par CNEUR01FR)
  - jointure Code remise -> Taux de remise (table "Remise NH")
  - Prix net = Prix tarif * (1 - Taux), arrondi à 2 décimales

Fonctions additionnelles (demande utilisateur) :
  - comparaison Case / New Holland : préfixe "CASE " sur la désignation
    des références présentes UNIQUEMENT dans le tarif Case
  - export xlsx / csv
"""

import io
import pandas as pd

# Offsets de découpage en largeur fixe (positions de début de chaque colonne).
# Issus directement du PowerQuery :
#   Csv.Document(..., 15, {0,18,58,59,60,68,79,92,97,101,102,107,112,113,116}, ...)
OFFSETS = [0, 18, 58, 59, 60, 68, 79, 92, 97, 101, 102, 107, 112, 113, 116]

# Colonnes de sortie, dans l'ordre final du PowerQuery.
COLS = [
    "Référence pièce",
    "Description Pièces",
    "Type",
    "Libre",
    "Date du prix",
    "Prix tarif",
    "Prix net",
    "Poids kg",
    "Quantité",
    "Première ligne de produit",
    "Code remise",
    "Taux de remise",
    "PCC",
    "MPC",
    "Code retour",
    "Famille Mistral",
]

# Table de remise par défaut (Remise NH.csv) : Code CNH -> Taux.
DEFAULT_REMISE = {
    "A": 0.50, "B": 0.44, "C": 0.40, "D": 0.30, "E": 0.30,
    "F": 0.30, "G": 0.40, "H": 0.25, "I": 0.15, "K": 0.46,
    "M": 0.24, "Z": 0.00, "1": 0.38, "2": 0.45,
}

CASE_PREFIX = "CASE "


def _to_int(s, default=0):
    """Convertit un champ texte en entier (tolérant aux espaces / champ vide)."""
    s = (s or "").strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else default


def _split_line(line):
    """Découpe une ligne en 15 segments selon OFFSETS."""
    seg = [line[OFFSETS[i]:OFFSETS[i + 1]] for i in range(len(OFFSETS) - 1)]
    seg.append(line[OFFSETS[-1]:])
    return seg


def parse_tarif_txt(text, remise_map=None):
    """
    Transforme le contenu texte d'un tarif CNH en DataFrame (colonnes = COLS).
    `remise_map` : dict Code CNH -> taux (float). Défaut = DEFAULT_REMISE.
    """
    if remise_map is None:
        remise_map = DEFAULT_REMISE

    rows = []
    for line in text.splitlines():
        line = line.rstrip("\r\n")
        if not line.strip():
            continue

        seg = _split_line(line)
        ref = seg[0].strip()
        # Ligne d'en-tête du fichier (ex: CNEUR01FR_FR20260105) -> ignorée
        if not ref or ref.startswith("CNEUR01FR"):
            continue

        desc = seg[1].rstrip()
        typ = seg[2].strip()
        libre = seg[3].strip()
        date_prix = _to_int(seg[4], None)
        prix_tarif = _to_int(seg[5]) / 100
        poids_kg = _to_int(seg[6]) / 1000
        quantite = _to_int(seg[7], None)
        prem_ligne = seg[8].strip()
        code_remise = seg[9].strip()
        pcc = seg[10].strip()
        mpc_raw = seg[11].strip()
        mpc = _to_int(mpc_raw, None)
        code_retour = seg[12].strip()

        # Famille Mistral = 3 premiers caractères du MPC (converti en texte d'abord,
        # comme Text.From(...) dans le PowerQuery -> perte des zéros de tête éventuels)
        famille = (str(mpc) if mpc is not None else mpc_raw)[:3]

        taux = remise_map.get(code_remise)
        prix_net = round(prix_tarif * (1 - taux), 2) if taux is not None else None

        rows.append([
            ref, desc, typ, libre, date_prix, prix_tarif, prix_net, poids_kg,
            quantite, prem_ligne, code_remise, taux, pcc, mpc, code_retour, famille,
        ])

    return pd.DataFrame(rows, columns=COLS)


def apply_case_prefix(df_case, nh_refs):
    """
    Préfixe "CASE " la désignation des références présentes UNIQUEMENT dans Case
    (c'est-à-dire absentes du jeu de références New Holland `nh_refs`).
    Les références communes ne sont pas modifiées.
    Retourne (df modifié, nb de lignes préfixées).
    """
    df = df_case.copy()
    mask = ~df["Référence pièce"].isin(nh_refs)
    df.loc[mask, "Description Pièces"] = (
        CASE_PREFIX + df.loc[mask, "Description Pièces"].astype(str).str.lstrip()
    )
    return df, int(mask.sum())


def to_xlsx_bytes(df, sheet_name="tariff"):
    """
    Sérialise un DataFrame en classeur xlsx (bytes).
    Utilise le mode streaming d'openpyxl (write_only) : ~40 % plus rapide
    et bien moins gourmand en mémoire que pandas.to_excel sur gros volumes.
    """
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet_name)
    ws.append(list(df.columns))
    for row in df.itertuples(index=False, name=None):
        ws.append(list(row))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def to_csv_bytes(df):
    """Sérialise un DataFrame en CSV (bytes) — séparateur ';', UTF-8 BOM (Excel-friendly)."""
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")
