"""
AlertManager - Coordena os níveis de alerta progressivo.

Níveis:
  1. Aviso pequeno (notificação na bandeja)
  2. Overlay semitransparente com mensagem
  3. Tela escura fullscreen bloqueante

Após cada ciclo de alertas, o nível volta para 1.
Se progressive_alerts estiver desativado, vai direto para nível 3.
"""

from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional


class AlertLevel:
    SMALL_WARNING = 1
    OVERLAY = 2
    FULL_BLOCK = 3


class AlertManager(QObject):
    """Gerencia os níveis progressivos de alerta."""

    # Emitido com o nível do alerta a ser exibido
    alert_triggered = Signal(int)
    # Emitido quando o alerta (bloqueio) termina
    alert_finished = Signal()

    def __init__(
        self,
        progressive: bool = True,
        block_duration: float = 8.0,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._progressive = progressive
        self._block_duration = block_duration
        self._current_level = AlertLevel.SMALL_WARNING
        self._active = False

    @property
    def progressive(self) -> bool:
        return self._progressive

    @progressive.setter
    def progressive(self, value: bool) -> None:
        self._progressive = value

    @property
    def block_duration(self) -> float:
        return self._block_duration

    @block_duration.setter
    def block_duration(self, value: float) -> None:
        self._block_duration = max(1.0, value)

    @property
    def current_level(self) -> int:
        return self._current_level

    @property
    def is_active(self) -> bool:
        return self._active

    @Slot()
    def trigger_alert(self) -> None:
        """Dispara o próximo nível de alerta."""
        if self._active:
            return

        self._active = True
        if self._progressive:
            level = self._current_level
            # Avança para o próximo nível na próxima vez
            if self._current_level < AlertLevel.FULL_BLOCK:
                self._current_level += 1
            else:
                self._current_level = AlertLevel.SMALL_WARNING
        else:
            level = AlertLevel.FULL_BLOCK

        self.alert_triggered.emit(level)

    @Slot()
    def finish_alert(self) -> None:
        """Marca o alerta atual como finalizado."""
        self._active = False
        self.alert_finished.emit()

    def reset_level(self) -> None:
        """Reseta o nível de alerta para o inicial."""
        self._current_level = AlertLevel.SMALL_WARNING

    def reset(self) -> None:
        """Reseta todo o estado."""
        self._active = False
        self._current_level = AlertLevel.SMALL_WARNING
