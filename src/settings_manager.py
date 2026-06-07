"""
SettingsManager - Gerencia configurações persistidas em JSON local.

Salva/carrega preferências como limites de volume, tempos de bloqueio,
cooldown e dispositivo de microfone selecionado.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


DEFAULT_SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".loud_voice_cooldown", "settings.json"
)


@dataclass
class AppSettings:
    # Limite de volume RMS normalizado (0.0 - 1.0)
    volume_threshold: float = 0.15
    # Tempo mínimo acumulado acima do limite para disparar (segundos)
    sustained_duration: float = 2.0
    # Janela de tempo para acumular (segundos)
    detection_window: float = 5.0
    # Duração do bloqueio em segundos
    block_duration: float = 8.0
    # Cooldown entre bloqueios em segundos
    cooldown_duration: float = 45.0
    # Dispositivo de microfone (None = padrão do sistema)
    microphone_device: Optional[int] = None
    # Modo progressivo de alertas (1=aviso, 2=overlay, 3=tela escura)
    progressive_alerts: bool = True
    # Volume calibrado (nível normal da criança)
    calibrated_volume: float = 0.05
    # Taxa de amostragem do áudio
    sample_rate: int = 16000
    # Tamanho do bloco de áudio em frames
    block_size: int = 1024


class SettingsManager:
    """Carrega e salva configurações em arquivo JSON local."""

    def __init__(self, path: str = DEFAULT_SETTINGS_PATH):
        self._path = path
        self.settings = AppSettings()
        self._ensure_dir()
        self.load()

    def _ensure_dir(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> None:
        """Carrega configurações do JSON. Se não existir, usa padrão."""
        if not os.path.exists(self._path):
            self.save()
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
        except (json.JSONDecodeError, IOError):
            # Se arquivo corrompido, usa padrão
            self.save()

    def save(self) -> None:
        """Salva configurações atuais no JSON."""
        self._ensure_dir()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)

    def reset_defaults(self) -> None:
        """Restaura configurações padrão."""
        self.settings = AppSettings()
        self.save()
