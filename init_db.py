import sqlite3
import pandas as pd
import re
import os

import globals

class EntrepriseDatabase:
    def __init__(self, db_path=globals.DATA_DIR + 'entreprise.db'):
        self.conn = None
        self.cursor = None
        self.db_path = db_path

    def open_connection(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = None
        self.cursor = None

    def create_tables(self):
        self.open_connection()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entreprises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forme_juridique TEXT NOT NULL,
                raison_sociale TEXT NOT NULL,
                capital_social REAL NOT NULL,
                adresse TEXT NOT NULL,
                ville TEXT NOT NULL,
                code_postal TEXT NOT NULL,
                numero_siren TEXT NOT NULL,
                fin_exercice TEXT NOT NULL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS plaquettes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entreprise_id INTEGER NOT NULL,
                entreprise_name TEXT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,  -- format 'YYYY-MM-DD'
                exercice_clos TEXT NOT NULL,  -- format 'YYYY-MM-DD'
                type TEXT NOT NULL,  -- exemple: 'AGO', 'AGE'
                lien_doc TEXT NOT NULL,
                FOREIGN KEY (entreprise_id) REFERENCES entreprises(id)
            )
        ''')
        
        self.conn.commit()
        self.close()
    
    def get_all_entreprises(self):
        self.open_connection()
        self.cursor.execute("SELECT * FROM entreprises")
        results = self.cursor.fetchall()
        self.close()
        return results
    
    def insert_entreprise(self, forme_juridique, raison_sociale, capital_social,
                      adresse, ville, code_postal, numero_siren, fin_exercice):
        self.open_connection()
        self.cursor.execute('''
            INSERT INTO entreprises (forme_juridique, raison_sociale, capital_social,
                                    adresse, ville, code_postal, numero_siren, fin_exercice)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (forme_juridique, raison_sociale, capital_social,
            adresse, ville, code_postal, numero_siren, fin_exercice))
        self.conn.commit()
        self.close()
        

    def initialize_database(self):
        """
        Initialize the database by creating the necessary tables and inserting data from an Excel file.
        """
        ## On regarde si la base de données entreprises a des données
        if self.get_all_entreprises():
            print("Database already initialized with data.")
            return
        
        else : 
            if not os.path.exists(globals.DATA_DIR + 'entreprise.db'):
                print("Database not found, creating a new one.")
            
            # Initialize the database
            database = EntrepriseDatabase()
            database.open_connection()

            df = pd.read_excel(globals.RESOURCES_DIR + 'Fichier client.xlsx')

            df.drop(['Code', 'Tél. fixe', 'Solde global', 'ColonneVisibiliteClientInfobulle', 'Tél. portable', 'Rég. fisc.', 'Cat. rev.', 'Colla. resp.'], axis=1, inplace=True)

            df = df.rename(columns={
                'Juridique': 'forme_juridique',
                'Nom complet': 'raison_sociale',
                'Capital social': 'capital_social', 
                'Adresse': 'adresse',
                'Ville': 'ville',
                'CP': 'code_postal',
                'N° Siret': 'numero_siren',
                'Fin exo (jj/mm)': 'fin_exercice'
            })

            formes_juridiques = ['SCI', 'SAS', 'SASU', 'E.I.M.', 'EURL', 'SARL', 'SA', 'SNC', 'SCS', 'SCA', 'SELARL', 'SELAS', 'SELUI', 'SASP', 'SASPL', 'SC', 'SCM']

            pattern = r'\b(?:' + '|'.join(re.escape(forme) for forme in formes_juridiques) + r')\b\.?'

            df['raison_sociale'] = df['raison_sociale'].str.replace(pattern, '', regex=True).str.strip()
            df['raison_sociale'] = df['raison_sociale'].str.upper()
            df['forme_juridique'] = df['forme_juridique'].str.upper()
            df['numero_siren'] = df['numero_siren'].astype(str).str[:9]
            df['code_postal'] = df['code_postal'].astype(str).str[:5]
            df['capital_social'] = df['capital_social'].astype(float)

            for index, row in df.iterrows():
                
                if pd.isna(row['fin_exercice']):
                    row['fin_exercice'] = '31/12'
                if pd.isna(row['capital_social']):
                    row['capital_social'] = 0
                if pd.isna(row['code_postal']):
                    row['code_postal'] = '00000'
                if pd.isna(row['ville']):
                    row['ville'] = 'Inconnu'
                if pd.isna(row['forme_juridique']):
                    row['forme_juridique'] = 'Inconnu'
                if pd.isna(row['raison_sociale']):
                    row['raison_sociale'] = 'Inconnu'
                    
                if pd.isna(row['numero_siren']):
                    row['numero_siren'] = '000000000'
                if pd.isna(row['adresse']):
                    row['adresse'] = 'Inconnue'
                
                database.insert_entreprise(
                    forme_juridique=row['forme_juridique'],
                    raison_sociale=row['raison_sociale'],
                    capital_social=row['capital_social'],
                    adresse=row['adresse'],
                    ville=row['ville'],
                    code_postal=row['code_postal'],
                    numero_siren=row['numero_siren'],
                    fin_exercice=row['fin_exercice']
                )

            print(df.head())
