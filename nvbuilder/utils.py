# nvbuilder/utils.py
"""Fonctions utilitaires pour nvBuilder."""

import hashlib
import shutil
import fnmatch
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import base64  # Pour encoder/décoder en Base64
import subprocess  # Pour exécuter des commandes externes

try:
    from colorama import Fore, Style  # Pour prompts interactifs
except ImportError:
    class DummyColorama: 
        def __getattr__(self, name): 
            return ""
    Fore = Style = DummyColorama()
    Style.RESET_ALL = ""

from .exceptions import ToolNotFoundError, EncryptionError
# Importer constantes nécessaires pour chiffrement jeton
from .constants import (
    DEFAULT_OPENSSL_CIPHER, 
    DEFAULT_OPENSSL_ITER, 
    DEFAULT_GPG_CIPHER_ALGO, 
    DEFAULT_GPG_S2K_OPTIONS
)

logger = logging.getLogger("nvbuilder")

def calculate_checksum(file_path: Path) -> str:
    """
    Calcule le checksum SHA256 d'un fichier.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        str: Checksum hexadécimal
    """
    sha256_hash = hashlib.sha256()
    buffer_size = 65536
    try:
        with open(file_path, 'rb') as f:
            while True: 
                data = f.read(buffer_size)
                if not data:
                    break
                sha256_hash.update(data)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Checksum impossible pour {file_path}: {e}")
        return "checksum_error"

def check_tool_availability(tool_name: str) -> str:
    """
    Vérifie si un outil externe est disponible dans le PATH.
    
    Args:
        tool_name: Nom de l'outil à vérifier
        
    Returns:
        str: Chemin complet de l'outil
        
    Raises:
        ToolNotFoundError: Si l'outil n'est pas trouvé
    """
    tool_path = shutil.which(tool_name)
    if not tool_path:
        raise ToolNotFoundError(tool_name)
    return tool_path

def check_exclusion(path_str: str, patterns: List[str], ignore_case: bool) -> bool:
    """
    Vérifie si un chemin correspond à un des patterns d'exclusion.
    
    Args:
        path_str: Chemin à vérifier
        patterns: Liste des patterns d'exclusion
        ignore_case: Si True, ignore la casse pour la comparaison
        
    Returns:
        bool: True si le chemin correspond à un pattern d'exclusion
    """
    path_norm = path_str.replace(os.sep, '/')
    path_check = path_norm.lower() if ignore_case else path_norm
    
    for pattern in patterns:
        pattern_norm = pattern.replace(os.sep, '/')
        pattern_check = pattern_norm.lower() if ignore_case else pattern_norm
        is_dir_pattern = pattern_check.endswith('/')
        
        if is_dir_pattern:
            path_dir_match = path_check + '/' if not path_check.endswith('/') else path_check
            if (fnmatch.fnmatchcase(path_dir_match, pattern_check + '*') or 
                fnmatch.fnmatchcase(path_dir_match, pattern_check)):
                return True
        elif fnmatch.fnmatchcase(path_check, pattern_check):
            return True
            
    return False

def get_standard_exclusions() -> Dict[str, List[str]]:
    """
    Retourne un dictionnaire des patterns d'exclusion standard par catégorie.
    
    Returns:
        Dict[str, List[str]]: Dictionnaire des patterns d'exclusion
    """
    return {
        "Version Control": [".git/", ".svn/", ".hg/", ".cvs/"],
        "Python": ["*.pyc", "*.pyo", "__pycache__/", "*.egg-info/", "build/", "dist/", 
                  "*.spec", ".venv/", "venv/", "env/"],
        "Logs & Temp": ["*.log", "*.tmp", "*~", "*.bak", "*.swp", ".DS_Store", "Thumbs.db"],
        "Configuration": [".env"],
        "IDE/Editor": [".vscode/", ".idea/", ".project", ".settings/"],
        "macOS": ["._*"]
    }

def get_all_standard_exclusions() -> List[str]:
    """
    Retourne une liste plate de tous les patterns d'exclusion standard.
    
    Returns:
        List[str]: Liste des patterns d'exclusion
    """
    all_patterns = []
    for patterns in get_standard_exclusions().values():
        all_patterns.extend(patterns)
    return all_patterns

def read_file_binary(file_path: Path) -> bytes:
    """
    Lit un fichier en binaire.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        bytes: Contenu binaire du fichier
        
    Raises:
        IOError: Si la lecture échoue
    """
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Erreur lecture binaire {file_path}: {e}") from e

def get_absolute_path(path_str: str, base_dir: Path) -> Path:
    """
    Convertit un chemin relatif en chemin absolu.
    
    Args:
        path_str: Chemin à convertir
        base_dir: Répertoire de base pour les chemins relatifs
        
    Returns:
        Path: Chemin absolu
    """
    path = Path(path_str)
    return (base_dir / path).resolve() if not path.is_absolute() else path.resolve()

def _get_nested(data: Dict, keys: List[str], default: Any = None) -> Any:
    """
    Récupère une valeur imbriquée dans un dictionnaire.
    
    Args:
        data: Dictionnaire source
        keys: Liste des clés pour accéder à la valeur
        default: Valeur par défaut si la clé n'existe pas
        
    Returns:
        Any: Valeur trouvée ou valeur par défaut
    """
    current = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return default
        current = current.get(key, {})
    
    if isinstance(current, dict) and keys:
        return current.get(keys[-1], default)
    elif not keys and isinstance(data, dict):
        return data
    else:
        return default

def _set_nested(data: Dict, keys: List[str], value: Any):
    """
    Définit une valeur imbriquée dans un dictionnaire.
    
    Args:
        data: Dictionnaire cible
        keys: Liste des clés pour accéder à l'emplacement
        value: Valeur à définir
    """
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]
        
    if keys:
        current[keys[-1]] = value

def prompt_string(config_dict: Dict, message: str, keys: List[str], 
                 default_value: Optional[str] = None) -> Optional[str]:
    """
    Demande à l'utilisateur de saisir une chaîne de caractères.
    
    Args:
        config_dict: Dictionnaire de configuration à mettre à jour
        message: Message à afficher
        keys: Chemin des clés dans le dictionnaire
        default_value: Valeur par défaut si l'utilisateur ne saisit rien
        
    Returns:
        Optional[str]: Valeur saisie ou par défaut
    """
    current_value = _get_nested(config_dict, keys)
    prompt_msg = f"{message}"
    
    default_display = default_value if default_value is not None else "aucun"
    if current_value is not None:
        prompt_msg += f" (actuel: '{current_value}')"
    else:
        prompt_msg += f" (défaut: '{default_display}')"
        
    prompt_msg += ": "
    user_input = input(prompt_msg).strip()
    
    final_value = user_input if user_input else (current_value if current_value is not None else default_value)
    
    if final_value is not None:
        _set_nested(config_dict, keys, final_value)
        
    return final_value

def prompt_bool(config_dict: Dict, message: str, keys: List[str], 
               default_value: bool = False) -> bool:
    """
    Demande à l'utilisateur de saisir une valeur booléenne.
    
    Args:
        config_dict: Dictionnaire de configuration à mettre à jour
        message: Message à afficher
        keys: Chemin des clés dans le dictionnaire
        default_value: Valeur par défaut
        
    Returns:
        bool: Valeur booléenne résultante
    """
    current_value = _get_nested(config_dict, keys, default=default_value)
    current_display = "oui" if current_value else "non"
    
    prompt_msg = f"{message} (oui/non) (actuel: {current_display}): "
    user_input = input(prompt_msg).lower().strip()
    
    if user_input in ["oui", "o", "y", "yes", "1", "true"]:
        final_value = True
    elif user_input in ["non", "n", "no", "0", "false"]:
        final_value = False
    else:
        final_value = current_value
        
    _set_nested(config_dict, keys, final_value)
    return final_value

def save_config_yaml(config_dict: Dict, output_path: Path):
    """
    Sauvegarde un dictionnaire de configuration au format YAML.
    
    Args:
        config_dict: Dictionnaire à sauvegarder
        output_path: Chemin du fichier de sortie
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, 
                          sort_keys=False, allow_unicode=True, indent=2)
        print(f"\n{Fore.GREEN}Configuration sauvegardée: {output_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erreur sauvegarde config: {e}{Style.RESET_ALL}")

def encrypt_string_to_base64(plaintext: str, password: str, tool: str,
                            cipher: str = DEFAULT_OPENSSL_CIPHER,
                            iterations: int = DEFAULT_OPENSSL_ITER,
                            gpg_cipher: str = DEFAULT_GPG_CIPHER_ALGO,
                            gpg_s2k: str = DEFAULT_GPG_S2K_OPTIONS) -> Optional[str]:
    """
    Chiffre une chaîne de caractères et retourne le résultat en Base64.
    
    Args:
        plaintext: Texte à chiffrer
        password: Mot de passe pour le chiffrement
        tool: Outil de chiffrement ('openssl' ou 'gpg')
        cipher: Algorithme de chiffrement pour openssl
        iterations: Nombre d'itérations pour le dérivation de clé avec openssl
        gpg_cipher: Algorithme de chiffrement pour gpg
        gpg_s2k: Options S2K pour gpg
        
    Returns:
        Optional[str]: Chaîne chiffrée encodée en Base64, ou None si échec
    """
    logger.debug(f"Chiffrement du jeton avec {tool}...")
    cmd = []
    env = os.environ.copy()
    plaintext_bytes = plaintext.encode('utf-8')

    try:
        if tool == "openssl":
            # Utiliser une variable d'environnement pour le mot de passe
            env['NVBUILDER_TOKEN_PASS'] = password
            # Chiffrer depuis stdin vers stdout
            cmd = [
                "openssl", "enc", f"-{cipher}", "-salt", "-pbkdf2",
                "-iter", str(iterations), "-pass", "env:NVBUILDER_TOKEN_PASS"
            ]
            process = subprocess.run(
                cmd, 
                input=plaintext_bytes, 
                capture_output=True, 
                check=True, 
                env=env
            )
            ciphertext = process.stdout

        elif tool == "gpg":
            # Chiffrer depuis stdin vers stdout
            s2k_opts = gpg_s2k.split()
            cmd = [
                "gpg", "--quiet", "--batch", "--yes", "--pinentry-mode", "loopback",
                "--symmetric", "--cipher-algo", gpg_cipher
            ] + s2k_opts + [
                "--passphrase", password, "--output", "-"  # Sortie vers stdout
            ]
            process = subprocess.run(
                cmd, 
                input=plaintext_bytes, 
                capture_output=True, 
                check=True
            )
            ciphertext = process.stdout
        else:
            raise EncryptionError(f"Outil de chiffrement non supporté pour le jeton: {tool}")

        # Encoder le résultat chiffré (binaire) en Base64
        return base64.b64encode(ciphertext).decode('ascii')

    except subprocess.CalledProcessError as e:
        err_msg = f"Échec chiffrement jeton avec {tool} (code {e.returncode})."
        if e.stderr:
            err_msg += f"\nstderr:\n{e.stderr.decode('utf-8', errors='ignore').strip()}"
        if e.stdout:
            err_msg += f"\nstdout:\n{e.stdout.decode('utf-8', errors='ignore').strip()}"
        logger.error(err_msg)
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue chiffrement jeton: {e}")
        return None
    finally:
        if 'NVBUILDER_TOKEN_PASS' in env:
            del env['NVBUILDER_TOKEN_PASS']