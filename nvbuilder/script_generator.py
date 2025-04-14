# nvbuilder/script_generator.py
"""Génère le script Bash final."""

import logging
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
import re

from .constants import TEMPLATE_FILENAME, ARCHIVE_MARKER
from .utils import read_file_binary, get_absolute_path
from .exceptions import TemplateError, BuildProcessError

try: 
    from colorama import Fore, Style
except ImportError: 
    class DummyColorama: 
        def __getattr__(self, name): 
            return ""
    Fore = Style = DummyColorama()
    Style.RESET_ALL = ""

logger = logging.getLogger("nvbuilder")

class ScriptGenerator:
    """Classe responsable de la génération du script Bash auto-extractible final."""

    def __init__(self, config: Dict[str, Any], metadata: Dict[str, Any]):
        """
        Initialise le générateur de script.
        
        Args:
            config: Configuration du build
            metadata: Métadonnées du build
        """
        self.config = config
        self.metadata = metadata
        self.package_dir = Path(__file__).parent.resolve()

    def generate(self, archive_to_embed_path: Path, archive_original_filename: str, 
                tar_command_flags: str, bash_snippets: Dict[str, str]) -> Path:
        """
        Génère le script final en intégrant l'archive et en remplaçant les placeholders.
        
        Args:
            archive_to_embed_path: Chemin vers l'archive à intégrer (compressée ou chiffrée)
            archive_original_filename: Nom du fichier d'archive original (pour extraction)
            tar_command_flags: Options pour la commande tar
            bash_snippets: Fragments de code bash à injecter dans le template
            
        Returns:
            Path: Chemin vers le script généré
            
        Raises:
            TemplateError: Si le template est invalide
            BuildProcessError: Si une erreur survient lors de la génération
        """
        # Charger le template
        template_content = self._load_template()
        
        # Encoder l'archive en base64
        archive_base64 = self._encode_archive(archive_to_embed_path)
        
        # Préparer le chemin de sortie
        output_config = self.config.get('output', {})
        output_filename = output_config.get('path', 'autoextract.sh')
        config_dir = self.config.get('_config_dir', Path('.'))
        output_path = get_absolute_path(output_filename, config_dir)
        
        # Préparer les remplacements
        replacements = self._prepare_replacements(archive_original_filename, tar_command_flags, bash_snippets)
        
        # Appliquer les remplacements au template
        final_script_content = self._apply_replacements(template_content, replacements)
        
        # Écrire le script final
        self._write_script(output_path, final_script_content, archive_base64)
        
        return output_path

    def _load_template(self) -> str:
        """
        Charge le contenu du template Bash depuis le fichier template.
        
        Returns:
            str: Contenu du template
            
        Raises:
            TemplateError: Si le template est introuvable ou invalide
        """
        template_path = self.package_dir / TEMPLATE_FILENAME
        logger.debug(f"Chargement template: {template_path}")
        
        if not template_path.is_file():
            raise TemplateError(f"Template introuvable: {template_path}")
            
        try:
            content = template_path.read_text(encoding='utf-8')
            
            # Vérifier que le template se termine par le marqueur correct
            expected_marker = f"# NVBUILDER_MARKER_LINE: %%ARCHIVE_MARKER%%"
            if not content.rstrip().endswith(expected_marker):
                raise TemplateError(
                    f"Template '{TEMPLATE_FILENAME}' doit finir par '{expected_marker}'."
                )
                
            # S'assurer qu'il y a un saut de ligne à la fin
            if not content.endswith("\n"):
                logger.warning("Ajout newline final après %%ARCHIVE_MARKER%%.")
                content = content.rstrip() + "\n"
                
            return content
            
        except Exception as e:
            if not isinstance(e, TemplateError):
                e = TemplateError(f"Lecture template '{template_path}' échouée: {e}")
            raise e

    def _encode_archive(self, archive_path: Path) -> bytes:
        """
        Lit l'archive et l'encode en Base64.
        
        Args:
            archive_path: Chemin vers l'archive à encoder
            
        Returns:
            bytes: Données encodées en base64
            
        Raises:
            BuildProcessError: Si l'encodage échoue
        """
        logger.info(f"Encodage Base64 de '{archive_path.name}'...")
        
        try:
            # Lire l'archive en binaire
            archive_data = read_file_binary(archive_path)
            
            # Encoder en base64
            encoded_data = base64.b64encode(archive_data)
            
            # Log du succès
            size_mb = len(encoded_data)/1024/1024
            logger.info(f"-> Encodage Base64 {Fore.GREEN}OK{Style.RESET_ALL} (Taille: {size_mb:.2f} Mo)")
            
            return encoded_data
            
        except Exception as e:
            raise BuildProcessError(f"Erreur encodage B64 {archive_path}: {e}") from e

    def _prepare_replacements(self, archive_original_filename: str, 
                             tar_command_flags: str, bash_snippets: Dict[str, str]) -> Dict[str, str]:
        """
        Prépare le dictionnaire de remplacements pour les placeholders du template.
        
        Args:
            archive_original_filename: Nom du fichier d'archive original
            tar_command_flags: Options pour la commande tar
            bash_snippets: Fragments de code bash à injecter
            
        Returns:
            Dict[str, str]: Dictionnaire de remplacements
        """
        # Extraire les informations nécessaires
        post_script = self.config.get('script', '') or ""
        comp_method = self.config.get('compression', {}).get('method', 'gz')
        
        # Déterminer le flag tar pour l'affichage
        tar_flag_only = tar_command_flags.replace('x','').replace('f','')
        comp_display = f"{comp_method} (-{tar_flag_only})" if tar_flag_only else ("aucune" if comp_method == 'none' else comp_method)
        
        # Informations système
        py_display = self.metadata.get('python_version', 'N/A')
        build_user_host = f"{self.metadata.get('build_user', 'N/A')}@{self.metadata.get('build_host', 'N/A')}"
        
        # État des fonctionnalités
        enc_enabled = self.metadata.get('encryption_enabled', False)
        enc_tool = self.metadata.get('encryption_tool') or "N/A"
        upd_enabled = self.metadata.get('update_enabled', False)
        url_display = self.config.get('update', {}).get('version_url', '') or 'N/A'
        
        # Construire le dictionnaire de remplacements
        replacements = {
            # Informations de version et système
            "%%NVBUILDER_VERSION%%": self.metadata.get('nvbuilder_version', 'N/A'),
            "%%CREATED_AT%%": self.metadata.get('created_at', 'N/A'),
            "%%BUILD_USER_HOST%%": build_user_host,
            "%%PLATFORM_BUILD%%": self.metadata.get('platform', 'N/A'),
            "%%PYTHON_VERSION_DISPLAY%%": py_display,
            "%%BUILD_VERSION%%": self.metadata.get('build_version', 'N/A'),
            
            # Configuration archive et extraction
            "%%ARCHIVE_MARKER%%": ARCHIVE_MARKER,
            "%%TAR_COMMAND_FLAGS%%": tar_command_flags,
            "%%POST_EXTRACTION_SCRIPT%%": post_script,
            "%%CONTENT_SOURCE_DIR%%": self.metadata.get('content_source_dir', 'N/A'),
            "%%ARCHIVE_CHECKSUM%%": self.metadata.get('archive_checksum_sha256', 'N/A'),
            "%%ENCRYPTED_CHECKSUM%%": self.metadata.get('encrypted_archive_checksum_sha256', 'N/A'),
            "%%ARCHIVE_ORIGINAL_FILENAME%%": archive_original_filename,
            
            # Informations d'affichage
            "%%COMPRESSION_DISPLAY%%": comp_display,
            "%%ENCRYPTION_TOOL_DISPLAY%%": enc_tool,
            "%%UPDATE_URL_DISPLAY%%": url_display,
            
            # Flags pour le script bash
            "%%BASH_ENCRYPTION_ENABLED_BOOL%%": "true" if enc_enabled else "false",
            "%%BASH_UPDATE_ENABLED_BOOL%%": "true" if upd_enabled else "false",
            
            # Snippets bash
            "%%BASH_UPDATE_VARS%%": bash_snippets.get("update_vars", ""),
            "%%BASH_UPDATE_ARG_PARSING%%": bash_snippets.get("update_arg_parsing", ""),
            "%%BASH_UPDATE_HELP%%": bash_snippets.get("update_help", ""),
            "%%BASH_UPDATE_CHECK_CALL%%": bash_snippets.get("update_check_call", ""),
            "%%BASH_UPDATE_FUNCTION%%": bash_snippets.get("update_function", ""),
            "%%BASH_ENCRYPTION_VARS%%": bash_snippets.get("encryption_vars", ""),
            "%%BASH_DECRYPTION_LOGIC%%": bash_snippets.get("decryption_logic", ""),
            "%%BASH_DECRYPTION_CLEANUP%%": bash_snippets.get("decryption_cleanup", "")
        }
        
        return replacements

    def _apply_replacements(self, template_content: str, replacements: Dict[str, str]) -> str:
        """
        Applique les remplacements au contenu du template.
        
        Args:
            template_content: Contenu du template
            replacements: Dictionnaire de remplacements
            
        Returns:
            str: Contenu avec remplacements appliqués
            
        Raises:
            TemplateError: Si des placeholders ne sont pas remplacés
        """
        logger.debug("Application des remplacements au template...")
        final_content = template_content
        
        # Appliquer chaque remplacement
        for placeholder, value in replacements.items():
            final_content = final_content.replace(placeholder, str(value))
        
        # Vérifier qu'il ne reste pas de placeholders non remplacés
        remaining = re.findall(r'%%[A-Z0-9_]+%%', final_content)
        if remaining:
            # Obtenir la liste unique des placeholders manquants
            unique_remaining = sorted(list(set(remaining)))
            raise TemplateError(f"Placeholders non remplacés: {unique_remaining}")
        
        return final_content

    def _write_script(self, output_path: Path, script_content: str, archive_base64: bytes):
        """
        Écrit le script final et ajoute les données Base64 de l'archive.
        
        Args:
            output_path: Chemin où écrire le script
            script_content: Contenu du script (partie texte)
            archive_base64: Données de l'archive encodées en base64
            
        Raises:
            BuildProcessError: Si l'écriture échoue
        """
        logger.info(f"Écriture script -> {output_path}")
        
        try:
            # Créer les répertoires parents si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Vérifier que le contenu se termine par le marqueur approprié
            expected_ending = f"# NVBUILDER_MARKER_LINE: {ARCHIVE_MARKER}\n"
            if not script_content.endswith(expected_ending):
                clean_content_end = script_content.rstrip()
                expected_marker_line = f"# NVBUILDER_MARKER_LINE: {ARCHIVE_MARKER}"
                
                if clean_content_end.endswith(expected_marker_line):
                    # Il manque juste le saut de ligne final
                    script_content = clean_content_end + "\n"
                else:
                    # Le marqueur est complètement absent ou incorrect
                    logger.error(f"FIN ATTENDUE:\n{expected_ending}\nFIN REELLE:\n{script_content[-100:]}")
                    raise BuildProcessError("Contenu final script ne finit pas par marqueur unique.")
            
            # Écrire le contenu du script suivi des données base64 et d'un saut de ligne final
            with open(output_path, 'wb') as f:
                f.write(script_content.encode('utf-8'))
                f.write(archive_base64)
                f.write(b'\n')
            
            # Rendre le script exécutable
            os.chmod(output_path, 0o755)
            
            logger.info(f"-> Écriture script {Fore.GREEN}OK{Style.RESET_ALL}")
            
        except Exception as e:
            raise BuildProcessError(f"Erreur écriture script '{output_path}': {e}") from e