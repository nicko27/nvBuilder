# nvbuilder/logging_setup.py
"""Configuration du logging."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any
import sys
import argparse
from colorama import Fore # Utiliser colorama pour les messages initiaux

from .constants import DEFAULT_LOG_FILENAME
from .utils import get_absolute_path

# Formatter simplifié pour la console
CONSOLE_FORMAT_QUIET = "%(message)s"
CONSOLE_FORMAT_DEBUG = "%(levelname)s: %(message)s"
FILE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def is_debug_mode():
    """
    Vérifie si le mode debug est activé via les arguments de ligne de commande.
    Parcourt sys.argv manuellement car argparse n'est pas encore configuré.
    """
    return '--debug' in sys.argv or '-d' in sys.argv

def setup_logging(log_config: Dict[str, Any], base_dir: Path):
    """Configure le logging basé sur la configuration fournie et le mode debug."""
    # Déterminer le niveau de log
    debug_mode = is_debug_mode()
    log_level_str = 'DEBUG' if debug_mode else log_config.get('level', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Configurer le logger racine 'nvbuilder'
    logger = logging.getLogger("nvbuilder")
    # Nettoyer les anciens handlers pour éviter les doublons
    for handler in logger.handlers[:]: 
        logger.removeHandler(handler)
    logger.setLevel(logging.DEBUG) # Capturer tous les niveaux à partir de DEBUG

    # Handler Fichier (toujours détaillé)
    file_handler = None
    try:
        log_file_str = log_config.get('file', DEFAULT_LOG_FILENAME)
        log_file_path = get_absolute_path(log_file_str, base_dir)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = log_config.get('max_size', 10485760)
        backup_count = log_config.get('backup_count', 3)
        file_formatter = logging.Formatter(log_config.get('format', FILE_FORMAT))
        file_handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"{Fore.YELLOW}AVERTISSEMENT: Logging fichier désactivé: {e}{Fore.RESET}")

    # Handler Console 
    console_formatter = logging.Formatter(CONSOLE_FORMAT_DEBUG if debug_mode else CONSOLE_FORMAT_QUIET)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    logger.propagate = False
    
    # Message de démarrage minimal si mode debug
    if debug_mode:
        logger.debug("Mode debug activé. Logs détaillés.")
    else:
        # Aucun message en mode normal sauf erreurs critiques
        logger.setLevel(logging.ERROR)