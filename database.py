import sqlite3
import os
import pandas as pd
from init_db import EntrepriseDatabase as InitEntrepriseDatabase
import globals


class EntrepriseDatabase:
    def __init__(self, db_path=globals.DATA_DIR + 'entreprise.db'):
        self.init_db = InitEntrepriseDatabase(db_path)
        self.init_db.create_tables()  # Assure que les tables sont créées avant d'utiliser la base de données
        self.db_path = db_path
        self.init_db.initialize_database()
        self.conn = None
        self.cursor = None

    def open_connection(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            

    
    ## Database methods for entreprises
    def get_entreprise_id_by_name(self, name):
        self.open_connection()
        self.cursor.execute("SELECT id FROM entreprises WHERE raison_sociale = ?", (name,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None
    
    def get_entreprise_juridique_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT forme_juridique FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_entreprise_capital_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT capital_social FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None
    
    def get_entreprise_adresse_rue_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT adresse FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_entreprise_adresse_code_postal_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT code_postal FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_entreprise_adresse_ville_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT ville FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_entreprise_exercice_clos_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT fin_exercice FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None
    
    def get_all_names_entreprises(self):
        self.open_connection()
        self.cursor.execute("SELECT raison_sociale FROM entreprises")
        rows = self.cursor.fetchall()
        self.close()
        return [row[0] for row in rows]
    
    def get_entreprise_name_by_id(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("SELECT raison_sociale FROM entreprises WHERE id = ?", (entreprise_id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None


    def find_assembly(self, entreprise_id, exercice_clos, type):
        self.open_connection()
        self.cursor.execute('''SELECT * FROM plaquettes WHERE entreprise_id = ? AND 
                            exercice_clos = ? AND type = ?''', (entreprise_id, exercice_clos, type))
        result = self.cursor.fetchone()
        self.close()
        
        return True if result else None

    ## General database methods
    def get_all_entreprises(self):
        self.open_connection()
        self.cursor.execute("SELECT * FROM entreprises")
        rows = self.cursor.fetchall()
        self.close()
        return rows

    def get_all_plaquettes(self):
        self.open_connection()
        self.cursor.execute("SELECT * FROM plaquettes")
        rows = self.cursor.fetchall()
        self.close()
        return rows

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
        
    def insert_empty_entreprise(self):
        self.open_connection()
        self.cursor.execute("""
            INSERT INTO entreprises (
                forme_juridique, raison_sociale, capital_social,
                adresse, ville, code_postal, numero_siren, fin_exercice
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "N/A", "Nouvelle entreprise", 0,
            "N/A", "N/A", "00000", "000000000", "31/12"
        ))
        self.conn.commit()
        last_id = self.cursor.lastrowid
        self.close()
        return last_id
    
    def update_entreprise(self, entreprise_id, **kwargs):
        self.open_connection()
        columns = ', '.join(f"{key} = ?" for key in kwargs)
        values = list(kwargs.values())
        values.append(entreprise_id)
        query = f"UPDATE entreprises SET {columns} WHERE id = ?"
        self.cursor.execute(query, values)
        self.conn.commit()
        self.close()
        
    def update_entreprise_field(self, entreprise_id, field_name, new_value):
        self.open_connection()
        query = f"UPDATE entreprises SET {field_name} = ? WHERE id = ?"
        self.cursor.execute(query, (new_value, entreprise_id))
        self.conn.commit()
        self.close()


    def delete_entreprise(self, entreprise_id):
        self.open_connection()
        self.cursor.execute("DELETE FROM entreprises WHERE id = ?", (entreprise_id,))
        self.conn.commit()
        self.close()

    def insert_plaquette(self, entreprise_id, entreprise_name, name, date, exercice_clos, type_plaquette, lien_doc):
        self.open_connection()
        self.cursor.execute('''
            INSERT INTO plaquettes (entreprise_id, entreprise_name, name, date, exercice_clos, type, lien_doc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (entreprise_id, entreprise_name, name, date, exercice_clos, type_plaquette, lien_doc))
        self.conn.commit()
        self.close()
     
    
    def insert_empty_plaquette(self, entreprise_id):
        
        entreprise_name = self.get_entreprise_juridique_by_id(entreprise_id) + " - " + self.get_entreprise_name_by_id(entreprise_id)
        
        self.open_connection()
        self.cursor.execute('''
            INSERT INTO plaquettes (entreprise_id, entreprise_name, name, date, exercice_clos, type, lien_doc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (entreprise_id, entreprise_name,"Approbation des comptes", "A remplir", "31/12/2024", "AGO", "Non renseigné"))
        self.conn.commit()
        last_id = self.cursor.lastrowid
        self.close()
        return last_id
        
    def update_plaquette(self, plaquette_id, **kwargs):
        self.open_connection()
        columns = ', '.join(f"{key} = ?" for key in kwargs)
        values = list(kwargs.values())
        values.append(plaquette_id)
        query = f"UPDATE plaquettes SET {columns} WHERE id = ?"
        self.cursor.execute(query, values)
        self.conn.commit()
        self.close()


    def delete_plaquette(self, plaquette_id):
        self.open_connection()
        self.cursor.execute("DELETE FROM plaquettes WHERE id = ?", (plaquette_id,))
        self.conn.commit()
        self.close()
        
 