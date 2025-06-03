import pandas as pd
import xml.etree.ElementTree as ET
import streamlit as st
from io import BytesIO
import re

# Fonction pour charger les fichiers via Streamlit
def load_file(label, file_type, header=None):
    uploaded_file = st.file_uploader(label, type=file_type)
    header_option = header if header is not None else 0
    if uploaded_file is not None:
        if file_type == "csv":
            return pd.read_csv(uploaded_file, sep=';', dtype={'Fournisseur': str, 'Référence Frn': str}, encoding='latin1')
        elif file_type == "xlsx":
            return pd.read_excel(uploaded_file, header=header_option)
        elif file_type == "txt":
            colspecs = [(0, 10), (10, 20), (20, 30), (30, 36), (36, 44), (44, 69), (69, 84), (84, 94), (94, 102),
                        (102, 105), (105, 109), (109, 115), (115, 119), (119, 134)]
            columns = ['Monnaie', 'Article', 'Prix', 'Remise', 'Date', 'Designation', 'Code EAN', 'Poids',
                       'Societe', 'PDR', 'Qte', 'Cond', 'VoirLP', 'HS Code']
            return pd.read_fwf(uploaded_file, colspecs=colspecs, names=columns, encoding='latin1')
    return None

# Fonction pour indenter l'XML pour une meilleure lisibilité
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

# Fonction pour récupérer une valeur dans infos.xlsx avec une valeur par défaut
def get_info(key, default=""):
    value = infos.loc[infos['donnee'] == key, 'valeur']
    return value.values[0] if not value.empty else default

# Fonction pour créer une ligne XML
def create_ligne_xml(parent, index, row):
    ligne = ET.SubElement(parent, "ligne")
    ET.SubElement(ligne, "NumLigtransaction").text = f"{index:05d}"
    ET.SubElement(ligne, "refagrizone").text = f"{identifiant} {row['Vendor Product Number']}"
    ET.SubElement(ligne, "reffour").text = row['Vendor Product Number']
    ET.SubElement(ligne, "libelle").text = row['Product Description']
    ET.SubElement(ligne, "qte").text = f"{row['Qty Pu']:.2f}"

    # Calcul du prix d'achat
    tarif_row = tarif[tarif['Article'] == row['Vendor Product Number']]
    if not tarif_row.empty:
        prix = float(tarif_row['Prix'].values[0])
        remise_lettre = tarif_row['Remise'].values[0]
        remise_taux = remise_mapping.get(remise_lettre, 0)
        prixachat = round(prix * (1 - remise_taux), 2)
    else:
        prixachat = 0.00

    ET.SubElement(ligne, "prixachat").text = f"{prixachat:.2f}"

    prixventeHT = row['Pu Value'] / row['Qty Pu'] if row['Qty Pu'] != 0 else 0
    ET.SubElement(ligne, "prixventeHT").text = f"{prixventeHT:.2f}"
    ET.SubElement(ligne, "prixventeTTC").text = "0.00"

    if agence == "00":
        ET.SubElement(ligne, "codefour").text = "408"

    ET.SubElement(ligne, "departlivr").text = ""

# Fonction pour créer un fichier XML

def create_xml(data, agence_code, suffix):
    global agence
    agence = agence_code
    transaction = ET.Element("transaction")

    entete = ET.SubElement(transaction, "entetetransaction")
    numtransaction = f"{data.iloc[0]['Purchase Order']}{suffix}" if not data.empty else ""
    ET.SubElement(entete, "numtransaction").text = numtransaction
    ET.SubElement(entete, "passtransaction").text = f"{data.iloc[0]['Purchase Order']}{suffix}" if not data.empty else ""
    ET.SubElement(entete, "agence").text = agence

    if agence == "00":
        ET.SubElement(entete, "code_edo").text = ""
        ET.SubElement(entete, "nivcommande").text = "0"

    adrfact = ET.SubElement(entete, "adrfact")
    ET.SubElement(adrfact, "emailfact").text = "vendor.invoices@kramp.com" if agence == "00" else ""
    ET.SubElement(adrfact, "nomfact").text = get_info('nomfact', 'Nom Facturation Inconnu')
    ET.SubElement(adrfact, "adr1fact").text = get_info('adr1fact', '')
    if agence == "00":
        ET.SubElement(adrfact, "adr2fact").text = ""
        ET.SubElement(adrfact, "adr3fact").text = ""
        ET.SubElement(adrfact, "telephonefact").text = ""
        ET.SubElement(adrfact, "numtva").text = ""
        ET.SubElement(adrfact, "numsiret").text = ""
    ET.SubElement(adrfact, "paysfact").text = get_info('paysfact', '')
    ET.SubElement(adrfact, "villefact").text = get_info('villefact', '')
    ET.SubElement(adrfact, "cpfact").text = get_info('cpfact', '')
    ET.SubElement(adrfact, "code_client").text = get_info('code_client', '')

    adrlivr = ET.SubElement(entete, "adrlivr")
    if agence == "00":
        ET.SubElement(adrlivr, "typadrlivr").text = "CL"
        ET.SubElement(adrlivr, "nominterloclivr").text = get_info('nomadrlivr', '')
    ET.SubElement(adrlivr, "emaillivr").text = "vendor.invoices@kramp.com" if agence == "00" else get_info('emaillivr', '')
    ET.SubElement(adrlivr, "nomadrlivr").text = get_info('nomadrlivr', '')
    ET.SubElement(adrlivr, "adr1livr").text = get_info('adr1livr', '')
    ET.SubElement(adrlivr, "adr2livr").text = get_info('adr2livr', '')
    if agence == "00":
        ET.SubElement(adrlivr, "adr3livr").text = ""
        ET.SubElement(adrlivr, "telephonelivr").text = ""
    ET.SubElement(adrlivr, "payslivr").text = get_info('payslivr', '')
    ET.SubElement(adrlivr, "villelivr").text = get_info('villelivr', '')
    ET.SubElement(adrlivr, "cplivr").text = get_info('cplivr', '')

    if agence == "00":
        livr = ET.SubElement(entete, "livr")
        for tag in ["trans", "mode", "idrelai", "departlivr", "delailivr", "infolivr"]:
            ET.SubElement(livr, tag).text = ""
        ET.SubElement(entete, "tauxwtva").text = "20"

    lignes = ET.SubElement(transaction, "lignes")
    for index, row in data.iterrows():
        create_ligne_xml(lignes, index + 1, row)

    pied = ET.SubElement(transaction, "pied")
    ET.SubElement(pied, "modepaiement").text = "TRANSFER"
    for tag in ["mtport", "mtht", "remise", "mttva", "mtttc"]:
        ET.SubElement(pied, tag).text = get_info(tag, "")
    if agence == "00":
        for tag in ["numtvacee", "domiciliation", "rib", "iban", "bic"]:
            ET.SubElement(pied, tag).text = ""

    indent_xml(transaction)

    encoding = "utf-8" if agence == "00" else "ISO-8859-1"
    tree = ET.ElementTree(transaction)
    xml_body = BytesIO()
    tree.write(xml_body, encoding=encoding, xml_declaration=False)
    xml_declaration = f'<?xml version="1.0" encoding="{encoding.upper()}"?>\n'.encode(encoding)
    xml_string = xml_body.getvalue().decode(encoding)
    # Correction ERP strict : remplacer toutes les balises auto-fermées par balises vides ouvertes/fermées
    xml_string = re.sub(r"<(\w+)(\s*)/>", r"<\1></\1>", xml_string)
    # Ajout de l'en-tête en UTF-8 strict
    final_xml = xml_declaration + xml_string.encode(encoding)
    return final_xml, numtransaction   

# Streamlit UI
st.title("Générateur de fichiers XML")

infos = load_file("Charger le fichier infos (XLSX)", "xlsx", header=0)
if infos is not None:
    if 'donnee' not in infos.columns or 'valeur' not in infos.columns:
        st.error("Les colonnes 'donnee' et 'valeur' sont absentes du fichier infos.")
        infos = None
purchase = load_file("Charger le fichier purchase (XLSX)", "xlsx", header=22)
stock = load_file("Charger le fichier stock (CSV)", "csv")
tarif = load_file("Charger le fichier tarif (TXT)", "txt")

if infos is not None and purchase is not None and stock is not None and tarif is not None:
    st.success("Fichiers chargés avec succès.")

    if 'Prix' in tarif.columns:
        tarif = tarif[tarif['Prix'].str.contains(r'^\d', na=False)]
        tarif['Prix'] = tarif['Prix'].str.replace(',', '.').astype(float)
    else:
        st.error("La colonne 'Prix' est absente du fichier tarif.txt.")

    remise_mapping = {
        row['donnee'].split(': ')[1].strip(): float(row['valeur'])
        for _, row in infos[infos['donnee'].str.contains('remise :', na=False)].iterrows()
    }

    identifiant = infos.loc[infos['donnee'] == 'identifiant', 'valeur'].values[0] if 'identifiant' in infos['donnee'].values else 'INCONNU'

    if 'Vendor Product Number' not in purchase.columns or 'Référence Frn' not in stock.columns:
        st.error("Les colonnes nécessaires ('Vendor Product Number', 'Référence Frn') sont absentes des fichiers chargés.")
    else:
        agence_00 = purchase[purchase['Vendor Product Number'].isin(stock['Référence Frn'])]
        agence_A1 = purchase[~purchase['Vendor Product Number'].isin(stock['Référence Frn'])]

        if st.button("Générer les fichiers XML"):
            xml_00, numtransaction_00 = create_xml(agence_00, "00", "KUH1")
            xml_A1, numtransaction_A1 = create_xml(agence_A1, "A1", "KUH2")
            st.session_state["xml_00"] = xml_00
            st.session_state["numtransaction_00"] = numtransaction_00
            st.session_state["xml_A1"] = xml_A1
            st.session_state["numtransaction_A1"] = numtransaction_A1
            st.success("Les fichiers XML ont été générés avec succès.")


    if "xml_00" in st.session_state and "xml_A1" in st.session_state:
        st.header("Téléchargement des fichiers")
        file_name_00 = f"IN_TRANS_{st.session_state['numtransaction_00']}.xml" if st.session_state.get("numtransaction_00") else "agence_00.xml"
        st.download_button(
            "Télécharger agence_00.xml",
            data=st.session_state["xml_00"],
            file_name=file_name_00,
            mime="application/xml"
        )
        file_name_A1 = f"agence_A1.xml"  # à adapter si tu veux aussi personnaliser ce nom-là
        st.download_button(
            "Télécharger agence_A1.xml",
            data=st.session_state["xml_A1"],
            file_name=file_name_A1,
            mime="application/xml"
        )

else:
    st.warning("Veuillez charger tous les fichiers nécessaires.")
