# -*- coding: utf-8 -*-
"""
Générateur de fichiers XML - Commandes fournisseur
Auteur : adapté depuis le script de mathon.alexis

Détection automatique du format purchase.
Si non reconnu → interface de mapping manuel visible dans Streamlit.
"""

import pandas as pd
import xml.etree.ElementTree as ET
import streamlit as st
from io import BytesIO
import re

# ==================== MAPPING DES FORMATS CONNUS ====================
# Chaque format mappe les colonnes du fichier fournisseur vers les champs internes.
# "prix_unitaire": None → calculé depuis valeur_ligne / quantite
FORMAT_SPECS = {
    "Format A – Ancien (Qty Pu / Pu Value)": {
        "purchase_order": "Purchase Order",
        "vendor_ref":     "Vendor Product Number",
        "description":    "Product Description",
        "quantite":       "Qty Pu",
        "valeur_ligne":   "Pu Value",
        "prix_unitaire":  None,
        "discount1":      None,
    },
    "Format B – Nouveau (Purchase Row Quantity)": {
        "purchase_order": "Po Number",
        "vendor_ref":     "Vendor Product Number",
        "description":    "Product Description",
        "quantite":       "Purchase Row Quantity",
        "valeur_ligne":   "Purchase Row Value Euro",
        "prix_unitaire":  "Gross Value Per Unit",
        "discount1":      "Discount 1",
    },
}

FORMAT_SIGNATURES = {
    "Format A – Ancien (Qty Pu / Pu Value)":           ["Qty Pu", "Pu Value", "Purchase Order"],
    "Format B – Nouveau (Purchase Row Quantity)": ["Purchase Row Quantity", "Gross Value Per Unit", "Po Number"],
}

# Labels affichés dans l'interface de mapping
CHAMPS_INTERNES = {
    "purchase_order": "N° de commande (purchase_order)",
    "vendor_ref":     "Référence produit fournisseur (vendor_ref)",
    "description":    "Description produit (description)",
    "quantite":       "Quantité commandée (quantite)",
    "prix_unitaire":  "Prix unitaire HT (prix_unitaire)  — laisser vide si calculé",
    "valeur_ligne":   "Valeur totale ligne HT (valeur_ligne) — utilisée si prix_unitaire vide",
    "discount1":      "Remise ligne % (discount1) — format -35 pour 35% — laisser vide si absent",
}


# ==================== CHARGEMENT DU FICHIER PURCHASE ====================
def try_load_excel(uploaded_file, header_row=0):
    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=header_row)
    df.columns = df.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    return df


def load_purchase_autodetect(uploaded_file):
    """
    Tente de détecter le format automatiquement.
    Retourne (df, nom_format) si trouvé, sinon (df_brut, None) pour mapping manuel.
    """
    # Tentative header ligne 1 (Format B)
    df = try_load_excel(uploaded_file, header_row=0)
    cols = set(df.columns)
    for fmt_name, signature in FORMAT_SIGNATURES.items():
        if all(c in cols for c in signature):
            return df, fmt_name

    # Tentative header dynamique (Format A)
    uploaded_file.seek(0)
    df_raw = pd.read_excel(uploaded_file, header=None)
    for i in range(0, min(40, len(df_raw))):
        for j in range(df_raw.shape[1]):
            if str(df_raw.iloc[i, j]).strip() == "Vendor Product Number":
                df = try_load_excel(uploaded_file, header_row=i)
                cols = set(df.columns)
                for fmt_name, signature in FORMAT_SIGNATURES.items():
                    if all(c in cols for c in signature):
                        return df, fmt_name
                # Header trouvé mais format inconnu → mapping manuel
                return df, None

    # Aucune détection → retourner header ligne 1 pour mapping manuel
    return try_load_excel(uploaded_file, header_row=0), None


# ==================== INTERFACE DE MAPPING ====================
def show_mapping_ui(df, spec_auto=None, expanded=False):
    """
    Affiche l'interface de mapping dans Streamlit.
    - Si spec_auto fourni : pré-remplit avec les valeurs du format détecté (mode consultation/édition)
    - Sinon : mapping manuel vide (format inconnu)
    Retourne le dict de mapping ou None si champs obligatoires manquants.
    """
    cols_fichier = ["— non mappé —"] + list(df.columns)
    mapping = {}
    all_mapped = True

    col1, col2 = st.columns(2)
    for i, (champ, label) in enumerate(CHAMPS_INTERNES.items()):
        col = col1 if i % 2 == 0 else col2
        with col:
            # Pré-sélection : depuis spec_auto ou heuristique sur le nom
            val_auto = spec_auto.get(champ) if spec_auto else None
            if val_auto and val_auto in cols_fichier:
                default = cols_fichier.index(val_auto)
            else:
                default = 0
                for j, c in enumerate(cols_fichier):
                    if champ.replace("_", " ").lower() in c.lower():
                        default = j
                        break

            choix = st.selectbox(label, options=cols_fichier, index=default, key=f"mapping_{champ}")
            mapping[champ] = None if choix == "— non mappé —" else choix

    # Validation
    for champ in ["purchase_order", "vendor_ref", "description", "quantite"]:
        if not mapping.get(champ):
            all_mapped = False

    if not mapping.get("prix_unitaire") and not mapping.get("valeur_ligne"):
        st.error("❌ Mappez au moins **Prix unitaire HT** ou **Valeur totale ligne HT**.")
        all_mapped = False

    if all_mapped:
        st.success("✅ Tous les champs obligatoires sont mappés.")

    return mapping if all_mapped else None


# ==================== NORMALISATION ====================
def normalize_purchase(df, spec):
    df = df.copy()

    # ── Filtrer les lignes sans référence fournisseur (ex : ligne de total) ──
    vendor_col = spec["vendor_ref"]
    df = df[df[vendor_col].notna() & (df[vendor_col].astype(str).str.strip() != "") & (df[vendor_col].astype(str).str.strip() != "nan")]

    df["_purchase_order"] = df[spec["purchase_order"]].astype(str)
    df["_vendor_ref"]     = df[spec["vendor_ref"]].astype(str).str.strip()
    df["_description"]    = df[spec["description"]].astype(str)
    df["_quantite"]       = pd.to_numeric(df[spec["quantite"]], errors="coerce").fillna(0)

    if spec.get("prix_unitaire"):
        df["_prix_unitaire"] = pd.to_numeric(df[spec["prix_unitaire"]], errors="coerce").fillna(0)
    elif spec.get("valeur_ligne"):
        valeur = pd.to_numeric(df[spec["valeur_ligne"]], errors="coerce").fillna(0)
        df["_prix_unitaire"] = (valeur / df["_quantite"].replace(0, float("nan"))).fillna(0)
    else:
        df["_prix_unitaire"] = 0.0

    # ── Remise ligne (Discount 1) : format -35 → taux 0.35 ──
    if spec.get("discount1") and spec["discount1"] in df.columns:
        raw_discount = pd.to_numeric(df[spec["discount1"]], errors="coerce").fillna(0)
        # La valeur est négative (ex : -35), on prend la valeur absolue pour le taux
        df["_discount1"] = raw_discount.abs() / 100
    else:
        df["_discount1"] = 0.0

    # ── Prix de vente HT = prix unitaire * (1 - remise) arrondi à 2 décimales ──
    df["_prixvente"] = (df["_prix_unitaire"] * (1 - df["_discount1"])).round(2)

    return df.reset_index(drop=True)


# ==================== UTILITAIRES ====================
def load_file(label, file_type, header=None):
    uploaded_file = st.file_uploader(label, type=file_type)
    if uploaded_file is not None:
        if file_type == "csv":
            return pd.read_csv(uploaded_file, sep=';', dtype={'Fournisseur': str, 'Référence Frn': str}, encoding='latin1')
        elif file_type == "xlsx":
            return pd.read_excel(uploaded_file, header=header if header is not None else 0)
        elif file_type == "txt":
            colspecs = [(0,10),(10,20),(20,30),(30,36),(36,44),(44,69),(69,84),(84,94),
                        (94,102),(102,105),(105,109),(109,115),(115,119),(119,134)]
            columns  = ['Monnaie','Article','Prix','Remise','Date','Designation','Code EAN',
                        'Poids','Societe','PDR','Qte','Cond','VoirLP','HS Code']
            return pd.read_fwf(uploaded_file, colspecs=colspecs, names=columns, encoding='latin1')
    return None


def get_info(key, default=""):
    value = infos.loc[infos['donnee'] == key, 'valeur']
    return value.values[0] if not value.empty else default


def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# ==================== CRÉATION XML ====================
def create_ligne_xml(parent, index, row):
    ligne = ET.SubElement(parent, "ligne")
    ET.SubElement(ligne, "NumLigtransaction").text = f"{index:05d}"
    ET.SubElement(ligne, "refagrizone").text       = f"{identifiant} {row['_vendor_ref']}"
    ET.SubElement(ligne, "reffour").text           = row['_vendor_ref']
    ET.SubElement(ligne, "libelle").text           = row['_description']
    ET.SubElement(ligne, "qte").text               = f"{row['_quantite']:.2f}"

    tarif_row = tarif[tarif['Article'] == row['_vendor_ref']]
    if not tarif_row.empty:
        prix          = float(tarif_row['Prix'].values[0])
        remise_lettre = tarif_row['Remise'].values[0]
        remise_taux   = remise_mapping.get(remise_lettre, 0)
        prixachat     = round(prix * (1 - remise_taux), 2)
    else:
        prixachat = 0.00

    ET.SubElement(ligne, "prixachat").text    = f"{prixachat:.2f}"
    # Prix de vente HT = Gross Value Per Unit * ((100 - abs(Discount 1)) / 100)
    ET.SubElement(ligne, "prixventeHT").text  = f"{row['_prixvente']:.2f}"
    ET.SubElement(ligne, "prixventeTTC").text = "0.00"
    if agence == "00":
        ET.SubElement(ligne, "codefour").text = "408"
    ET.SubElement(ligne, "departlivr").text = ""


def create_xml(data, agence_code, suffix):
    global agence
    agence         = agence_code
    transaction    = ET.Element("transaction")
    entete         = ET.SubElement(transaction, "entetetransaction")
    numtransaction = f"{data.iloc[0]['_purchase_order']}{suffix}" if not data.empty else ""

    ET.SubElement(entete, "numtransaction").text  = numtransaction
    ET.SubElement(entete, "passtransaction").text = numtransaction
    ET.SubElement(entete, "agence").text          = agence
    if agence == "00":
        ET.SubElement(entete, "code_edo").text    = ""
        ET.SubElement(entete, "nivcommande").text = "0"

    adrfact = ET.SubElement(entete, "adrfact")
    ET.SubElement(adrfact, "emailfact").text = "vendor.invoices@kramp.com" if agence == "00" else ""
    ET.SubElement(adrfact, "nomfact").text   = get_info('nomfact', 'Nom Facturation Inconnu')
    ET.SubElement(adrfact, "adr1fact").text  = get_info('adr1fact', '')
    if agence == "00":
        for tag in ["adr2fact","adr3fact","telephonefact","numtva","numsiret"]:
            ET.SubElement(adrfact, tag).text = ""
    ET.SubElement(adrfact, "paysfact").text    = get_info('paysfact', '')
    ET.SubElement(adrfact, "villefact").text   = get_info('villefact', '')
    ET.SubElement(adrfact, "cpfact").text      = get_info('cpfact', '')
    ET.SubElement(adrfact, "code_client").text = get_info('code_client', '')

    adrlivr = ET.SubElement(entete, "adrlivr")
    if agence == "00":
        ET.SubElement(adrlivr, "typadrlivr").text      = "CL"
        ET.SubElement(adrlivr, "nominterloclivr").text = get_info('nomadrlivr', '')
    ET.SubElement(adrlivr, "emaillivr").text  = "vendor.invoices@kramp.com" if agence == "00" else get_info('emaillivr', '')
    ET.SubElement(adrlivr, "nomadrlivr").text = get_info('nomadrlivr', '')
    ET.SubElement(adrlivr, "adr1livr").text   = get_info('adr1livr', '')
    ET.SubElement(adrlivr, "adr2livr").text   = get_info('adr2livr', '')
    if agence == "00":
        ET.SubElement(adrlivr, "adr3livr").text      = ""
        ET.SubElement(adrlivr, "telephonelivr").text = ""
    ET.SubElement(adrlivr, "payslivr").text = get_info('payslivr', '')
    ET.SubElement(adrlivr, "villelivr").text = get_info('villelivr', '')
    ET.SubElement(adrlivr, "cplivr").text    = get_info('cplivr', '')

    if agence == "00":
        livr = ET.SubElement(entete, "livr")
        for tag in ["trans","mode","idrelai","departlivr","delailivr","infolivr"]:
            ET.SubElement(livr, tag).text = ""
        ET.SubElement(entete, "tauxwtva").text = "20"

    lignes = ET.SubElement(transaction, "lignes")
    for index, row in data.iterrows():
        create_ligne_xml(lignes, index + 1, row)

    pied = ET.SubElement(transaction, "pied")
    ET.SubElement(pied, "modepaiement").text = "TRANSFER"
    for tag in ["mtport","mtht","remise","mttva","mtttc"]:
        ET.SubElement(pied, tag).text = get_info(tag, "")
    if agence == "00":
        for tag in ["numtvacee","domiciliation","rib","iban","bic"]:
            ET.SubElement(pied, tag).text = ""

    indent_xml(transaction)
    encoding        = "utf-8" if agence == "00" else "ISO-8859-1"
    tree            = ET.ElementTree(transaction)
    xml_body        = BytesIO()
    tree.write(xml_body, encoding=encoding, xml_declaration=False)
    xml_declaration = f'<?xml version="1.0" encoding="{encoding.upper()}"?>\n'.encode(encoding)
    xml_string      = xml_body.getvalue().decode(encoding)
    xml_string      = re.sub(r"<(\w+)(\s*)/>", r"<\1></\1>", xml_string)
    return xml_declaration + xml_string.encode(encoding), numtransaction


# ==================== INTERFACE STREAMLIT ====================
st.title("Générateur de fichiers XML")

# --- Fichier infos ---
infos = load_file("Charger le fichier infos (XLSX)", "xlsx", header=0)
if infos is not None:
    if 'donnee' not in infos.columns or 'valeur' not in infos.columns:
        st.error("Les colonnes 'donnee' et 'valeur' sont absentes du fichier infos.")
        infos = None

# --- Fichier purchase ---
uploaded_purchase = st.file_uploader("Charger le fichier purchase (XLSX)", type="xlsx")
purchase = None

if uploaded_purchase is not None:
    purchase_raw, fmt_detecte = load_purchase_autodetect(uploaded_purchase)

    if fmt_detecte:
        st.success(f"✅ Format détecté automatiquement : **{fmt_detecte}**")
        spec_auto = FORMAT_SPECS[fmt_detecte]

        with st.expander("🔍 Voir / modifier le mapping détecté", expanded=False):
            st.caption("Le mapping a été appliqué automatiquement. Modifiez-le si une colonne est incorrecte.")
            mapping = show_mapping_ui(purchase_raw, spec_auto=spec_auto)

        # Si l'expander n'est pas ouvert, on applique le spec auto directement
        if mapping is None:
            mapping = spec_auto

    else:
        st.warning("⚠️ Format non reconnu. Veuillez mapper les colonnes manuellement.")
        st.markdown("### 🔧 Mapping des colonnes")
        st.caption("Associez chaque champ nécessaire à la colonne correspondante dans votre fichier.")
        mapping = show_mapping_ui(purchase_raw, spec_auto=None)

    if mapping:
        purchase = normalize_purchase(purchase_raw, mapping)
        st.info(f"📋 {len(purchase)} lignes chargées — aperçu :")
        st.dataframe(
            purchase[["_purchase_order","_vendor_ref","_description","_quantite","_prix_unitaire","_discount1","_prixvente"]].head(5),
            use_container_width=True
        )

# --- Autres fichiers ---
stock = load_file("Charger le fichier stock (CSV)", "csv")
tarif = load_file("Charger le fichier tarif (TXT)", "txt")

# --- Génération ---
if infos is not None and purchase is not None and stock is not None and tarif is not None:
    st.success("Tous les fichiers sont chargés.")

    if 'Prix' in tarif.columns:
        tarif = tarif[tarif['Prix'].str.contains(r'^\d', na=False)]
        tarif['Prix'] = tarif['Prix'].str.replace(',', '.').astype(float)
    else:
        st.error("La colonne 'Prix' est absente du fichier tarif.txt.")
        st.stop()

    remise_mapping = {
        row['donnee'].split(': ')[1].strip(): float(row['valeur'])
        for _, row in infos[infos['donnee'].str.contains('remise :', na=False)].iterrows()
    }
    identifiant = infos.loc[infos['donnee'] == 'identifiant', 'valeur'].values[0] \
        if 'identifiant' in infos['donnee'].values else 'INCONNU'

    agence_00 = purchase[purchase['_vendor_ref'].isin(stock['Référence Frn'])]
    agence_A1 = purchase[~purchase['_vendor_ref'].isin(stock['Référence Frn'])]
    st.info(f"🏭 Agence 00 : {len(agence_00)} lignes | Agence A1 : {len(agence_A1)} lignes")

    if st.button("Générer les fichiers XML"):
        xml_00, num_00 = create_xml(agence_00, "00", "KUH1")
        xml_A1, num_A1 = create_xml(agence_A1, "A1", "KUH2")
        st.session_state.update({"xml_00": xml_00, "num_00": num_00, "xml_A1": xml_A1, "num_A1": num_A1})
        st.success("Fichiers XML générés avec succès.")

    if "xml_00" in st.session_state:
        st.header("Téléchargement")
        st.download_button("⬇️ Télécharger agence_00.xml",
            data=st.session_state["xml_00"],
            file_name=f"IN_TRANS_{st.session_state['num_00']}.xml",
            mime="application/xml")
        st.download_button("⬇️ Télécharger agence_A1.xml",
            data=st.session_state["xml_A1"],
            file_name="agence_A1.xml",
            mime="application/xml")
else:
    st.warning("Veuillez charger tous les fichiers nécessaires.")
