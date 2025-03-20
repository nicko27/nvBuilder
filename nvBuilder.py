#!/bin/bash
# Ce script est à la fois un script shell et un script Python
# Il s'exécute d'abord comme un script shell, puis lance l'interpréteur Python

# Bannière et version
VERSION="1.2.0"
BANNER_TEXT="nvBuilder - Archive auto-extractible multifonction"

# Vérifier si Python 3 est disponible
if ! command -v python3 &>/dev/null; then
    echo -e "\033[31m\033[1m✗\033[0m Python 3 est requis mais n'est pas installé."
    echo -e "\033[34m\033[1m→\033[0m Sur Ubuntu/Debian: sudo apt install python3"
    exit 1
fi

# Exécuter la partie Python de ce script
python3 -c "
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import tempfile
import tarfile
import json
import argparse
import subprocess
import urllib.request
import configparser
import io
import stat
import fnmatch
import hashlib
import datetime
import logging
import platform
import base64
import re
import threading
import time
import signal
import getpass
import pwd
import grp
import ssl
import socket
import struct
import random
import string
import textwrap
import shlex
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set, Callable
from contextlib import contextmanager
from functools import wraps

# Version du script
VERSION = \"$VERSION\"

# Couleurs et formatage (compatible avec les terminaux Linux)
BOLD = \"\\033[1m\"
RED = \"\\033[31m\"
GREEN = \"\\033[32m\"
YELLOW = \"\\033[33m\"
BLUE = \"\\033[34m\"
RESET = \"\\033[0m\"

class NvBuilder:
    def __init__(self):
        # Configuration générale
        self.extract_dir = \"\"
        self.extract_only = False
        self.need_root = True
        self.version_url = \"http://localhost/newInstall.sh.version\"
        self.version_check = True
        self.script_exec = \"start.sh\"
        self.debug = False
        self.skip_version_check = False
        self.config_file = \"\"
        self.verbosity = 1  # 0=silencieux, 1=minimal, 2=normal, 3=verbeux
        self.output_format = \"sh\"  # sh ou py
        self.force = False
        self.log_file = \"\"
        self.logger = None
        self.interactive = True
        self.startup_banner = True
        self.banner_text = \"$BANNER_TEXT\"
        
        # Compression et archivage
        self.compression = \"bzip2\"  # bzip2, gzip, xz
        self.output_file = \"\"
        self.content_dir = \"\"
        self.include_patterns = []
        self.exclude_patterns = []
        self.nested_archives = []  # Liste d'autres archives à inclure
        
        # Intégrité et sécurité
        self.create_checksum = True
        self.verify_checksum = True
        self.encrypt = False
        self.encrypt_password = \"\"
        self.signature_key = \"\"
        self.remote_hash_url = \"\"
        self.hash_algorithm = \"sha256\"  # md5, sha1, sha256, sha512
        self.expiration_date = None  # Format: YYYY-MM-DD
        
        # Gestion des permissions
        self.preserve_permissions = True
        self.force_root_ownership = False
        self.default_mode = 0o755  # Permission par défaut pour les fichiers extraits
        
        # Gestion de l'exécution
        self.pre_exec_script = \"\"
        self.post_exec_script = \"\"
        self.install_deps = True
        self.retry_count = 3
        self.timeout = 300  # en secondes
        self.min_disk_space = 0  # en Mo
        self.required_packages = []
        self.required_commands = []
        self.conditional_execution = \"\"  # Expression conditionnelle pour l'exécution
        
        # Sauvegarde
        self.backup = True
        self.backup_dir = \"\"
        self.cleanup = True
        self.send_calling_dir = False
        
        # État interne
        self._extraction_start_time = None
        self._required_disk_space = 0
        self._script_mode = \"extraction\"  # 'création' ou 'extraction'
        self._temp_dirs = []
        self._original_dir = os.getcwd()
        self._installation_summary = []
        
        # Parser les arguments
        self.parse_args()
        
        # Configuration de la journalisation
        self.setup_logging()
        
        # Trapper les signaux pour le nettoyage
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Configure les gestionnaires de signaux pour le nettoyage"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Gestionnaire de signaux pour un nettoyage propre"""
        self.log_warning(f\"Signal reçu ({signum}), arrêt en cours...\")
        self.cleanup_temp_files()
        sys.exit(1)
    
    def setup_logging(self):
        """Configure la journalisation"""
        self.logger = logging.getLogger(\"nvBuilder\")
        
        # Définir le niveau de journalisation en fonction de la verbosité
        if self.verbosity == 0:
            log_level = logging.ERROR
        elif self.verbosity == 1:
            log_level = logging.WARNING
        elif self.verbosity == 2:
            log_level = logging.INFO
        else:
            log_level = logging.DEBUG
            
        self.logger.setLevel(log_level)
        
        # Supprimer les gestionnaires existants
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Gestionnaire pour la console, sauf en mode silencieux
        if self.verbosity > 0:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            
            # Formateur personnalisé
            class ColoredFormatter(logging.Formatter):
                def format(self, record):
                    if record.levelno == logging.DEBUG:
                        prefix = f\"{BLUE}{BOLD}→{RESET}\"
                    elif record.levelno == logging.INFO:
                        prefix = f\"{BLUE}{BOLD}→{RESET}\"
                    elif record.levelno == logging.WARNING:
                        prefix = f\"{YELLOW}{BOLD}⚠{RESET}\"
                    elif record.levelno == logging.ERROR:
                        prefix = f\"{RED}{BOLD}✗{RESET}\"
                    else:
                        prefix = f\"{GREEN}{BOLD}✓{RESET}\"
                    return f\"  {prefix} {record.getMessage()}\"
                    
            formatter = ColoredFormatter()
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
        
        # Ajouter un gestionnaire de fichier si un fichier de log est spécifié
        if self.log_file:
            try:
                file_handler = logging.FileHandler(self.log_file)
                file_handler.setLevel(logging.DEBUG)  # Toujours niveau DEBUG dans le fichier
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.log_error(f\"Impossible d'ouvrir le fichier de log: {str(e)}\")
    
    def log_debug(self, message):
        """Affiche un message de debug"""
        self.logger.debug(message)
    
    def log_info(self, message):
        """Affiche un message d'information"""
        self.logger.info(message)
    
    def log_success(self, message):
        """Affiche un message de succès"""
        self.logger.critical(message)  # Using CRITICAL for success messages with custom formatter
    
    def log_warning(self, message):
        """Affiche un message d'avertissement"""
        self.logger.warning(message)
    
    def log_error(self, message):
        """Affiche un message d'erreur"""
        self.logger.error(message)
    
    def show_banner(self):
        """Affiche une bannière de démarrage"""
        if not self.startup_banner or self.verbosity == 0:
            return
            
        width = 70
        padding = (width - len(self.banner_text) - 2) // 2
        banner = [
            f\"{BLUE}{BOLD}{'=' * width}{RESET}\",
            f\"{BLUE}{BOLD}|{' ' * padding}{self.banner_text}{' ' * (width - padding - len(self.banner_text) - 2)}|{RESET}\",
            f\"{BLUE}{BOLD}|{' ' * (width - 2)}|{RESET}\",
            f\"{BLUE}{BOLD}|{' ' * (padding + 2)}Version: {VERSION}{' ' * (width - padding - 12 - len(VERSION))}|{RESET}\",
            f\"{BLUE}{BOLD}{'=' * width}{RESET}\"
        ]
        
        for line in banner:
            print(line)
    
    def progress_bar(self, current, total, prefix='', suffix='', length=50):
        """Affiche une barre de progression dans la console"""
        if self.verbosity < 2 or not sys.stdout.isatty():
            return
            
        percent = f\"{100 * (current / float(total)):.1f}\"
        filled_length = int(length * current // total)
        bar = '█' * filled_length + '░' * (length - filled_length)
        
        sys.stdout.write(f'\\r{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()
        
        if current == total:
            sys.stdout.write('\\n')
        
    def parse_args(self):
        """Parse les arguments de ligne de commande"""
        parser = argparse.ArgumentParser(description='Crée ou extrait une archive auto-extractible avec options avancées')
        
        # Options de base
        parser.add_argument('-c', '--config', dest='config_file', help='Utilise le fichier de configuration spécifié')
        parser.add_argument('-d', '--dir', dest='extract_dir', help='Spécifie le répertoire d\\'extraction')
        parser.add_argument('-x', '--extract-only', dest='extract_only', action='store_true', help='Extrait uniquement l\\'archive sans exécuter le script')
        parser.add_argument('--debug', dest='debug', action='store_true', help='Active le mode debug')
        parser.add_argument('--skip-version', dest='skip_version', action='store_true', help='Désactive la vérification de version')
        
        # Options de création
        parser.add_argument('-f', '--format', dest='output_format', choices=['sh', 'py'], help='Format du script généré (sh ou py)')
        parser.add_argument('-o', '--output', dest='output_file', help='Nom du fichier de sortie')
        parser.add_argument('--content', dest='content_dir', help='Répertoire contenant les fichiers à archiver')
        parser.add_argument('-z', '--compression', dest='compression', choices=['bzip2', 'gzip', 'xz'], help='Méthode de compression')
        parser.add_argument('--include', dest='include', action='append', help='Pattern de fichiers à inclure (peut être répété)')
        parser.add_argument('--exclude', dest='exclude', action='append', help='Pattern de fichiers à exclure (peut être répété)')
        parser.add_argument('--nested', dest='nested', action='append', help='Ajouter une archive imbriquée (peut être répété)')
        
        # Sécurité et intégrité
        parser.add_argument('--encrypt', dest='encrypt', action='store_true', help='Chiffre l\\'archive')
        parser.add_argument('--password', dest='password', help='Mot de passe pour le chiffrement')
        parser.add_argument('--sign', dest='sign_key', help='Clé pour signer l\\'archive')
        parser.add_argument('--hash-url', dest='hash_url', help='URL pour vérifier le hash distant')
        parser.add_argument('--hash-algo', dest='hash_algo', choices=['md5', 'sha1', 'sha256', 'sha512'], help='Algorithme de hachage')
        parser.add_argument('--expire', dest='expire', help='Date d\\'expiration (YYYY-MM-DD)')
        parser.add_argument('--no-checksum', dest='no_checksum', action='store_true', help='Désactive la vérification du checksum')
        
        # Permissions
        parser.add_argument('--preserve', dest='preserve', action='store_true', help='Préserve les permissions des fichiers')
        parser.add_argument('--force-root', dest='force_root', action='store_true', help='Force les permissions root pour les fichiers extraits')
        parser.add_argument('--chmod', dest='chmod', help='Permissions à appliquer aux fichiers extraits (ex: 755)')
        
        # Exécution
        parser.add_argument('--pre-exec', dest='pre_exec', help='Script à exécuter avant l\\'extraction')
        parser.add_argument('--post-exec', dest='post_exec', help='Script à exécuter après l\\'extraction')
        parser.add_argument('--no-deps', dest='no_deps', action='store_true', help='Ne pas installer les dépendances manquantes')
        parser.add_argument('--retries', dest='retries', type=int, help='Nombre de tentatives en cas d\\'échec')
        parser.add_argument('--timeout', dest='timeout', type=int, help='Délai d\\'expiration en secondes')
        parser.add_argument('--min-space', dest='min_space', type=int, help='Espace disque minimum requis (en Mo)')
        parser.add_argument('--require-pkg', dest='require_pkg', action='append', help='Paquet requis pour l\\'exécution (peut être répété)')
        parser.add_argument('--require-cmd', dest='require_cmd', action='append', help='Commande requise pour l\\'exécution (peut être répété)')
        parser.add_argument('--if', dest='condition', help='Condition pour l\\'exécution (expression Python)')
        
        # Sauvegarde et nettoyage
        parser.add_argument('--backup', dest='backup', action='store_true', help='Active la sauvegarde avant extraction')
        parser.add_argument('--no-backup', dest='no_backup', action='store_true', help='Désactive la sauvegarde avant extraction')
        parser.add_argument('--backup-dir', dest='backup_dir', help='Répertoire de sauvegarde')
        parser.add_argument('--no-cleanup', dest='no_cleanup', action='store_true', help='Désactive le nettoyage automatique')
        
        # Interface utilisateur
        parser.add_argument('--force', dest='force', action='store_true', help='Force l\\'écrasement des fichiers existants')
        parser.add_argument('--log', dest='log_file', help='Fichier de journalisation')
        parser.add_argument('-q', '--quiet', dest='quiet', action='store_true', help='Mode silencieux')
        parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0, help='Augmente la verbosité (peut être répété)')
        parser.add_argument('--non-interactive', dest='non_interactive', action='store_true', help='Mode non interactif')
        parser.add_argument('--no-banner', dest='no_banner', action='store_true', help='Désactive l\\'affichage de la bannière')
        parser.add_argument('--banner-text', dest='banner_text', help='Texte de la bannière')
        
        args, unknown = parser.parse_known_args()
        
        # Traiter les arguments inconnus comme des options pour le script intégré
        self.script_options = unknown
        
        # Configuration de base
        if args.config_file:
            self.config_file = args.config_file
        if args.extract_dir:
            self.extract_dir = args.extract_dir
        if args.extract_only:
            self.extract_only = True
        if args.debug:
            self.debug = True
        if args.skip_version:
            self.skip_version_check = True
            
        # Options de création
        if args.output_format:
            self.output_format = args.output_format
        if args.output_file:
            self.output_file = args.output_file
        if args.content_dir:
            self.content_dir = args.content_dir
        if args.compression:
            self.compression = args.compression
        if args.include:
            self.include_patterns = args.include
        if args.exclude:
            self.exclude_patterns = args.exclude
        if args.nested:
            self.nested_archives = args.nested
            
        # Sécurité et intégrité
        if args.encrypt:
            self.encrypt = True
        if args.password:
            self.encrypt_password = args.password
        if args.sign_key:
            self.signature_key = args.sign_key
        if args.hash_url:
            self.remote_hash_url = args.hash_url
        if args.hash_algo:
            self.hash_algorithm = args.hash_algo
        if args.expire:
            self.expiration_date = args.expire
        if args.no_checksum:
            self.create_checksum = False
            self.verify_checksum = False
            
        # Permissions
        if args.preserve:
            self.preserve_permissions = True
        if args.force_root:
            self.force_root_ownership = True
        if args.chmod:
            try:
                self.default_mode = int(args.chmod, 8)
            except ValueError:
                pass  # Sera validé plus tard
                
        # Exécution
        if args.pre_exec:
            self.pre_exec_script = args.pre_exec
        if args.post_exec:
            self.post_exec_script = args.post_exec
        if args.no_deps:
            self.install_deps = False
        if args.retries is not None:
            self.retry_count = args.retries
        if args.timeout is not None:
            self.timeout = args.timeout
        if args.min_space is not None:
            self.min_disk_space = args.min_space
        if args.require_pkg:
            self.required_packages = args.require_pkg
        if args.require_cmd:
            self.required_commands = args.require_cmd
        if args.condition:
            self.conditional_execution = args.condition
            
        # Sauvegarde et nettoyage
        if args.backup:
            self.backup = True
        if args.no_backup:
            self.backup = False
        if args.backup_dir:
            self.backup_dir = args.backup_dir
        if args.no_cleanup:
            self.cleanup = False
            
        # Interface utilisateur
        if args.force:
            self.force = True
        if args.log_file:
            self.log_file = args.log_file
        if args.quiet:
            self.verbosity = 0
        else:
            self.verbosity = min(3, 2 + args.verbose)  # 2 = normal, 3 = verbeux
        if args.non_interactive:
            self.interactive = False
        if args.no_banner:
            self.startup_banner = False
        if args.banner_text:
            self.banner_text = args.banner_text
    
    def load_config(self):
        """Charge la configuration depuis un fichier"""
        if not self.config_file:
            return False
            
        if not os.path.isfile(self.config_file):
            self.log_error(f\"Fichier de configuration non trouvé : {self.config_file}\")
            sys.exit(1)
            
        self.log_info(f\"Chargement de la configuration depuis {self.config_file}\")
        
        # Déterminer l'extension du fichier
        _, ext = os.path.splitext(self.config_file)
        
        if ext.lower() == '.ini':
            return self.load_config_ini()
        elif ext.lower() in ['.json', '.js']:
            return self.load_config_json()
        elif ext.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                return self.load_config_yaml()
            except ImportError:
                self.log_warning(\"Module yaml non disponible, tentative de parser comme JSON\")
                return self.load_config_json()
        else:
            # Essayons de détecter le type de fichier
            with open(self.config_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('{'):
                    return self.load_config_json()
                elif content.startswith('#') or '=' in content:
                    return self.load_config_ini()
                else:
                    try:
                        import yaml
                        return self.load_config_yaml()
                    except ImportError:
                        self.log_warning(\"Module yaml non disponible, tentative de parser comme INI\")
                        return self.load_config_ini()
    
    def load_config_yaml(self):
        """Charge la configuration depuis un fichier YAML"""
        try:
            import yaml
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                
            # Charger les paramètres
            self._load_config_from_dict(config)
            return True
            
        except Exception as e:
            self.log_error(f\"Erreur lors du chargement du fichier YAML : {str(e)}\")
            sys.exit(1)
    
    def load_config_json(self):
        """Charge la configuration depuis un fichier JSON"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            # Charger les paramètres
            self._load_config_from_dict(config)
            return True
        
        except Exception as e:
            self.log_error(f\"Erreur lors du chargement du fichier JSON : {str(e)}\")
            sys.exit(1)
    
    def load_config_ini(self):
        """Charge la configuration depuis un fichier INI"""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            if 'general' not in config:
                self.log_error(\"Section 'general' manquante dans le fichier INI\")
                sys.exit(1)
                
            # Convertir la configuration INI en dictionnaire
            config_dict = {}
            
            # Section general
            general = config['general']
            for key, value in general.items():
                config_dict[key] = self._convert_value(value)
                
            # Section patterns
            if 'patterns' in config:
                patterns = config['patterns']
                config_dict['include_patterns'] = [p.strip() for p in patterns.get('include', '').split(',') if p.strip()]
                config_dict['exclude_patterns'] = [p.strip() for p in patterns.get('exclude', '').split(',') if p.strip()]
                if 'nested' in patterns:
                    config_dict['nested_archives'] = [p.strip() for p in patterns.get('nested', '').split(',') if p.strip()]
            
            # Section security
            if 'security' in config:
                security = config['security']
                for key in ['encrypt', 'encrypt_password', 'signature_key', 'remote_hash_url', 
                            'hash_algorithm', 'expiration_date', 'create_checksum', 'verify_checksum']:
                    if key in security:
                        config_dict[key] = self._convert_value(security[key])
            
            # Section permissions
            if 'permissions' in config:
                perms = config['permissions']
                for key in ['preserve_permissions', 'force_root_ownership']:
                    if key in perms:
                        config_dict[key] = self._convert_value(perms[key])
                if 'default_mode' in perms:
                    try:
                        config_dict['default_mode'] = int(perms['default_mode'], 8)
                    except ValueError:
                        self.log_warning(f\"Mode de permissions invalide: {perms['default_mode']}\")
            
            # Section execution
            if 'execution' in config:
                exec_section = config['execution']
                for key in ['pre_exec_script', 'post_exec_script', 'install_deps', 'retry_count', 
                            'timeout', 'min_disk_space', 'conditional_execution']:
                    if key in exec_section:
                        config_dict[key] = self._convert_value(exec_section[key])
                
                if 'required_packages' in exec_section:
                    config_dict['required_packages'] = [p.strip() for p in exec_section.get('required_packages', '').split(',') if p.strip()]
                if 'required_commands' in exec_section:
                    config_dict['required_commands'] = [p.strip() for p in exec_section.get('required_commands', '').split(',') if p.strip()]
            
            # Section backup
            if 'backup' in config:
                backup = config['backup']
                for key in ['backup', 'backup_dir', 'cleanup']:
                    if key in backup:
                        config_dict[key] = self._convert_value(backup[key])
            
            # Section ui
            if 'ui' in config:
                ui = config['ui']
                for key in ['verbosity', 'interactive', 'startup_banner', 'banner_text']:
                    if key in ui:
                        config_dict[key] = self._convert_value(ui[key])
            
            # Charger la configuration
            self._load_config_from_dict(config_dict)
            
            return True
            
        except Exception as e:
            self.log_error(f\"Erreur lors du chargement du fichier INI : {str(e)}\")
            sys.exit(1)
    
    def _convert_value(self, value):
        """Convertit une valeur de chaîne en type approprié"""
        if value.lower() in ['true', 'yes', 'on', '1']:
            return True
        elif value.lower() in ['false', 'no', 'off', '0']:
            return False
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
            return float(value)
        else:
            return value
    
    def _load_config_from_dict(self, config):
        """Charge la configuration à partir d'un dictionnaire"""
        # Paramètres simples (chaînes)
        for key in ['output_file', 'content_dir', 'script_exec', 'compression', 'version_url',
                    'output_format', 'encrypt_password', 'signature_key', 'remote_hash_url',
                    'hash_algorithm', 'expiration_date', 'pre_exec_script', 'post_exec_script',
                    'conditional_execution', 'backup_dir', 'log_file', 'banner_text']:
            if key in config and isinstance(config[key], str) and config[key]:
                setattr(self, key, config[key])
        
        # Paramètres numériques
        for key in ['verbosity', 'retry_count', 'timeout', 'min_disk_space', 'default_mode']:
            if key in config and (isinstance(config[key], int) or isinstance(config[key], float)):
                setattr(self, key, config[key])
        
        # Paramètres booléens
        for key in ['need_root', 'version_check', 'debug', 'backup', 'extract_only',
                    'encrypt', 'create_checksum', 'verify_checksum', 'preserve_permissions',
                    'force_root_ownership', 'install_deps', 'force', 'cleanup',
                    'interactive', 'startup_banner', 'send_calling_dir']:
            if key in config and isinstance(config[key], bool):
                setattr(self, key, config[key])
        
        # Listes
        for key in ['include_patterns', 'exclude_patterns', 'nested_archives',
                    'required_packages', 'required_commands']:
            if key in config and isinstance(config[key], list):
                setattr(self, key, config[key])
                
        # Traitement spécial pour certains champs
        if 'extract_dir' in config and config['extract_dir']:
            self.extract_dir = str(config['extract_dir'])
    
    def normalize_paths(self):
        """Normalise les chemins relatifs en absolus"""
        # Convertir les chemins relatifs en absolus
        if self.content_dir and not os.path.isabs(self.content_dir):
            self.content_dir = os.path.abspath(self.content_dir)
            
        if self.output_file and not os.path.isabs(self.output_file):
            self.output_file = os.path.abspath(self.output_file)
            
        if self.backup_dir and not os.path.isabs(self.backup_dir):
            self.backup_dir = os.path.abspath(self.backup_dir)
            
        if self.extract_dir and not os.path.isabs(self.extract_dir):
            self.extract_dir = os.path.abspath(self.extract_dir)
            
        self.log_debug(f\"Chemin source absolu : {self.content_dir}\")
        self.log_debug(f\"Chemin sortie absolu : {self.output_file}\")
        if self.backup_dir:
            self.log_debug(f\"Chemin backup absolu : {self.backup_dir}\")
    
    def validate_config(self):
        """Valide la configuration chargée"""
        # En mode création, vérifier les paramètres nécessaires
        if self.config_file:  # Mode création
            if not self.output_file:
                self.log_error("Configuration invalide : output_file est requis")
                sys.exit(1)
                
            if not self.content_dir:
                self.log_error("Configuration invalide : content_dir est requis")
                sys.exit(1)
                
            # Vérifier que le dossier source existe
            if not os.path.isdir(self.content_dir):
                self.log_error(f"Dossier source non trouvé : {self.content_dir}")
                sys.exit(1)
                
            # Vérifier que le dossier de sortie existe
            output_dir = os.path.dirname(self.output_file)
            if output_dir and not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.log_info(f"Dossier de sortie créé : {output_dir}")
                except Exception as e:
                    self.log_error(f"Impossible de créer le dossier de sortie : {output_dir}")
                    self.log_debug(f"Erreur : {str(e)}")
                    sys.exit(1)
                    
            # Vérifier si le fichier de sortie existe déjà
            if os.path.exists(self.output_file) and not self.force:
                if self.interactive:
                    response = input(f"Le fichier {self.output_file} existe déjà. Voulez-vous l'écraser ? (o/n) ").strip().lower()
                    if response not in ['o', 'oui', 'y', 'yes']:
                        self.log_info("Opération annulée par l'utilisateur")
                        sys.exit(0)
                else:
                    self.log_error(f"Le fichier {self.output_file} existe déjà. Utilisez --force pour l'écraser.")
                    sys.exit(1)
                
            # Vérifier la méthode de compression
            if self.compression not in ['bzip2', 'gzip', 'xz']:
                self.log_warning(f"Méthode de compression '{self.compression}' non reconnue, utilisation de bzip2 par défaut")
                self.compression = 'bzip2'
                
            # Vérifier le format de sortie
            if self.output_format not in ['sh', 'py']:
                self.log_warning(f"Format de sortie '{self.output_format}' non reconnu, utilisation de sh par défaut")
                self.output_format = 'sh'
                
            # Vérifier les archives imbriquées
            for archive in self.nested_archives:
                if not os.path.isfile(archive):
                    self.log_error(f"Archive imbriquée non trouvée : {archive}")
                    sys.exit(1)
                    
            # Vérifier le chiffrement
            if self.encrypt and not self.encrypt_password and self.interactive:
                # Demander le mot de passe en mode interactif
                password = getpass.getpass("Entrez le mot de passe pour le chiffrement: ")
                password_confirm = getpass.getpass("Confirmez le mot de passe: ")
                
                if password != password_confirm:
                    self.log_error("Les mots de passe ne correspondent pas")
                    sys.exit(1)
                    
                self.encrypt_password = password
                
            elif self.encrypt and not self.encrypt_password and not self.interactive:
                # Générer un mot de passe aléatoire en mode non interactif
                self.encrypt_password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
                self.log_info(f"Mot de passe généré automatiquement: {self.encrypt_password}")
                
            # Vérifier la date d'expiration
            if self.expiration_date:
                try:
                    exp_date = datetime.datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
                    if exp_date < datetime.date.today():
                        self.log_warning("La date d'expiration est dans le passé")
                except ValueError:
                    self.log_error("Format de date d'expiration invalide, utilisez YYYY-MM-DD")
                    sys.exit(1)
                    
            # Vérifier les permissions par défaut
            if not isinstance(self.default_mode, int) or self.default_mode < 0 or self.default_mode > 0o777:
                self.log_warning(f"Mode de permissions invalide: {self.default_mode}, utilisation de 0o755 par défaut")
                self.default_mode = 0o755
                
        # Vérifications pour le mode extraction
        else:
            # Rien de spécial à vérifier pour l'instant
            pass
    
    def check_root(self):
        """Vérifie si l'utilisateur a les droits root nécessaires"""
        if self.need_root and os.geteuid() != 0:
            self.log_info("Ce script nécessite les droits administrateur")
            self.log_info("Veuillez exécuter le script avec sudo")
            sys.exit(1)
    
    def check_dependencies(self):
        """Vérifie si les dépendances nécessaires sont installées"""
        dependencies = []
        
        # Compression
        if self.compression == 'bzip2':
            dependencies.append('bzip2')
        elif self.compression == 'gzip':
            dependencies.append('gzip')
        elif self.compression == 'xz':
            dependencies.append('xz-utils')
            
        # Chiffrement
        if self.encrypt:
            dependencies.append('openssl')
            
        # Ajouter les commandes requises
        dependencies.extend(self.required_commands)
            
        # Vérifier chaque dépendance
        missing = []
        for dep in dependencies:
            try:
                subprocess.run(['which', dep], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                missing.append(dep)
                
        if missing:
            self.log_warning(f"Dépendances manquantes : {', '.join(missing)}")
            
            if self.install_deps:
                if self.interactive:
                    response = input("Voulez-vous installer les dépendances manquantes ? (o/n) ").strip().lower()
                    if response not in ['o', 'oui', 'y', 'yes']:
                        self.log_warning("Installation des dépendances annulée par l'utilisateur")
                        return False
                        
                try:
                    self.log_info("Installation des dépendances...")
                    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                    
                    # Installer les dépendances système
                    if [dep for dep in missing if dep not in self.required_commands]:
                        subprocess.run(['sudo', 'apt-get', 'install', '-y'] + 
                                     [dep for dep in missing if dep not in self.required_commands], 
                                     check=True)
                    
                    # Installer les paquets requis
                    if self.required_packages:
                        subprocess.run(['sudo', 'apt-get', 'install', '-y'] + self.required_packages, check=True)
                        
                    self.log_success("Dépendances installées avec succès")
                    return True
                except subprocess.CalledProcessError as e:
                    self.log_error(f"Erreur lors de l'installation des dépendances : {e}")
                    return False
            else:
                self.log_error(f"Veuillez installer les dépendances manquantes : {', '.join(missing)}")
                return False
                
        # Vérifier les paquets requis
        if self.required_packages and self.install_deps:
            try:
                # Vérifier si les paquets sont déjà installés
                installed_packages = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\\n']).decode().splitlines()
                missing_packages = [pkg for pkg in self.required_packages if pkg not in installed_packages]
                
                if missing_packages:
                    self.log_warning(f"Paquets requis manquants : {', '.join(missing_packages)}")
                    
                    if self.interactive:
                        response = input("Voulez-vous installer les paquets requis manquants ? (o/n) ").strip().lower()
                        if response not in ['o', 'oui', 'y', 'yes']:
                            self.log_warning("Installation des paquets annulée par l'utilisateur")
                            return False
                            
                    self.log_info("Installation des paquets requis...")
                    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                    subprocess.run(['sudo', 'apt-get', 'install', '-y'] + missing_packages, check=True)
                    self.log_success("Paquets requis installés avec succès")
                    
            except subprocess.CalledProcessError as e:
                self.log_error(f"Erreur lors de la vérification ou de l'installation des paquets requis : {e}")
                return False
                
        return True
    
    def check_disk_space(self):
        """Vérifie l'espace disque disponible"""
        if self.min_disk_space <= 0:
            return True
            
        # Vérifier l'espace disque disponible
        target_dir = self.extract_dir if self.extract_dir else os.getcwd()
        
        try:
            # Obtenir l'espace disque disponible en Mo
            if platform.system() == 'Windows':
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(target_dir), None, None, ctypes.pointer(free_bytes))
                free_mb = free_bytes.value / (1024 * 1024)
            else:
                stat = os.statvfs(target_dir)
                free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
                
            self.log_debug(f"Espace disque disponible : {free_mb:.2f} Mo")
            
            if free_mb < self.min_disk_space:
                self.log_error(f"Espace disque insuffisant : {free_mb:.2f} Mo disponible, {self.min_disk_space} Mo requis")
                return False
                
            return True
            
        except Exception as e:
            self.log_error(f"Erreur lors de la vérification de l'espace disque : {str(e)}")
            return False
    
    def check_version(self):
        """Vérifie si une nouvelle version est disponible"""
        if not self.version_check or self.extract_only or self.skip_version_check or not self.version_url:
            return
            
        self.log_info("Vérification des mises à jour...")
        self.log_debug(f"Version locale : {VERSION}")
        self.log_debug(f"URL de vérification : {self.version_url}")
        
        try:
            with urllib.request.urlopen(self.version_url, timeout=10) as response:
                remote_info = response.read().decode('utf-8')
                
            self.log_debug(f"Réponse brute : {remote_info}")
            
            try:
                info = json.loads(remote_info)
                remote_version = info.get('version', '')
                remote_url = info.get('url', '')
                changelog = info.get('changelog', '')
                
                self.log_debug(f"Version distante extraite : {remote_version}")
                
                if remote_version and remote_version != VERSION:
                    self.log_warning(f"Une nouvelle version est disponible : {remote_version}")
                    self.log_info(f"Version actuelle : {VERSION}")
                    if remote_url:
                        self.log_info(f"URL de téléchargement : {remote_url}")
                    if changelog:
                        self.log_info("Changements :")
                        for line in changelog.split('\\n'):
                            self.log_info(f"  - {line}")
                    
                    if self.interactive:
                        response = input("Voulez-vous télécharger et installer la nouvelle version ? (o/n) ").strip().lower()
                        if response in ['o', 'oui', 'y', 'yes']:
                            self.update_script(remote_url)
                        else:
                            self.log_warning("Mise à jour ignorée, poursuite avec la version actuelle")
                    else:
                        self.log_warning("Poursuite avec la version actuelle")
                else:
                    self.log_success(f"Version à jour ({VERSION})")
                    
            except json.JSONDecodeError:
                self.log_warning("Format de version invalide")
                self.log_debug("Impossible d'extraire la version de la réponse")
                
        except Exception as e:
            self.log_warning("Impossible de vérifier les mises à jour")
            self.log_debug(f"Erreur de connexion : {str(e)}")
    
    def update_script(self, url):
        """Télécharge et installe une nouvelle version du script"""
        if not url:
            self.log_error("URL de téléchargement non spécifiée")
            return
            
        self.log_info(f"Téléchargement de la nouvelle version depuis {url}")
        
        try:
            # Créer un répertoire temporaire
            temp_dir = tempfile.mkdtemp()
            self._temp_dirs.append(temp_dir)
            temp_file = os.path.join(temp_dir, os.path.basename(url))
            
            # Télécharger le fichier
            urllib.request.urlretrieve(url, temp_file)
            
            # Rendre le script exécutable
            os.chmod(temp_file, os.stat(temp_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            
            # Remplacer le script actuel
            script_path = os.path.abspath(sys.argv[0])
            shutil.copy2(temp_file, script_path)
            
            self.log_success("Mise à jour réussie, veuillez redémarrer le script")
            
            # Quitter le script
            sys.exit(0)
            
        except Exception as e:
            self.log_error(f"Erreur lors de la mise à jour : {str(e)}")
    
    def check_expiration(self):
        """Vérifie si l'archive a expiré"""
        if not self.expiration_date:
            return True
            
        try:
            exp_date = datetime.datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
            today = datetime.date.today()
            
            if today > exp_date:
                self.log_error(f"Cette archive a expiré le {self.expiration_date}")
                return False
                
            # Afficher un avertissement si l'expiration est proche (moins de 7 jours)
            days_left = (exp_date - today).days
            if days_left <= 7:
                self.log_warning(f"Cette archive expirera dans {days_left} jour(s)")
                
            return True
            
        except ValueError:
            self.log_error("Format de date d'expiration invalide")
            return False
            
    def verify_remote_hash(self, file_path):
        """Vérifie le hash d'un fichier par rapport à un hash distant"""
        if not self.remote_hash_url:
            return True
            
        self.log_info("Vérification du hash distant...")
        
        try:
            # Calculer le hash local
            local_hash = self.compute_file_checksum(file_path)
            self.log_debug(f"Hash local ({self.hash_algorithm}): {local_hash}")
            
            # Récupérer le hash distant
            with urllib.request.urlopen(self.remote_hash_url, timeout=10) as response:
                remote_hash = response.read().decode('utf-8').strip()
                
            self.log_debug(f"Hash distant: {remote_hash}")
            
            # Comparer les hash
            if local_hash.lower() != remote_hash.lower():
                self.log_error("Le hash distant ne correspond pas au hash local")
                self.log_error(f"Hash local: {local_hash}")
                self.log_error(f"Hash distant: {remote_hash}")
                return False
                
            self.log_success("Vérification du hash réussie")
            return True
            
        except Exception as e:
            self.log_error(f"Erreur lors de la vérification du hash distant : {str(e)}")
            return False
    
    def prepare_extract_dir(self):
        """Prépare le répertoire d'extraction"""
        if not self.extract_dir:
            self.extract_dir = tempfile.mkdtemp()
            self._temp_dirs.append(self.extract_dir)
            self.log_info(f"Répertoire d'extraction temporaire créé: {self.extract_dir}")
        else:
            # S'assurer que le chemin est absolu
            if not os.path.isabs(self.extract_dir):
                self.extract_dir = os.path.abspath(self.extract_dir)
            
            # Créer le répertoire s'il n'existe pas
            if not os.path.isdir(self.extract_dir):
                try:
                    os.makedirs(self.extract_dir, exist_ok=True)
                    self.log_info(f"Répertoire d'extraction créé: {self.extract_dir}")
                except Exception as e:
                    self.log_error(f"Impossible de créer le répertoire d'extraction: {self.extract_dir}")
                    self.log_debug(f"Erreur: {str(e)}")
                    sys.exit(1)
            
            # Vérifier les permissions
            if not os.access(self.extract_dir, os.W_OK):
                self.log_error(f"Permissions insuffisantes sur le répertoire: {self.extract_dir}")
                sys.exit(1)
                
        self.log_debug(f"Extraction dans: {self.extract_dir}")
    
    def compute_file_checksum(self, file_path, algorithm=None):
        """Calcule le checksum d'un fichier selon l'algorithme spécifié"""
        if algorithm is None:
            algorithm = self.hash_algorithm
            
        hash_func = None
        if algorithm == 'md5':
            hash_func = hashlib.md5()
        elif algorithm == 'sha1':
            hash_func = hashlib.sha1()
        elif algorithm == 'sha256':
            hash_func = hashlib.sha256()
        elif algorithm == 'sha512':
            hash_func = hashlib.sha512()
        else:
            self.log_warning(f"Algorithme de hash non supporté: {algorithm}, utilisation de SHA-256")
            hash_func = hashlib.sha256()
            
        # Calculer le hash
        with open(file_path, "rb") as f:
            # Lire et mettre à jour le hash par blocs de 64K
            for byte_block in iter(lambda: f.read(65536), b""):
                hash_func.update(byte_block)
                
        return hash_func.hexdigest()
    
    def encrypt_file(self, file_path, output_path=None, password=None):
        """Chiffre un fichier avec OpenSSL"""
        if output_path is None:
            output_path = file_path + ".enc"
            
        if not password and self.encrypt_password:
            password = self.encrypt_password
            
        if not password:
            # Générer un mot de passe aléatoire si aucun n'est fourni
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            self.log_info(f"Mot de passe généré pour le chiffrement : {password}")
            self.encrypt_password = password
        
        try:
            # Utiliser OpenSSL pour chiffrer le fichier
            cmd = [
                'openssl', 'enc', '-aes-256-cbc', '-salt',
                '-in', file_path,
                '-out', output_path,
                '-pass', f'pass:{password}'
            ]
            
            self.log_debug(f"Commande de chiffrement: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.log_success(f"Fichier chiffré avec succès : {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.log_error(f"Erreur lors du chiffrement du fichier: {str(e)}")
            self.log_debug(f"Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            return None
    
    def decrypt_file(self, file_path, output_path=None, password=None):
        """Déchiffre un fichier avec OpenSSL"""
        if output_path is None:
            output_path = file_path.replace('.enc', '') if file_path.endswith('.enc') else file_path + '.dec'
            
        if not password and self.encrypt_password:
            password = self.encrypt_password
            
        if not password and self.interactive:
            password = getpass.getpass("Entrez le mot de passe pour le déchiffrement: ")
            
        if not password:
            self.log_error("Mot de passe requis pour le déchiffrement")
            return None
        
        try:
            # Utiliser OpenSSL pour déchiffrer le fichier
            cmd = [
                'openssl', 'enc', '-aes-256-cbc', '-d', '-salt',
                '-in', file_path,
                '-out', output_path,
                '-pass', f'pass:{password}'
            ]
            
            self.log_debug(f"Commande de déchiffrement: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.log_success(f"Fichier déchiffré avec succès : {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.log_error(f"Erreur lors du déchiffrement du fichier: {str(e)}")
            self.log_debug(f"Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            
            # Si le mot de passe est incorrect, demander à nouveau en mode interactif
            if self.interactive and "bad decrypt" in (e.stderr.decode() if e.stderr else ''):
                self.log_warning("Mot de passe incorrect, veuillez réessayer")
                new_password = getpass.getpass("Entrez le mot de passe pour le déchiffrement: ")
                return self.decrypt_file(file_path, output_path, new_password)
                
            return None
            
    def sign_file(self, file_path, output_path=None, key=None):
        """Signe un fichier avec une clé privée"""
        if output_path is None:
            output_path = file_path + ".sig"
            
        if not key and self.signature_key:
            key = self.signature_key
            
        if not key:
            self.log_error("Clé de signature requise")
            return None
        
        try:
            # Utiliser OpenSSL pour signer le fichier
            # Créer d'abord un hash du fichier
            hash_file = file_path + ".hash"
            with open(hash_file, 'w') as f:
                f.write(self.compute_file_checksum(file_path))
                
            # Signer le hash avec la clé privée
            cmd = [
                'openssl', 'dgst', '-sha256', '-sign', key,
                '-out', output_path,
                hash_file
            ]
            
            self.log_debug(f"Commande de signature: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Nettoyer
            os.remove(hash_file)
            
            self.log_success(f"Fichier signé avec succès : {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.log_error(f"Erreur lors de la signature du fichier: {str(e)}")
            self.log_debug(f"Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            return None
        except Exception as e:
            self.log_error(f"Erreur lors de la signature du fichier: {str(e)}")
            return None
    
    def verify_signature(self, file_path, signature_path, public_key=None):
        """Vérifie la signature d'un fichier avec une clé publique"""
        if not public_key and self.signature_key:
            # Si la clé de signature est une clé publique
            public_key = self.signature_key
            
        if not public_key:
            self.log_error("Clé publique requise pour la vérification de la signature")
            return False
            
        if not os.path.isfile(signature_path):
            self.log_error(f"Fichier de signature non trouvé: {signature_path}")
            return False
        
        try:
            # Utiliser OpenSSL pour vérifier la signature
            # Créer d'abord un hash du fichier
            hash_file = file_path + ".hash"
            with open(hash_file, 'w') as f:
                f.write(self.compute_file_checksum(file_path))
                
            # Vérifier la signature avec la clé publique
            cmd = [
                'openssl', 'dgst', '-sha256', '-verify', public_key,
                '-signature', signature_path,
                hash_file
            ]
            
            self.log_debug(f"Commande de vérification: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Nettoyer
            os.remove(hash_file)
            
            # Vérifier le résultat
            if "Verified OK" in result.stdout.decode():
                self.log_success("Signature vérifiée avec succès")
                return True
            else:
                self.log_error("Vérification de la signature échouée")
                return False
                
        except subprocess.CalledProcessError as e:
            self.log_error(f"Erreur lors de la vérification de la signature: {str(e)}")
            self.log_debug(f"Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            return False
        except Exception as e:
            self.log_error(f"Erreur lors de la vérification de la signature: {str(e)}")
            return False
            
    def backup_files(self, target_dir, files=None):
        """Sauvegarde les fichiers avant extraction"""
        if not self.backup:
            return True
            
        self.log_info("Sauvegarde des fichiers existants...")
        
        try:
            # Créer le répertoire de sauvegarde
            backup_dir = self.backup_dir
            if not backup_dir:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = os.path.join(tempfile.gettempdir(), f"nvbuilder_backup_{timestamp}")
            
            os.makedirs(backup_dir, exist_ok=True)
            self.log_debug(f"Répertoire de sauvegarde: {backup_dir}")
            
            # Si aucun fichier n'est spécifié, sauvegarder tout le répertoire cible
            if not files:
                # Créer une archive tar de tout le répertoire
                backup_file = os.path.join(backup_dir, "backup.tar.gz")
                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(target_dir, arcname=os.path.basename(target_dir))
                    
                self.log_success(f"Sauvegarde complète créée: {backup_file}")
            else:
                # Sauvegarder uniquement les fichiers spécifiés
                for file in files:
                    file_path = os.path.join(target_dir, file)
                    if os.path.exists(file_path):
                        backup_path = os.path.join(backup_dir, file)
                        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                        shutil.copy2(file_path, backup_path)
                        
                self.log_success(f"Sauvegarde des fichiers spécifiques créée: {backup_dir}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Erreur lors de la sauvegarde des fichiers: {str(e)}")
            return False
            
    def compress_files(self):
        """Compresse les fichiers du dossier source dans une archive"""
        self.log_info("Compression des fichiers...")
        
        # Créer un répertoire temporaire
        temp_dir = tempfile.mkdtemp()
        self._temp_dirs.append(temp_dir)
        archive_path = os.path.join(temp_dir, "archive.tar")
        
        try:
            # Mesurer l'espace requis
            total_size = 0
            total_files = 0
            for root, dirs, files in os.walk(self.content_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.should_include_file(file_path):
                        total_size += os.path.getsize(file_path)
                        total_files += 1
                        
            self._required_disk_space = total_size / (1024 * 1024)  # En Mo
            self.log_debug(f"Espace requis pour l'archive: {self._required_disk_space:.2f} Mo")
            self.log_debug(f"Nombre de fichiers à archiver: {total_files}")
            
            # Créer l'archive tar
            mode = 'w'
            if self.compression == 'bzip2':
                mode = 'w:bz2'
            elif self.compression == 'gzip':
                mode = 'w:gz'
            elif self.compression == 'xz':
                mode = 'w:xz'
            else:
                self.log_error(f"Méthode de compression non supportée: {self.compression}")
                shutil.rmtree(temp_dir)
                sys.exit(1)
            
            with tarfile.open(archive_path, mode) as tar:
                # Ajouter les fichiers à l'archive
                processed_files = 0
                for root, dirs, files in os.walk(self.content_dir):
                    # Filtrer les dossiers à exclure
                    dirs[:] = [d for d in dirs if self.should_include_dir(os.path.join(root, d))]
                    
                    # Traiter les fichiers
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.content_dir)
                        
                        if self.should_include_file(file_path):
                            tar.add(file_path, arcname=rel_path)
                            processed_files += 1
                            if total_files > 0:
                                self.progress_bar(processed_files, total_files, 
                                                "Compression", f"{processed_files}/{total_files}")
            
            # Calcul de la taille finale
            archive_size = os.path.getsize(archive_path)
            compression_ratio = total_size / archive_size if archive_size > 0 else 0
            self.log_success(f"Archive créée avec succès ({archive_size/1024/1024:.2f} Mo, taux de compression: {compression_ratio:.2f}x)")
            
            # Ajouter les archives imbriquées
            if self.nested_archives:
                self.add_nested_archives(archive_path)
                
            # Calculer et stocker le checksum
            if self.create_checksum:
                checksum = self.compute_file_checksum(archive_path)
                checksum_file = os.path.join(temp_dir, "checksum.txt")
                with open(checksum_file, 'w') as f:
                    f.write(f"{checksum} *{os.path.basename(archive_path)}")
                self.log_success(f"Checksum ({self.hash_algorithm}) créé: {checksum}")
                
            # Chiffrer l'archive si demandé
            if self.encrypt:
                encrypted_path = self.encrypt_file(archive_path)
                if encrypted_path:
                    archive_path = encrypted_path
                else:
                    self.log_error("Échec du chiffrement, utilisation de l'archive non chiffrée")
                    
            # Signer l'archive si une clé est fournie
            if self.signature_key:
                signature_path = self.sign_file(archive_path)
                if not signature_path:
                    self.log_warning("Signature de l'archive impossible, continuation sans signature")
            
            # Générer le script auto-extractible
            self.generate_self_extracting_script(archive_path)
            
        except Exception as e:
            self.log_error(f"Erreur lors de la compression des fichiers: {str(e)}")
            self.log_debug(traceback.format_exc())
            self.cleanup_temp_files()
            sys.exit(1)
        
    def should_include_file(self, file_path):
        """Détermine si un fichier doit être inclus dans l'archive"""
        # Obtenir le chemin relatif
        rel_path = os.path.relpath(file_path, self.content_dir)
        
        # Vérifier si le fichier doit être inclus/exclu
        include_file = True
        
        # Si des patterns d'inclusion sont spécifiés, il faut qu'au moins un corresponde
        if self.include_patterns:
            include_file = False
            for pattern in self.include_patterns:
                if fnmatch.fnmatch(rel_path, pattern):
                    include_file = True
                    break
        
        # Vérifier si le fichier doit être exclu (les exclusions ont priorité)
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                include_file = False
                break
        
        return include_file
        
    def should_include_dir(self, dir_path):
        """Détermine si un dossier doit être inclus dans l'archive"""
        # Obtenir le chemin relatif
        rel_path = os.path.relpath(dir_path, self.content_dir)
        
        # Vérifier si le dossier doit être exclu
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path + '/', pattern):
                return False
                
        return True
        
    def add_nested_archives(self, archive_path):
        """Ajoute des archives imbriquées à l'archive principale"""
        if not self.nested_archives:
            return
            
        self.log_info("Ajout des archives imbriquées...")
        
        # Créer un répertoire temporaire pour les archives imbriquées
        nested_dir = tempfile.mkdtemp()
        self._temp_dirs.append(nested_dir)
        
        # Extraire l'archive principale
        with tarfile.open(archive_path, 'r') as tar:
            tar.extractall(path=nested_dir)
            
        # Créer un sous-répertoire pour les archives imbriquées
        nested_archives_dir = os.path.join(nested_dir, "nested_archives")
        os.makedirs(nested_archives_dir, exist_ok=True)
        
        # Copier les archives imbriquées
        for i, nested_archive in enumerate(self.nested_archives):
            if os.path.isfile(nested_archive):
                dest_path = os.path.join(nested_archives_dir, f"archive_{i}_{os.path.basename(nested_archive)}")
                shutil.copy2(nested_archive, dest_path)
                self.log_debug(f"Archive imbriquée ajoutée: {dest_path}")
                
        # Recréer l'archive principale avec les archives imbriquées
        os.remove(archive_path)
        
        # Déterminer le mode en fonction de la compression
        mode = 'w'
        if self.compression == 'bzip2':
            mode = 'w:bz2'
        elif self.compression == 'gzip':
            mode = 'w:gz'
        elif self.compression == 'xz':
            mode = 'w:xz'
            
        with tarfile.open(archive_path, mode) as tar:
            tar.add(nested_dir, arcname='.')
            
        self.log_success(f"Archives imbriquées ajoutées: {len(self.nested_archives)}")
        
    def generate_self_extracting_script(self, archive_path):
        """Génère un script auto-extractible avec l'archive"""
        self.log_info("Génération du script auto-extractible...")
        
        try:
            # Lire le contenu actuel du script
            with open(__file__, 'r') as current_script:
                script_content = current_script.read()
                
            # Déterminer le type de script à générer
            if self.output_format == 'sh':
                self.generate_sh_script(script_content, archive_path)
            elif self.output_format == 'py':
                self.generate_py_script(script_content, archive_path)
            else:
                self.log_error(f"Format de sortie non supporté: {self.output_format}")
                sys.exit(1)
                
        except Exception as e:
            self.log_error(f"Erreur lors de la génération du script auto-extractible: {str(e)}")
            self.log_debug(traceback.format_exc())
            sys.exit(1)
            
    def generate_sh_script(self, script_content, archive_path):
        """Génère un script shell auto-extractible"""
        # Créer le contenu du script shell
        shell_script = f'''#!/bin/bash
# {self.banner_text}
# Version: {VERSION}
# Généré le: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Configuration
EXTRACT_DIR=""
EXTRACT_ONLY=0
DEBUG=0
SKIP_VERSION=0
NEED_ROOT={1 if self.need_root else 0}
MIN_SPACE={self.min_disk_space}
PRESERVE_PERMS={1 if self.preserve_permissions else 0}
FORCE_ROOT={1 if self.force_root_ownership else 0}
SCRIPT_EXEC="{self.script_exec}"
CLEANUP={1 if self.cleanup else 0}
BACKUP={1 if self.backup else 0}
'''

        # Ajouter les paramètres de chiffrement si nécessaire
        if self.encrypt:
            shell_script += f'ENCRYPTED=1\n'
            if self.encrypt_password and not self.interactive:
                shell_script += f'PASSWORD="{self.encrypt_password}"\n'
            else:
                shell_script += f'PASSWORD=""\n'
        else:
            shell_script += 'ENCRYPTED=0\n'
            
        # Ajouter les vérifications d'expiration
        if self.expiration_date:
            shell_script += f'EXPIRATION="{self.expiration_date}"\n'
            
        # Ajouter l'assistance pour les couleurs
        shell_script += '''
# Couleurs et formatage
BOLD="\\033[1m"
RED="\\033[31m"
GREEN="\\033[32m"
YELLOW="\\033[33m"
BLUE="\\033[34m"
RESET="\\033[0m"

# Fonction d'aide
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Affiche cette aide"
    echo "  -d, --dir DIR        Spécifie le répertoire d'extraction"
    echo "  -x, --extract-only   Extrait uniquement l'archive sans exécuter le script"
    echo "      --debug          Active le mode debug"
    echo "      --skip-version   Désactive la vérification de version"
    echo "  -q, --quiet          Mode silencieux"
    echo "  -v, --verbose        Mode verbeux"
    echo "      --no-backup      Désactive la sauvegarde avant extraction"
    echo "      --backup-dir DIR Spécifie le répertoire de sauvegarde"
    echo "      --no-cleanup     Désactive le nettoyage automatique"
    echo "      --force          Force l'écrasement des fichiers existants"
}

# Fonction de log
log() {
    local level=$1
    local message=$2
    local prefix=""
    
    case $level in
        "debug")
            [[ $DEBUG -eq 0 ]] && return
            prefix="${BLUE}${BOLD}→${RESET}"
            ;;
        "info")
            prefix="${BLUE}${BOLD}→${RESET}"
            ;;
        "warning")
            prefix="${YELLOW}${BOLD}⚠${RESET}"
            ;;
        "error")
            prefix="${RED}${BOLD}✗${RESET}"
            ;;
        "success")
            prefix="${GREEN}${BOLD}✓${RESET}"
            ;;
    esac
    
    echo -e "  ${prefix} ${message}"
}

# Extraire l'archive
extract_archive() {
    local extract_dir=$1
    local marker_line=$(awk '/^__ARCHIVE_MARKER__/ {print NR + 1; exit 0; }' "$0")
    
    log "info" "Extraction de l'archive..."
    log "debug" "Marqueur d'archive à la ligne ${marker_line}"
    
    # Créer un fichier temporaire pour stocker l'archive
    local temp_archive=$(mktemp)
    tail -n +"$marker_line" "$0" > "$temp_archive"
    
    # Vérifier si le fichier contient des données
    if [ ! -s "$temp_archive" ]; then
        log "error" "Aucune donnée d'archive trouvée"
        rm -f "$temp_archive"
        return 1
    fi
    
    # Si l'archive est chiffrée, la déchiffrer d'abord
    if [ "$ENCRYPTED" -eq 1 ]; then
        log "info" "Déchiffrement de l'archive..."
        
        # Demander le mot de passe si non spécifié
        if [ -z "$PASSWORD" ]; then
            read -s -p "  ${BLUE}${BOLD}→${RESET} Entrez le mot de passe de déchiffrement: " PASSWORD
            echo ""
        fi
        
        local decrypted_archive=$(mktemp)
        if ! openssl enc -aes-256-cbc -d -salt -in "$temp_archive" -out "$decrypted_archive" -pass "pass:$PASSWORD" 2>/dev/null; then
            log "error" "Échec du déchiffrement (mot de passe incorrect?)"
            rm -f "$temp_archive" "$decrypted_archive"
            return 1
        fi
        
        # Remplacer l'archive chiffrée par l'archive déchiffrée
        mv "$decrypted_archive" "$temp_archive"
        log "success" "Archive déchiffrée avec succès"
    fi
    
    # Extraire l'archive
    case "$COMPRESSION" in
        "bzip2")
            if ! tar xjf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                log "error" "Échec de l'extraction bzip2"
                rm -f "$temp_archive"
                return 1
            fi
            ;;
        "gzip")
            if ! tar xzf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                log "error" "Échec de l'extraction gzip"
                rm -f "$temp_archive"
                return 1
            fi
            ;;
        "xz")
            if ! tar xJf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                log "error" "Échec de l'extraction xz"
                rm -f "$temp_archive"
                return 1
            fi
            ;;
        *)
            # Essayer de détecter automatiquement le format
            if tar xjf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                COMPRESSION="bzip2"
            elif tar xzf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                COMPRESSION="gzip"
            elif tar xJf "$temp_archive" -C "$extract_dir" 2>/dev/null; then
                COMPRESSION="xz"
            else
                log "error" "Format d'archive non reconnu"
                rm -f "$temp_archive"
                return 1
            fi
            ;;
    esac
    
    # Nettoyer
    rm -f "$temp_archive"
    
    log "success" "Extraction réussie dans $extract_dir"
    return 0
}

# Vérifier les droits root
check_root() {
    if [ "$NEED_ROOT" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
        log "error" "Ce script nécessite les droits administrateur"
        log "info" "Veuillez exécuter le script avec sudo"
        exit 1
    fi
}

# Vérifier l'espace disque
check_disk_space() {
    if [ "$MIN_SPACE" -gt 0 ]; then
        local available
        if [ "$(uname)" = "Darwin" ]; then
            # macOS
            available=$(df -m . | tail -1 | awk '{print $4}')
        else
            # Linux
            available=$(df -m . | tail -1 | awk '{print $4}')
        fi
        
        if [ "$available" -lt "$MIN_SPACE" ]; then
            log "error" "Espace disque insuffisant: ${available}Mo disponible, ${MIN_SPACE}Mo requis"
            exit 1
        fi
    fi
}

# Vérifier l'expiration
check_expiration() {
    if [ -n "$EXPIRATION" ]; then
        local today=$(date +%s)
        local expire_date=$(date -d "$EXPIRATION" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$EXPIRATION" +%s 2>/dev/null)
        
        if [ "$today" -gt "$expire_date" ]; then
            log "error" "Cette archive a expiré le $EXPIRATION"
            exit 1
        fi
        
        # Afficher un avertissement si l'expiration est proche (moins de 7 jours)
        local days_left=$(( (expire_date - today) / 86400 ))
        if [ "$days_left" -le 7 ]; then
            log "warning" "Cette archive expirera dans $days_left jour(s)"
        fi
    fi
}

# Fonction de sauvegarde
backup_target_dir() {
    if [ "$BACKUP" -eq 1 ]; then
        local target_dir=$1
        local backup_dir=${BACKUP_DIR:-$(mktemp -d)}
        
        log "info" "Sauvegarde du répertoire cible..."
        
        # Créer une archive de sauvegarde
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local backup_file="${backup_dir}/backup_${timestamp}.tar.gz"
        
        if ! tar czf "$backup_file" -C "$target_dir" . >/dev/null 2>&1; then
            log "warning" "Échec de la sauvegarde, continuation sans sauvegarde"
            return 1
        fi
        
        log "success" "Sauvegarde créée: $backup_file"
    fi
}

# Exécuter un script intégré
run_embedded_script() {
    local script_path=$1
    
    if [ ! -f "$script_path" ]; then
        log "error" "Script non trouvé: $script_path"
        return 1
    fi
    
    log "info" "Exécution du script $script_path"
    chmod +x "$script_path"
    
    if ! "$script_path"; then
        log "error" "Échec de l'exécution du script"
        return 1
    fi
    
    log "success" "Script exécuté avec succès"
    return 0
}

# Parser les arguments
BACKUP_DIR=""
QUIET=0
VERBOSE=0
FORCE=0
COMPRESSION="{self.compression}"

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dir)
            EXTRACT_DIR="$2"
            shift 2
            ;;
        -x|--extract-only)
            EXTRACT_ONLY=1
            shift
            ;;
        --debug)
            DEBUG=1
            shift
            ;;
        --skip-version)
            SKIP_VERSION=1
            shift
            ;;
        -q|--quiet)
            QUIET=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        --no-backup)
            BACKUP=0
            shift
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP=0
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        -p|--password)
            PASSWORD="$2"
            shift 2
            ;;
        *)
            # Options inconnues sont passées au script intégré
            break
            ;;
    esac
done

# Configurer le niveau de verbosité
if [ "$QUIET" -eq 1 ]; then
    # Rediriger toutes les sorties vers /dev/null
    exec 1>/dev/null
    exec 2>/dev/null
fi

# Afficher la bannière
if [ "$QUIET" -eq 0 ]; then
    echo -e "${BLUE}${BOLD}=================================${RESET}"
    echo -e "${BLUE}${BOLD}|  {self.banner_text}  |${RESET}"
    echo -e "${BLUE}${BOLD}|  Version: {VERSION}  |${RESET}"
    echo -e "${BLUE}${BOLD}=================================${RESET}"
fi

# Vérifications initiales
check_root
check_disk_space
check_expiration

# Préparer le répertoire d'extraction
if [ -z "$EXTRACT_DIR" ]; then
    EXTRACT_DIR=$(mktemp -d)
    log "info" "Répertoire d'extraction temporaire créé: $EXTRACT_DIR"
    CLEANUP_EXTRACT_DIR=1
else
    # S'assurer que le répertoire existe
    mkdir -p "$EXTRACT_DIR"
    CLEANUP_EXTRACT_DIR=0
fi

# Extraire l'archive
if ! extract_archive "$EXTRACT_DIR"; then
    log "error" "Échec de l'extraction de l'archive"
    
    # Nettoyer si nécessaire
    if [ "$CLEANUP" -eq 1 ] && [ "$CLEANUP_EXTRACT_DIR" -eq 1 ]; then
        log "debug" "Nettoyage du répertoire d'extraction"
        rm -rf "$EXTRACT_DIR"
    fi
    
    exit 1
fi

# Configurer les permissions si nécessaire
if [ "$FORCE_ROOT" -eq 1 ]; then
    log "info" "Application des permissions root"
    find "$EXTRACT_DIR" -type f -exec chown root:root {} \\;
    find "$EXTRACT_DIR" -type d -exec chown root:root {} \\;
fi

# Exécuter le script principal si nécessaire
if [ "$EXTRACT_ONLY" -eq 0 ]; then
    script_path="$EXTRACT_DIR/$SCRIPT_EXEC"
    
    # Sauvegarde du répertoire cible si nécessaire
    if [ "$BACKUP" -eq 1 ]; then
        backup_target_dir "$EXTRACT_DIR"
    fi
    
    # Exécuter le script
    if ! run_embedded_script "$script_path"; then
        log "error" "Échec de l'exécution du script principal"
        
        # Nettoyer si nécessaire
        if [ "$CLEANUP" -eq 1 ] && [ "$CLEANUP_EXTRACT_DIR" -eq 1 ]; then
            log "debug" "Nettoyage du répertoire d'extraction"
            rm -rf "$EXTRACT_DIR"
        fi
        
        exit 1
    fi
fi

# Nettoyer si nécessaire
if [ "$CLEANUP" -eq 1 ] && [ "$CLEANUP_EXTRACT_DIR" -eq 1 ]; then
    log "debug" "Nettoyage du répertoire d'extraction"
    rm -rf "$EXTRACT_DIR"
fi

log "success" "Terminé"
exit 0

__ARCHIVE_MARKER__
'''

        # Écrire le script shell dans le fichier de sortie
        with open(self.output_file, 'w') as output_script:
            output_script.write(shell_script)
            
        # Ajouter l'archive en binaire
        with open(self.output_file, 'ab') as output_script:
            with open(archive_path, 'rb') as archive:
                output_script.write(archive.read())
                
        # Rendre le script exécutable
        os.chmod(self.output_file, os.stat(self.output_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        self.log_success(f"Script auto-extractible sh généré : {self.output_file}")
    
    def generate_py_script(self, script_content, archive_path):
        """Génère un script Python auto-extractible"""
        # Extraire les parties importantes du script actuel
        script_lines = script_content.split('\n')
        script_header = []
        script_footer = []
        
        # Partie Python uniquement (ignorer le shell header)
        in_python = False
        for line in script_lines:
            if line.strip() == 'python3 -c "':
                in_python = True
                continue
            elif in_python:
                script_header.append(line)
            else:
                continue
                
        # Créer le contenu du script Python
        py_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# {self.banner_text}
# Version: {VERSION}
# Généré le: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

'''
        
        # Ajouter les imports et classes nécessaires
        py_script += '\n'.join(script_header) + '\n'
        
        # Créer le bloc principal
        py_script += '''
# Point d'entrée principal
if __name__ == '__main__':
    # Créer et exécuter le builder
    builder = NvBuilder()
    builder.run()
    
# Marqueur de fin du script
__ARCHIVE_MARKER__
'''
        
        # Écrire le script Python dans le fichier de sortie
        with open(self.output_file, 'w') as output_script:
            output_script.write(py_script)
            
        # Ajouter l'archive en binaire
        with open(self.output_file, 'ab') as output_script:
            with open(archive_path, 'rb') as archive:
                output_script.write(archive.read())
                
        # Rendre le script exécutable
        os.chmod(self.output_file, os.stat(self.output_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        self.log_success(f"Script auto-extractible py généré : {self.output_file}")
    
    def extract_archive(self):
        """Extrait l'archive intégrée dans ce script"""
        self._extraction_start_time = time.time()
        self.log_info("Recherche et extraction de l'archive...")
        
        # Rechercher la marque dans le fichier
        marker_found = False
        marker_line = 0
        
        try:
            with open(sys.argv[0], 'r') as script:
                for i, line in enumerate(script):
                    if line.strip() == "__ARCHIVE_MARKER__":
                        marker_found = True
                        marker_line = i + 1
                        break
            
            if not marker_found:
                self.log_error("Marque d'archive non trouvée dans le script")
                sys.exit(1)
                
            self.log_debug(f"Début de l'archive à la ligne : {marker_line}")
            
            # Créer un fichier temporaire pour stocker l'archive
            temp_archive = tempfile.NamedTemporaryFile(delete=False)
            temp_archive_path = temp_archive.name
            temp_archive.close()
            self._temp_dirs.append(temp_archive_path)
            
            # Extraire la partie archive
            with open(sys.argv[0], 'rb') as src, open(temp_archive_path, 'wb') as dst:
                # Ignorer les lignes jusqu'à la marque
                for _ in range(marker_line):
                    src.readline()
                
                # Copier le reste (l'archive) dans le fichier temporaire
                chunk = src.read(4096)
                while chunk:
                    dst.write(chunk)
                    chunk = src.read(4096)
            
            # Vérifier si le fichier contient des données
            if os.path.getsize(temp_archive_path) == 0:
                self.log_error("Aucune donnée d'archive trouvée")
                os.unlink(temp_archive_path)
                sys.exit(1)
                
            archive_size = os.path.getsize(temp_archive_path)
            self.log_debug(f"Taille de l'archive: {archive_size} octets")
            
            # Si l'archive est chiffrée, la déchiffrer d'abord
            if self.encrypt:
                if not self.encrypt_password and self.interactive:
                    self.encrypt_password = getpass.getpass("Entrez le mot de passe pour le déchiffrement: ")
                    
                decrypted_path = self.decrypt_file(temp_archive_path)
                if decrypted_path:
                    temp_archive_path = decrypted_path
                else:
                    self.log_error("Échec du déchiffrement de l'archive")
                    self.cleanup_temp_files()
                    sys.exit(1)
            
            # Essayer d'extraire l'archive avec différentes méthodes de compression
            extraction_success = False
            error_log = io.StringIO()
            
            # Essayer différentes méthodes d'extraction
            for mode, compression_name in [('r:bz2', 'bzip2'), ('r:gz', 'gzip'), ('r:xz', 'xz'), ('r:', 'non compressé')]:
                try:
                    self.log_debug(f"Tentative d'extraction avec {compression_name}...")
                    with tarfile.open(temp_archive_path, mode) as tar:
                        # Lister les fichiers avant extraction pour vérification
                        file_list = tar.getnames()
                        total_size = sum(m.size for m in tar.getmembers())
                        total_files = len(file_list)
                        
                        self.log_debug(f"Archive contient {total_files} fichiers, taille totale: {total_size/1024/1024:.2f} Mo")
                        
                        # Mise à jour des paramètres internes
                        self._required_disk_space = total_size / (1024 * 1024)  # En Mo
                        
                        # Vérifier l'espace disque avant extraction
                        if not self.check_disk_space():
                            self.log_error("Espace disque insuffisant pour l'extraction")
                            self.cleanup_temp_files()
                            sys.exit(1)
                            
                        # Extraction proprement dite avec barre de progression
                        if self.verbosity >= 2:
                            self.log_info(f"Extraction de {total_files} fichiers...")
                            
                            # Extraction avec barre de progression
                            extracted_files = 0
                            for member in tar.getmembers():
                                tar.extract(member, path=self.extract_dir)
                                extracted_files += 1
                                self.progress_bar(extracted_files, total_files, 
                                                "Extraction", f"{extracted_files}/{total_files}")
                        else:
                            # Extraction simple
                            tar.extractall(path=self.extract_dir)
                            
                    extraction_success = True
                    self.log_success(f"Extraction {compression_name} réussie dans {self.extract_dir}")
                    break
                except Exception as e:
                    error_log.write(f"Échec du mode {compression_name}: {str(e)}\n")
                    if mode != 'r:':  # Ne pas afficher d'erreur pour le mode par défaut
                        self.log_warning(f"Échec de l'extraction {compression_name}, essai suivant...")
            
            # Nettoyer
            os.unlink(temp_archive_path)
            
            if not extraction_success:
                self.log_error("Toutes les tentatives d'extraction ont échoué")
                if self.debug:
                    self.log_error("Détails des erreurs:")
                    self.log_error(error_log.getvalue())
                self.cleanup_temp_files()
                sys.exit(1)
                
            # Vérifier le contenu du répertoire d'extraction
            if self.debug:
                self.log_debug(f"Contenu du répertoire d'extraction ({self.extract_dir}):")
                for item in os.listdir(self.extract_dir):
                    self.log_debug(f"  - {item}")
                    
            # Configurer les permissions si nécessaire
            if self.force_root_ownership:
                self.log_info("Application des permissions root")
                try:
                    for root, dirs, files in os.walk(self.extract_dir):
                        for d in dirs:
                            os.chown(os.path.join(root, d), 0, 0)  # root:root
                        for f in files:
                            os.chown(os.path.join(root, f), 0, 0)  # root:root
                except Exception as e:
                    self.log_warning(f"Impossible de modifier les permissions: {str(e)}")
                
            self.log_info(f"Extraction terminée en {time.time() - self._extraction_start_time:.2f} secondes")
            
            # Traiter les archives imbriquées
            nested_dir = os.path.join(self.extract_dir, "nested_archives")
            if os.path.isdir(nested_dir):
                self.log_info("Traitement des archives imbriquées...")
                for nested_file in os.listdir(nested_dir):
                    nested_path = os.path.join(nested_dir, nested_file)
                    if os.path.isfile(nested_path):
                        self.log_debug(f"Extraction de l'archive imbriquée: {nested_file}")
                        try:
                            # Déterminer le format de l'archive
                            if nested_file.endswith('.tar.bz2') or nested_file.endswith('.tbz2'):
                                mode = 'r:bz2'
                            elif nested_file.endswith('.tar.gz') or nested_file.endswith('.tgz'):
                                mode = 'r:gz'
                            elif nested_file.endswith('.tar.xz') or nested_file.endswith('.txz'):
                                mode = 'r:xz'
                            else:
                                mode = 'r'  # Essayer sans compression
                                
                            with tarfile.open(nested_path, mode) as tar:
                                tar.extractall(path=self.extract_dir)
                                
                            self.log_success(f"Archive imbriquée extraite: {nested_file}")
                        except Exception as e:
                            self.log_warning(f"Échec de l'extraction de l'archive imbriquée {nested_file}: {str(e)}")
                            
                # Supprimer le répertoire des archives imbriquées après extraction
                if self.cleanup:
                    try:
                        shutil.rmtree(nested_dir)
                    except Exception as e:
                        self.log_debug(f"Impossible de supprimer le répertoire des archives imbriquées: {str(e)}")
        
        except Exception as e:
            self.log_error(f"Erreur lors de l'extraction de l'archive: {str(e)}")
            self.log_debug(traceback.format_exc())
            self.cleanup_temp_files()
            sys.exit(1)
    
    def execute_script(self):
        """Exécute le script après extraction"""
        if not self.script_exec or self.extract_only:
            return
            
        script_path = os.path.join(self.extract_dir, self.script_exec)
        
        self.log_debug(f"Vérification du script {self.script_exec}")
        if not os.path.isfile(script_path):
            self.log_error(f"Script {self.script_exec} non trouvé dans le répertoire d'extraction")
            sys.exit(1)
            
        self.log_debug("Script trouvé")
        
        # Exécuter le script pre-exec si présent
        if self.pre_exec_script:
            pre_script_path = os.path.join(self.extract_dir, self.pre_exec_script)
            if os.path.isfile(pre_script_path):
                self.log_info(f"Exécution du script pré-exécution: {self.pre_exec_script}")
                try:
                    # Rendre le script exécutable
                    os.chmod(pre_script_path, os.stat(pre_script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    
                    # Exécuter le script
                    result = subprocess.run([pre_script_path], cwd=self.extract_dir, 
                                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    self.log_success("Script pré-exécution terminé avec succès")
                except subprocess.CalledProcessError as e:
                    self.log_error(f"Erreur lors de l'exécution du script pré-exécution (code {e.returncode})")
                    self.log_debug(f"Sortie d'erreur: {e.stderr.decode()}")
                    if not self.force:
                        sys.exit(1)
                except Exception as e:
                    self.log_error(f"Erreur lors de l'exécution du script pré-exécution: {str(e)}")
                    if not self.force:
                        sys.exit(1)
        
        # Vérifier si l'exécution est conditionnelle
        if self.conditional_execution:
            self.log_info(f"Évaluation de la condition: {self.conditional_execution}")
            try:
                # Créer un environnement d'évaluation sécurisé
                eval_globals = {
                    'os': os,
                    'platform': platform,
                    'sys': sys,
                    'extract_dir': self.extract_dir,
                    'datetime': datetime,
                }
                
                # Évaluer la condition
                condition_result = eval(self.conditional_execution, eval_globals, {})
                
                if not condition_result:
                    self.log_warning("Condition d'exécution non satisfaite, script principal ignoré")
                    return
                    
                self.log_info("Condition d'exécution satisfaite")
                
            except Exception as e:
                self.log_error(f"Erreur lors de l'évaluation de la condition: {str(e)}")
                if not self.force:
                    sys.exit(1)
        
        # Sauvegarder le répertoire cible si demandé
        if self.backup:
            self.backup_files(self.extract_dir)
            
        # Rendre le script principal exécutable
        os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        # Changer de répertoire
        original_dir = os.getcwd()
        os.chdir(self.extract_dir)
        
        # Construire les options pour le script principal
        cmd = [f"./{self.script_exec}"]
        if self.debug:
            cmd.append("--debug")
        if self.skip_version_check:
            cmd.append("--skip-version")
            
        # Ajouter les options passées en ligne de commande
        cmd.extend(self.script_options)
            
        self.log_info(f"Exécution de {' '.join(cmd)}")
        
        # Exécuter le script avec retries
        for attempt in range(self.retry_count):
            try:
                # Ajouter un timeout si spécifié
                kwargs = {}
                if self.timeout > 0:
                    kwargs['timeout'] = self.timeout
                
                # Exécuter le script
                result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE if self.verbosity < 2 else None, 
                                      stderr=subprocess.PIPE if self.verbosity < 2 else None, **kwargs)
                
                self.log_success("Script exécuté avec succès")
                
                # Ajouter au résumé d'installation
                self._installation_summary.append({
                    'script': self.script_exec,
                    'status': 'success',
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                break
            except subprocess.TimeoutExpired:
                self.log_error(f"Timeout lors de l'exécution du script (tentative {attempt+1}/{self.retry_count})")
                if attempt == self.retry_count - 1:
                    self._installation_summary.append({
                        'script': self.script_exec,
                        'status': 'timeout',
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if not self.force:
                        os.chdir(original_dir)
                        sys.exit(1)
            except subprocess.CalledProcessError as e:
                self.log_error(f"Erreur lors de l'exécution du script (code {e.returncode}, tentative {attempt+1}/{self.retry_count})")
                if self.debug:
                    self.log_debug(f"Sortie d'erreur: {e.stderr.decode() if e.stderr else 'N/A'}")
                
                if attempt == self.retry_count - 1:
                    self._installation_summary.append({
                        'script': self.script_exec,
                        'status': 'error',
                        'code': e.returncode,
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if not self.force:
                        os.chdir(original_dir)
                        sys.exit(1)
            except Exception as e:
                self.log_error(f"Erreur lors de l'exécution du script: {str(e)}")
                if attempt == self.retry_count - 1:
                    self._installation_summary.append({
                        'script': self.script_exec,
                        'status': 'exception',
                        'error': str(e),
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if not self.force:
                        os.chdir(original_dir)
                        sys.exit(1)
                        
            # Attendre avant de réessayer
            if attempt < self.retry_count - 1:
                wait_time = 2 ** attempt  # Backoff exponentiel: 1s, 2s, 4s, 8s...
                self.log_warning(f"Nouvelle tentative dans {wait_time} secondes...")
                time.sleep(wait_time)
                
        # Exécuter le script post-exec si présent
        if self.post_exec_script:
            post_script_path = os.path.join(self.extract_dir, self.post_exec_script)
            if os.path.isfile(post_script_path):
                self.log_info(f"Exécution du script post-exécution: {self.post_exec_script}")
                try:
                    # Rendre le script exécutable
                    os.chmod(post_script_path, os.stat(post_script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    
                    # Exécuter le script
                    result = subprocess.run([post_script_path], cwd=self.extract_dir, 
                                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    self.log_success("Script post-exécution terminé avec succès")
                except subprocess.CalledProcessError as e:
                    self.log_error(f"Erreur lors de l'exécution du script post-exécution (code {e.returncode})")
                    self.log_debug(f"Sortie d'erreur: {e.stderr.decode() if e.stderr else 'N/A'}")
                except Exception as e:
                    self.log_error(f"Erreur lors de l'exécution du script post-exécution: {str(e)}")
        
        # Revenir au répertoire original
        os.chdir(original_dir)
        
    def create_installation_summary(self):
        """Crée un résumé de l'installation"""
        if not self._installation_summary:
            return
            
        summary_file = os.path.join(self.extract_dir, "installation_summary.json")
        
        try:
            # Ajouter des informations système
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'architecture': platform.machine(),
                'hostname': platform.node(),
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'user': getpass.getuser()
            }
            
            # Créer le résumé complet
            summary = {
                'system': system_info,
                'version': VERSION,
                'extract_dir': self.extract_dir,
                'steps': self._installation_summary
            }
            
            # Écrire le résumé dans un fichier JSON
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
            self.log_debug(f"Résumé d'installation créé: {summary_file}")
            
        except Exception as e:
            self.log_debug(f"Impossible de créer le résumé d'installation: {str(e)}")
        
    def cleanup_temp_files(self):
        """Nettoie les fichiers temporaires"""
        if not self.cleanup:
            self.log_debug("Nettoyage désactivé, conservation des fichiers temporaires")
            return
            
        self.log_debug("Nettoyage des fichiers temporaires...")
        
        # Supprimer les répertoires temporaires
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    if os.path.isdir(temp_dir):
                        shutil.rmtree(temp_dir)
                    else:
                        os.unlink(temp_dir)
                except Exception as e:
                    self.log_debug(f"Impossible de supprimer {temp_dir}: {str(e)}")
                    
        # Réinitialiser la liste
        self._temp_dirs = []
        
    def run(self):
        """Point d'entrée principal du script"""
        try:
            # Afficher la bannière
            self.show_banner()
            
            # Déterminer le mode d'exécution (création ou extraction)
            create_mode = self.config_file is not None or (self.content_dir and self.output_file)
            
            if create_mode:
                # Mode création
                self._script_mode = "creation"
                self.log_info("Mode: création d'archive auto-extractible")
                
                # Vérification des dépendances
                self.check_dependencies()
                
                # Charger la configuration si spécifiée
                if self.config_file:
                    self.load_config()
                    
                # Normaliser les chemins
                self.normalize_paths()
                
                # Valider la configuration
                self.validate_config()
                
                # Compresser les fichiers
                self.compress_files()
                
            else:
                # Mode extraction
                self._script_mode = "extraction"
                self.log_info("Mode: extraction d'archive auto-extractible")
                
                # Vérifier les droits root si nécessaire
                self.check_root()
                
                # Vérifier si l'archive a expiré
                if not self.check_expiration():
                    sys.exit(1)
                    
                # Vérifier l'espace disque disponible
                if not self.check_disk_space():
                    sys.exit(1)
                    
                # Vérifier le hash distant si spécifié
                if self.remote_hash_url and not self.verify_remote_hash(sys.argv[0]):
                    sys.exit(1)
                    
                # Vérifier les mises à jour disponibles
                self.check_version()
                
                # Préparer le répertoire d'extraction
                self.prepare_extract_dir()
                
                # Extraire l'archive
                self.extract_archive()
                
                # Exécuter le script principal
                self.execute_script()
                
                # Créer un résumé de l'installation
                self.create_installation_summary()
                
                # Nettoyer les fichiers temporaires
                self.cleanup_temp_files()
                
            self.log_success("Opération terminée avec succès")
            
        except KeyboardInterrupt:
            self.log_warning("Opération interrompue par l'utilisateur")
            self.cleanup_temp_files()
            sys.exit(130)
        except Exception as e:
            self.log_error(f"Erreur inattendue: {str(e)}")
            if self.debug:
                self.log_debug(traceback.format_exc())
            self.cleanup_temp_files()
            sys.exit(1)

# Partie principale pour le mode création ou extraction
if __name__ == '__main__':
    import fnmatch
    
    # Créer et exécuter l'instance de NvBuilder
    builder = NvBuilder()
    builder.run()
    
# Marqueur de fin du script Python
# __ARCHIVE_BELOW__
"

# Exécuter le code Python
exec(__doc__)