import pandas as pd
import xml.etree.ElementTree as ET
import streamlit as st
from io import BytesIO

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

# Fonction pour créer un fichier XML
def create_xml(data, agence, suffix):
    transaction = ET.Element("transaction")

    # En-tête de transaction
    entete = ET.SubElement(transaction, "entetetransaction")
    ET.SubElement(entete, "numtransaction").text = f"{data.iloc[0]['Purchase Order']} {suffix}" if not data.empty else ""
    ET.SubElement(entete, "passtransaction").text = f"{data.iloc[0]['Purchase Order']} {suffix}" if not data.empty else ""
    ET.SubElement(entete, "agence").text = agence

    # Informations de facturation
    adrfact = ET.SubElement(transaction, "adrfact")
    ET.SubElement(adrfact, "emailfact").text = ""
    ET.SubElement(adrfact, "nomfact").text = infos.loc[infos['donnee'] == 'nomfact', 'valeur'].values[0] if 'nomfact' in infos['donnee'].values else "Nom Facturation Inconnu"
    ET.SubElement(adrfact, "adr1fact").text = infos.loc[infos['donnee'] == 'adr1fact', 'valeur'].values[0] if 'adr1fact' in infos['donnee'].values else ""
    ET.SubElement(adrfact, "paysfact").text = infos.loc[infos['donnee'] == 'paysfact', 'valeur'].values[0] if 'paysfact' in infos['donnee'].values else ""
    ET.SubElement(adrfact, "villefact").text = infos.loc[infos['donnee'] == 'villefact', 'valeur'].values[0] if 'villefact' in infos['donnee'].values else ""
    ET.SubElement(adrfact, "cpfact").text = infos.loc[infos['donnee'] == 'cpfact', 'valeur'].values[0] if 'cpfact' in infos['donnee'].values else ""

    # Section lignes
    lignes = ET.SubElement(transaction, "lignes")
    for index, row in data.iterrows():
        ligne = ET.SubElement(lignes, "ligne")
        ET.SubElement(ligne, "NumLigtransaction").text = f"{index + 1:05d}"
        ET.SubElement(ligne, "refagrizone").text = f"Ref-{row['Product Number']}"

    # Indenter et convertir en bytes
    indent_xml(transaction)
    tree = ET.ElementTree(transaction)
    xml_data = BytesIO()
    tree.write(xml_data, encoding="ISO-8859-1", xml_declaration=True)
    return xml_data.getvalue()

# Streamlit UI
st.title("Générateur de fichiers XML")

# Charger les fichiers
infos = load_file("Charger le fichier infos (XLSX)", "xlsx")
if infos is not None:
    if 'donnee' not in infos.columns or 'valeur' not in infos.columns:
        st.error("Les colonnes 'donnee' et 'valeur' sont absentes du fichier infos.")
        infos = None
purchase = load_file("Charger le fichier purchase (XLSX)", "xlsx")
stock = load_file("Charger le fichier stock (CSV)", "csv")
tarif = load_file("Charger le fichier tarif (TXT)", "txt")

if infos is not None and purchase is not None and stock is not None and tarif is not None:
    st.success("Fichiers chargés avec succès.")

    # Vérifier les colonnes nécessaires
    if 'Product Number' not in purchase.columns or 'Référence Frn' not in stock.columns:
        st.error("Les colonnes nécessaires ('Product Number', 'Référence Frn') sont absentes des fichiers chargés.")
    else:
        # Diviser les données
        agence_00 = purchase[purchase['Product Number'].isin(stock['Référence Frn'])]
        agence_A1 = purchase[~purchase['Product Number'].isin(stock['Référence Frn'])]

        # Bouton pour générer les XML
        if st.button("Générer les fichiers XML"):
            xml_00 = create_xml(agence_00, "00", "KUH1")
            xml_A1 = create_xml(agence_A1, "A1", "KUH2")

            # Téléchargement des fichiers
            st.download_button("Télécharger agence_00.xml", data=xml_00, file_name="agence_00.xml", mime="application/xml")
            st.download_button("Télécharger agence_A1.xml", data=xml_A1, file_name="agence_A1.xml", mime="application/xml")
else:
    st.warning("Veuillez charger tous les fichiers nécessaires.")
