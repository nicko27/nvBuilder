# nvbuilder/logging_setup.py
"""Configuration du logging."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any
import sys
from colorama import Fore # Utiliser colorama pour les messages initiaux

from .constants import DEFAULT_LOG_FILENAME
from .utils import get_absolute_path

# Formatter plus simple pour la console
CONSOLE_FORMAT = "%(levelname)s: %(message)s"
# Formatter plus détaillé pour le fichier
FILE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(log_config: Dict[str, Any], base_dir: Path):
    """Configure le logging basé sur la configuration fournie."""
    log_level_str = log_config.get('level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configurer le logger racine 'nvbuilder'
    logger = logging.getLogger("nvbuilder")
    # Nettoyer les anciens handlers pour éviter doublons
    for handler in logger.handlers[:]: logger.removeHandler(handler)
    logger.setLevel(logging.DEBUG) # Capturer tous les niveaux à partir de DEBUG

    # Handler Fichier (plus détaillé)
    file_handler = None
    try:
        log_file_str = log_config.get('file', DEFAULT_LOG_FILENAME)
        log_file_path = get_absolute_path(log_file_str, base_dir)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = log_config.get('max_size', 10485760)
        backup_count = log_config.get('backup_count', 3)
        file_formatter = logging.Formatter(log_config.get('format', FILE_FORMAT)) # Utiliser format config ou défaut fichier
        file_handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG) # Logguer DEBUG et plus dans le fichier
        logger.addHandler(file_handler)
        # Logguer le chemin du fichier log une fois qu'il est ouvert
        logger.debug(f"Logging fichier activé vers: {log_file_path}")
    except Exception as e:
        print(f"{Fore.YELLOW}AVERTISSEMENT: Logging fichier désactivé ('{log_config.get('file')}'): {e}{Fore.RESET}")

    # Handler Console (moins verbeux par défaut)
    console_formatter = logging.Formatter(CONSOLE_FORMAT)
    console_handler = logging.StreamHandler(sys.stdout) # Utiliser stdout pour messages normaux
    console_handler.setFormatter(console_formatter)
    # Le niveau de la console dépend du niveau global demandé dans la config
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    logger.propagate = False
    logger.debug("Logger 'nvbuilder' configuré.")