"""
OverlayWindow - Janela fullscreen always-on-top de bloqueio visual.

Exibe mensagem clara com contador regressivo.
Fecha automaticamente ao final do tempo configurado.
Não bloqueia teclado e mouse.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont


class OverlayWindow(QWidget):
    """Janela de bloqueio fullscreen com contador regressivo."""

    # Emitido quando o overlay fecha (tempo esgotado)
    overlay_closed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do overlay."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 240);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ícone / título
        title = QLabel("Volume alto acumulado.")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #ff4444; padding: 20px;")
        layout.addWidget(title)

        # Mensagem principal
        self._message_label = QLabel(
            "Fale mais baixo para continuar jogando."
        )
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        self._message_label.setFont(QFont("Segoe UI", 22))
        self._message_label.setStyleSheet("color: white; padding: 10px;")
        layout.addWidget(self._message_label)

        # Contador regressivo
        self._countdown_label = QLabel()
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setFont(QFont("Segoe UI", 72, QFont.Weight.Bold))
        self._countdown_label.setStyleSheet("color: white;")
        layout.addWidget(self._countdown_label)

        # Instrução
        self._releasing_label = QLabel()
        self._releasing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._releasing_label.setFont(QFont("Segoe UI", 16))
        self._releasing_label.setStyleSheet("color: rgba(255, 255, 255, 160);")
        layout.addWidget(self._releasing_label)

    def show_block(self, duration: float) -> None:
        """Exibe o bloqueio fullscreen com duração em segundos."""
        self._remaining = int(duration)
        self._countdown_label.setText(str(self._remaining))
        self._releasing_label.setText(
            f"Liberando em {self._remaining} segundos."
        )

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
            self._releasing_label.setText(
                f"Liberando em {self._remaining} segundo{'s' if self._remaining > 1 else ''}."
            )

    def force_close(self) -> None:
        """Fecha o overlay imediatamente."""
        self._timer.stop()
        self.hide()
        self.overlay_closed.emit()
