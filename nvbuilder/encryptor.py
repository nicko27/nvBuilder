# nvbuilder/encryptor.py
"""Chiffre une archive."""

import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import check_tool_availability, calculate_checksum
from .exceptions import EncryptionError, ToolNotFoundError
from .constants import DEFAULT_ENCRYPTION_TOOL, DEFAULT_OPENSSL_CIPHER, DEFAULT_OPENSSL_ITER, DEFAULT_GPG_CIPHER_ALGO, DEFAULT_GPG_S2K_OPTIONS
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()  # Initialiser ici aussi au cas où __main__ ne serait pas appelé
except ImportError:
    # Créer des substituts vides si colorama n'est pas là
    class DummyColorama:
        def __getattr__(self, name): return ""
    Fore = Style = DummyColorama()
    # Définir RESET_ALL comme chaîne vide pour éviter erreurs
    Style.RESET_ALL = ""


logger = logging.getLogger("nvbuilder")

class Encryptor:
    """Classe responsable du chiffrement de l'archive."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'encrypteur avec la configuration donnée.
        
        Args:
            config: Configuration de compression incluant les paramètres de chiffrement
        """
        compression_config = config.get('compression', {})
        self.debug_mode = config.get('debug_mode', False)
        
        # Paramètres de l'outil de chiffrement
        self.tool = compression_config.get('encryption_tool', DEFAULT_ENCRYPTION_TOOL)
        
        # Paramètres spécifiques selon l'outil
        if self.tool == "openssl":
            self.cipher = compression_config.get('openssl_cipher', DEFAULT_OPENSSL_CIPHER)
            self.iterations = compression_config.get('openssl_iter', DEFAULT_OPENSSL_ITER)
            self.gpg_cipher = None  # Non utilisé pour OpenSSL
            self.gpg_s2k = None    # Non utilisé pour OpenSSL
        elif self.tool == "gpg":
            self.gpg_cipher = DEFAULT_GPG_CIPHER_ALGO
            self.gpg_s2k = DEFAULT_GPG_S2K_OPTIONS
            self.cipher = None      # Non utilisé pour GPG
            self.iterations = None  # Non utilisé pour GPG
        else:
            raise EncryptionError(f"Outil de chiffrement non supporté : {self.tool}")

    def encrypt(self, archive_path: Path, password: str) -> Path:
        """
        Chiffre le fichier d'archive spécifié.
        
        Args:
            archive_path: Chemin du fichier à chiffrer
            password: Mot de passe de chiffrement
        
        Returns:
            Path: Chemin du fichier chiffré
        
        Raises:
            EncryptionError: Si le chiffrement échoue
            ToolNotFoundError: Si l'outil de chiffrement est absent
        """
        BLUE = Fore.BLUE
        GREEN = Fore.GREEN
        YELLOW = Fore.YELLOW
        CYAN = Fore.CYAN
        MAGENTA = Fore.MAGENTA
        BRIGHT = Style.BRIGHT
        DIM = Style.DIM
        RESET = Style.RESET_ALL   
        # Définir l'extension de chiffrement
        enc_ext = ".enc" if self.tool == "openssl" else ".gpg"
        encrypted_path = archive_path.with_suffix(archive_path.suffix + enc_ext)

        # Message de début de chiffrement
        if self.debug_mode:
            logger.info(f"Chiffrement ({self.tool}) vers {encrypted_path.name}...")
        else:
            print(f"{BLUE}{BRIGHT}Chiffrement en cours...      ", end=" ", flush=True)

        try:
            # Vérifier la disponibilité de l'outil
            check_tool_availability(self.tool)
        except ToolNotFoundError as e:
            raise EncryptionError(f"Chiffrement impossible: {e}") from e

        cmd = []
        env = os.environ.copy()
        archive_path_str, encrypted_path_str = str(archive_path), str(encrypted_path)
        
        try:
            # Préparation de la commande selon l'outil
            if self.tool == "openssl":
                env['NVBUILDER_ENC_PASS'] = password
                cmd = [
                    "openssl", "enc", f"-{self.cipher}", "-salt", "-pbkdf2", 
                    "-iter", str(self.iterations), 
                    "-in", archive_path_str, 
                    "-out", encrypted_path_str, 
                    "-pass", "env:NVBUILDER_ENC_PASS"
                ]
            elif self.tool == "gpg":
                s2k_opts = self.gpg_s2k.split()
                cmd = [
                    "gpg", "--quiet", "--batch", "--yes", 
                    "--pinentry-mode", "loopback", 
                    "--symmetric", 
                    "--cipher-algo", self.gpg_cipher
                ] + s2k_opts + [
                    "--passphrase", password, 
                    "-o", encrypted_path_str, 
                    archive_path_str
                ]

            # Exécution de la commande
            if self.debug_mode:
                logger.debug(f"Exécution {self.tool} pour chiffrement...")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                env=env, 
                check=False
            )

            # Vérification du résultat
            if result.returncode != 0:
                err_msg = f"Échec chiffrement {self.tool} (code {result.returncode})."
                if result.stderr:
                    err_msg += f"\nStderr: {result.stderr.strip()}"
                if result.stdout:
                    err_msg += f"\nStdout: {result.stdout.strip()}"
                
                # Supprimer le fichier incomplet
                if encrypted_path.exists():
                    encrypted_path.unlink(missing_ok=True)
                
                raise EncryptionError(err_msg)
            else:
                # Calcul du checksum
                checksum = calculate_checksum(encrypted_path)
                
                # Messages de confirmation
                if self.debug_mode:
                    logger.info(f"•  Chiffrement {Fore.GREEN}OK{Style.RESET_ALL}. Checksum: {checksum[:12]}...")
                else:
                    print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
                
                return encrypted_path

        except Exception as e:
            # Nettoyage en cas d'erreur
            if encrypted_path.exists():
                encrypted_path.unlink(missing_ok=True)
            
            # Relancer comme erreur de chiffrement si ce n'est pas déjà le cas
            if isinstance(e, EncryptionError):
                raise
            raise EncryptionError(f"Erreur inattendue chiffrement: {e}") from e
        finally:
            # Toujours nettoyer le mot de passe de l'environnement
            if 'NVBUILDER_ENC_PASS' in env:
                del env['NVBUILDER_ENC_PASS']