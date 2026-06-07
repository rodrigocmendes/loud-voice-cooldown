"""
Logger - Configuração de logs técnicos para troubleshooting.

Registra eventos como início/parada do monitoramento, detecção de picos,
lembretes, bloqueios e cooldowns. Não registra áudio nem conteúdo falado.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.expanduser("~"), ".loud_voice_cooldown")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logger() -> logging.Logger:
    """Configura e retorna o logger principal da aplicação."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("loud_voice_cooldown")
    logger.setLevel(logging.DEBUG)

    # Handler de arquivo com rotação (max 2MB, 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # Handler de console (apenas INFO+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(levelname)-7s | %(message)s")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Retorna o logger da aplicação (cria se necessário)."""
    logger = logging.getLogger("loud_voice_cooldown")
    if not logger.handlers:
        return setup_logger()
    return logger
