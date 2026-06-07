"""
SettingsManager - Gerencia configurações persistidas em JSON local.

Salva/carrega preferências: limite de volume, intervalos de análise,
janela de acúmulo, tempos de bloqueio/cooldown e dispositivo de microfone.
"""

import hashlib
import json
import os
from dataclasses import dataclass, asdict


DEFAULT_SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".loud_voice_cooldown", "settings.json"
)


@dataclass
class AppSettings:
    # Limite de volume para alerta (escala 0-100)
    volume_threshold: int = 40
    # Intervalo de análise em milissegundos
    analysis_interval_ms: int = 100
    # Janela de acúmulo em segundos
    accumulation_window: float = 10.0
    # Tempo acumulado acima do limite para acionar bloqueio (segundos)
    block_accumulation: float = 5.0
    # Duração do lembrete visual (segundos)
    reminder_duration: float = 1.5
    # Cooldown entre lembretes visuais (segundos)
    reminder_cooldown: float = 3.0
    # Duração do bloqueio visual (segundos)
    block_duration: float = 8.0
    # Cooldown após bloqueio (segundos)
    post_block_cooldown: float = 45.0
    # Permitir lembretes durante cooldown pós-bloqueio
    allow_reminders_during_cooldown: bool = True
    # Dispositivo de microfone (None = padrão do sistema)
    microphone_device: int | None = None
    # Taxa de amostragem do áudio
    sample_rate: int = 16000
    # Tamanho do bloco de áudio em frames
    block_size: int = 1024
    # Hash SHA-256 da senha de admin (vazio = sem proteção)
    admin_password_hash: str = ""
    # Iniciar minimizado na tray (discreto)
    start_minimized: bool = True
    # Iniciar monitoramento automaticamente
    auto_start_monitoring: bool = True


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
            self.save()

    def save(self) -> None:
        """Salva configurações atuais no JSON."""
        self._ensure_dir()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)

    def reset_defaults(self) -> None:
        """Restaura configurações padrão."""
        pw_hash = self.settings.admin_password_hash
        self.settings = AppSettings()
        self.settings.admin_password_hash = pw_hash
        self.save()

    # --- Senha de admin ---

    @staticmethod
    def hash_password(password: str) -> str:
        """Gera hash SHA-256 da senha."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def has_password(self) -> bool:
        """Verifica se uma senha de admin foi definida."""
        return bool(self.settings.admin_password_hash)

    def verify_password(self, password: str) -> bool:
        """Verifica se a senha informada está correta."""
        if not self.has_password():
            return True
        return self.hash_password(password) == self.settings.admin_password_hash

    def set_password(self, new_password: str) -> None:
        """Define nova senha de admin."""
        self.settings.admin_password_hash = self.hash_password(new_password)
        self.save()

    def remove_password(self) -> None:
        """Remove a senha de admin."""
        self.settings.admin_password_hash = ""
        self.save()
