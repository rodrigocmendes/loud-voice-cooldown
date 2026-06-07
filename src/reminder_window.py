"""
ReminderWindow - Lembrete visual não-bloqueante (toast).

Exibe mensagem rápida "Fale mais baixo" por tempo configurável.
Não cobre a tela inteira e não bloqueia interação.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication


class ReminderWindow(QWidget):
    """Toast não-bloqueante exibido quando pico de voz alta é detectado."""

    # Emitido quando o lembrete fecha
    reminder_closed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._auto_close)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do lembrete."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(420, 100)
        self.setStyleSheet(
            "background-color: rgba(255, 140, 0, 230); border-radius: 12px;"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("Fale mais baixo")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self._label.setStyleSheet("color: white;")
        layout.addWidget(self._label)

    def show_reminder(self, duration_s: float = 1.5) -> None:
        """Exibe o lembrete por `duration_s` segundos."""
        # Posiciona no topo central da tela
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            x = (geometry.width() - self.width()) // 2
            y = 40  # Topo com margem
            self.move(x, y)

        self.show()
        self.raise_()
        self._timer.start(int(duration_s * 1000))

    def _auto_close(self) -> None:
        """Fecha o lembrete automaticamente."""
        self.hide()
        self.reminder_closed.emit()

    def force_close(self) -> None:
        """Fecha o lembrete imediatamente."""
        self._timer.stop()
        self.hide()
