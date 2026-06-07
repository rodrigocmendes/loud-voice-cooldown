"""
CooldownManager - Controla intervalos mínimos entre bloqueios.

Após um bloqueio, impede novos alertas por um período configurável
para evitar punições repetidas em sequência.
"""

import time
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional


class CooldownManager(QObject):
    """Gerencia o cooldown entre alertas/bloqueios."""

    # Emitido quando o cooldown termina e o sistema está pronto
    cooldown_finished = Signal()
    # Emitido com o tempo restante de cooldown (segundos)
    cooldown_tick = Signal(float)

    def __init__(
        self,
        cooldown_duration: float = 45.0,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._cooldown_duration = cooldown_duration
        self._cooldown_start: Optional[float] = None
        self._in_cooldown = False

    @property
    def cooldown_duration(self) -> float:
        return self._cooldown_duration

    @cooldown_duration.setter
    def cooldown_duration(self, value: float) -> None:
        self._cooldown_duration = max(0.0, value)

    @property
    def in_cooldown(self) -> bool:
        """Verifica se está em período de cooldown."""
        if not self._in_cooldown:
            return False
        elapsed = time.time() - self._cooldown_start
        if elapsed >= self._cooldown_duration:
            self._in_cooldown = False
            self.cooldown_finished.emit()
            return False
        return True

    @property
    def remaining_time(self) -> float:
        """Retorna tempo restante do cooldown em segundos."""
        if not self._in_cooldown or self._cooldown_start is None:
            return 0.0
        elapsed = time.time() - self._cooldown_start
        remaining = self._cooldown_duration - elapsed
        return max(0.0, remaining)

    @Slot()
    def start_cooldown(self) -> None:
        """Inicia o período de cooldown."""
        self._cooldown_start = time.time()
        self._in_cooldown = True

    @Slot()
    def cancel_cooldown(self) -> None:
        """Cancela o cooldown manualmente."""
        self._in_cooldown = False
        self._cooldown_start = None

    def reset(self) -> None:
        """Reseta o estado do cooldown."""
        self._in_cooldown = False
        self._cooldown_start = None
