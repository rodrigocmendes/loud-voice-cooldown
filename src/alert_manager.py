"""
AlertManager - Coordena lembretes visuais e bloqueios.

Gerencia cooldown entre lembretes (3s padrão) e cooldown após bloqueio (45s).
O acúmulo continua durante cooldown de lembretes.
"""

import time
from PySide6.QtCore import QObject, Signal, Slot

from .logger import get_logger


class AlertManager(QObject):
    """Gerencia lembretes e bloqueios com cooldowns independentes."""

    # Emitido para exibir lembrete visual não-bloqueante
    show_reminder = Signal()
    # Emitido para acionar bloqueio fullscreen
    show_block = Signal()
    # Emitido quando o bloqueio termina
    block_finished = Signal()

    def __init__(
        self,
        reminder_cooldown: float = 3.0,
        block_duration: float = 8.0,
        allow_reminders_during_cooldown: bool = True,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._reminder_cooldown = reminder_cooldown
        self._block_duration = block_duration
        self._allow_reminders_during_cooldown = allow_reminders_during_cooldown
        self._last_reminder_time: float = 0.0
        self._block_active = False
        self._log = get_logger()

    # --- Propriedades ---

    @property
    def reminder_cooldown(self) -> float:
        return self._reminder_cooldown

    @reminder_cooldown.setter
    def reminder_cooldown(self, value: float) -> None:
        self._reminder_cooldown = max(0.5, value)

    @property
    def block_duration(self) -> float:
        return self._block_duration

    @block_duration.setter
    def block_duration(self, value: float) -> None:
        self._block_duration = max(1.0, value)

    @property
    def allow_reminders_during_cooldown(self) -> bool:
        return self._allow_reminders_during_cooldown

    @allow_reminders_during_cooldown.setter
    def allow_reminders_during_cooldown(self, value: bool) -> None:
        self._allow_reminders_during_cooldown = value

    @property
    def is_block_active(self) -> bool:
        return self._block_active

    # --- Lembrete ---

    def can_show_reminder(self) -> bool:
        """Verifica se o cooldown entre lembretes permite exibir."""
        elapsed = time.time() - self._last_reminder_time
        return elapsed >= self._reminder_cooldown

    @Slot()
    def request_reminder(self) -> None:
        """Tenta exibir um lembrete (respeita cooldown)."""
        if self._block_active:
            return
        if not self.can_show_reminder():
            return
        self._last_reminder_time = time.time()
        self._log.info("Lembrete exibido")
        self.show_reminder.emit()

    @Slot()
    def force_reminder(self) -> None:
        """Exibe lembrete imediatamente (botão de teste)."""
        self._last_reminder_time = time.time()
        self._log.info("Lembrete exibido (teste)")
        self.show_reminder.emit()

    # --- Bloqueio ---

    @Slot()
    def trigger_block(self) -> None:
        """Aciona o bloqueio visual fullscreen."""
        if self._block_active:
            return
        self._block_active = True
        self._log.info("Bloqueio acionado (duração: %.1fs)", self._block_duration)
        self.show_block.emit()

    @Slot()
    def finish_block(self) -> None:
        """Marca o bloqueio como finalizado."""
        self._block_active = False
        self._log.info("Bloqueio finalizado")
        self.block_finished.emit()

    @Slot()
    def force_block(self) -> None:
        """Aciona bloqueio imediatamente (botão de teste)."""
        self._block_active = True
        self._log.info("Bloqueio acionado (teste)")
        self.show_block.emit()

    def reset(self) -> None:
        """Reseta estado."""
        self._block_active = False
        self._last_reminder_time = 0.0
