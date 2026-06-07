"""
AudioMonitor - Captura áudio do microfone em tempo real usando sounddevice.

Emite sinais com o nível de volume RMS calculado a cada bloco de áudio.
Não grava, não transcreve e não envia nada pela rede.
"""

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
import sounddevice as sd
from typing import Optional


class AudioMonitor(QObject):
    """Captura áudio do microfone e calcula RMS em tempo real."""

    # Sinal emitido com o valor RMS normalizado (0.0 a 1.0) a cada bloco
    volume_updated = Signal(float)
    # Sinal emitido quando ocorre erro na captura
    error_occurred = Signal(str)

    def __init__(
        self,
        device: Optional[int] = None,
        sample_rate: int = 16000,
        block_size: int = 1024,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._device = device
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._stream: Optional[sd.InputStream] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def set_device(self, device: Optional[int]) -> None:
        """Define o dispositivo de captura. None = padrão do sistema."""
        was_running = self._running
        if was_running:
            self.stop()
        self._device = device
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
        except Exception as e:
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

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback chamado por sounddevice a cada bloco de áudio."""
        if status:
            # Ignora erros de overflow silenciosamente
            pass
        # Calcula RMS do bloco
        rms = float(np.sqrt(np.mean(indata**2)))
        # Normaliza para faixa 0-1 (clamp)
        normalized = min(rms * 5.0, 1.0)  # Fator de escala para sensibilidade
        self.volume_updated.emit(normalized)

    @staticmethod
    def list_devices() -> list[dict]:
        """Lista dispositivos de entrada disponíveis."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append({"index": i, "name": dev["name"]})
        return input_devices
