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
    from colorama import Fore, Style; 
except ImportError: 
    class DummyColorama: 
        def __getattr__(self, name): 
            return ""
    Fore = Style = DummyColorama(); Style.RESET_ALL = ""


logger = logging.getLogger("nvbuilder")

class Encryptor:
    """Classe responsable du chiffrement de l'archive."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('compression', {})
        self.tool = self.config.get('encryption_tool', DEFAULT_ENCRYPTION_TOOL)
        # Récupérer/utiliser les paramètres spécifiques
        self.cipher = self.config.get('openssl_cipher', DEFAULT_OPENSSL_CIPHER)
        self.iterations = self.config.get('openssl_iter', DEFAULT_OPENSSL_ITER)
        self.gpg_cipher = DEFAULT_GPG_CIPHER_ALGO # Utiliser constante pour GPG
        self.gpg_s2k = DEFAULT_GPG_S2K_OPTIONS   # Utiliser constante pour GPG

    def encrypt(self, archive_path: Path, password: str) -> Path:
        """Chiffre le fichier archive_path."""
        enc_ext = ".enc" if self.tool == "openssl" else ".gpg"
        encrypted_path = archive_path.with_suffix(archive_path.suffix + enc_ext)

        logger.info(f"Chiffrement ({self.tool}) vers {encrypted_path.name}...")
        try: check_tool_availability(self.tool)
        except ToolNotFoundError as e: raise EncryptionError(f"Chiffrement impossible: {e}") from e

        cmd = []; env = os.environ.copy()
        archive_path_str, encrypted_path_str = str(archive_path), str(encrypted_path)
        try:
            if self.tool == "openssl":
                env['NVBUILDER_ENC_PASS'] = password
                cmd = ["openssl", "enc", f"-{self.cipher}", "-salt", "-pbkdf2", "-iter", str(self.iterations), "-in", archive_path_str, "-out", encrypted_path_str, "-pass", "env:NVBUILDER_ENC_PASS"]
            elif self.tool == "gpg":
                s2k_opts = self.gpg_s2k.split()
                cmd = ["gpg", "--quiet", "--batch", "--yes", "--pinentry-mode", "loopback", "--symmetric", "--cipher-algo", self.gpg_cipher] + s2k_opts + ["--passphrase", password, "-o", encrypted_path_str, archive_path_str]

            logger.debug(f"Exécution {self.tool} pour chiffrement...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env, check=False)

            if result.returncode != 0:
                err_msg = f"Échec chiffrement {self.tool} (code {result.returncode}).";
                if result.stderr: err_msg += f"\nStderr: {result.stderr.strip()}"
                if result.stdout: err_msg += f"\nStdout: {result.stdout.strip()}" # Moins fréquent mais possible
                if encrypted_path.exists(): encrypted_path.unlink(missing_ok=True)
                raise EncryptionError(err_msg)
            else:
                checksum = calculate_checksum(encrypted_path)
                logger.info(f"-> Chiffrement {Fore.GREEN}OK{Style.RESET_ALL}. Checksum: {checksum[:12]}...")
                return encrypted_path

        except Exception as e:
            if encrypted_path.exists(): encrypted_path.unlink(missing_ok=True)
            if isinstance(e, EncryptionError): raise
            raise EncryptionError(f"Erreur inattendue chiffrement: {e}") from e
        finally:
            if 'NVBUILDER_ENC_PASS' in env: del env['NVBUILDER_ENC_PASS']