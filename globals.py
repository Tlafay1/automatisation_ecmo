import os
import pathlib
import sys

BASE_PATH = pathlib.Path(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))))
RESOURCES_DIR = BASE_PATH / "resources"
DATA_DIR = pathlib.Path(os.getenv('APPDATA')) / "ECMO Automatisation"

DB_NAME = "entreprise.db"
DB_PATH = DATA_DIR / DB_NAME
