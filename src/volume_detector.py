"""
VolumeDetector - Detecta voz alta sustentada usando janela deslizante.

Regra: se o volume ficar acima do limite por pelo menos `sustained_duration`
segundos acumulados dentro de uma janela de `detection_window` segundos,
o alerta é disparado. Isso evita falsos positivos por picos rápidos.
"""

import time
from collections import deque
from PySide6.QtCore import QObject, Signal, Slot
from typing import Optional


class VolumeDetector(QObject):
    """Analisa volume ao longo do tempo e detecta voz alta sustentada."""

    # Emitido quando voz alta sustentada é detectada
    loud_voice_detected = Signal()
    # Emitido com a fração do tempo acumulado (0.0-1.0) para visualização
    accumulation_updated = Signal(float)

    def __init__(
        self,
        threshold: float = 0.15,
        sustained_duration: float = 2.0,
        detection_window: float = 5.0,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._threshold = threshold
        self._sustained_duration = sustained_duration
        self._detection_window = detection_window
        # Armazena tuplas (timestamp, acima_do_limite: bool)
        self._samples: deque = deque()
        self._enabled = True

    @property
    def threshold(self) -> float:
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        self._threshold = max(0.0, min(1.0, value))

    @property
    def sustained_duration(self) -> float:
        return self._sustained_duration

    @sustained_duration.setter
    def sustained_duration(self, value: float) -> None:
        self._sustained_duration = value

    @property
    def detection_window(self) -> float:
        return self._detection_window

    @detection_window.setter
    def detection_window(self, value: float) -> None:
        self._detection_window = value

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._samples.clear()

    @Slot(float)
    def process_volume(self, volume: float) -> None:
        """Processa uma amostra de volume e verifica se excedeu o limite."""
        if not self._enabled:
            return

        now = time.time()
        is_loud = volume > self._threshold
        self._samples.append((now, is_loud))

        # Remove amostras fora da janela de detecção
        cutoff = now - self._detection_window
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # Calcula tempo acumulado acima do limite
        accumulated = self._calculate_accumulated_time()
        fraction = min(accumulated / self._sustained_duration, 1.0) if self._sustained_duration > 0 else 0.0
        self.accumulation_updated.emit(fraction)

        # Verifica se atingiu o tempo sustentado
        if accumulated >= self._sustained_duration:
            self._samples.clear()
            self.loud_voice_detected.emit()

    def _calculate_accumulated_time(self) -> float:
        """Calcula tempo total acima do limite dentro da janela."""
        if len(self._samples) < 2:
            return 0.0

        total = 0.0
        samples_list = list(self._samples)
        for i in range(1, len(samples_list)):
            if samples_list[i - 1][1]:  # Se a amostra anterior estava acima
                dt = samples_list[i][0] - samples_list[i - 1][0]
                total += dt
        return total

    def reset(self) -> None:
        """Limpa o histórico de amostras."""
        self._samples.clear()
