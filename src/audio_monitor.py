"""
AudioMonitor - Captura áudio do microfone em tempo real usando sounddevice.

Calcula o volume RMS e converte para escala 0-100.
Não grava, não transcreve e não envia nada pela rede.
"""

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
import sounddevice as sd

from .logger import get_logger

# Fator de escala para converter RMS float32 em 0-100.
# Fala normal ~0.01-0.05 RMS → 4-20 na escala.
# Fala alta ~0.08-0.25 RMS → 32-100 na escala.
VOLUME_SCALE = 400


class AudioMonitor(QObject):
    """Captura áudio do microfone e calcula volume em escala 0-100."""

    # Sinal emitido com o volume (0-100) a cada bloco de áudio
    volume_updated = Signal(float)
    # Sinal emitido quando ocorre erro na captura
    error_occurred = Signal(str)

    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = 16000,
        block_size: int = 1024,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._device = device
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._stream: sd.InputStream | None = None
        self._running = False
        self._current_volume: float = 0.0
        self._log = get_logger()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_volume(self) -> float:
        """Volume atual na escala 0-100."""
        return self._current_volume

    def set_device(self, device: int | None) -> None:
        """Define o dispositivo de captura. None = padrão do sistema."""
        was_running = self._running
        if was_running:
            self.stop()
        self._device = device
        self._log.info("Microfone selecionado: %s", device if device is not None else "padrão")
        if was_running:
            self.start()

    def set_sample_rate(self, rate: int) -> None:
        self._sample_rate = rate

    def set_block_size(self, size: int) -> None:
        self._block_size = size

    @Slot()
    def start(self) -> None:
        """Inicia a captura de áudio."""
        if self._running:
            return
        try:
            self._stream = sd.InputStream(
                device=self._device,
                channels=1,
                samplerate=self._sample_rate,
                blocksize=self._block_size,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            self._log.info("Captura de áudio iniciada (device=%s)", self._device)
        except Exception as e:
            self._log.error("Erro ao iniciar captura: %s", e)
            self.error_occurred.emit(f"Erro ao iniciar captura: {e}")

    @Slot()
    def stop(self) -> None:
        """Para a captura de áudio."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._running = False
        self._current_volume = 0.0
        self._log.info("Captura de áudio parada")

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info, status
    ) -> None:
        """Callback por bloco de áudio: calcula RMS e converte para 0-100."""
        if status:
            pass  # Ignora overflow silenciosamente
        rms = float(np.sqrt(np.mean(indata**2)))
        volume = min(rms * VOLUME_SCALE, 100.0)
        self._current_volume = volume
        self.volume_updated.emit(volume)

    @staticmethod
    def list_devices() -> list[dict]:
        """Lista dispositivos de entrada disponíveis."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append({"index": i, "name": dev["name"]})
        return input_devices
