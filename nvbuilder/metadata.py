# nvbuilder/metadata.py
"""Gestion des métadonnées du build."""

import platform
import sys
import getpass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging
from .constants import VERSION, DEFAULT_ENCRYPTION_TOOL, DEFAULT_UPDATE_MODE
from .utils import get_absolute_path

logger = logging.getLogger("nvbuilder")

class MetadataManager:
    """Collecte et gère les métadonnées du processus de build."""

    def __init__(self, config: Dict[str, Any], build_version: str):
        """
        Initialise le gestionnaire de métadonnées.
        
        Args:
            config: Configuration du build
            build_version: Version unique du build
        """
        self.config = config
        self.build_version = build_version
        self.debug_mode = config.get('debug_mode', False)
        self.data: Dict[str, Any] = self._initialize()

    def _initialize(self) -> Dict[str, Any]:
        """Initialise le dictionnaire de métadonnées."""
        encryption_enabled = self.config.get('compression', {}).get('encrypted', False)
        update_enabled = self.config.get('update', {}).get('enabled', False)
        update_mode = self.config.get('update', {}).get('mode', DEFAULT_UPDATE_MODE)
        
        # Log d'avertissement pour la configuration chiffrement + mises à jour
        if update_enabled and encryption_enabled:
            if self.debug_mode:
                if update_mode == "auto-replace":
                    logger.warning("MàJ HTTP (mode auto-replace) et Chiffrement activés. Cela nécessitera une saisie de mot de passe.")
                else:
                    logger.warning("MàJ HTTP et Chiffrement activés. Vérification de version et d'intégrité activée.")

        metadata = {
            "nvbuilder_version": VERSION,
            "build_version": self.build_version,
            "created_at": datetime.now().isoformat(),
            "python_version": platform.python_version(),
            "platform": sys.platform,
            "build_host": platform.node(),
            "build_user": getpass.getuser(),
            "files_included": [],
            "files_excluded": [],
            "archive_checksum_sha256": None,
            "encrypted_archive_checksum_sha256": None,
            # --- Champs pour mises à jour sécurisées ---
            "script_checksum_sha256": None,  # Hash du fichier .sh final
            "password_check_token_b64": None,  # Jeton chiffré en base64
            "token_encryption_params": None,  # Params utilisés pour chiffrer jeton
            # --- Autres métadonnées ---
            "content_source_dir": str(self.config.get('content', './content')),
            "post_extraction_script": self.config.get('script', 'install.sh'),
            "update_enabled": update_enabled,
            "update_mode": update_mode if update_enabled else None,
            "encryption_enabled": encryption_enabled,
            "encryption_tool": None,
            "archive_size": 0,
            "encrypted_archive_path": None
        }
        
        if metadata["encryption_enabled"]:
            metadata["encryption_tool"] = self.config.get('compression', {}).get('encryption_tool', DEFAULT_ENCRYPTION_TOOL)
            
        return metadata

    def update(self, key: str, value: Any):
        """Met à jour une clé spécifique dans les métadonnées."""
        self.data[key] = value

    def add_included_file(self, file_info: Dict[str, Any]):
        """Ajoute un fichier à la liste des fichiers inclus."""
        self.data['files_included'].append(file_info)
        
    def add_excluded_file(self, file_info: Dict[str, Any]):
        """Ajoute un fichier à la liste des fichiers exclus."""
        self.data['files_excluded'].append(file_info)
        
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur depuis les métadonnées."""
        return self.data.get(key, default)
        
    def get_all(self) -> Dict[str, Any]:
        """Récupère l'ensemble des métadonnées."""
        return self.data.copy()

    def get_public_metadata(self) -> Dict[str, Any]:
        """Retourne les métadonnées pour le fichier .json (exclut listes fichiers)."""
        # Exclure les listes détaillées des fichiers
        public_meta = {k: v for k, v in self.data.items() if k not in ['files_included', 'files_excluded']}
        
        # Ajouter les compteurs
        public_meta['files_included_count'] = len(self.data.get('files_included', []))
        public_meta['files_excluded_count'] = len(self.data.get('files_excluded', []))
        
        # Ajouter la taille de l'archive chiffrée si disponible
        enc_path = self.data.get('encrypted_archive_path')
        public_meta['encrypted_size'] = None
        if enc_path and Path(enc_path).exists():
            try:
                public_meta['encrypted_size'] = Path(enc_path).stat().st_size
            except OSError:
                pass
                
        # Ne pas inclure les informations de vérification de mot de passe 
        # si le chiffrement n'est pas activé
        if not self.data.get('encryption_enabled'):
             public_meta.pop('password_check_token_b64', None)
             public_meta.pop('token_encryption_params', None)
             
        return public_meta

    def write_metadata_file(self, output_script_path: Path):
        """Écrit le fichier .json de métadonnées."""
        if not self.config.get('generate_metadata_file', True):
            return
            
        metadata_output_path = output_script_path.with_suffix('.json')
        public_data = self.get_public_metadata()
        
        try:
            with open(metadata_output_path, 'w', encoding='utf-8') as f:
                json.dump(public_data, f, indent=2, ensure_ascii=False)
            
            if self.debug_mode:
                logger.info(f"Fichier metadata généré: {metadata_output_path}")
        except Exception as e:
            # Message d'erreur uniquement en mode debug
            if self.debug_mode:
                logger.warning(f"Génération {metadata_output_path} échouée: {e}")

    def write_version_file(self):
        """Génère le fichier version.json pour les mises à jour."""
        version_file_path_str = self.config.get('update', {}).get('version_file_path')
        if not version_file_path_str:
            if self.debug_mode:
                logger.debug("Chemin version.json non spécifié.")
            return

        config_dir = self.config.get('_config_dir', Path('.'))
        output_path = get_absolute_path(version_file_path_str, config_dir)
        
        try:
            # Créer les répertoires parents si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Données de version principale
            v_data = {
                "build_version": self.build_version,
                "generated_at": self.data['created_at'],
                "script_checksum_sha256": self.data.get('script_checksum_sha256'),
                "password_check_token_b64": self.data.get('password_check_token_b64') if self.data['encryption_enabled'] else None,
                "token_encryption_params": self.data.get('token_encryption_params') if self.data['encryption_enabled'] else None,
            }
            
            # Informations sur l'archive interne
            archive_info = {
                "size": self.data.get('archive_size', 0),
                "encrypted_size": self.get_public_metadata().get('encrypted_size'),
                "files_included_count": len(self.data.get('files_included', [])),
                "post_extraction_script": self.data.get('post_extraction_script'),
                "compression_method": self.config.get('compression', {}).get('method', 'gz'),
                "encryption_enabled": self.data.get('encryption_enabled', False),
                "encryption_tool": self.data.get('encryption_tool'),
                "build_platform": self.data.get('platform'),
                "build_python_version": self.data.get('python_version'),
                "archive_checksum_sha256": self.data.get('archive_checksum_sha256'),
                "encrypted_archive_checksum_sha256": self.data.get('encrypted_archive_checksum_sha256') if self.data['encryption_enabled'] else None,
            }
            
            # Ajouter les informations d'archive
            v_data["archive_info"] = archive_info

            # Filtrer les valeurs None pour un JSON plus propre
            v_data_final = {k: v for k, v in v_data.items() if v is not None}
            archive_info_final = {k: v for k, v in archive_info.items() if v is not None}
            if archive_info_final:
                v_data_final["archive_info"] = archive_info_final

            # Écrire le fichier JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(v_data_final, f, indent=2, ensure_ascii=False)
                
            if self.debug_mode:
                logger.info(f"Fichier version généré: {output_path}")
            
        except Exception as e:
            # Message d'erreur uniquement en mode debug
            if self.debug_mode:
                logger.error(f"Err génération version.json '{output_path}': {e}")