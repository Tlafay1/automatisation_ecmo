import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, 
    QStackedWidget, QFileDialog, QMessageBox, 
    QTableWidget, QTableWidgetItem,
    QLineEdit, QCompleter, QDialog, QDialogButtonBox, QComboBox,
    QInputDialog, 
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal


from database import EntrepriseDatabase
from processing import (processing)
from threading import Thread


class LogEmitter(QObject):
    log_signal = pyqtSignal(str)

class LogPage(QWidget):
    def __init__(self, dossier_selectionne=None):
        super().__init__()        
        layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(QLabel("Logs"))
        layout.addWidget(self.log_area)
        self.setLayout(layout)
        if dossier_selectionne:
            self.log(f"Traitement en cours pour : {dossier_selectionne}")

    def log(self, message: str):
        self.log_area.append(message)



class EntreprisesPage(QWidget):
    def __init__(self, db: EntrepriseDatabase):
        super().__init__()
        self.db = db
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Forme juridique", "Raison sociale", "Capital social",
            "Adresse", "Ville", "Code postal", "SIREN", "Fin exercice"
        ])

        self.table.cellChanged.connect(self.handle_cell_change)

        self.add_button = QPushButton("Ajouter une entreprise")
        self.add_button.clicked.connect(self.ajouter_entreprise)
        
        self.delete_button = QPushButton("Supprimer l'entreprise sélectionnée")
        self.delete_button.clicked.connect(self.supprimer_entreprise)

        layout.addWidget(QLabel("Entreprises enregistrées"))
        layout.addWidget(self.table)
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)


        self.setLayout(layout)
        self._suppress_changes = False
        self.load_entreprises()  # chargement initial

    def load_entreprises(self):
        entreprises = self.db.get_all_entreprises()

        self._suppress_changes = True
        self.table.setRowCount(len(entreprises))

        for row_idx, row_data in enumerate(entreprises):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col_idx == 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # ID non modifiable
                self.table.setItem(row_idx, col_idx, item)
        self._suppress_changes = False

    def handle_cell_change(self, row, column):
        if self._suppress_changes:
            return

        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        entreprise_id = int(id_item.text())

        new_value = self.table.item(row, column).text()

        column_mapping = {
            1: "forme_juridique",
            2: "raison_sociale",
            3: "capital_social",
            4: "adresse",
            5: "ville",
            6: "code_postal",
            7: "numero_siren",
            8: "fin_exercice"
        }

        if column in column_mapping:
            field_name = column_mapping[column]
            self.db.update_entreprise_field(entreprise_id, field_name, new_value)
            self.load_entreprises()  # Recharge après modification

    def ajouter_entreprise(self):
        # Insère une entreprise vide avec valeurs par défaut, retourne son ID    
        new_id = self.db.insert_empty_entreprise()
        self.load_entreprises()
    
    def supprimer_entreprise(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une ligne à supprimer.")
            return

        # On suppose sélection d’une seule plage (une ou plusieurs lignes sélectionnées)
        rows_to_delete = set()
        for selection in selected_ranges:
            for row in range(selection.topRow(), selection.bottomRow() + 1):
                rows_to_delete.add(row)

        confirm = QMessageBox.question(
            self, "Confirmation",
            f"Voulez-vous vraiment supprimer {len(rows_to_delete)} entreprise(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            for row in sorted(rows_to_delete, reverse=True):
                id_item = self.table.item(row, 0)
                if id_item:
                    entreprise_id = int(id_item.text())
                    self.db.delete_entreprise(entreprise_id)
            self.load_entreprises()


class PlaquettesPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Entreprise ID", "Entreprise", "Nom de l'AG", "Date de l'AG", "Exercice clos",
            "Type (AGO/AGE)", "Lien du document"
        ])

        self.table.cellChanged.connect(self.handle_cell_change)

        self.add_button = QPushButton("Ajouter une plaquette")
        self.add_button.clicked.connect(self.ajouter_plaquette)

        self.delete_button = QPushButton("Supprimer la plaquette sélectionnée")
        self.delete_button.clicked.connect(self.supprimer_plaquette)

        layout.addWidget(QLabel("Plaquettes générées"))
        layout.addWidget(self.table)
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)


        self.setLayout(layout)
        self._suppress_changes = False
        self.load_plaquettes()  # chargement initial


    def load_plaquettes(self):
        plaquettes = self.db.get_all_plaquettes()

        self._suppress_changes = True
        self.table.setRowCount(len(plaquettes))

        for row_idx, row_data in enumerate(plaquettes):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col_idx == 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # ID non modifiable
                self.table.setItem(row_idx, col_idx, item)
        self._suppress_changes = False

    def handle_cell_change(self, row, column):
        if self._suppress_changes:
            return

        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        plaquette_id = int(id_item.text())

        new_value = self.table.item(row, column).text()

        column_mapping = {
            1: "id",
            2: "entreprise_id",
            3: "entreprise_name",
            4: "name",
            5: "date",
            6: "exercice_clos",
            7: "type",
            8: "lien_doc"
        }

        if column in column_mapping:
            field_name = column_mapping[column]
            self.db.update_plaquette_field(plaquette_id, field_name, new_value)
            self.load_plaquettes()  # Recharge après modification

    def ajouter_plaquette(self):
        noms_entreprises = self.db.get_all_names_entreprises()

        dialog = QDialog(self)
        dialog.setWindowTitle("Sélection d'entreprise")
        layout = QVBoxLayout(dialog)

        label = QLabel("Pour quelle entreprise voulez-vous ajouter une plaquette ?")
        line_edit = QLineEdit()
        completer = QCompleter(noms_entreprises)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line_edit.setCompleter(completer)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button_box)

        def on_accept():
            nom_entreprise = line_edit.text()
            if nom_entreprise in noms_entreprises:
                entreprise_id = self.db.get_entreprise_id_by_name(nom_entreprise)
                self.db.insert_empty_plaquette(entreprise_id)
                self.load_plaquettes()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Erreur", f"L'entreprise « {nom_entreprise} » n'existe pas.")

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(dialog.reject)

        dialog.exec()

    def supprimer_plaquette(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une ligne à supprimer.")
            return

        # On suppose sélection d’une seule plage (une ou plusieurs lignes sélectionnées)
        rows_to_delete = set()
        for selection in selected_ranges:
            for row in range(selection.topRow(), selection.bottomRow() + 1):
                rows_to_delete.add(row)

        confirm = QMessageBox.question(
            self, "Confirmation",
            f"Voulez-vous vraiment supprimer {len(rows_to_delete)} plaquette(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            for row in sorted(rows_to_delete, reverse=True):
                id_item = self.table.item(row, 0)
                if id_item:
                    plaquette_id = int(id_item.text())
                    self.db.delete_plaquette(plaquette_id)
            self.load_plaquettes()



class HomePage(QWidget):
    def __init__(self, start_callback, stop_callback):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # marges autour du contenu
        layout.setSpacing(20)                      # espacement global entre items

        # Directory selection
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(10)  # espacement entre label + bouton
        dir_label = QLabel("Sélectionnez le répertoire racine :")
        dir_layout.addWidget(dir_label)
        self.browse_button = QPushButton("Parcourir...")
        dir_layout.addWidget(self.browse_button)
        layout.addLayout(dir_layout)

        # Petit écart spécifique avant path_label
        layout.addSpacing(5)
        # Afficher le chemin sélectionné
        self.path_label = QLabel("")
        self.path_label.setStyleSheet("color: gray;")
        # on centre horizontalement
        layout.addWidget(self.path_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(10)
        mode_label = QLabel("Mode :")
        mode_layout.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Auto (conseillé)", "Semi-auto", "Manuel"])
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # Start, stop grouped
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.start_button = QPushButton("Démarrer l'application")
        self.start_button.setEnabled(False)
        btn_layout.addWidget(self.start_button, stretch=1)
        self.stop_button = QPushButton("Arrêter")
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.stop_button, stretch=1)
        layout.addLayout(btn_layout)

        # Ajout d'un stretch final pour repousser le contenu vers le haut
        layout.addStretch()

        self.setLayout(layout)
        self.selected_folder = None
        self.start_callback = start_callback
        self.stop_callback = stop_callback

        self.browse_button.clicked.connect(self.select_folder)
        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_stop)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier racine")
        if folder:
            self.selected_folder = folder
            self.start_button.setEnabled(True)
            self.path_label.setText(f"Répertoire sélectionné : {folder}")

    def on_start(self):
        if self.selected_folder:
            self.stop_button.setEnabled(True)
            self.start_callback(self.selected_folder)

    def on_stop(self):
        self.stop_callback()

class MainWindow(QWidget):
    
    ask_question_signal = pyqtSignal(str, object)  # question, queue pour la réponse
    ask_directory_signal = pyqtSignal(str, object, str)  # question, queue, start_dir
    ask_entreprise_signal = pyqtSignal(object)  # queue pour la réponse
    ask_yes_no_signal = pyqtSignal(str, object)  # question, queue
    ask_file_signal = pyqtSignal(str, object, str)  # question, queue, start_dir


    def __init__(self, database):
        super().__init__()
        self.setWindowTitle("Générateur de Plaquettes Juridiques")
        self.setGeometry(100, 100, 800, 600)
        self.db = database
        self.state = "inactive"  # États possibles : "active", "inactive"
        self.ask_question_signal.connect(self._handle_user_question)
        self.ask_directory_signal.connect(self._handle_user_directory)
        self.ask_entreprise_signal.connect(self._handle_user_enterprise)
        self.ask_yes_no_signal.connect(self._handle_yes_no)
        self.ask_file_signal.connect(self._handle_user_file)


        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        self.stack = QStackedWidget()

        # Pages
        self.home_page = HomePage(self.start_app, self.stop_process)
        self.log_page = LogPage()
            
        self.log_emitter = LogEmitter()
        self.log_emitter.log_signal.connect(self.log_page.log)
         
        self.entreprises_page = EntreprisesPage(self.db)
        self.plaquettes_page = PlaquettesPage(self.db)

        self.mode = self.home_page.mode_combo.currentText() # Modes possibles : "auto", "semi-auto", "manual"

        for page in (self.home_page, self.log_page, self.entreprises_page, self.plaquettes_page):
            self.stack.addWidget(page)

        # Navigation buttons stretch full width
        btn_home = QPushButton("Accueil")
        btn_log = QPushButton("Traitement")
        btn_ent = QPushButton("Entreprises")
        btn_pla = QPushButton("Plaquettes")
        for btn, page in [(btn_home, self.home_page), (btn_log, self.log_page), (btn_ent, self.entreprises_page), (btn_pla, self.plaquettes_page)]:
            btn.clicked.connect(lambda _, p=page: self.stack.setCurrentWidget(p))
            btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().verticalPolicy())
            nav_layout.addWidget(btn)

        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

    def start_app(self, root_folder):
        self.log_page.log(f"Dossier racine sélectionné : {root_folder}")
        self.stack.setCurrentWidget(self.log_page)
        self.state = "active"
        self.home_page.start_button.setEnabled(False)
        self.mode = self.home_page.mode_combo.currentText()

        def run_processing():
            processing(self.mode, self.home_page.selected_folder, self.db, self)
            # Quand processing est terminé, on réactive le bouton via le thread principal Qt
            QTimer.singleShot(0, self.on_processing_finished)

        thread = Thread(target=run_processing)
        thread.start()

    def on_processing_finished(self):
        self.log_page.log("✅ Traitement terminé.")
        self.state = "inactive"
        self.home_page.start_button.setEnabled(True)

    def stop_process(self):
        self.log_page.log("Arrêt du traitement...")
        self.state = "inactive"
        self.home_page.start_button.setEnabled(True)
    
    
    def log(self, message):
        self.log_page.log(message)

    def ask_user_input(self, question, callback):
        def ask():
            text, ok = QInputDialog.getText(self, "Question", question)
            if ok:
                callback(text)
            else:
                callback(None)
        QTimer.singleShot(0, ask)

    def _handle_user_directory(self, question, directory_queue, start_dir=None):
        directory = QFileDialog.getExistingDirectory(
            self,
            question,
            start_dir if start_dir else ""  # chemin de départ
        )
        directory_queue.put(directory if directory else None)
    
    def _handle_user_file(self, question, file_queue, start_dir=None):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            question,
            start_dir if start_dir else ""  # chemin de départ
        )
        file_queue.put(file_path if file_path else None)


    def _handle_user_question(self, question, result_queue):
        text, ok = QInputDialog.getText(self, "Question", question)
        result_queue.put(text if ok else None)
        
    def _handle_user_enterprise(self, result_queue):
        noms_entreprises = self.db.get_all_names_entreprises()

        dialog = QDialog(self)
        dialog.setWindowTitle("Sélection d'entreprise")
        layout = QVBoxLayout(dialog)

        label = QLabel("Pour quelle entreprise voulez-vous ajouter une plaquette ?")
        line_edit = QLineEdit()
        completer = QCompleter(noms_entreprises)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line_edit.setCompleter(completer)

        button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )


        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button_box)

        chosen = {"value": None}  # petit conteneur mutable

        def on_accept():
            nom_entreprise = line_edit.text()
            if nom_entreprise in noms_entreprises:
                chosen["value"] = nom_entreprise
                dialog.accept()
            else:
                QMessageBox.warning(self, "Erreur", f"L'entreprise « {nom_entreprise} » n'existe pas.")

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            result_queue.put(chosen["value"])
        else:
            result_queue.put(None)
    
    def _handle_yes_no(self, question, result_queue):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        result_queue.put(reply == QMessageBox.StandardButton.Yes)


    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(EntrepriseDatabase())
    window.show()
    sys.exit(app.exec())
