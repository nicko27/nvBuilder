#!/usr/bin/env python3
import os
import sys
import tarfile
import tempfile
import argparse
import datetime
import shutil
import yaml
import logging
import hashlib
import json
import fnmatch
import stat
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class Metadata:
    def __init__(self):
        self.data = {
            "version": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "created_at": datetime.datetime.now().isoformat(),
            "files": [],
            "total_size": 0,
            "checksum": "",
            "excluded_files": [],
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "architecture": sys.getfilesystemencoding()
            }
        }

    def add_file(self, file_path: str, size: int, checksum: str):
        self.data["files"].append({
            "path": file_path,
            "size": size,
            "checksum": checksum
        })
        self.data["total_size"] += size

    def add_excluded_file(self, file_path: str):
        self.data["excluded_files"].append(file_path)

    def set_archive_checksum(self, checksum: str):
        self.data["checksum"] = checksum

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Metadata':
        metadata = cls()
        metadata.data = json.loads(json_str)
        return metadata

class FileFilter:
    def __init__(self, patterns: List[str], ignore_case: bool = True):
        self.patterns = patterns
        self.ignore_case = ignore_case

    def should_exclude(self, file_path: str) -> bool:
        if self.ignore_case:
            file_path = file_path.lower()
        return any(fnmatch.fnmatch(file_path, pattern.lower() if self.ignore_case else pattern) 
                  for pattern in self.patterns)

class MessageFormatter:
    TAG_SIZE = 8
    
    @staticmethod
    def format_message(text_tag: str, message: str, info_sup: str = "") -> str:
        nbspace = (MessageFormatter.TAG_SIZE - len(text_tag)) // 2
        left = " " * nbspace
        right = left
        if (nbspace * 2 + len(text_tag)) != MessageFormatter.TAG_SIZE:
            right += " "
        
        tag = f"[{left}{text_tag}{right}]"
        return f"{tag} {message} {info_sup}"

    @staticmethod
    def show_message(text_tag: str, message: str, info_sup: str = ""):
        print(MessageFormatter.format_message(text_tag, message, info_sup))

    @staticmethod
    def show_success(message: str):
        MessageFormatter.show_message("OK", message)

    @staticmethod
    def show_error(message: str):
        MessageFormatter.show_message("ERREUR", message)

    @staticmethod
    def show_info(message: str, info_sup: str = ""):
        MessageFormatter.show_message("INFO", message, info_sup)

    @staticmethod
    def show_action(message: str):
        MessageFormatter.show_message("ACTION", message)

class NvBuilder:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.metadata = Metadata()
        self.temp_dir = None
        self.script_name = os.path.basename(self.config['output'])
        self.file_filter = FileFilter(
            self.config.get('exclude', {}).get('patterns', []),
            self.config.get('exclude', {}).get('ignore_case', True)
        )
        self.setup_logging()
        self.validate_config()

    def load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            MessageFormatter.show_error(f"Fichier de configuration {config_path} non trouvé")
            sys.exit(1)
        return config

    def setup_logging(self):
        log_config = self.config['logging']
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_config['file']),
                logging.StreamHandler()
            ]
        )

    def validate_config(self):
        if not os.path.exists(self.config['content']):
            raise ValueError(f"Le dossier {self.config['content']} n'existe pas")
        
        if self.config['script'] and not os.path.exists(os.path.join(self.config['content'], self.config['script'])):
            raise ValueError(f"Le script {self.config['script']} n'existe pas dans le dossier {self.config['content']}")
        
        if self.config['update']['enabled']:
            if not self.config['update']['version_url'] or not self.config['update']['autoupdate_url']:
                raise ValueError("La mise à jour automatique nécessite version_url et autoupdate_url")

    def create_temp_dir(self):
        if self.config['logging']['debug']:
            self.temp_dir = tempfile.mkdtemp(prefix=f"{self.script_name}.", dir=os.getcwd())
        else:
            self.temp_dir = tempfile.mkdtemp(prefix=f"{self.script_name}.")

    def create_version_file(self):
        if self.config['update']['version_file']:
            with open(self.config['update']['version_file'], 'w') as f:
                f.write(self.metadata.data['version'])

    def calculate_checksum(self, file_path: str, algorithm: str = 'sha256') -> str:
        try:
            hash_func = getattr(hashlib, algorithm)
            with open(file_path, 'rb') as f:
                return hash_func(f.read()).hexdigest()
        except FileNotFoundError:
            raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
        except PermissionError:
            raise PermissionError(f"Permission refusée pour accéder à {file_path}")
        except Exception as e:
            raise Exception(f"Erreur lors du calcul du checksum: {str(e)}")

    def should_include_file(self, file_path: str) -> bool:
        return not self.file_filter.should_exclude(file_path)

    def create_archive(self):
        MessageFormatter.show_action("Compression des fichiers")
        archive_path = os.path.join(self.temp_dir, "include.tar.gz")
        
        with tarfile.open(archive_path, "w:gz") as tar:
            for root, _, files in os.walk(self.config['content']):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.config['content'])
                    
                    if self.should_include_file(arcname):
                        tar.add(file_path, arcname=arcname)
                        
                        # Ajout des métadonnées du fichier
                        size = os.path.getsize(file_path)
                        checksum = self.calculate_checksum(file_path, self.config['integrity']['checksum'])
                        self.metadata.add_file(arcname, size, checksum)
                    else:
                        self.metadata.add_excluded_file(arcname)
                        MessageFormatter.show_info(f"Fichier exclu: {arcname}")

        # Calcul du checksum de l'archive
        archive_checksum = self.calculate_checksum(archive_path, self.config['integrity']['checksum'])
        self.metadata.set_archive_checksum(archive_checksum)

    def create_extractor_script(self):
        script_content = f"""#!/usr/bin/env python3
import os
import sys
import tarfile
import tempfile
import argparse
import subprocess
import hashlib
import json
import fnmatch
import shutil
import stat
import re
from pathlib import Path
from typing import Optional

# Codes ANSI pour la coloration
ANSI_RESET = "\\033[0m"
ANSI_BOLD = "\\033[1m"
ANSI_DIM = "\\033[2m"
ANSI_RED = "\\033[31m"
ANSI_GREEN = "\\033[32m"
ANSI_YELLOW = "\\033[33m"
ANSI_BLUE = "\\033[34m"
ANSI_MAGENTA = "\\033[35m"
ANSI_CYAN = "\\033[36m"

# Constantes
MAX_METADATA_SIZE = 8192  # Taille maximale des métadonnées en octets
CHUNK_SIZE = 8192  # Taille des chunks pour la lecture des fichiers
DOWNLOAD_TIMEOUT = 30  # Timeout pour les téléchargements en secondes

def is_safe_path(base_path: Path, path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(base_path.resolve())
    except Exception:
        return False

def safe_join_paths(base_path: Path, *paths: str) -> Optional[Path]:
    try:
        result = base_path
        for path in paths:
            result = result / path
        return result if is_safe_path(base_path, result) else None
    except Exception:
        return None

def calculate_checksum(file_path: str, algorithm: str = 'sha256') -> str:
    try:
        hash_func = getattr(hashlib, algorithm)
        with open(file_path, 'rb') as f:
            hasher = hash_func()
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
            return hasher.hexdigest()
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
    except PermissionError:
        raise PermissionError(f"Permission refusée pour accéder à {file_path}")
    except Exception as e:
        raise Exception(f"Erreur lors du calcul du checksum: {str(e)}")

def verify_checksum(file_path: str, expected_checksum: str, algorithm: str = 'sha256') -> bool:
    try:
        return calculate_checksum(file_path, algorithm) == expected_checksum
    except Exception as e:
        print_error(f"Erreur lors de la vérification du checksum: {str(e)}")
        return False

def download_file(url: str, dest_path: Path, timeout: int = DOWNLOAD_TIMEOUT) -> bool:
    try:
        import urllib.request
        import urllib.error
        import socket
        
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                print_error(f"Erreur HTTP: {response.status}")
                return False
                
            with open(dest_path, 'wb') as f:
                while chunk := response.read(CHUNK_SIZE):
                    f.write(chunk)
        return True
    except urllib.error.URLError as e:
        print_error(f"Erreur URL: {str(e)}")
        return False
    except socket.timeout:
        print_error("Délai d'attente dépassé")
        return False
    except Exception as e:
        print_error(f"Erreur lors du téléchargement: {str(e)}")
        return False

def print_boxed(title: str, content: str = "", color: str = ANSI_BLUE):
    width = 80
    print(f"{color}{'=' * width}{ANSI_RESET}")
    print(f"{color}{ANSI_BOLD}{title.center(width)}{ANSI_RESET}")
    if content:
        print(f"{color}{'-' * width}{ANSI_RESET}")
        print(f"{content.center(width)}")
    print(f"{color}{'=' * width}{ANSI_RESET}")

def print_message(tag: str, message: str, info_sup: str = "", color: str = ANSI_BLUE):
    tag_width = 8
    tag = tag.center(tag_width)
    print(f"{color}[{tag}]{ANSI_RESET} {message} {ANSI_DIM}{info_sup}{ANSI_RESET}")

def print_success(message: str):
    print_message("OK", message, color=ANSI_GREEN)

def print_error(message: str):
    print_message("ERREUR", message, color=ANSI_RED)

def print_info(message: str, info_sup: str = ""):
    print_message("INFO", message, info_sup, color=ANSI_BLUE)

def print_action(message: str):
    print_message("ACTION", message, color=ANSI_MAGENTA)

def print_warning(message: str):
    print_message("ATTENTION", message, color=ANSI_YELLOW)

def print_progress(current: int, total: int, message: str = ""):
    width = 40
    progress = int((current / total) * width)
    bar = "█" * progress + "░" * (width - progress)
    percentage = int((current / total) * 100)
    print(f"{ANSI_CYAN}[{bar}] {percentage:3d}%{ANSI_RESET} {message}")

def check_for_updates(version_url: str, current_version: str) -> tuple[bool, str]:
    try:
        import urllib.request
        import urllib.error
        import socket
        
        try:
            response = urllib.request.urlopen(version_url, timeout=10)
            remote_version = response.read().decode().strip()
            
            if not remote_version:
                return False, "Version distante vide"
                
            try:
                return int(remote_version) > int(current_version), remote_version
            except ValueError:
                return False, "Format de version invalide"
                
        except urllib.error.URLError as e:
            return False, f"Erreur URL: {str(e)}"
        except socket.timeout:
            return False, "Délai d'attente dépassé"
            
    except Exception as e:
        return False, f"Erreur inattendue: {str(e)}"

def ensure_extract_dir(extract_dir: Path) -> None:
    if extract_dir.exists():
        try:
            shutil.rmtree(extract_dir)
        except Exception as e:
            print_error(f"Impossible de nettoyer le répertoire existant: {str(e)}")
            sys.exit(1)
    try:
        extract_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print_error(f"Impossible de créer le répertoire d'extraction: {str(e)}")
        sys.exit(1)

def read_metadata(archive_data: bytes) -> tuple[dict, int]:
    try:
        archive_start = archive_data.find(b"__ARCHIVE_BELOW__") + len(b"__ARCHIVE_BELOW__")
        metadata_end = archive_data.find(b"\\n", archive_start)
        if metadata_end == -1:
            raise ValueError("Format de métadonnées invalide")
            
        metadata_json = archive_data[archive_start:metadata_end].decode().strip()
        metadata = json.loads(metadata_json)
        return metadata, metadata_end + 1
    except Exception as e:
        raise ValueError(f"Erreur lors de la lecture des métadonnées: {str(e)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-update", action="store_true", help="Désactive la mise à jour automatique")
    parser.add_argument("--debug", action="store_true", help="Active le mode debug")
    parser.add_argument("--extract-only", action="store_true", help="Extrait uniquement les fichiers")
    parser.add_argument("--no-verify", action="store_true", help="Désactive la vérification d'intégrité")
    parser.add_argument("--list-excluded", action="store_true", help="Affiche la liste des fichiers exclus")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    current_dir = script_path.parent
    script_name = script_path.name

    # Extraction des métadonnées
    try:
        with open(__file__, 'rb') as f:
            archive_data = f.read()
        metadata, archive_start = read_metadata(archive_data)
    except Exception as e:
        print_error(f"Erreur lors de la lecture des métadonnées: {str(e)}")
        sys.exit(1)

    print_boxed("NvBuilder Auto-Extracteur", f"Version {metadata['version']}")

    # Création du répertoire temporaire
    if args.debug or args.extract_only:
        extract_dir = current_dir / f"{script_name}.extract"
    else:
        extract_dir = Path(tempfile.mkdtemp(prefix=f"{script_name}."))
    
    ensure_extract_dir(extract_dir)

    # Vérification de la version si nécessaire
    if not args.no_update and "{self.config['update']['enabled']}":
        print_action("Vérification de la version distante")
        try:
            has_update, remote_version = check_for_updates("{self.config['update']['version_url']}", metadata['version'])
            if has_update:
                print_warning(f"Une nouvelle version est disponible : {remote_version}")
                print_action("Téléchargement de la nouvelle version")
                new_script_path = current_dir / script_name
                if download_file("{self.config['update']['autoupdate_url']}", new_script_path):
                    # Permissions plus restrictives : rwxr-xr-x
                    os.chmod(new_script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    print_success("Mise à jour téléchargée avec succès")
                    print_action("Redémarrage avec la nouvelle version")
                    os.execv(sys.executable, [sys.executable, str(new_script_path)] + sys.argv[1:])
            else:
                print_success("Vous utilisez la dernière version")
        except Exception as e:
            print_error(f"Impossible de vérifier la version: {str(e)}")

    # Affichage des fichiers exclus si demandé
    if args.list_excluded and metadata.get("excluded_files"):
        print_boxed("Fichiers Exclus", color=ANSI_YELLOW)
        for file in metadata["excluded_files"]:
            print_info(f"- {file}")
        if not args.extract_only:
            sys.exit(0)

    # Vérification de l'intégrité si activée
    if not args.no_verify and "{self.config['integrity']['verify']}":
        print_action("Vérification de l'intégrité")
        try:
            archive_checksum = calculate_checksum(archive_data[archive_start:], "{self.config['integrity']['checksum']}")
            if archive_checksum != metadata["checksum"]:
                print_error("L'intégrité de l'archive est compromise")
                sys.exit(1)
            print_success("Vérification de l'intégrité réussie")
        except Exception as e:
            print_error(f"Erreur lors de la vérification de l'intégrité: {str(e)}")
            sys.exit(1)

    # Extraction des fichiers
    print_action("Décompression des fichiers")
    try:
        with tarfile.open(fileobj=archive_data[archive_start:], mode="r:gz") as tar:
            members = tar.getmembers()
            total = len(members)
            for i, member in enumerate(members, 1):
                try:
                    # Vérification de sécurité du chemin
                    if not is_safe_path(extract_dir, Path(member.name)):
                        print_warning(f"Chemin non sécurisé ignoré: {member.name}")
                        continue
                        
                    tar.extract(member, path=extract_dir)
                    print_progress(i, total, f"Extraction de {member.name}")
                except Exception as e:
                    print_error(f"Erreur lors de l'extraction de {member.name}: {str(e)}")
                    sys.exit(1)
    except Exception as e:
        print_error(f"Erreur lors de l'ouverture de l'archive: {str(e)}")
        sys.exit(1)

    # Vérification des fichiers extraits
    if not args.no_verify and "{self.config['integrity']['verify']}":
        print_action("Vérification des fichiers extraits")
        total = len(metadata["files"])
        for i, file_info in enumerate(metadata["files"], 1):
            file_path = safe_join_paths(extract_dir, file_info["path"])
            if not file_path:
                print_warning(f"Chemin non sécurisé ignoré: {file_info['path']}")
                continue
                
            if not verify_checksum(str(file_path), file_info["checksum"], "{self.config['integrity']['checksum']}"):
                print_error(f"L'intégrité du fichier {file_info['path']} est compromise")
                sys.exit(1)
            print_progress(i, total, f"Vérification de {file_info['path']}")
        print_success("Vérification des fichiers réussie")

    # Exécution du script si nécessaire
    if not args.extract_only and "{self.config['script']}":
        print_action(f"Lancement de {self.config['script']}")
        script_path = safe_join_paths(extract_dir, "{self.config['script']}")
        if script_path and script_path.exists():
            try:
                os.chdir(extract_dir)
                subprocess.run([sys.executable, str(script_path)], check=True)
            except subprocess.CalledProcessError as e:
                print_error(f"Erreur lors de l'exécution du script: {str(e)}")
                sys.exit(1)
            except Exception as e:
                print_error(f"Erreur inattendue lors de l'exécution du script: {str(e)}")
                sys.exit(1)

    if args.extract_only:
        print_info("Les fichiers sont dans", str(extract_dir))

    # Nettoyage si activé
    if "{self.config['output']['cleanup']}" and not args.debug and not args.extract_only:
        print_action("Nettoyage des fichiers temporaires")
        try:
            shutil.rmtree(extract_dir)
        except Exception as e:
            print_warning(f"Impossible de nettoyer les fichiers temporaires: {str(e)}")

    print_boxed("Extraction Terminée", "Tous les fichiers ont été extraits avec succès", color=ANSI_GREEN)

if __name__ == "__main__":
    main() 