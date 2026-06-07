"""
Loud Voice Cooldown - Ponto de entrada do aplicativo.

Aplicação para Windows 11 que monitora o volume do microfone em tempo real
e ajuda uma criança a falar mais baixo enquanto joga online com fone de ouvido.

- Não grava áudio
- Não transcreve fala
- Não envia nada para a internet
- Analisa apenas o nível de volume do microfone
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.logger import setup_logger
from src.main_window import MainWindow


def main() -> None:
    # Configura logging antes de tudo
    setup_logger()

    # Habilita high DPI no Windows
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Loud Voice Cooldown")
    app.setOrganizationName("LoudVoiceCooldown")
    app.setQuitOnLastWindowClosed(False)  # Permite rodar na bandeja

    window = MainWindow()
    if not window.should_start_minimized():
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
