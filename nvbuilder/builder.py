# nvbuilder/builder.py
"""Classe principale NvBuilder."""

import logging
import time
import getpass
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import sys
from datetime import datetime

from .config import ConfigLoader
from .logging_setup import setup_logging
from .metadata import MetadataManager
from .archiver import Archiver
from .encryptor import Encryptor
from .bash_snippets import generate_update_snippets, generate_encryption_snippets, BashSnippetsDict
from .script_generator import ScriptGenerator
from .utils import get_absolute_path, get_standard_exclusions, calculate_checksum, encrypt_string_to_base64
from .exceptions import NvBuilderError, ConfigError, EncryptionError, ToolNotFoundError
from .constants import VERSION,DEFAULT_UPDATE_MODE, PASSWORD_CHECK_TOKEN, DEFAULT_OPENSSL_CIPHER, DEFAULT_OPENSSL_ITER, DEFAULT_GPG_CIPHER_ALGO, DEFAULT_GPG_S2K_OPTIONS

# Import des couleurs sémantiques
from .colors import (
    ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, INFO_COLOR, DETAIL_COLOR,
    UPDATE_COLOR, DEBUG_COLOR, HEADER_COLOR, BANNER_COLOR, FILENAME_COLOR,
    PATH_COLOR, OPTION_COLOR, KEY_COLOR, VALUE_COLOR, 
    HIGHLIGHT_STYLE, SUBTLE_STYLE, RESET_STYLE
)

logger = logging.getLogger("nvbuilder")  # Récupérer le logger configuré

class NvBuilder:
    """Orchestre la création de l'archive auto-extractible."""

    def __init__(self, config_path_str: Optional[str] = None, 
                 use_standard_exclusions: bool = False, 
                 debug_mode: bool = False):
        """
        Initialise le builder avec la configuration spécifiée.
        
        Args:
            config_path_str: Chemin vers le fichier de configuration YAML.
            use_standard_exclusions: Si True, ajoute automatiquement les exclusions standard.
            debug_mode: Active le mode debug pour des logs plus verbeux.
        """
        self.start_time = time.time()
        self.password: Optional[str] = None
        self.debug_mode = debug_mode

        # Config Loader (peut lever ConfigError)
        self.config_loader = ConfigLoader(config_path_str)
        self.config_path = self.config_loader.config_path
        self.base_dir = self.config_path.parent
        self.config = self.config_loader.load()  # Charge et valide
        self.config['_config_dir'] = self.base_dir

        # Configurer le logging APRES chargement config
        # Passer le mode debug à la configuration de logging
        if debug_mode:
            self.config['logging'] = self.config.get('logging', {})
            self.config['logging']['level'] = 'DEBUG'
        setup_logging(self.config.get('logging', {}), self.base_dir)

        if debug_mode:
            logger.info(f"{HIGHLIGHT_STYLE}--- Début du Build (Mode Debug) ---{RESET_STYLE}")
            logger.info(f"Fichier configuration : {self.config_path}")

        if use_standard_exclusions:
            self.config_loader.apply_standard_exclusions()
            self.config = self.config_loader.config  # Recharger

        self.build_version = self._generate_build_version()
        self.metadata_manager = MetadataManager(self.config, self.build_version)

    def _generate_build_version(self) -> str:
        """Génère un numéro de version de build basé sur la date et l'heure."""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _display_config_summary(self):
        """Affiche un résumé de la configuration utilisée pour le build."""
        # Définir des alias de couleurs pour une meilleure lisibilité
        
        # Extraction des informations principales
        content_dir = self.config.get('content', './content')
        output_path = self.config.get('output', {}).get('path', 'autoextract.sh')
        post_script = self.config.get('script', '')
        comp_method = self.config.get('compression', {}).get('method', 'gz')
        comp_level = self.config.get('compression', {}).get('level', 9)
        is_encrypted = self.config.get('compression', {}).get('encrypted', False)
        encryption_tool = self.config.get('compression', {}).get('encryption_tool', 'openssl')
        update_enabled = self.config.get('update', {}).get('enabled', False)
        update_mode = self.config.get('update', {}).get('mode', DEFAULT_UPDATE_MODE)
        update_url = self.config.get('update', {}).get('version_url', '')
        hooks_pre = self.config.get('hooks', {}).get('pre_build', [])
        hooks_post = self.config.get('hooks', {}).get('post_build', [])
        exclude_patterns = self.config.get('exclude', {}).get('patterns', [])
        
        # Afficher la bannière de résumé de configuration
        print(f"{INFO_COLOR}{HIGHLIGHT_STYLE}RÉSUMÉ DE LA CONFIGURATION{RESET_STYLE}")
        print(f"{INFO_COLOR}{HIGHLIGHT_STYLE}-----------------------{RESET_STYLE}")
        
        # Paramètres généraux
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Paramètres généraux:{RESET_STYLE}")
        print(f"  {HIGHLIGHT_STYLE}• Source:{RESET_STYLE}           {DETAIL_COLOR}{content_dir}{RESET_STYLE}")
        print(f"  {HIGHLIGHT_STYLE}• Destination:{RESET_STYLE}      {DETAIL_COLOR}{output_path}{RESET_STYLE}")
        if post_script:
            print(f"  {HIGHLIGHT_STYLE}• Script post-ext:{RESET_STYLE}  {DETAIL_COLOR}{post_script}{RESET_STYLE}")
        else:
            print(f"  {HIGHLIGHT_STYLE}• Script post-ext:{RESET_STYLE}  {SUBTLE_STYLE}Aucun{RESET_STYLE}")
        
        # Afficher si les droits root sont requis
        need_root = self.config.get('output', {}).get('need_root', False)
        print(f"  {HIGHLIGHT_STYLE}• Droits root:{RESET_STYLE}      {SUCCESS_COLOR}Requis{RESET_STYLE}" if need_root else f"  {HIGHLIGHT_STYLE}• Droits root:{RESET_STYLE}  {WARNING_COLOR}Non requis{RESET_STYLE}")
        
        # Compression et chiffrement
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Compression et sécurité:{RESET_STYLE}")
        comp_display = f"{comp_method}" if comp_method == 'none' else f"{comp_method} (niveau {comp_level})"
        print(f"  {HIGHLIGHT_STYLE}• Compression:{RESET_STYLE}   {DETAIL_COLOR}{comp_display}{RESET_STYLE}")
        
        if is_encrypted:
            print(f"  {HIGHLIGHT_STYLE}• Chiffrement:{RESET_STYLE}   {SUCCESS_COLOR}Activé{RESET_STYLE} ({encryption_tool})")
        else:
            print(f"  {HIGHLIGHT_STYLE}• Chiffrement:{RESET_STYLE}   {WARNING_COLOR}Désactivé{RESET_STYLE}")
        
        # Mise à jour
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Mise à jour:{RESET_STYLE}")
        if update_enabled:
            print(f"  {HIGHLIGHT_STYLE}• Statut:{RESET_STYLE}        {SUCCESS_COLOR}Activée{RESET_STYLE}")
            print(f"  {HIGHLIGHT_STYLE}• Mode:{RESET_STYLE}          {DETAIL_COLOR}{update_mode}{RESET_STYLE}")
            print(f"  {HIGHLIGHT_STYLE}• URL version:{RESET_STYLE}   {DETAIL_COLOR}{update_url}{RESET_STYLE}")
        else:
            print(f"  {HIGHLIGHT_STYLE}• Statut:{RESET_STYLE}        {WARNING_COLOR}Désactivée{RESET_STYLE}")
        
        # Hooks
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Hooks:{RESET_STYLE}")
        if hooks_pre or hooks_post:
            if hooks_pre:
                print(f"  {HIGHLIGHT_STYLE}• Pre-build:{RESET_STYLE}    {SUCCESS_COLOR}{len(hooks_pre)} hook(s){RESET_STYLE}")
            if hooks_post:
                print(f"  {HIGHLIGHT_STYLE}• Post-build:{RESET_STYLE}   {SUCCESS_COLOR}{len(hooks_post)} hook(s){RESET_STYLE}")
        else:
            print(f"  {HIGHLIGHT_STYLE}• Hooks:{RESET_STYLE}        {SUBTLE_STYLE}Aucun{RESET_STYLE}")
        
        # Exclusions
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Exclusions:{RESET_STYLE}")
        exclude_count = len(exclude_patterns)
        if exclude_count > 0:
            print(f"  {HIGHLIGHT_STYLE}• Motifs:{RESET_STYLE}       {SUCCESS_COLOR}{exclude_count} exclusion(s){RESET_STYLE}")
            if self.debug_mode or exclude_count <= 5:
                # Montrer toutes les exclusions en mode debug ou s'il y en a peu
                for pattern in exclude_patterns[:5]:
                    print(f"    {DETAIL_COLOR}∙ {pattern}{RESET_STYLE}")
                if exclude_count > 5:
                    print(f"    {SUBTLE_STYLE}... et {exclude_count - 5} autres{RESET_STYLE}")
        else:
            print(f"  {HIGHLIGHT_STYLE}• Motifs:{RESET_STYLE}       {SUBTLE_STYLE}Aucun{RESET_STYLE}")
        
        # Information sur la génération
        print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Informations de build:{RESET_STYLE}")
        print(f"  {HIGHLIGHT_STYLE}• Version:{RESET_STYLE}      {DETAIL_COLOR}NvBuilder v{VERSION}{RESET_STYLE}")
        print(f"  {HIGHLIGHT_STYLE}• Build ID:{RESET_STYLE}     {DETAIL_COLOR}{self.build_version}{RESET_STYLE}")
        print(f"  {HIGHLIGHT_STYLE}• Plateforme:{RESET_STYLE}   {DETAIL_COLOR}{platform.system()} {platform.release()}{RESET_STYLE}")
        
    def _get_encryption_password(self) -> bool:
        """
        Demande et valide le mot de passe de chiffrement si nécessaire.
        
        Returns:
            bool: True si la saisie a réussi, False sinon
        """
        if not self.metadata_manager.get('encryption_enabled'):
            if self.debug_mode:
                logger.info("Chiffrement: Désactivé")
            return True

        if self.debug_mode:
            logger.info("Chiffrement: Activé")
        
        try:
            while True:
                # Utiliser sys.stdout.write pour contrôle fin + flush
                print(f"\n{INFO_COLOR}{HIGHLIGHT_STYLE}Cryptage de l'archive{RESET_STYLE}")
                sys.stdout.write(f"   • Entrez le mot de passe pour le chiffrement : {RESET_STYLE}")
                sys.stdout.flush()
                pwd1 = getpass.getpass(prompt='')  # Prompt vide car déjà affiché
                if not pwd1:
                    print(f"{WARNING_COLOR}Mot de passe vide interdit.{RESET_STYLE}")
                    continue
                    
                sys.stdout.write(f"   • Confirmez le mot de passe : {RESET_STYLE}")
                sys.stdout.flush()
                pwd2 = getpass.getpass(prompt='')
                
                if pwd1 == pwd2:
                    self.password = pwd1
                    return True
                else:
                    print(f"{ERROR_COLOR}Mots de passe différents. Réessayez.{RESET_STYLE}")
        except EOFError:
            logger.error("Lecture mdp impossible (non interactif?).")
            return False
        except KeyboardInterrupt:
            print("\nSaisie mdp annulée.")
            return False
        except Exception as e:
            logger.error(f"Erreur saisie mdp: {e}", exc_info=True)
            return False

    def _run_hooks(self, hook_type: str):
        """
        Exécute les hooks configurés (pre_build ou post_build).
        
        Args:
            hook_type: Type de hook à exécuter ('pre_build' ou 'post_build')
            
        Raises:
            NvBuilderError: Si l'exécution d'un hook échoue
        """
        hooks = self.config.get('hooks', {}).get(hook_type, [])
        if not hooks:
            return
            
        if self.debug_mode:
            logger.info(f"{HIGHLIGHT_STYLE}--- Exécution Hooks '{hook_type}' ---{RESET_STYLE}")
        
        import subprocess
        success = True
        
        for cmd in hooks:
            try:
                if self.debug_mode:
                    logger.info(f"  • Exécution: {cmd}")
                
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, 
                                        text=True, encoding='utf-8', cwd=self.base_dir)
                                        
                if self.debug_mode:
                    if result.stdout:
                        logger.debug(f"Hook stdout:\n{result.stdout.strip()}")
                    if result.stderr:
                        logger.warning(f"{WARNING_COLOR}Hook stderr:\n{result.stderr.strip()}{RESET_STYLE}")
                    
            except FileNotFoundError:
                logger.error(f"{ERROR_COLOR}Hook Erreur: Commande '{cmd.split()[0]}' non trouvée.{RESET_STYLE}")
                success = False
            except subprocess.CalledProcessError as e:
                logger.error(f"{ERROR_COLOR}Hook Échec (code {e.returncode}): {cmd}{RESET_STYLE}")
                if e.stdout:
                    logger.error(f"Hook stdout:\n{e.stdout.strip()}")
                if e.stderr:
                    logger.error(f"Hook stderr:\n{e.stderr.strip()}")
                success = False
            except Exception as e:
                logger.error(f"{ERROR_COLOR}Hook Erreur '{cmd}': {e}{RESET_STYLE}")
                success = False
                
        if self.debug_mode:
            status = f"{SUCCESS_COLOR}OK" if success else f"{ERROR_COLOR}ÉCHEC"
            logger.info(f"{HIGHLIGHT_STYLE}--- Fin Hooks '{hook_type}' ({status}{RESET_STYLE}{HIGHLIGHT_STYLE}) ---{RESET_STYLE}")
        
        if not success:
            raise NvBuilderError(f"Échec lors de l'exécution des hooks {hook_type}.")

    def build(self) -> Optional[Path]:
        """
        Orchestre le processus de build complet.
        
        Returns:
            Path: Chemin vers le script généré si succès, None sinon
        """
        output_script_path: Optional[Path] = None
        archiver: Optional[Archiver] = None
        
        try:
            # Afficher un résumé de la configuration avant de commencer
            self._display_config_summary()
            
            # Afficher les informations de base en mode debug
            if self.debug_mode:
                logger.info(f"Source contenu   : {self.config.get('content')}")
                logger.info(f"Script sortie    : {self.config.get('output',{}).get('path')}")
                logger.info(f"Script post-exec : {self.config.get('script') or 'Aucun'}")

            # Obtenir le mot de passe si nécessaire
            if not self._get_encryption_password():
                raise NvBuilderError("Mot de passe requis/annulé.")

            # Hooks pré-build
            self._run_hooks('pre_build')

            # Mise à jour du mode de mise à jour dans les métadonnées
            if self.metadata_manager.get('update_enabled'):                
                update_mode = self.config.get('update', {}).get('mode', DEFAULT_UPDATE_MODE)
                self.metadata_manager.update('update_mode', update_mode)
                if self.debug_mode:
                    logger.info(f"Mode de mise à jour défini : {update_mode}")

            # Étape 1: Créer l'archive
            if self.debug_mode:
                logger.info(f"{HIGHLIGHT_STYLE}--- Étape 1: Création Archive ---{RESET_STYLE}")
            
            archiver = Archiver(self.config, self.metadata_manager)
            archive_path, basename, ext, tar_flag = archiver.create()
            archive_original_filename = basename + ext
            path_to_embed = archive_path
            token_b64 = None
            token_params = None

            # Étape 2: Chiffrer l'archive si demandé
            if self.metadata_manager.get('encryption_enabled'):
                if self.debug_mode:
                    logger.info(f"{HIGHLIGHT_STYLE}--- Étape 2: Chiffrement ---{RESET_STYLE}")
                
                encryptor = Encryptor(self.config)
                try:
                    # Chiffrer l'archive
                    encrypted_archive_path = encryptor.encrypt(archive_path, self.password)
                    path_to_embed = encrypted_archive_path
                    enc_checksum = calculate_checksum(encrypted_archive_path)
                    self.metadata_manager.update('encrypted_archive_checksum_sha256', enc_checksum)
                    self.metadata_manager.update('encrypted_archive_path', str(encrypted_archive_path))
                    
                    if self.debug_mode:
                        logger.debug(f"Suppression archive non chiffrée: {archive_path}")
                    archive_path.unlink(missing_ok=True)

                    # Chiffrer le jeton de vérification
                    if self.debug_mode:
                        logger.info("Chiffrement du jeton de vérification...")
                    
                    token_b64 = encrypt_string_to_base64(
                        plaintext=PASSWORD_CHECK_TOKEN, 
                        password=self.password,
                        tool=encryptor.tool, 
                        cipher=encryptor.cipher, 
                        iterations=encryptor.iterations,
                        gpg_cipher=encryptor.gpg_cipher, 
                        gpg_s2k=encryptor.gpg_s2k
                    )
                    
                    if not token_b64:
                        raise NvBuilderError("Échec chiffrement jeton.")
                        
                    self.metadata_manager.update('password_check_token_b64', token_b64)
                    
                    # Enregistrer les paramètres utilisés pour le chiffrement du jeton
                    token_params = {"tool": encryptor.tool}
                    if encryptor.tool == "openssl":
                        token_params.update({"cipher": encryptor.cipher, "iter": encryptor.iterations})
                    elif encryptor.tool == "gpg":
                        token_params.update({"cipher": encryptor.gpg_cipher, "s2k_options": encryptor.gpg_s2k})
                        
                    self.metadata_manager.update('token_encryption_params', token_params)

                except (EncryptionError, ToolNotFoundError) as e:
                    raise NvBuilderError(f"Échec chiffrement: {e}") from e

            # Étape 3: Préparer les snippets Bash
            if self.debug_mode:
                logger.info(f"{HIGHLIGHT_STYLE}--- Étape 3: Préparation Script Bash ---{RESET_STYLE}")
            
            metadata_dict = self.metadata_manager.get_all()
            
            # Générer uniquement les snippets de chiffrement
            encryption_snippets = generate_encryption_snippets(self.config, metadata_dict, archive_original_filename)
            
            # Initialiser snippets comme un dictionnaire vide car nous n'avons plus besoin des snippets de mise à jour
            bash_snippets = encryption_snippets

            # Étape 4: Générer le script final
            if self.debug_mode:
                logger.info(f"{HIGHLIGHT_STYLE}--- Étape 4: Génération Script Final ---{RESET_STYLE}")
            
            script_generator = ScriptGenerator(self.config, metadata_dict)
            tar_command_flags = "x" + tar_flag + "f"
            output_script_path = script_generator.generate(path_to_embed, archive_original_filename, tar_command_flags, bash_snippets)

            # Étape 5: Finalisation (Hash, Fichiers annexes)
            if self.debug_mode:
                logger.info(f"{HIGHLIGHT_STYLE}--- Étape 5: Finalisation (Hash, Fichiers Annexes) ---{RESET_STYLE}")
            
            script_hash = calculate_checksum(output_script_path)
            self.metadata_manager.update('script_checksum_sha256', script_hash)
            
            if self.debug_mode:
                logger.info(f"Hash SHA256 du script '{output_script_path.name}': {script_hash[:12]}...")

            # Écrire les fichiers de métadonnées
            self.metadata_manager.write_metadata_file(output_script_path)
            self.metadata_manager.write_version_file()

            # Hooks post-build
            self._run_hooks('post_build')

            # Afficher les informations de fin
            if self.debug_mode:
                end_time = time.time()
                duration = end_time - self.start_time
                final_size_mb = output_script_path.stat().st_size / (1024 * 1024)
                logger.info(f"{SUCCESS_COLOR}{HIGHLIGHT_STYLE}--- Build Terminé (Mode Debug) ---{RESET_STYLE}")
                logger.info(f"Durée du build: {duration:.2f}s")
                logger.info(f"Script généré : {output_script_path} ({final_size_mb:.2f} Mo)")
                
                if self.metadata_manager.get('update_enabled'):
                    update_mode = self.metadata_manager.get('update_mode', 'check-only')
                    logger.info(f"Mode de mise à jour : {update_mode}")
            
            return output_script_path

        except NvBuilderError as e:
            # Erreur attendue (avec message explicite)
            if self.debug_mode:
                logger.error(f"{ERROR_COLOR}{HIGHLIGHT_STYLE}--- Échec du Build ---{RESET_STYLE}")
                logger.error(f"{ERROR_COLOR}Erreur: {e}{RESET_STYLE}")
            else:
                print(f"{ERROR_COLOR}Échec du Build: {e}{RESET_STYLE}", file=sys.stderr)
            return None
        except Exception as e:
            # Erreur inattendue (avec traceback complet)
            if self.debug_mode:
                logger.error(f"{ERROR_COLOR}{HIGHLIGHT_STYLE}--- Échec du Build (Erreur Inattendue) ---{RESET_STYLE}")
                logger.error(f"{ERROR_COLOR}Erreur: {e}{RESET_STYLE}")
                logger.critical("Traceback:", exc_info=True)
            else:
                print(f"{ERROR_COLOR}Erreur inattendue lors du build.{RESET_STYLE}", file=sys.stderr)
            return None
        finally:
            # Nettoyage final
            if archiver:
                archiver.cleanup()
            # Effacer le mot de passe de la mémoire
            if self.password:
                try:
                    self.password = '*' * len(self.password)
                    del self.password
                    self.password = None
                except:
                    pass