"""
VolumeDetector - Detecta picos de voz alta e acumula tempo acima do limite.

Analisa volume a cada intervalo configurável (padrão 100ms).
Usa janela móvel para acumular tempo acima do limite.
Dispara bloqueio quando o acumulado atinge o limiar configurado.
"""

import time
from collections import deque
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from .logger import get_logger


class VolumeDetector(QObject):
    """Analisa volume periodicamente e acumula tempo acima do limite."""

    # Emitido quando volume está acima do limite (pico detectado)
    peak_detected = Signal()
    # Emitido com o tempo acumulado (segundos) para atualizar UI
    accumulation_updated = Signal(float)
    # Emitido quando tempo acumulado atinge o limiar de bloqueio
    block_triggered = Signal()

    def __init__(
        self,
        threshold: int = 40,
        analysis_interval_ms: int = 100,
        accumulation_window: float = 60.0,
        block_accumulation: float = 5.0,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._threshold = threshold
        self._analysis_interval_ms = analysis_interval_ms
        self._accumulation_window = accumulation_window
        self._block_accumulation = block_accumulation
        self._enabled = True
        self._log = get_logger()

        # Timestamps de cada tick em que o volume estava acima do limite
        self._loud_ticks: deque[float] = deque()

        # Estatísticas para painel de debug
        self._trigger_count = 0
        self._last_trigger_time: str | None = None
        self._max_recent_volume: float = 0.0
        self._max_volume_decay_counter = 0

        # Referência ao AudioMonitor para ler current_volume
        self._volume_source = None

        # Timer de análise
        self._timer = QTimer(self)
        self._timer.setInterval(analysis_interval_ms)
        self._timer.timeout.connect(self._analyze)

    # --- Propriedades ---

    @property
    def threshold(self) -> int:
        return self._threshold

    @threshold.setter
    def threshold(self, value: int) -> None:
        self._threshold = max(0, min(100, value))

    @property
    def analysis_interval_ms(self) -> int:
        return self._analysis_interval_ms

    @analysis_interval_ms.setter
    def analysis_interval_ms(self, value: int) -> None:
        self._analysis_interval_ms = max(50, value)
        self._timer.setInterval(self._analysis_interval_ms)

    @property
    def accumulation_window(self) -> float:
        return self._accumulation_window

    @accumulation_window.setter
    def accumulation_window(self, value: float) -> None:
        self._accumulation_window = max(5.0, value)

    @property
    def block_accumulation(self) -> float:
        return self._block_accumulation

    @block_accumulation.setter
    def block_accumulation(self, value: float) -> None:
        self._block_accumulation = max(1.0, value)

    @property
    def accumulated_time(self) -> float:
        """Tempo total acumulado acima do limite dentro da janela (segundos)."""
        self._prune_old_ticks()
        return len(self._loud_ticks) * (self._analysis_interval_ms / 1000.0)

    @property
    def trigger_count(self) -> int:
        return self._trigger_count

    @property
    def last_trigger_time(self) -> str | None:
        return self._last_trigger_time

    @property
    def max_recent_volume(self) -> float:
        return self._max_recent_volume

    # --- Métodos públicos ---

    def set_volume_source(self, audio_monitor) -> None:
        """Define a fonte de volume (AudioMonitor) para leitura periódica."""
        self._volume_source = audio_monitor

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def start(self) -> None:
        """Inicia o timer de análise."""
        self._timer.start()

    def stop(self) -> None:
        """Para o timer de análise."""
        self._timer.stop()

    def reset(self) -> None:
        """Zera acumulador e estatísticas."""
        self._loud_ticks.clear()
        self._trigger_count = 0
        self._last_trigger_time = None
        self._max_recent_volume = 0.0
        self.accumulation_updated.emit(0.0)
        self._log.info("Acumulador resetado")

    def inject_time(self, seconds: float) -> None:
        """Injeta tempo artificial no acumulador (para botão de teste)."""
        now = time.time()
        tick_duration = self._analysis_interval_ms / 1000.0
        num_ticks = int(seconds / tick_duration)
        for i in range(num_ticks):
            self._loud_ticks.append(now - (num_ticks - i) * tick_duration)
        accumulated = self.accumulated_time
        self._log.info("Tempo artificial injetado: %.1fs (acumulado: %.1fs)", seconds, accumulated)
        self.accumulation_updated.emit(accumulated)
        # Verifica se atingiu o limiar
        if accumulated >= self._block_accumulation:
            self._log.info("Bloqueio acionado por acúmulo (%.1fs >= %.1fs)", accumulated, self._block_accumulation)
            self.block_triggered.emit()

    # --- Análise periódica ---

    @Slot()
    def _analyze(self) -> None:
        """Chamado a cada intervalo de análise."""
        if not self._enabled or self._volume_source is None:
            return

        volume = self._volume_source.current_volume
        now = time.time()

        # Atualiza volume máximo recente (decai a cada ~3s)
        if volume > self._max_recent_volume:
            self._max_recent_volume = volume
            self._max_volume_decay_counter = 0
        else:
            self._max_volume_decay_counter += 1
            # Decai após ~30 ticks (3s a 100ms)
            if self._max_volume_decay_counter > 30:
                self._max_recent_volume = max(volume, self._max_recent_volume * 0.95)
                self._max_volume_decay_counter = 0

        # Compara com o limite
        if volume > self._threshold:
            self._loud_ticks.append(now)
            self._trigger_count += 1
            self._last_trigger_time = datetime.now().strftime("%H:%M:%S")
            self._log.debug("Volume acima do limite: %.1f > %d", volume, self._threshold)
            self.peak_detected.emit()

        # Remove ticks fora da janela
        self._prune_old_ticks()

        # Calcula acumulado e emite
        accumulated = len(self._loud_ticks) * (self._analysis_interval_ms / 1000.0)
        self.accumulation_updated.emit(accumulated)

        # Verifica se atingiu o limiar de bloqueio
        if accumulated >= self._block_accumulation:
            self._log.info(
                "Bloqueio acionado por acúmulo (%.1fs >= %.1fs)",
                accumulated, self._block_accumulation,
            )
            self.block_triggered.emit()

    def _prune_old_ticks(self) -> None:
        """Remove ticks mais antigos que a janela de acúmulo."""
        cutoff = time.time() - self._accumulation_window
        while self._loud_ticks and self._loud_ticks[0] < cutoff:
            self._loud_ticks.popleft()
