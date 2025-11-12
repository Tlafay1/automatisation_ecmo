import unicodedata
import fitz  
import re
from datetime import datetime, timedelta
from pypdf import PdfMerger, PdfWriter, PdfReader
import os
from dateutil.relativedelta import relativedelta
from threading import Event
from queue import Queue


# Il faudra à chaque fois mettre les noms de fichiers en miniscules
# Et également voir s'il n'y a pas une corespondance en remplaçant les espaces par des tirets
# Cela servira pas nécessairement à faire tourner le programme, c'est plus utile pour la détection d'erreurs potentielles
# du programme. 
# Utiliser un dictionnaire pour faire correspondre chaque document à une clé unique
assembly_docs = {
    "Feuille de présence": ["feuille de présence"],
    "Procès-verbal de l'assemblée générale": ["proces verbal des decisions", "pv ag", 
                                              "pv", "procès-verbal de l'assemblée générale", "ag",
                                              "procès-verbal", "proces verbal"],
    "Rapport spécial": ["rapport spécial"],
    "Rapport de gestion" : ["rapport de gestion"],
    "Déclaration de confidentialité": ["déclaration de confidentialité"],
    "Attestation de conformité et de pouvoir": ["attestation de conformité et de pouvoir"],
    "Texte des décisions d'affectation du résultat": [
        "texte des decisions daffectation du resultat",
        "texte des décisions d affectation du résulat",
        "affectation du resultat",
        "affectation"
    ],
    "Etat des conventions" : ["Etat des conventions"],
    "Pouvoir pour les formalités": ["pouvoir pour les formalités", "pouvoir"],
    "Certificat de dépôt des comptes annuels": ["certificat de dépôt", "certificat de dépôt des comptes annuels", "certificat de dépôt d'actes"],
    "Statuts": ["statuts", "statuts mis à jour"],
    "Extrait Kbis": ["extrait kbis", "kbis"],
    "Attestation de parution": ["attestation de parution"],
    "Liste des anciens sièges": ["liste des anciens sièges", "siege"],
    "Certificat de dépôt d'actes" : ["certificat de dépôt d'actes", "certificat de depot d'actes"],
    "Autorisation de domiciliation": ["autorisation de domiciliation", "domiciliation"],
    "Déclaration de non-condamnation": ["déclaration de non-condamnation", "dnc", "non-condamnation", "condamnation"],
    "Annonce légale": ["annonce légale", "annonce"],
    "Registre des bénéficiaires effectifs": ["registre des bénéficiaires effectifs", "beneficiaire"],
    "Imprimé M2 (CERFA 11682)": ["imprimé M2 (CERFA 11682)", "M2", "cerfa 11682", "imprimé M2", "11682"],
    "Acte de cession": ["acte", "acte modificatif", "acte de cession", "cession"]
}


#Structure json de la plaquette à remplir
plaquette = {
    "Structure" : {
        "Forme Juridique" : False,
        "Raison sociale" : False,
        "Capital social" : False,
        "Adresse" : {
            "Rue":  False,
            "Code postal" : False,
            "Ville" : False,
        },
        "Exercice clos le" : False,
        "Exercice comptable" : False,
        "Date de l'AGE" : False
    },
    "AGO" : {
        "Fixation de la rémunération gérance" : {
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            }
        },
        "Abandon de créance" : {
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            }
        },
        "Approbation des comptes" : {
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False,
            },
            "Documents relatifs à l'approbation des comptes" : {
                "Attestation de conformité et de pouvoir" : False,
                "Rapport spécial" : False,
                "Etat des conventions" : False,
                "Rapport de gestion": False,
                "Déclaration de confidentialité" : False,
                "Texte des décisions d'affectation du résultat" : False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation": {
                "Certificat de dépôt des comptes annuels" : False
            }
        }
    },
    "AGE" : {
        "Transfert de siège social" : {
            "Statuts" : {
                "Statuts mis à jour" : False
            },
            "Assemblée générale extraordinare" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs au changement de dirigeant" : {
                "Attestation de parution" : False,
                "Autorisation de domiciliation" : False,
                "Liste des anciens sièges" : False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Certificat de dépôt d'actes" : False
            }
        },
        "Changement de dirigeant" : {
            "Statuts" : {
                "Statuts mis à jour" : False
            },
            "Assemblée générale extraordinare" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs au changement de dirigeant" : {
                "Attestation de parution" : False,
                "Déclaration de non-condamnation" : False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Certificat de dépôt d'actes" : False
            }
        },
        "Perte de la moitié du capital social" : {
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs à la perte de la moitié du capital social" : {
                "Pouvoir pour les formalités" : False,
                "Annonce légale" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Registre des bénéficiaires effectifs" : False,
                "Certificat de dépôt d'acte" : False
            }
        },
        "Reconstitution des capitaux propres" : {
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Registre des bénéficiaires effectifs" : False,
                "Certificat de dépôt d'actes" : False
            }
        },
        "Changement de dénomination sociale" : {
            "Statuts" : {
                "Statuts mis à jour" : False
            },
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs au changement de dénomination" : {
                "Attestation de parution" : False,
                "Imprimé M2 (CERFA 11682)": False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Registre des bénéficiaires effectifs" : False,
                "Certificat de dépôt d'actes" : False
            }
        },
        "Modification de la date de clôture de l'exercice social" : {
            "Statuts" : {
                "Statuts mis à jour" : False
            },
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs au changement de dénomination" : {
                "Acte" : False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Registre des bénéficiaires effectifs" : False,
                "Certificat de dépôt d'actes" : False
            }
        },
        "Cession de parts sociales" : {
            "Statuts" : {
                "Statuts mis à jour" : False
            },
            "Assemblée générale" : {
                "Feuille de présence" : False,
                "Procès-verbal de l'assemblée générale" : False
            },
            "Documents relatifs à la cession de parts sociales" : {
                "Acte de cession" : False,
                "Pouvoir pour les formalités" : False
            },
            "Documents de validation" : {
                "Extrait Kbis" : False,
                "Registre des bénéficiaires effectifs" : False,
                "Certificat de dépôt d'actes" : False
            }
        }
    }   
}

def normalize_filename(name):
    name = name.lower().replace("-", " ")
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = name.replace("’", "'").replace("’", "'").replace("œ", "oe")
    return name.strip()

def doc_in_assembly_docs(doc):
    doc_norm = normalize_filename(doc)
    for key, aliases in assembly_docs.items():
        for assembly_doc in [normalize_filename(alias) for alias in aliases]:
            if assembly_doc in doc_norm or doc_norm in assembly_doc : 
                return key
    return None

def extract_date_from_string(folder_name: str) -> str | None:
    """
    Extrait une date d'un nom de dossier et la renvoie sous le format jj/mm/yyyy.
    Reconnaît : jj.mm.yyyy, jj-mm-yyyy, jj/mm/yyyy, yyyy-mm-dd, yyyy.mm.dd, yyyy/mm/dd.
    Retourne None si aucune date valide n'est trouvée.
    """

    # Motifs possibles
    patterns = [
        r"(\d{2})[.\-/](\d{2})[.\-/](\d{4})",  # jj.mm.yyyy ou jj-mm-yyyy ou jj/mm/yyyy
        r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})",  # yyyy.mm.dd ou yyyy-mm-dd ou yyyy/mm/dd
    ]

    for pattern in patterns:
        match = re.search(pattern, folder_name)
        if match:
            try:
                if len(match.group(1)) == 4:  # yyyy-mm-dd
                    year, month, day = match.group(1), match.group(2), match.group(3)
                else:  # jj-mm-yyyy
                    day, month, year = match.group(1), match.group(2), match.group(3)

                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime("%d/%m/%Y")
            except ValueError:
                continue  # Si la date est invalide (ex: 31/02/2023), on passe
    return None

def extraire_annee(text):
    # Cherche une année entre 1900 et 2099
    matches = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    if matches:
        return int(matches[0])  # retourne la première année trouvée
    return None

def empty_plaquette(plaquette):
    """
    Réinitialise la plaquette sauf les clés de la structure.
    """
    for key in plaquette.keys():
        if key != "Structure" and key != "nom":
            for sub_key in plaquette[key].keys():
                if isinstance(plaquette[key][sub_key], dict):
                    for sub_sub_key in plaquette[key][sub_key].keys():
                        if isinstance(plaquette[key][sub_key][sub_sub_key], dict):
                            for sub_sub_sub_key in plaquette[key][sub_key][sub_sub_key]:
                                    plaquette[key][sub_key][sub_sub_key][sub_sub_sub_key] = False
                        else:
                            plaquette[key][sub_key][sub_sub_key] = False

def extraire_duree_exercice(text):
    match = re.search(r"\*Durée de l'exercice en nombre de mois \* (\d{1,2})", text)
    if match:
        duree = match.group(1)
        print(f"Durée de l'exercice trouvée : {duree} mois")
        return duree
    else:
        print("⚠️ Durée de l'exercice non trouvée.")
        return None
                                
def date_debut_exercice(AG_dossier_path, exercice_clos, entreprise, window):
    duree_exercice = None
    if AG_dossier_path:
        for document in os.listdir(AG_dossier_path):
            file_path = os.path.join(AG_dossier_path, document)
            
            if os.path.isfile(file_path) and document.endswith(".pdf"):
                if normalize_filename("Bilan") in normalize_filename(document):
                    print(f"{document} trouvé !")
                    reader = PdfReader(file_path)
                    
                    if len(reader.pages) > 0:
                        first_page = reader.pages[0]
                        text = first_page.extract_text()
                        duree_exercice = extraire_duree_exercice(text)
        
        if not duree_exercice:
            print("⚠️ Durée de l'exercice non trouvée dans les documents PDF.")
            
            result_queue = Queue()

            # Envoie la demande au thread principal via le signal
            window.ask_question_signal.emit(
                f"Quel est la durée de l'exercice clos {exercice_clos} de {entreprise} ?", result_queue
            )

            # Attend que la réponse soit mise dans la queue
            response = result_queue.get()

            if response is None:
                window.log_page.log("Aucune réponse donnée, annulation.")
                return
            else:
                window.log_page.log(f"Réponse donnée : {response}")
                duree_exercice = response.strip()
                    
        try:
            print(f"Durée de l'exercice : {duree_exercice} mois, ", type(duree_exercice))
            duree_exercice = int(duree_exercice)
            fin_exercice = datetime.strptime(exercice_clos, "%d/%m/%Y")
            print(f"Date de fin d'exercice : {fin_exercice}")
            debut_exercice = fin_exercice - relativedelta(months=duree_exercice) + relativedelta(days=1)
            return debut_exercice.strftime("%d/%m/%Y")
        
        except ValueError:
            print("⚠️ Erreur de conversion de la durée de l'exercice.")
            return "None"
    return "None"

def fusionner_pdfs(pdfs: list[str], sortie: str) -> None:
    writer = PdfWriter()

    for pdf_path in pdfs:
        reader = PdfReader(pdf_path)
        # ajoute toutes les pages du reader dans le writer
        for page in reader.pages:
            writer.add_page(page)

    # écrit le résultat
    with open(sortie, "wb") as f_out:
        writer.write(f_out)
        
def is_empty_plaquette(plaquette):
    for key in plaquette.keys():
        if key != "Structure" and key != "nom":  
            # Ex : AGO
            for sub_key in plaquette[key].keys():
                # Ex : Approbation des comptes
                if isinstance(plaquette[key][sub_key], dict):
                    for sub_sub_key in plaquette[key][sub_key].keys():
                        # Ex : Assemblée générale
                        if isinstance(plaquette[key][sub_key][sub_sub_key], dict):
                            for sub_sub_sub_key in plaquette[key][sub_key][sub_sub_key].keys():
                                #Ex : Feuille de présence
                                if plaquette[key][sub_key][sub_sub_key][sub_sub_sub_key] :
                                    return False
                        else:
                            if plaquette[key][sub_key][sub_sub_key] :
                                return False
    return True

def count_pdf_pages(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        print(f"Erreur lors de la lecture du PDF {pdf_path}: {e}")
        return 0
    
    
def extract_partial_date_from_filename(file_path):
    file_name = normalize_filename(os.path.basename(file_path))
    file_name = file_name.replace(".pdf", "")
    
    # Recherche motif avec jour, mois, année (ex: 13 Mai 2023)
    match = re.search(r"(\d{1,2}) (\w+) (\d{4})", file_name)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        return (day, month_name, year)

    # Recherche motif jour et mois (ex: 13 Mai)
    match = re.search(r"(\d{1,2}) (\w+)", file_name)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        return (day, month_name, None)

    # Recherche motif mois et année (ex: Mai 2023)
    match = re.search(r"(\w+) (\d{4})", file_name)
    if match:
        month_name = match.group(1).lower()
        year = int(match.group(2))
        return (None, month_name, year)

    # Recherche motif 13-05-2023
    match = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", file_name)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        return (day, month, year)

    # Recherche motif 2023-05-13
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", file_name)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return (day, month, year)

    # Recherche motif 2023-05
    match = re.search(r"(\d{4})-(\d{1,2})", file_name)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        return (None, month, year)
    return None


def normalize_month(month_str):
    mois_fr_map = {
        "janvier": 1, "janv": 1, "jan": 1,
        "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "fév": 2, "fev": 2,
        "mars": 3, "mar": 3,
        "avril": 4, "avr": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7, "juil": 7, "jui": 7,
        "août": 8, "aout": 8, "aoû": 8, "aou": 8,
        "septembre": 9, "sept": 9, "sep": 9,
        "octobre": 10, "oct": 10,
        "novembre": 11, "nov": 11,
        "décembre": 12, "decembre": 12, "déc": 12, "dec": 12
    }
    # Normalisation unicode + minuscules
    month_str = unicodedata.normalize('NFKD', month_str).encode('ASCII', 'ignore').decode('ASCII').lower()
    return mois_fr_map.get(month_str)


def date_doc_search(file_path):
    reader = PdfReader(file_path)
    text = reader.pages[0].extract_text() or ""

    # Autorise lettres accentuées + insensible à la casse
    m = re.search(r'\b(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})\b', text, flags=re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month_str = m.group(2)
        year = int(m.group(3))

        # normaliser pour mapping
        month_norm = normalize_month(month_str)
        if month_norm:
            try:
                return datetime(year, month_norm, day)
            except ValueError:
                print(f"⚠️ Date invalide trouvée : {day} {month_str} {year}")
    return None

def extract_AG_date(file_path):
    partial_date = extract_partial_date_from_filename(file_path)
    doc_date = date_doc_search(file_path)  # datetime ou None

    if partial_date is None:
        print(f"ℹ️ Aucune date trouvée dans le nom du fichier {file_path}.")
        return None

    day, month, year = partial_date  # day peut être None, month peut être str ou int, year peut être None

    # Normaliser le mois
    if isinstance(month, str): 
        month = normalize_month(month)
        if month is None:
            print(f"⚠️ Mois '{month}' non reconnu dans le nom du fichier {file_path}.")
            return None

    # Si année manquante dans le nom, essayer avec doc_date
    if year is None:
        if doc_date:
            year = doc_date.year
        else:
            print("⚠️ Impossible de déterminer l'année, ni dans le nom ni dans le document.")
            return None

    # Vérifier la cohérence avec la date dans le document
    if doc_date:
        # Si jour dans nom présent, on compare jour+mois+année, sinon juste mois+année
        if day is not None:
            if day != doc_date.day or month != doc_date.month or year != doc_date.year:
                print(f"❗ Incohérence entre nom de fichier et contenu du PDF dans {file_path}.")
                print(f"   Nom fichier: {day}/{month}/{year} vs Doc: {doc_date.day}/{doc_date.month}/{doc_date.year}")
                return None
        else:
            # Pas de jour dans nom, on compare mois et année uniquement
            if month != doc_date.month or year != doc_date.year:
                print(f"❗ Incohérence entre nom de fichier et contenu du PDF dans {file_path} (mois/année).")
                return None
    else:
        print(f"ℹ️ Pas de date extraite du contenu du PDF pour {file_path}.")

    # Construire la date finale en string jj/mm/aaaa (si jour manquant, on met 01)
    if day is None:
        day = 1

    try:
        date_obj = datetime(year, month, day)
        return date_obj.strftime("%d/%m/%Y")
    except ValueError:
        print(f"⚠️ Date invalide formée avec les infos extraites : {day}/{month}/{year}")
        return None


def AGO_type_by_date(file_path, AG_date_json, debut_exercice, fin_exercice):
    """
    Rempli AG_date_json avec les dates des documents de l'AGO
    """
    AG_date_str = extract_AG_date(file_path)

    try:
        debut_exercice_obj = datetime.strptime(debut_exercice, "%d/%m/%Y").date()

        if len(fin_exercice.split("/")) == 2:  # format "jj/mm"
            # On ajoute l'année de début_exercice
            fin_exercice = f"{fin_exercice}/{debut_exercice_obj.year}"

        fin_exercice_obj = datetime.strptime(fin_exercice, "%d/%m/%Y").date()
    except ValueError:
        print(f"⚠️ Erreur de format de date pour les exercices : {debut_exercice} ou {fin_exercice}")
        return None

    
    if AG_date_str is None:
        print(f"⚠️ Date extraite invalide ou inexistante pour {file_path}")
        return None

    try:
        AG_date_obj = datetime.strptime(AG_date_str, "%d/%m/%Y").date()
    except ValueError:
        print(f"⚠️ Erreur de format de date pour '{AG_date_str}'")
        return None

    try: 
        debut_exercice_obj = datetime.strptime(debut_exercice, "%d/%m/%Y").date()
        fin_exercice_obj = datetime.strptime(fin_exercice, "%d/%m/%Y").date()
    except ValueError:
        print(f"⚠️ Erreur de format de date pour les exercices : {debut_exercice} ou {fin_exercice}")
        return None

    # Définition des périodes pour une meilleure lisibilité
    periode_remuneration = (debut_exercice_obj - timedelta(days=30), debut_exercice_obj + timedelta(days=30))
    periode_abandon = (fin_exercice_obj - timedelta(days=30), fin_exercice_obj)
    periode_approbation = (fin_exercice_obj + timedelta(days=1), fin_exercice_obj + timedelta(days=180))

    if periode_remuneration[0] <= AG_date_obj <= periode_remuneration[1]:
        AG_date_json["Fixation de la rémunération gérance"] = AG_date_obj
        return "Fixation de la rémunération gérance"

    if periode_abandon[0] <= AG_date_obj <= periode_abandon[1]:
        AG_date_json["Abandon de créance"] = AG_date_obj
        return "Abandon de créance"

    if periode_approbation[0] <= AG_date_obj <= periode_approbation[1]:
        AG_date_json["Approbation des comptes"] = AG_date_obj
        return "Approbation des comptes"
    return None

def filter_client_name(client):
    # On filtre le nom du client pour enlever les préfixes
    if client.lower()[:3] in ["sc "]:
        return client[3:]
    if client.lower()[:4] in ["sci ", "scm ", "sas "]:
        return client[4:]        
    if client.lower()[:5] in ["sasu ", "sarl ", "eurl "]:
        return client[5:]      
    if client.lower()[:7] in ["selarl "]:
        return client[7:]
    return client

def search_client(directory, database):
    # il faut retrouver le nom d'un client dans une chaîne de caractère comme celle-ci :
    # C:/Users/noahl/OneDrive - Centrale Lille/Documents/Automatisation ECMO/JURIDIQUE/GREGGO PIZZA/AGO 31.12.2017
    # On sélectionne le texte entre les / et on vérifie la database

    for part in directory.replace("\\", "/").split("/"):
        client = filter_client_name(part)
        client = client.upper()

        special_clients = {
            "ARCHEA" : "BERJA.D'AMENAGEMENT",
            "ONE" : "OPTIMISATION NUTRITION ENFANCE",
            "TPC" : "TIXIER PLOMBERIE CHAUFFAGE"
        }
        for key, value in special_clients.items():
            if client == key:
                client = value

        client_id = database.get_entreprise_id_by_name(client)
        if client_id:
            return client_id
    return None

aliases = {
    "Reconstitution des capitaux propres": ["reconstitution des capitaux propres", "reconstitution"],
    "Transfert de siège social": ["transfert de siège social", "transfert"],
    "Changement de dirigeant": ["changement de dirigeant", "dirigeant"],
    "Perte de la moitié du capital social": ["perte de la moitié du capital social", "perte de capital"]
}

def match(list2):
    for key, alias_list in aliases.items():
        for alias in alias_list:
            for item2 in list2:
                if normalize_filename(alias) in normalize_filename(item2) or normalize_filename(item2) in normalize_filename(alias):
                    return key
    return None

def remove_pdfs(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory, filename)
            try:
                os.remove(file_path)
                print(f"🗑️ Fichier supprimé : {file_path}")
            except Exception as e:
                print(f"⚠️ Erreur lors de la suppression de {file_path} : {e}")
                

    