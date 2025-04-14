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
from .constants import VERSION, PASSWORD_CHECK_TOKEN, DEFAULT_OPENSSL_CIPHER, DEFAULT_OPENSSL_ITER, DEFAULT_GPG_CIPHER_ALGO, DEFAULT_GPG_S2K_OPTIONS

# Gestion de colorama avec fallback
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

logger = logging.getLogger("nvbuilder")  # Récupérer le logger configuré

class NvBuilder:
    """Orchestre la création de l'archive auto-extractible."""

    def __init__(self, config_path_str: Optional[str] = None, use_standard_exclusions: bool = False):
        """
        Initialise le builder avec la configuration spécifiée.
        
        Args:
            config_path_str: Chemin vers le fichier de configuration YAML.
            use_standard_exclusions: Si True, ajoute automatiquement les exclusions standard.
        """
        self.start_time = time.time()
        self.password: Optional[str] = None

        # Config Loader (peut lever ConfigError)
        self.config_loader = ConfigLoader(config_path_str)
        self.config_path = self.config_loader.config_path
        self.base_dir = self.config_path.parent
        self.config = self.config_loader.load()  # Charge et valide
        self.config['_config_dir'] = self.base_dir

        # Configurer le logging APRES chargement config
        setup_logging(self.config.get('logging', {}), self.base_dir)

        logger.info(f"{Style.BRIGHT}--- Début du Build (NVBuilder v{VERSION}) ---{Style.RESET_ALL}")
        logger.info(f"Fichier configuration : {self.config_path}")

        if use_standard_exclusions:
            self.config_loader.apply_standard_exclusions()
            self.config = self.config_loader.config  # Recharger

        self.build_version = self._generate_build_version()
        self.metadata_manager = MetadataManager(self.config, self.build_version)

    def _generate_build_version(self) -> str:
        """Génère un numéro de version de build basé sur la date et l'heure."""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _get_encryption_password(self) -> bool:
        """
        Demande et valide le mot de passe de chiffrement si nécessaire.
        
        Returns:
            bool: True si la saisie a réussi, False sinon
        """
        if not self.metadata_manager.get('encryption_enabled'):
            logger.info("Chiffrement: Désactivé")
            return True

        logger.info("Chiffrement: Activé")
        try:
            while True:
                # Utiliser sys.stdout.write pour contrôle fin + flush
                sys.stdout.write("Entrez le mot de passe pour le chiffrement : ")
                sys.stdout.flush()
                pwd1 = getpass.getpass(prompt='')  # Prompt vide car déjà affiché
                if not pwd1:
                    print(f"{Fore.YELLOW}Mot de passe vide interdit.{Style.RESET_ALL}")
                    continue
                    
                sys.stdout.write("Confirmez le mot de passe : ")
                sys.stdout.flush()
                pwd2 = getpass.getpass(prompt='')
                
                if pwd1 == pwd2:
                    self.password = pwd1
                    return True
                else:
                    print(f"{Fore.RED}Mots de passe différents. Réessayez.{Style.RESET_ALL}")
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
            
        logger.info(f"{Style.BRIGHT}--- Exécution Hooks '{hook_type}' ---{Style.RESET_ALL}")
        import subprocess
        success = True
        
        for cmd in hooks:
            try:
                logger.info(f"  -> Exécution: {cmd}")
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, 
                                        text=True, encoding='utf-8', cwd=self.base_dir)
                                        
                if result.stdout:
                    logger.debug(f"Hook stdout:\n{result.stdout.strip()}")
                if result.stderr:
                    logger.warning(f"{Fore.YELLOW}Hook stderr:\n{result.stderr.strip()}{Style.RESET_ALL}")
                    
            except FileNotFoundError:
                logger.error(f"{Fore.RED}Hook Erreur: Commande '{cmd.split()[0]}' non trouvée.{Style.RESET_ALL}")
                success = False
            except subprocess.CalledProcessError as e:
                logger.error(f"{Fore.RED}Hook Échec (code {e.returncode}): {cmd}{Style.RESET_ALL}")
                if e.stdout:
                    logger.error(f"Hook stdout:\n{e.stdout.strip()}")
                if e.stderr:
                    logger.error(f"Hook stderr:\n{e.stderr.strip()}")
                success = False
            except Exception as e:
                logger.error(f"{Fore.RED}Hook Erreur '{cmd}': {e}{Style.RESET_ALL}")
                success = False
                
        status = f"{Fore.GREEN}OK" if success else f"{Fore.RED}ÉCHEC"
        logger.info(f"{Style.BRIGHT}--- Fin Hooks '{hook_type}' ({status}{Style.RESET_ALL}{Style.BRIGHT}) ---{Style.RESET_ALL}")
        
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
            # Afficher les informations de base
            logger.info(f"Source contenu   : {self.config.get('content')}")
            logger.info(f"Script sortie    : {self.config.get('output',{}).get('path')}")
            logger.info(f"Script post-exec : {self.config.get('script') or 'Aucun'}")

            # Obtenir le mot de passe si nécessaire
            if not self._get_encryption_password():
                raise NvBuilderError("Mot de passe requis/annulé.")

            # Hooks pré-build
            self._run_hooks('pre_build')

            # Étape 1: Créer l'archive
            logger.info(f"{Style.BRIGHT}--- Étape 1: Création Archive ---{Style.RESET_ALL}")
            archiver = Archiver(self.config, self.metadata_manager)
            archive_path, basename, ext, tar_flag = archiver.create()
            archive_original_filename = basename + ext
            path_to_embed = archive_path
            token_b64 = None
            token_params = None

            # Étape 2: Chiffrer l'archive si demandé
            if self.metadata_manager.get('encryption_enabled'):
                logger.info(f"{Style.BRIGHT}--- Étape 2: Chiffrement ---{Style.RESET_ALL}")
                encryptor = Encryptor(self.config)
                try:
                    # Chiffrer l'archive
                    encrypted_archive_path = encryptor.encrypt(archive_path, self.password)
                    path_to_embed = encrypted_archive_path
                    enc_checksum = calculate_checksum(encrypted_archive_path)
                    self.metadata_manager.update('encrypted_archive_checksum_sha256', enc_checksum)
                    self.metadata_manager.update('encrypted_archive_path', str(encrypted_archive_path))
                    logger.debug(f"Suppression archive non chiffrée: {archive_path}")
                    archive_path.unlink(missing_ok=True)

                    # Chiffrer le jeton de vérification
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
            logger.info(f"{Style.BRIGHT}--- Étape 3: Préparation Script Bash ---{Style.RESET_ALL}")
            metadata_dict = self.metadata_manager.get_all()
            
            # Générer les snippets de mise à jour et de chiffrement
            update_snippets = generate_update_snippets(self.config, metadata_dict)
            encryption_snippets = generate_encryption_snippets(self.config, metadata_dict, archive_original_filename)
            
            # Vérifier que le snippet de mise à jour est correctement généré
            if metadata_dict.get('update_enabled'):
                logger.debug(f"Snippet update_check_call généré: {update_snippets.get('update_check_call')}")
                # S'assurer que le snippet est défini même en cas de problème
                if not update_snippets.get('update_check_call'):
                    logger.warning("Correction: Snippet update_check_call manquant, il sera forcé")
                    update_snippets['update_check_call'] = 'if [ "$NO_UPDATE_CHECK" -eq 0 ]; then\n    check_for_updates_and_download_if_needed\nfi'
            
            # Combiner tous les snippets
            bash_snippets: BashSnippetsDict = {**update_snippets, **encryption_snippets}

            # Étape 4: Générer le script final
            logger.info(f"{Style.BRIGHT}--- Étape 4: Génération Script Final ---{Style.RESET_ALL}")
            script_generator = ScriptGenerator(self.config, metadata_dict)
            tar_command_flags = "x" + tar_flag + "f"
            output_script_path = script_generator.generate(path_to_embed, archive_original_filename, tar_command_flags, bash_snippets)

            # Étape 5: Finalisation (Hash, Fichiers annexes)
            logger.info(f"{Style.BRIGHT}--- Étape 5: Finalisation (Hash, Fichiers Annexes) ---{Style.RESET_ALL}")
            script_hash = calculate_checksum(output_script_path)
            self.metadata_manager.update('script_checksum_sha256', script_hash)
            logger.info(f"Hash SHA256 du script '{output_script_path.name}': {script_hash[:12]}...")

            # Écrire les fichiers de métadonnées
            self.metadata_manager.write_metadata_file(output_script_path)
            self.metadata_manager.write_version_file()

            # Hooks post-build
            self._run_hooks('post_build')

            # Afficher les informations de fin
            end_time = time.time()
            duration = end_time - self.start_time
            final_size_mb = output_script_path.stat().st_size / (1024 * 1024)
            logger.info(f"{Fore.GREEN}{Style.BRIGHT}--- Build Terminé: SUCCÈS (Durée: {duration:.2f}s) ---{Style.RESET_ALL}")
            logger.info(f"Script généré : {output_script_path} ({final_size_mb:.2f} Mo)")
            
            return output_script_path

        except NvBuilderError as e:
            # Erreur attendue (avec message explicite)
            logger.error(f"{Fore.RED}{Style.BRIGHT}--- Échec du Build ---{Style.RESET_ALL}")
            logger.error(f"{Fore.RED}Erreur: {e}{Style.RESET_ALL}")
            logger.debug("Traceback:", exc_info=False)
            return None
        except Exception as e:
            # Erreur inattendue (avec traceback complet)
            logger.error(f"{Fore.RED}{Style.BRIGHT}--- Échec du Build (Erreur Inattendue) ---{Style.RESET_ALL}")
            logger.error(f"{Fore.RED}Erreur: {e}{Style.RESET_ALL}")
            logger.critical("Traceback:", exc_info=True)
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