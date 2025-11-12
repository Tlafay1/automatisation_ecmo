from queue import Queue
import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt
from datetime import datetime
import locale
from pypdf import PdfMerger, PdfReader, PdfWriter
from utils import (plaquette, extraire_annee, is_empty_plaquette,
                   date_debut_exercice, doc_in_assembly_docs, 
                   empty_plaquette, fusionner_pdfs, normalize_filename,
                   count_pdf_pages, extract_AG_date, AGO_type_by_date,
                   search_client, filter_client_name, match, remove_pdfs,
                   extract_date_from_string)
from latex import compiler_latex
import copy
import re
from dateutil.relativedelta import relativedelta

plaquette_copy = copy.deepcopy(plaquette)
try:
    locale.setlocale(locale.LC_TIME, 'French_France')  # Windows
except locale.Error:
    print("⚠️ Impossible de définir la locale française.")


formes_juridiques = [
    "SARL", "SAS", "SCI", "SCM", "SC", "SELARL", "EURL", "SASU"
]

# Bonne idée, faire plusieurs modes : 
# 1. Mode ultra-manuel : On choisi son AG et les documents à mettre dedans avec le nom qu'ils ont (ça ajoute dans le excel
# ce qui a été fait, pas forcément évident)
# 2. Mode semi-auto : On choisi les dossiers précis où sont les AG que l'on veut faire. Ex : CHEMGO -> AGO 31.12.2024
# 3. Mode auto : On ne touche à rien, tout se fait à partir de l'historique déjà rempli des plaquettes.

# Il faut une fonction pause et redémarrer le programme en cas de problème dans la base de données
# Il faut faire une page d'accueil dans l'interface pour choisir le mode de fonctionnement, démarrer, mettre sur pause, redémarrer

## A faire : automatiquement ajouter une modification à la base de donnée dans le cas des AGE.
## A faire : Ajouter un démarrage/redémarrage du programme depuis l'appli en cas d'erreur dans la bdd/choses à modifier

# Il faut également réussir à séparer les AGOs des AGE 
# Les AGOs vont ensembles et les AGEs sont toutes séparés (tout trié par entreprise bien sûr)


def fill_plaquette_structure(plaquette_to_edit, entreprise_id, database):
    # On rempli la data dans plaquette_to_edit
    plaquette_to_edit["Structure"]["Raison sociale"] = database.get_entreprise_name_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Forme Juridique"] = database.get_entreprise_juridique_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Capital social"] = database.get_entreprise_capital_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Adresse"]["Rue"] = database.get_entreprise_adresse_rue_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Adresse"]["Code postal"] = database.get_entreprise_adresse_code_postal_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Adresse"]["Ville"] = database.get_entreprise_adresse_ville_by_id(entreprise_id)
    plaquette_to_edit["Structure"]["Exercice clos le"] = database.get_entreprise_exercice_clos_by_id(entreprise_id)  
    
def fill_plaquette_date(fin_exercice, AG_dossier_filtered, plaquette_name, AG_type, plaquette_to_edit, dossier_path, client, window):
    if fin_exercice in AG_dossier_filtered:
        
        year = extraire_annee(AG_dossier_filtered)
        
        if AG_type == "AGO":
            plaquette_name["value"] += f"-{AG_type}-{year}"
            fin_exercice = fin_exercice + "/" + str(year)

        if AG_type == "AGE":
            # Dans le cas d'une AGE, c'est la date qui est mise dans le dossier. Or, si elle a été produite le 03/03 mais que la clôture d'exercice est le 28/02, il faudra mettre year+1
            # on extrait la date dans AG_dossier_filtered, elle est sous deux formats possibles : jj/mm/yyyy ou yyyy/mm/jj il faut également remplacer les / par des . ou -


            # Exemple : AG_dossier_filtered contient le nom du dossier
            extracted_date = extract_date_from_string(AG_dossier_filtered)

            if extracted_date :
                # Construction de la date de clôture (28/02/yyyy)
                closure_date = datetime.strptime(fin_exercice + f"/{extracted_date.year}", "%d/%m/%Y")

                if extracted_date > closure_date:
                    fin_exercice = fin_exercice + "/" + str(extracted_date.year + 1)
                else:
                    fin_exercice = fin_exercice + "/" + str(extracted_date.year)


        date_obj = datetime.strptime(fin_exercice, "%d/%m/%Y")
        date_formatee = date_obj.strftime("%d %B %Y")  
        plaquette_to_edit["Structure"]["Exercice clos le"] = date_formatee
        
        # On récupère la date de début. C'est mis ici pour ne pas demander à l'utilisateur de
        # La saisir si la plaquette est incorrecte
        debut_exercice = date_debut_exercice(dossier_path, fin_exercice, client, window)
        if debut_exercice:
            plaquette_to_edit["Structure"]["Exercice comptable"] = "Du " + \
                debut_exercice + " au " + fin_exercice
        
            if AG_type == "AGE":
                result_queue = Queue()
                window.ask_question_signal.emit("Quelle est la date de l'assemblée générale extraordinaire ? (Format : jj/mm/aaaa)", result_queue)
                response = result_queue.get()

                # On vérifie le format et repose la question s'il est incorrect
                while not re.match(r"^\d{2}/\d{2}/\d{4}$", response):
                    result_queue = Queue()
                    window.ask_question_signal.emit("Format incorrect. Quelle est la date de l'assemblée générale extraordinaire ? (Format : jj/mm/aaaa)", result_queue)
                    response = result_queue.get()
                
                plaquette_to_edit["Structure"]["Date de l'AGE"] = response

                year = response.split("/")[-1]
                plaquette_name["value"] += f"-{AG_type}-{response.replace('/', '-')}"
            return True
        else : 
            return False

def type_and_assembly_doc(doc, assembly_doc, doc_path, AG_date_json, debut_exercice, fin_exercice, window, AG_type):
    if AG_type == "AGO":
        if assembly_doc == "Feuille de présence" or assembly_doc == "Procès-verbal de l'assemblée générale":
            AG_date = extract_AG_date(doc_path)
            if "remuneration" in normalize_filename(doc) or "gerance" in normalize_filename(doc):
                AGO_type = "Fixation de la rémunération gérance"
            elif "abandon" in normalize_filename(doc) or "creance" in normalize_filename(doc):
                AGO_type = "Abandon de créance"
            elif AG_date:
                # On prend le format jj/mm/yyyy de la date
                # On regarde si c'est proche typiquement, si c'est plus de trois mois après la clôture,
                # c'est un approbationd des comptes, si c'est au début de l'exercice, c'est une rémunération, etc.
                # La fonction AGO_sub_type permet de déterminer le type d'assemblée générale et modifier AG_date_json
                # Elle retourne le type de l'assemblée générale ordinaire
                print(f"Fichier avec AG_date trouvé : {doc}. AG_date : {AG_date}")
                AGO_type = AGO_type_by_date(doc_path, AG_date_json, debut_exercice, fin_exercice)
            else :
                AGO_type = "Approbation des comptes"
            return (AGO_type, "Assemblée générale")
        else :
            return ("Approbation des comptes", "Documents relatifs à l'approbation des comptes")
    elif AG_type == "AGE":
        
        AG_sub_type = match(doc_path.split("/"))
        
        # Trouve la clé correspondant à la valeur assembly_doc dans plaquette_copy["AGE"]
        AG_sub_sub_type = None
        for key, sub_dict in plaquette_copy["AGE"].items():
            for sub_key, docs_dict in sub_dict.items():
                for doc_key in docs_dict.keys():
                    if doc_key == assembly_doc:
                        AG_sub_sub_type = key
                    break
        if AG_sub_type and AG_sub_sub_type:
            return (AG_sub_type, AG_sub_sub_type)
        else :
            window.log_emitter.log_signal.emit(f"⚠️ Impossible de déterminer le type de l'AGE pour le document {doc}. Veuillez le faire manuellement.")
            return None

def traiter_document(doc, assembly_doc, plaquette, doc_path, window, AG_date_json, debut_exercice, fin_exercice, AG_type):
    if doc.endswith(".pdf"):
        AG_sub_type, AG_sub_sub_type = type_and_assembly_doc(doc, assembly_doc, doc_path, AG_date_json, debut_exercice, fin_exercice, window, AG_type)
        if AG_sub_type :
            plaquette[AG_type][AG_sub_type][AG_sub_sub_type][assembly_doc] = doc_path

def traiter_documents_non_signes(AG_dossier_path, client_doc, plaquette, window, AG_dossier, AG_date_json, debut_exercice, fin_exercice, AG_type):
    client_docs_path = os.path.join(AG_dossier_path, client_doc)
    AG_sub_type = None
    if os.path.isdir(client_docs_path):
        if client_doc == "Rémunération gérance" or "gerance" in normalize_filename(client_doc):
            AG_sub_type = "Fixation de la rémunération gérance"
        elif client_doc == "Abandon de créance" or "abandon" in normalize_filename(client_doc):
            AG_sub_type = "Abandon de créance"
        if AG_sub_type:
            for AG_docs in os.listdir(client_docs_path):
                assembly_doc = doc_in_assembly_docs(AG_docs)
                AG_docs_path = os.path.join(client_docs_path, AG_docs)
                if AG_docs.endswith(".pdf") and assembly_doc:
                    plaquette[AG_type][f"{AG_sub_type}"]["Assemblée générale"][f"{assembly_doc}"] = AG_docs_path
                    
    if not os.path.isdir(client_docs_path) :     
    # Détection totale, on identifie également les noms "gérance", "abandon", ...
        assembly_doc = doc_in_assembly_docs(client_doc)
        if assembly_doc:
            traiter_document(client_doc, assembly_doc, plaquette, client_docs_path, window, AG_date_json, debut_exercice, fin_exercice, AG_type)

def traiter_documents_signes(folder_path, unsigned_plaquette, plaquette_to_edit, window, AG_dossier, AG_date_json, debut_exercice, fin_exercice, AG_type):
    # On regarde si le dossier contient des documents signés et on rempli plaquette_to_edit
    # Aussi on suppose qu'il n'y a que des approbations des comptes dans les dossiers signés
    # Ce qui n'est pas la réalité mais on va faire avec pour l'instant
        
    for signed_doc in os.listdir(folder_path):
        signed_doc_path = os.path.join(folder_path, signed_doc)
        # Ici on vérifie seulement que le nom du fichier signé contient le nom de l'assemblée
        
        assembly_doc = doc_in_assembly_docs(signed_doc)
        count = True
        if assembly_doc :
            AG_sub_type, AG_sub_sub_type = type_and_assembly_doc(signed_doc, assembly_doc, signed_doc_path, AG_date_json, debut_exercice, fin_exercice, window, AG_type)
            if AG_sub_type is None:
                continue
            if unsigned_plaquette[AG_type][AG_sub_type][AG_sub_sub_type][assembly_doc] :
                if count_pdf_pages(signed_doc_path) != count_pdf_pages(unsigned_plaquette[AG_type][AG_sub_type][AG_sub_sub_type][assembly_doc]):
                    # Le nombre de pages est différent, on ne peut pas le traiter
                    window.log_emitter.log_signal.emit(f"Le document signé {signed_doc} n'a pas le même nombre de pages que le document non signé.")
                    count = False
            else :
                window.log_emitter.log_signal.emit(f"Document signé trouvé mais pas son équivalent non signé : {signed_doc}. Il sera tout de même ajouté.")
            if count:
                traiter_document(signed_doc, assembly_doc, plaquette_to_edit, signed_doc_path, window, AG_date_json, debut_exercice, fin_exercice, AG_type)

def show_produced_plaquette(plaquette, window):
    # Affiche le contenu de la plaquette dans l'interface
    for key, value in plaquette.items():
        if key != "Structure" and key != "nom":
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            if isinstance(sub_sub_value, dict):
                                for doc_key, doc_value in sub_sub_value.items():
                                    if doc_value:
                                        doc_name = os.path.basename(doc_value)
                                        window.log_emitter.log_signal.emit(f"{key} - {sub_key} - {sub_sub_key} - {doc_key} : {doc_name} ajouté à la plaquette.")

def check_plaquette_structure(plaquette_to_edit, window, AG_type):
    for key, value in plaquette_to_edit["Structure"].items():
        if AG_type == "AGO" and key == "Date de l'AGE":
            continue
        if value is False: 
            window.log_emitter.log_signal.emit(f"Information manquante dans la plaquette : {key}. Veuillez vérifier la base de données et redémarrer le programme.")
            return False
    return True

def fill_plaquette(AG_dossier_path, plaquette_to_edit, database, entreprise_id, window, plaquette_name, AG_date_json):

    client = database.get_entreprise_name_by_id(entreprise_id)
    AG_dossier = os.path.basename(AG_dossier_path)
    AG_dossier_filtered = AG_dossier.replace(".", "/").replace("-", "/").replace("_", "/")

    if "AG" in AG_dossier:
        fin_exercice = database.get_entreprise_exercice_clos_by_id(entreprise_id)
        if "AGO" in AG_dossier:
            if fill_plaquette_date(fin_exercice, AG_dossier_filtered, plaquette_name, "AGO", plaquette_to_edit, AG_dossier_path, client, window):
                if database.find_assembly(entreprise_id, fin_exercice, "AGO"):
                    window.log_emitter.log_signal.emit("L'assemblée générale ordinaire a déjà été réalisée. (Modifiez la base de donnée dans le cas contraire.)")
                    return False
                else:     
                    
                    if not check_plaquette_structure(plaquette_to_edit, window, "AGO"):
                        return False
                                                   
                    unsigned_plaquette = copy.deepcopy(plaquette_to_edit)
                    unsigned_plaquette["nom"] = "unsigned_plaquette"
                    debut_exercice = plaquette_to_edit["Structure"]["Exercice comptable"].split(" ")[1]                                
                    for client_doc in os.listdir(AG_dossier_path):      
                        traiter_documents_non_signes(AG_dossier_path, client_doc, unsigned_plaquette, window, AG_dossier, AG_date_json, debut_exercice, fin_exercice, "AGO")

                        client_docs_path = os.path.join(AG_dossier_path, client_doc)
                        if os.path.isdir(client_docs_path) and client_doc == "Documents signés":
                            traiter_documents_signes(folder_path=client_docs_path, unsigned_plaquette=unsigned_plaquette,
                                                    plaquette_to_edit=plaquette_to_edit, window=window, AG_dossier=AG_dossier,
                                                    AG_date_json=AG_date_json, debut_exercice=debut_exercice, fin_exercice=fin_exercice, AG_type="AGO")                                            
                        continue
                    return True  
            else :
                window.log_emitter.log_signal.emit("❌ La date n'a pas été donnée, la plaquette ne sera pas générée.")        
                return False
        if "AGE" in AG_dossier:
            if fill_plaquette_date(fin_exercice, AG_dossier_filtered, plaquette_name, "AGE", plaquette_to_edit, AG_dossier_path, client, window):
                if database.find_assembly(entreprise_id, plaquette_to_edit["Structure"]["Date de l'AGE"], "AGE"):
                    window.log_emitter.log_signal.emit("L'assemblée générale extraordinaire a déjà été réalisée. (Modifiez la base de donnée dans le cas contraire.)")
                else:
                    if not check_plaquette_structure(plaquette_to_edit, window, "AGE"):
                        return False
                    for client_doc in os.listdir(AG_dossier_path):
                        traiter_documents_non_signes(AG_dossier_path, client_doc, unsigned_plaquette, window, AG_dossier, AG_date_json, debut_exercice, fin_exercice, "AGE")

                        client_docs_path = os.path.join(AG_dossier_path, client_doc)
                        if os.path.isdir(client_docs_path) and client_doc == "Documents signés":
                            traiter_documents_signes(folder_path=client_docs_path, unsigned_plaquette=unsigned_plaquette,
                                                    plaquette_to_edit=plaquette_to_edit, window=window, AG_dossier=AG_dossier,
                                                    AG_date_json=AG_date_json, debut_exercice=debut_exercice, fin_exercice=fin_exercice, AG_type="AGE")
            return None
    else :
        window.log_emitter.log_signal.emit(f"Dossier AG non trouvé : {AG_dossier}")
        
def manually_fill_plaquette(AG_type, plaquette_to_edit, window, plaquette_name):
        if AG_type == "AGE":
            result_queue = Queue()
            window.ask_question_signal.emit("Quelle est la date de l'assemblée générale extraordinaire ? (Format : jj/mm/aaaa)", result_queue)
            response = result_queue.get()

            # On vérifie le format et repose la question s'il est incorrect
            while not re.match(r"^\d{2}/\d{2}/\d{4}$", response):
                result_queue = Queue()
                window.ask_question_signal.emit("Format incorrect. Quelle est la date de l'assemblée générale extraordinaire ? (Format : jj/mm/aaaa)", result_queue)
                response = result_queue.get()
            
            plaquette_to_edit["Structure"]["Date de l'AGE"] = response
            plaquette_name["value"] += f"-{AG_type}-{response.replace('/', '-')}"
            
            for AG_sub_type, AG_sub_sub_type in plaquette_to_edit["AGE"].items():
                result_queue = Queue()
                window.ask_yes_no_signal.emit(f"Voulez-vous faire un/une {AG_sub_type} ?", result_queue)
                reponse = result_queue.get()
                if reponse:
                    for AG_sub_sub_type, AG_sub_sub_sub_type in AG_sub_type.items():
                        result_queue = Queue()
                        window.ask_yes_no_signal.emit(f"Ce document doit-il être ajouté au sommaire :'{AG_sub_sub_sub_type}' ? ", result_queue)
                        response = result_queue.get()
                        
                        plaquette_to_edit["AGE"][AG_sub_type][AG_sub_sub_type][AG_sub_sub_sub_type] = True if response else False                        
            return None

        elif AG_type == "AGO":
            year = plaquette_to_edit["Structure"]["Exercice clos le"].split("/")[-1]
            plaquette_name["value"] += f"-{AG_type}-{year}"

            # Demander les documents spécifiques à l'AGO
            for AG_sub_type, AG_sub_sub_type in plaquette_to_edit["AGO"].items():
                result_queue = Queue()
                window.ask_yes_no_signal.emit(f"Voulez-vous faire un/une {AG_sub_type} ?", result_queue)
                reponse = result_queue.get()
                if reponse:
                    for AG_sub_sub_type, AG_sub_sub_sub_type in AG_sub_sub_type.items():
                        for key, value in AG_sub_sub_sub_type.items():
                            result_queue = Queue()
                            window.ask_yes_no_signal.emit(f"Ce document doit-il être ajouté au sommaire : {key} ? ", result_queue)
                            response = result_queue.get()
                            
                            plaquette_to_edit["AGO"][AG_sub_type][AG_sub_sub_type][key] = True if response else False
            return None
                        


def generate_plaquette(generer_plaquette, plaquette_to_edit, window, AG_date_json, plaquette_name, database, entreprise_id, client, plaquette_path):
    if is_empty_plaquette(plaquette_to_edit) :
        generer_plaquette = False
    
    if generer_plaquette:  
        # Compilation de la plaquette et récupération du chemin

        plaquette_pdf = compiler_latex(plaquette_json=plaquette_to_edit, nom_fichier=plaquette_name["value"], dossier_compilation=".", 
                                        dossier_sortie_absolu=plaquette_path)
        if plaquette_pdf and os.path.exists(plaquette_pdf):
            pdfs = [plaquette_pdf]
            # On ajoute les pdfs : 
            for key, value in plaquette_to_edit["AGO"].items():
                for sub_key, sub_value in value.items():
                    for doc_key, doc_value in sub_value.items():
                        if doc_value:
                            pdfs.append(doc_value)
                            print(f"Ajout du document {doc_value} à la plaquette.")

            fusionner_pdfs(pdfs, plaquette_pdf)
            fin_exercice = plaquette_to_edit["Structure"]["Exercice clos le"]
            if plaquette_to_edit["Structure"]["Date de l'AGE"]:
                database.insert_plaquette(entreprise_id, client, plaquette_name["value"], plaquette_to_edit["Structure"]["Date de l'AGE"], fin_exercice, "AGE", plaquette_path + plaquette_name["value"])
            else:
                database.insert_plaquette(entreprise_id, client, plaquette_name["value"], "A renseigner", fin_exercice, "AGO", plaquette_path + plaquette_name["value"])
            show_produced_plaquette(plaquette_to_edit, window)
        else:
            window.log_emitter.log_signal.emit("❌ Impossible de fusionner : la plaquette n'a pas été générée.")


def mode_auto(dossier_racine, database, window):  
    window.log_emitter.log_signal.emit("Mode auto activé. Traitement des dossiers...")
    # Chemin du dossier à créer
    plaquette_path = dossier_racine + "/Plaquettes"

    # Crée le dossier s'il n'existe pas déjà
    if not os.path.exists(plaquette_path):
        os.makedirs(plaquette_path)
    
    # On parcours les clients
    for client in os.listdir(dossier_racine):
        client_path = os.path.join(dossier_racine, client)
                
        # On vérifie que c'est bien un dossier
        if os.path.isdir(client_path):
            # On parcours le dossier en vérifiant le nom du dossier 
            plaquette_to_edit = copy.deepcopy(plaquette_copy)
            plaquette_to_edit["nom"] = "plaquette_to_edit"
            database.open_connection()
            
            # On filtre le nom du client pour éviter les erreurs de nom
            client = filter_client_name(client)
                
            client = client.upper()
            
            special_clients = {
                "ARCHEA" : "BERJA.D'AMENAGEMENT",
                "ONE" : "OPTIMISATION NUTRITION ENFANCE",
                "TPC" : "TIXIER PLOMBERIE CHAUFFAGE"
            }
            for key, value in special_clients.items():
                if client == key:
                    client = value
            
            entreprise_id = database.get_entreprise_id_by_name(client)

            if entreprise_id :
                # On rempli la plaquette_to_edit avec les données de l'entreprise                           
                window.log_emitter.log_signal.emit(f"Entreprise trouvée : {client} (ID de référence: {entreprise_id})")
                fill_plaquette_structure(plaquette_to_edit, entreprise_id, database)
                
                for AG_dossier in os.listdir(client_path):
                    # On détermine si oui ou non on réalise la plaquette
                    # J'identifie où sont les AGs à prendre (en fonction de la date et pourquoi pas des plaquettes déjé faites)

                    AG_dossier_path = os.path.join(client_path, AG_dossier)
                    plaquette_name = {}
                    plaquette_name["value"] = f"{client}"
                    AG_date_json = {
                                    "Fixation de la rémunération gérance" : None,
                                    "Abandon de créance" : None,
                                    "Approbation des comptes" : None
                                }
                    
                    generer_plaquette = fill_plaquette(AG_dossier_path, plaquette_to_edit, database, entreprise_id, window, plaquette_name, AG_date_json)

                    # On génère la plaquette à partir de plaquette_to_edit
                    # Et on l'insère dans la base de données
                    # la vérification suivante est insuffisante
                    # Il faut vérifier s'il y a à minima les documents pour faire une AG.
                    
                    generate_plaquette(generer_plaquette, plaquette_to_edit, window, AG_date_json, plaquette_name, database, entreprise_id, client, plaquette_path)

                    empty_plaquette(plaquette_to_edit)
                    remove_pdfs(os.getcwd())

                    window.log_emitter.log_signal.emit(f"Plaquette {plaquette_name['value']} générée.")
            else :
                window.log_emitter.log_signal.emit(f"Entreprise inconnue : {client}. Vérifiez l'orthographe ou bien ajoutez là à la base de données.")


        # On donne l'info de ce que le programme a réalisé : 
            # Dossier réalisé, emplacement de la plaquette, problèmes potentiels à vérifier
    
def mode_semi_auto(dossier_racine, database, window):
    window.log_emitter.log_signal.emit("Mode semi-auto activé. Traitement des dossiers...")
    # Chemin du dossier à créer
    plaquette_path = dossier_racine + "/Plaquettes"

    # Crée le dossier s'il n'existe pas déjà
    if not os.path.exists(plaquette_path):
        os.makedirs(plaquette_path)
        
    plaquette_to_edit = copy.deepcopy(plaquette_copy)    

    # L'utilisateur sélectionne un dossier
    directory_queue = Queue()
    window.ask_directory_signal.emit("Sélectionnez le dossier contenant les documents", directory_queue, dossier_racine)
    response = directory_queue.get()
    
    if response is None:
        window.log_emitter.log_signal.emit("Aucun dossier sélectionné.")
        return None

    print(f"Dossier sélectionné : {response}")
    client_id = search_client(response, database)

    if client_id is None:
        window.log_emitter.log_signal.emit("Aucun client trouvé dans le dossier sélectionné.")
        return None

    client_name = database.get_entreprise_name_by_id(client_id)

    plaquette_name = {"value": ""}
    plaquette_name["value"] += f"{database.get_entreprise_name_by_id(client_id)}"
    AG_date_json = {
        "Fixation de la rémunération gérance" : None,
        "Abandon de créance" : None,
        "Approbation des comptes" : None
    }

    fill_plaquette_structure(plaquette_to_edit, client_id, database)

    generer_plaquette = fill_plaquette(response, plaquette_to_edit, database, client_id, window, plaquette_name, AG_date_json)
    generate_plaquette(generer_plaquette, plaquette_to_edit, window, AG_date_json, plaquette_name, database, client_id, client_name, plaquette_path)
    remove_pdfs(os.getcwd())
    window.log_emitter.log_signal.emit(f"Plaquette {plaquette_name['value']} générée.")

    return None


def mode_manual(dossier_racine, database, window):
    window.log_emitter.log_signal.emit("Mode manuel activé. Traitement des dossiers...")
    # Chemin du dossier à créer
    plaquette_path = dossier_racine + "/Plaquettes"

    # Crée le dossier s'il n'existe pas déjà
    if not os.path.exists(plaquette_path):
        os.makedirs(plaquette_path)

    plaquette_to_edit = copy.deepcopy(plaquette_copy)

    q = Queue()
    window.ask_entreprise_signal.emit(q)
    client_name = q.get()
    
    if client_name is None:
        window.log_emitter.log_signal.emit("Aucun client sélectionné.")
        return None

    plaquette_name = {}
    plaquette_name["value"] = f"{client_name}"
    client_id = database.get_entreprise_id_by_name(client_name)

    # Ensuite on rempli les infos de la structure en affichant les infos pour que l'utilisateur vérifie :
    fill_plaquette_structure(plaquette_to_edit, client_id, database)
    
    # Demander la date de l'exercice clos et la durée de l'exercice
    
    result_queue = Queue()
    window.ask_question_signal.emit("Quelle est la date de l'exercice clos ? (format jj/mm/yyy)", result_queue)
    response = result_queue.get()

    # On vérifie le format et repose la question s'il est incorrect
    while not re.match(r"^\d{2}/\d{2}/\d{4}$", response):
        result_queue = Queue()
        window.ask_question_signal.emit("Format incorrect. Quelle est la date de l'assemblée générale extraordinaire ? (Format : jj/mm/aaaa)", result_queue)
        response = result_queue.get()

    plaquette_to_edit["Structure"]["Exercice clos le"] = response

    # Demander la durée de l'exercice
    result_queue = Queue()
    window.ask_question_signal.emit("Quelle est la durée de l'exercice ? (en mois)", result_queue)
    response = result_queue.get()

    # On vérifie que la réponse est un nombre
    while not response.isdigit():
        result_queue = Queue()
        window.ask_question_signal.emit("Format incorrect. Quelle est la durée de l'exercice ? (en mois)", result_queue)
        response = result_queue.get()

    duree_exercice = response

    # Demander le type d'AG : AGO, AGE
    result_queue = Queue()
    window.ask_question_signal.emit("Quel est le type d'AG ? (AGO/AGE)", result_queue)
    response = result_queue.get()

    # On vérifie que la réponse est valide
    while response not in ["AGO", "AGE"]:
        result_queue = Queue()
        window.ask_question_signal.emit("Format incorrect. Quel est le type d'AG ? (AGO/AGE)", result_queue)
        response = result_queue.get()
    AG_type = response
    
    # On récupère la date de début. C'est mis ici pour ne pas demander à l'utilisateur de
    # La saisir si la plaquette est incorrecte
    exercice_clos = plaquette_to_edit["Structure"]["Exercice clos le"]
    try:
            print(f"Durée de l'exercice : {duree_exercice} mois, ", type(duree_exercice))
            duree_exercice = int(duree_exercice)
            fin_exercice = datetime.strptime(exercice_clos, "%d/%m/%Y")
            print(f"Date de fin d'exercice : {fin_exercice}")
            debut_exercice = fin_exercice - relativedelta(months=duree_exercice) + relativedelta(days=1)
            debut_exercice = debut_exercice.strftime("%d/%m/%Y")
        
    except ValueError:
        print("⚠️ Erreur de conversion de la durée de l'exercice.")
        return "None"

    
    plaquette_to_edit["Structure"]["Exercice comptable"] = "Du " + \
        debut_exercice + " au " + plaquette_to_edit["Structure"]["Exercice clos le"]
        
    manually_fill_plaquette(AG_type, plaquette_to_edit, window, plaquette_name)

    # On produit le sommaire à partir de plaquette_to_edit
    plaquette_pdf = compiler_latex(plaquette_json=plaquette_to_edit, nom_fichier=plaquette_name["value"], dossier_compilation=".", 
                                        dossier_sortie_absolu=plaquette_path)

    if plaquette_pdf and os.path.exists(plaquette_pdf):
        folder_path = ""
        pdfs = [plaquette_pdf]
        # On ajoute les pdfs : 
        for key, value in plaquette_to_edit[f"{AG_type}"].items():
            for sub_key, sub_value in value.items():
                for doc_key, doc_value in sub_value.items():
                    if doc_value:
                        result_queue = Queue()
                        if folder_path == "":
                            window.ask_file_signal.emit(f"Veuillez sélectionner le fichier pour {doc_key} :", result_queue, dossier_racine)
                        else :
                            window.ask_file_signal.emit(f"Veuillez sélectionner le fichier pour {doc_key} :", result_queue, folder_path)
                        file_path = result_queue.get()
                        pdfs.append(file_path)
                        folder_path = os.path.dirname(file_path)
                        
        fusionner_pdfs(pdfs, plaquette_pdf)
        fin_exercice = plaquette_to_edit["Structure"]["Exercice clos le"]
        if plaquette_to_edit["Structure"]["Date de l'AGE"]:
            database.insert_plaquette(client_id, client_name, plaquette_name["value"], plaquette_to_edit["Structure"]["Date de l'AGE"], fin_exercice, "AGE", plaquette_path + plaquette_name["value"])
        else:
            database.insert_plaquette(client_id, client_name, plaquette_name["value"], "A renseigner", fin_exercice, "AGO", plaquette_path + plaquette_name["value"])

        window.log_emitter.log_signal.emit(f"Plaquette générée et enregistrée : {plaquette_name['value']}.pdf")
    remove_pdfs(os.getcwd())
    window.log_emitter.log_signal.emit(f"Plaquette {plaquette_name['value']} générée.")

    return None

def processing(mode, dossier_racine, database, window):
    if mode == "Auto (conseillé)":
        mode_auto(dossier_racine, database, window)
    elif mode == "Semi-auto":
        mode_semi_auto(dossier_racine, database, window)
    elif mode == "Manuel":
        mode_manual(dossier_racine, database, window)
    else :
        window.log_emitter.log_signal.emit("Mode de traitement inconnu.")