"""
OverlayWindow - Janela fullscreen always-on-top que bloqueia a tela.

Exibe mensagem calma com contador regressivo e libera automaticamente
ao final do tempo configurado.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QGuiApplication
from typing import Optional

from .alert_manager import AlertLevel


class OverlayWindow(QWidget):
    """Janela de overlay/bloqueio fullscreen."""

    # Emitido quando o overlay é fechado (tempo esgotado)
    overlay_closed = Signal()

    # Mensagens por nível
    MESSAGES = {
        AlertLevel.SMALL_WARNING: "⚠️ Atenção! Você está falando um pouco alto.",
        AlertLevel.OVERLAY: "🔊 Você está falando muito alto!\nFale mais baixo para continuar jogando.",
        AlertLevel.FULL_BLOCK: "🛑 Você está falando muito alto.\nFale mais baixo para continuar jogando.",
    }

    # Cores de fundo por nível (RGBA)
    BACKGROUNDS = {
        AlertLevel.SMALL_WARNING: "rgba(255, 165, 0, 200)",   # Laranja semi
        AlertLevel.OVERLAY: "rgba(180, 0, 0, 220)",            # Vermelho semi
        AlertLevel.FULL_BLOCK: "rgba(0, 0, 0, 245)",           # Preto quase opaco
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._level = AlertLevel.FULL_BLOCK

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do overlay."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mensagem principal
        self._message_label = QLabel()
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        font = QFont("Segoe UI", 28, QFont.Weight.Bold)
        self._message_label.setFont(font)
        self._message_label.setStyleSheet("color: white; padding: 40px;")
        layout.addWidget(self._message_label)

        # Contador regressivo
        self._countdown_label = QLabel()
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        countdown_font = QFont("Segoe UI", 72, QFont.Weight.Bold)
        self._countdown_label.setFont(countdown_font)
        self._countdown_label.setStyleSheet("color: white;")
        layout.addWidget(self._countdown_label)

        # Instrução
        self._instruction_label = QLabel("Respire fundo e fale mais baixo...")
        self._instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_font = QFont("Segoe UI", 16)
        self._instruction_label.setFont(instruction_font)
        self._instruction_label.setStyleSheet("color: rgba(255, 255, 255, 180);")
        layout.addWidget(self._instruction_label)

    def show_alert(self, level: int, duration: float) -> None:
        """Exibe o overlay com o nível e duração especificados."""
        self._level = level
        self._remaining = int(duration)

        # Configura visual baseado no nível
        message = self.MESSAGES.get(level, self.MESSAGES[AlertLevel.FULL_BLOCK])
        background = self.BACKGROUNDS.get(level, self.BACKGROUNDS[AlertLevel.FULL_BLOCK])

        self._message_label.setText(message)
        self._countdown_label.setText(str(self._remaining))
        self.setStyleSheet(f"background-color: {background};")

        # Para nível 1, mostra janela menor (não fullscreen)
        if level == AlertLevel.SMALL_WARNING:
            self.resize(600, 300)
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            # Centraliza na tela
            screen = QGuiApplication.primaryScreen()
            if screen:
                geometry = screen.geometry()
                x = (geometry.width() - 600) // 2
                y = (geometry.height() - 300) // 2
                self.move(x, y)
            self.show()
        else:
            # Fullscreen para níveis 2 e 3
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.showFullScreen()

        self._timer.start()

    @Slot()
    def _tick(self) -> None:
        """Atualiza o contador regressivo a cada segundo."""
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self.hide()
            self.overlay_closed.emit()
        else:
            self._countdown_label.setText(str(self._remaining))

    def force_close(self) -> None:
        """Fecha o overlay imediatamente."""
        self._timer.stop()
        self.hide()
        self.overlay_closed.emit()
