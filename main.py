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
                   empty_plaquette, fusionner_pdfs, normalize_filename)
from interface import MainWindow, LogPage, HomePage
from database import EntrepriseDatabase as Database
from init_db import EntrepriseDatabase as InitDatabase
from latex import compiler_latex
from processing import processing

def main(mode = None):
    
    database = Database()
    app = QApplication(sys.argv)

    window = MainWindow(database)
    window.show()

    sys.exit(app.exec())

main()