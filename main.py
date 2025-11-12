import sys
from PyQt6.QtWidgets import (
    QApplication,
)
from interface import MainWindow
from database import EntrepriseDatabase as Database


def main(mode=None):

    database = Database()
    app = QApplication(sys.argv)

    window = MainWindow(database)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
