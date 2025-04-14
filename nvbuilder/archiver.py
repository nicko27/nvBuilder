# nvbuilder/archiver.py
"""Crée l'archive tar."""

import tarfile
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import stat
import sys # Pour sys.stdout.write

from .metadata import MetadataManager
from .utils import calculate_checksum, check_exclusion, get_absolute_path
from .exceptions import ArchiveError
try: 
    from colorama import Fore, Style; 
except ImportError: 
    class DummyColorama: 
        def __getattr__(self, name): 
            return ""
    Fore = Style = DummyColorama(); Style.RESET_ALL = ""

logger = logging.getLogger("nvbuilder")

class Archiver:
    """Classe responsable de la création de l'archive tar."""

    def __init__(self, config: Dict[str, Any], metadata_manager: MetadataManager):
        self.config = config
        self.metadata = metadata_manager
        self.temp_dir_path: Optional[Path] = None

    def create(self) -> Tuple[Path, str, str, str]:
        """Crée l'archive tar compressée (ou non)."""
        content_dir_str = self.config.get('content', './content')
        config_dir = self.config.get('_config_dir', Path('.'))
        content_dir = get_absolute_path(content_dir_str, config_dir)

        if not content_dir.is_dir(): raise ArchiveError(f"Source '{content_dir}' inexistante.")
        if not any(content_dir.iterdir()):
            logger.warning(f"Source '{content_dir}' vide.")
            try: (content_dir / "README_NVBUILDER_EMPTY.txt").write_text(f"NVB Src vide {datetime.now():%F %T}\n", encoding='utf-8')
            except Exception as e: logger.error(f"Création README échouée: {e}")

        try: self.temp_dir_path = Path(tempfile.mkdtemp(prefix="nvb_archive_")); logger.debug(f"Temp archive créé: {self.temp_dir_path}")
        except Exception as e: raise ArchiveError(f"Création temp archive échouée: {e}") from e

        comp_cfg = self.config['compression']; method = comp_cfg['method'].lower(); level = comp_cfg['level']
        modes = {'gz': ('w:gz', '.tar.gz'), 'bz2': ('w:bz2', '.tar.bz2'), 'xz': ('w:xz', '.tar.xz'), 'none': ('w:', '.tar')}
        if method not in modes: method = 'gz'; logger.warning(f"Comp invalide -> 'gz'.")
        mode, ext = modes[method]; archive_basename = "content"; archive_path = self.temp_dir_path / f"{archive_basename}{ext}"
        tar_flags_map = {'gz': 'z', 'bz2': 'j', 'xz': 'J', 'none': ''}; tar_flag = tar_flags_map[method]

        details = f"méthode: {method}";
        if method != 'none':
            try: 
                level = int(level)
                assert 1 <= level <= 9
            except: 
                level = 9
                logger.warning(f"Niveau comp invalide -> 9.")
            details += f", niveau: {level}"
        logger.info(f"Création archive '{archive_path.name}' ({details})")
        sys.stdout.write("Archivage: ") # Indicateur de progression
        sys.stdout.flush()

        try:
            exclude_patterns = self.config['exclude']['patterns']; ignore_case = self.config['exclude']['ignore_case']
            tar_args = {'name': str(archive_path), 'mode': mode, 'encoding': 'utf-8', 'errorlevel': 1}
            if method in ['gz', 'bz2']: tar_args['compresslevel'] = level
            num_files, total_size, excluded_dirs, progress_count = 0, 0, set(), 0

            with tarfile.open(**tar_args) as tar:
                for root, dirs, files in os.walk(content_dir, topdown=True, onerror=lambda e: logger.warning(f"os.walk err: {e}")):
                    current_path = Path(root); rel_root = current_path.relative_to(content_dir)
                    if any(str(p) in excluded_dirs for p in current_path.parents): dirs[:], files[:] = [], []; continue
                    orig_dirs = list(dirs); dirs[:] = []
                    for d in orig_dirs: 
                        d_abs, d_rel = current_path/d, (rel_root/d).as_posix()
                        if check_exclusion(d_rel+'/', exclude_patterns, ignore_case): 
                            self.metadata.add_excluded_file({'path':d_rel+'/', 'reason':'Pattern'})
                            excluded_dirs.add(str(d_abs))
                        else: dirs.append(d)
                    for f in files:
                        f_abs, f_rel = current_path/f, (rel_root/f).as_posix()
                        if check_exclusion(f_rel, exclude_patterns, ignore_case): self.metadata.add_excluded_file({'path':f_rel, 'reason':'Pattern'}); continue
                        try:
                            f_stat = f_abs.lstat(); is_link = stat.S_ISLNK(f_stat.st_mode)
                            tar.add(f_abs, arcname=f_rel, recursive=False)
                            f_size = f_stat.st_size; f_sum = "symlink" if is_link else (calculate_checksum(f_abs) if f_size > 0 else "empty_file")
                            self.metadata.add_included_file({'path': f_rel, 'size': f_size, 'checksum_sha256': f_sum, 'mtime': f_stat.st_mtime, 'is_link': is_link})
                            num_files += 1; total_size += f_size
                            # Afficher un point tous les 50 fichiers par exemple
                            progress_count += 1
                            if progress_count % 50 == 0: sys.stdout.write("."); sys.stdout.flush()
                        except FileNotFoundError: logger.warning(f"Disparu: '{f_rel}'")
                        except Exception as e: logger.warning(f"Ajout échoué '{f_rel}': {e}")

            sys.stdout.write(" Terminé.\n") # Fin de l'indicateur de progression
            sys.stdout.flush()

            size_mb = total_size / (1024*1024); excluded_count = len(self.metadata.get('files_excluded', []))
            logger.info(f"-> {num_files} fichiers inclus ({size_mb:.2f} Mo){f', {excluded_count} exclus' if excluded_count else '.'}")
            if excluded_count > 0: logger.debug(f"{sum(1 for i in self.metadata.get('files_excluded', []) if not i['path'].endswith('/'))} fichiers/{excluded_count - sum(1 for i in self.metadata.get('files_excluded', []) if not i['path'].endswith('/'))} dirs exclus.")

            archive_checksum = calculate_checksum(archive_path); archive_size = archive_path.stat().st_size
            self.metadata.update('archive_checksum_sha256', archive_checksum); self.metadata.update('archive_size', archive_size)
            logger.info(f"Checksum archive: {archive_checksum[:12]}..."); logger.info(f"Taille archive: {archive_size / (1024*1024):.2f} Mo")
            return archive_path, archive_basename, ext, tar_flag

        except Exception as e:
            sys.stdout.write(f"{Fore.RED} ERREUR{Style.RESET_ALL}\n") # Indiquer erreur sur la ligne de progression
            self.cleanup()
            raise ArchiveError(f"Erreur création archive tar: {e}") from e

    def cleanup(self): # Inchangé
        if self.temp_dir_path and self.temp_dir_path.exists(): logger.debug(f"Nettoyage temp archive: {self.temp_dir_path}"); shutil.rmtree(self.temp_dir_path, ignore_errors=True); self.temp_dir_path = None