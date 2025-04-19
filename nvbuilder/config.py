"""Gestion de la configuration."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import copy
import logging
import traceback
import time

from .constants import DEFAULT_CONFIG, DEFAULT_CONFIG_FILENAME, VERSION, DEFAULT_UPDATE_MODE, UPDATE_MODES
from .exceptions import ConfigError
from .utils import (get_absolute_path, get_all_standard_exclusions,
                    _get_nested, _set_nested, prompt_string, prompt_bool,
                    save_config_yaml)

# Import des couleurs sémantiques
from .colors import (
    ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, INFO_COLOR, DETAIL_COLOR,
    UPDATE_COLOR, DEBUG_COLOR, HEADER_COLOR, BANNER_COLOR, FILENAME_COLOR,
    PATH_COLOR, OPTION_COLOR, KEY_COLOR, VALUE_COLOR, 
    HIGHLIGHT_STYLE, SUBTLE_STYLE, RESET_STYLE
)

logger = logging.getLogger("nvbuilder")

class ConfigLoader:
    """Charge, valide et fournit la configuration depuis un fichier YAML."""

    def __init__(self, config_path_str: Optional[str] = None, base_dir: Optional[Path] = None, debug_mode: bool = False):
        self.cwd = Path.cwd()
        self.config_path = self._resolve_config_path(config_path_str, self.cwd)
        self.base_dir = self.config_path.parent
        self.config: Dict[str, Any] = {}
        self.debug_mode = debug_mode

    def _resolve_config_path(self, config_path_str: Optional[str], cwd: Path) -> Path:
        """Résout le chemin du fichier de configuration."""
        path_str = config_path_str or DEFAULT_CONFIG_FILENAME
        return get_absolute_path(path_str, cwd)

    def load(self) -> Dict[str, Any]:
        """Charge et valide la configuration."""
        if self.debug_mode:
            logger.debug(f"Tentative de chargement config: {self.config_path}")
        
        raw_config = {}
        if self.config_path.is_file():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f: 
                    raw_config = yaml.safe_load(f) or {}
                
                if self.debug_mode:
                    logger.info(f"Config lue: {self.config_path}")
            except yaml.YAMLError as e: 
                raise ConfigError(f"Syntaxe YAML err '{self.config_path}': {e}") from e
            except Exception as e: 
                raise ConfigError(f"Lecture '{self.config_path}' échouée: {e}") from e
        else:
            if self.debug_mode:
                logger.warning(f"Fichier config '{self.config_path}' non trouvé. Utilisation des défauts.")
            raw_config = {}
        
        self.config = self._apply_defaults(raw_config)
        self._validate_config()
        
        # Ajouter le mode debug à la configuration
        self.config['debug_mode'] = self.debug_mode
        
        # Configurer le répertoire de base
        self.config['_config_dir'] = self.base_dir
        
        if self.debug_mode:
            logger.debug("Configuration chargée et validée.")
        
        return self.config

    def _apply_defaults(self, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les valeurs par défaut en fusionnant récursivement."""
        config_with_defaults = copy.deepcopy(DEFAULT_CONFIG)

        def merge_dicts(default: Dict, loaded: Dict) -> Dict:
            """Fonction interne de fusion récursive des dictionnaires."""
            merged = default.copy() # Commencer avec une copie des défauts
            # Parcourir les clés chargées
            for key, loaded_value in loaded.items():
                default_value = merged.get(key)
                # Si la clé existe dans les deux et ce sont des dictionnaires -> fusion récursive
                if isinstance(loaded_value, dict) and isinstance(default_value, dict):
                    merged[key] = merge_dicts(default_value, loaded_value)
                # Sinon (clé nouvelle, ou pas des dictionnaires) -> remplacer par la valeur chargée
                else:
                    merged[key] = loaded_value
            return merged

        # Appeler la fonction de fusion récursive
        final_config = merge_dicts(config_with_defaults, raw_config)
        return final_config

    def _validate_config(self):
        """Valide la configuration chargée."""
        # Vérification du contenu
        if not isinstance(self.config.get('content'), str) or not self.config['content']:
             raise ConfigError("'content' requis (chaîne non vide).")
        
        # Vérification du chemin de sortie
        if 'output' not in self.config or not isinstance(self.config.get('output'), dict) or \
           not isinstance(self.config['output'].get('path'), str) or not self.config['output']['path']:
             raise ConfigError("'output.path' requis (chaîne non vide).")
        
        # Vérification de la compression
        if 'compression' not in self.config or not isinstance(self.config.get('compression'), dict):
            raise ConfigError("Section 'compression' manquante ou invalide.")
        
        comp_method = self.config['compression'].get('method')
        if comp_method not in ['gz', 'bz2', 'xz', 'none']:
             raise ConfigError(f"Méthode compression invalide: '{comp_method}'.")
        
        if self.debug_mode:
            logger.debug("Validation config OK.")

    def apply_standard_exclusions(self):
        """Applique les exclusions standard à la configuration."""
        if not self.config:
            if self.debug_mode:
                logger.warning("Config non chargée, exclusions std non appliquées.")
            return
        
        # Assurer l'existence de la section exclude
        excl_conf = self.config.setdefault('exclude', copy.deepcopy(DEFAULT_CONFIG['exclude']))
        patterns = excl_conf.setdefault('patterns', [])
        
        # Assurer le type liste
        if not isinstance(patterns, list): 
            patterns = []
        
        excl_conf['patterns'] = patterns
        
        # Récupérer les exclusions standard
        std_list = get_all_standard_exclusions()
        added = 0
        cur_lower = {p.lower() for p in patterns}
        newly_added = []

        # Ajouter les exclusions standard
        for p in std_list: 
            if p.lower() not in cur_lower:
                patterns.append(p)
                added += 1
                newly_added.append(p)

        # Gestion des messages selon le mode debug
        if added > 0:
            if self.debug_mode:
                logger.info(f"{DETAIL_COLOR}{added} exclusion(s) standard ajoutée(s).{RESET_STYLE}")
                logger.debug(f"Ajoutées: {', '.join(newly_added)}")
            excl_conf['patterns'] = sorted(patterns)
        else:
            if self.debug_mode:
                logger.debug("Aucune exclusion standard à ajouter.")

    @staticmethod
    def interactive_create(config_path_str: Optional[str] = None, debug_mode: bool = False):
        """Mode de création interactive de configuration."""
        try:
            # Afficher une belle bannière ASCII
            print(f"\n{BANNER_COLOR}{HIGHLIGHT_STYLE}╔══════════════════════════════════════════════════════════╗{RESET_STYLE}")
            print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}║            {SUCCESS_COLOR}NV{INFO_COLOR}BUILDER{BANNER_COLOR} CONFIGURATION v{VERSION}             ║{RESET_STYLE}")
            print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}╚══════════════════════════════════════════════════════════╝{RESET_STYLE}")
            print(f"{INFO_COLOR}         Assistant de configuration interactif{RESET_STYLE}\n")
            
            # Définir des fonctions d'affichage améliorées
            def section_title(title):
                print(f"\n{HEADER_COLOR}{HIGHLIGHT_STYLE}{'━' * 5} {title} {'━' * (45 - len(title))}{RESET_STYLE}")
            
            def option_value(option, value, important=False):
                value_color = HIGHLIGHT_STYLE if important else ""
                print(f"  {INFO_COLOR}•{RESET_STYLE} {option}: {value_color}{value}{RESET_STYLE}")
            
            default_path = DEFAULT_CONFIG_FILENAME
            config_path_str = input(f"{INFO_COLOR}Chemin config{RESET_STYLE} (défaut: '{default_path}') : ") or default_path
            config_path = get_absolute_path(config_path_str, Path.cwd())
            config: Dict[str, Any] = {}
            
            if config_path.is_file():
                try:
                    print(f"\n{SUCCESS_COLOR}Chargement config: {config_path}{RESET_STYLE}")
                    # Effet de chargement
                    for i in range(5):
                        print(f"\r{SUBTLE_STYLE}Lecture... {'▓' * i}{'░' * (4-i)}{RESET_STYLE}", end="")
                        time.sleep(0.1)
                    print("\r" + " " * 20 + "\r", end="")
                    
                    f = open(config_path, 'r', encoding='utf-8')
                    loaded_yaml = yaml.safe_load(f)
                    f.close()
                    config = loaded_yaml if isinstance(loaded_yaml, dict) else {}
                    print(f"{WARNING_COLOR}(Entrée vide = conserver actuel/défaut){RESET_STYLE}")
                except Exception as e:
                    print(f"{ERROR_COLOR}Erreur lecture {config_path}: {e}. Nouvelle config.{RESET_STYLE}")
                    config = {}
            else:
                print(f"\nCréation config: {config_path}")
                config = {}
                
            defaults_ref = copy.deepcopy(DEFAULT_CONFIG)
            
            section_title("Base")
            prompt_string(config, "Source contenu", ['content'], defaults_ref['content'])
            prompt_string(config, "Script post-exec", ['script'], defaults_ref['script'])
            prompt_string(config, "Fichier sortie", ['output', 'path'], defaults_ref['output']['path'])
            prompt_bool(config, "Exécution en root requise", ['output', 'need_root'], defaults_ref['output']['need_root'])
            
            section_title("Compression")
            allowed_methods = ['gz', 'bz2', 'xz', 'none']
            comp_method = _get_nested(config, ['compression', 'method'], defaults_ref['compression']['method'])
            
            # Afficher les options de compression de manière plus visuelle
            print(f"{INFO_COLOR}Méthode de compression:{RESET_STYLE}")
            for i, method in enumerate(allowed_methods):
                if method == comp_method:
                    print(f"  {DETAIL_COLOR}{HIGHLIGHT_STYLE}[{i+1}] {method}{RESET_STYLE} {DETAIL_COLOR}(actuel){RESET_STYLE}")
                else:
                    print(f"  {DETAIL_COLOR}[{i+1}] {method}{RESET_STYLE}")
                
            while True:
                method_input = input(f"Méthode (1-{len(allowed_methods)}) : ").strip()
                if not method_input:
                    break
                try:
                    idx = int(method_input) - 1
                    if 0 <= idx < len(allowed_methods):
                        comp_method = allowed_methods[idx]
                        break
                    else:
                        print(f"{ERROR_COLOR}Option invalide.{RESET_STYLE}")
                except ValueError:
                    # Essayer aussi avec la saisie directe de la méthode
                    if method_input in allowed_methods:
                        comp_method = method_input
                        break
                    else:
                        print(f"{ERROR_COLOR}Méthode invalide.{RESET_STYLE}")
                    
            _set_nested(config, ['compression', 'method'], comp_method)
            
            if comp_method != 'none':
                level_str = ""
                valid = False
                cur_lvl = _get_nested(config, ['compression', 'level'], defaults_ref['compression']['level'])
                
                # Visualiser les niveaux de compression
                print(f"{INFO_COLOR}Niveau de compression:{RESET_STYLE}")
                print(f"  {SUBTLE_STYLE}Min{RESET_STYLE} [1]{'•' * cur_lvl}[{cur_lvl}]{(8-cur_lvl) * '·'}[9] {SUBTLE_STYLE}Max{RESET_STYLE}")
                
                while not valid:
                    level_input = input(f"Niveau (1-9) (actuel: {HIGHLIGHT_STYLE}{cur_lvl}{RESET_STYLE}) : ").strip()
                    if not level_input:
                        level_str = str(cur_lvl)
                        valid = True
                    else:
                        try:
                            lv = int(level_input)
                            assert 1 <= lv <= 9
                            level_str = level_input
                            valid = True
                        except:
                            print(f"{ERROR_COLOR}Niveau invalide (1-9).{RESET_STYLE}")
                            
                _set_nested(config, ['compression', 'level'], int(level_str))
            else:
                _set_nested(config, ['compression', 'level'], None)
                
            is_encrypted = prompt_bool(config, "Chiffrement?", ['compression', 'encrypted'], _get_nested(config, ['compression', 'encrypted'], defaults_ref['compression']['encrypted']))
            
            if is_encrypted:
                allowed_tools = ['openssl', 'gpg']
                enc_tool = ""
                cur_tool = _get_nested(config, ['compression', 'encryption_tool'], defaults_ref['compression']['encryption_tool'])
                
                # Présentation des outils de chiffrement
                print(f"{INFO_COLOR}Outil de chiffrement:{RESET_STYLE}")
                for tool in allowed_tools:
                    is_current = tool == cur_tool
                    status = f"{DETAIL_COLOR}(actuel){RESET_STYLE}" if is_current else ""
                    print(f"  {HIGHLIGHT_STYLE if is_current else ''}{tool}{RESET_STYLE} {status}")
                
                while enc_tool not in allowed_tools:
                    tool_input = input(f"Outil ({'/'.join(allowed_tools)}) : ").lower().strip()
                    if not tool_input:
                        enc_tool = cur_tool
                        break
                    elif tool_input in allowed_tools:
                        enc_tool = tool_input
                        break
                    else:
                        print(f"{ERROR_COLOR}Outil invalide.{RESET_STYLE}")
                        
                _set_nested(config, ['compression', 'encryption_tool'], enc_tool)
                print(f"{WARNING_COLOR}Outil '{enc_tool}' requis sur cible.{RESET_STYLE}")
            else:
                _set_nested(config, ['compression', 'encryption_tool'], defaults_ref['compression']['encryption_tool'])
                
            section_title("Exclusions")
            if 'exclude' not in config or not isinstance(config.get('exclude'), dict):
                config['exclude'] = copy.deepcopy(defaults_ref['exclude'])
            if 'patterns' not in config['exclude'] or not isinstance(config['exclude']['patterns'], list):
                config['exclude']['patterns'] = []
            if 'ignore_case' not in config['exclude']:
                config['exclude']['ignore_case'] = True
                
            current_patterns = config['exclude']['patterns']
            
            if prompt_bool(config, "Configurer?", ['__dummy_ex'], bool(current_patterns)):
                ignore_case = prompt_bool(config, "Ignorer casse?", ['exclude', 'ignore_case'], config['exclude']['ignore_case'])
                std_list = get_all_standard_exclusions()
                std_lower = {p.lower() for p in std_list}
                cur_lower = {p.lower() for p in current_patterns}
                has_std = any(p in cur_lower for p in std_lower)
                want_std = prompt_bool(config, "Inclure std?", ['__dummy_std'], has_std)
                temp_list = []
                processed_keys = set()
                added = 0
                removed = 0
                
                if want_std:
                    for p in std_list:
                        key = p.lower() if ignore_case else p
                        if key not in processed_keys:
                            temp_list.append(p)
                            processed_keys.add(key)
                            if p.lower() not in cur_lower:
                                added += 1
                                
                    for p in current_patterns:
                        key = p.lower() if ignore_case else p
                        if p.lower() not in std_lower and key not in processed_keys:
                            temp_list.append(p)
                            processed_keys.add(key)
                            
                    if added > 0:
                        print(f"{DETAIL_COLOR}{added} std ajoutée(s).{RESET_STYLE}")
                else:
                    for p in current_patterns:
                        key = p.lower() if ignore_case else p
                        if p.lower() not in std_lower:
                            if key not in processed_keys:
                                temp_list.append(p)
                                processed_keys.add(key)
                        elif p.lower() in cur_lower:
                            removed += 1
                            
                    if removed > 0:
                        print(f"{DETAIL_COLOR}{removed} std retirée(s).{RESET_STYLE}")
                        
                current_patterns = temp_list
                custom_current = [p for p in current_patterns if p.lower() not in std_lower]
                print(f"\n{INFO_COLOR}Exclusions personnalisées actuelles:{RESET_STYLE}")
                if custom_current:
                    for p in sorted(custom_current):
                        print(f"  {DETAIL_COLOR}• {p}{RESET_STYLE}")
                else:
                    print(f"  {SUBTLE_STYLE}(aucune){RESET_STYLE}")
                    
                if prompt_bool(config, "Ajouter/modif perso?", ['__dummy_cust'], True):
                    print(f"{INFO_COLOR}Motifs perso (vide=fin):{RESET_STYLE}")
                    final_custom = list(custom_current)
                    custom_keys = set(p.lower() if ignore_case else p for p in final_custom)
                    
                    while True:
                        pat = input("Ajouter: ").strip()
                        if not pat:
                            break
                        key = pat.lower() if ignore_case else pat
                        if key not in custom_keys:
                            final_custom.append(pat)
                            custom_keys.add(key)
                            print(f" {SUCCESS_COLOR}✓{RESET_STYLE} Ajouté: '{pat}'")
                        else:
                            print(f"{WARNING_COLOR} ⚠ Existe déjà.{RESET_STYLE}")
                            
                    all_final = []
                    final_seen = set()
                    
                    if want_std:
                        for p in std_list:
                            key = p.lower() if ignore_case else p
                            if key not in final_seen:
                                all_final.append(p)
                                final_seen.add(key)
                                
                    for p in final_custom:
                        key = p.lower() if ignore_case else p
                        if key not in final_seen:
                            all_final.append(p)
                            final_seen.add(key)
                            
                    config['exclude']['patterns'] = sorted(all_final)
                else:
                    config['exclude']['patterns'] = sorted(current_patterns)
            else:
                if not config['exclude']['patterns']:
                    print("Aucune exclusion.")
                else:
                    print("Exclusions ignorées.")
                    
            for k in ['__dummy_ex', '__dummy_std', '__dummy_cust']:
                config.pop(k, None)
                
            section_title("Mise à jour HTTP")
            is_encrypted_final = _get_nested(config, ['compression', 'encrypted'])
            update_default = _get_nested(config, ['update', 'enabled'], defaults_ref['update']['enabled'])
            
            if is_encrypted_final:
                print(f"{WARNING_COLOR}Chiffrement activé -> MàJ Check-Only recommandée.{RESET_STYLE}")
                update_is_enabled = prompt_bool(config, "Activer MàJ?", ['update', 'enabled'], update_default)
            else:
                update_is_enabled = prompt_bool(config, "Activer MàJ?", ['update', 'enabled'], update_default)
                
            if update_is_enabled:
                prompt_string(config, "URL JSON", ['update', 'version_url'], _get_nested(config, ['update', 'version_url']))
                prompt_string(config, "URL paquet", ['update', 'package_url'], _get_nested(config, ['update', 'package_url']))
                prompt_string(config, "Chemin local version.json", ['update', 'version_file_path'], _get_nested(config, ['update', 'version_file_path']))
                
                # Ajout du choix du mode de mise à jour
                current_mode = _get_nested(config, ['update', 'mode'], DEFAULT_UPDATE_MODE)
                modes_allowed = UPDATE_MODES
                mode_descriptions = {
                    "check-only": "Vérifier uniquement",
                    "download-only": "Télécharger sans installer",
                    "auto-replace": "Remplacer et relancer auto",
                    "auto-replace-always": "Remplacer sans vérif mot de passe"
                }
                
                print(f"\n{INFO_COLOR}Mode de mise à jour:{RESET_STYLE}")
                for i, mode in enumerate(modes_allowed):
                    desc = mode_descriptions.get(mode, mode)
                    is_current = mode == current_mode
                    status = f"{DETAIL_COLOR}(actuel){RESET_STYLE}" if is_current else ""
                    print(f"  {HIGHLIGHT_STYLE if is_current else ''}{i+1}. {desc} ({mode}){RESET_STYLE} {status}")
                
                while True:
                    mode_input = input(f"Mode (1-{len(modes_allowed)}) : ").strip()
                    if not mode_input:
                        break
                    try:
                        mode_idx = int(mode_input) - 1
                        if 0 <= mode_idx < len(modes_allowed):
                            current_mode = modes_allowed[mode_idx]
                            _set_nested(config, ['update', 'mode'], current_mode)
                            break
                        else:
                            print(f"{ERROR_COLOR}Choix invalide. Entrez un nombre entre 1 et {len(modes_allowed)}.{RESET_STYLE}")
                    except ValueError:
                        print(f"{ERROR_COLOR}Veuillez entrer un nombre.{RESET_STYLE}")
                
                print(f"{WARNING_COLOR}Nécessite curl/wget cible.{RESET_STYLE}")

            # Avertissement pour auto-replace
            if current_mode == "auto-replace":
                print(f"{WARNING_COLOR}ATTENTION: Le mode 'auto-replace' remplacera automatiquement\nle script et le relancera lors des mises à jour.{RESET_STYLE}")
                if is_encrypted_final:
                    print(f"{ERROR_COLOR}NB: Le chiffrement est activé - le mode auto-replace nécessitera\nquand même une saisie manuelle du mot de passe.{RESET_STYLE}")
            elif current_mode == "auto-replace-always":
                print(f"{ERROR_COLOR}ATTENTION: Le mode 'auto-replace-always' remplacera automatiquement\nle script sans demander de mot de passe pour les mises à jour.{RESET_STYLE}")
                if is_encrypted_final:
                    print(f"{ERROR_COLOR}NB: Le chiffrement est activé mais en mode auto-replace-always,\naucune vérification de mot de passe ne sera effectuée pour les mises à jour.{RESET_STYLE}")
            else:
                [_set_nested(config, ['update', k], '') for k in ['version_url', 'package_url', 'version_file_path']]
                _set_nested(config, ['update', 'enabled'], False)
                _set_nested(config, ['update', 'mode'], DEFAULT_UPDATE_MODE)
                
            section_title("Hooks Locaux")
            if 'hooks' not in config or not isinstance(config.get('hooks'), dict):
                config['hooks'] = {'pre_build': [], 'post_build': []}
            if 'pre_build' not in config['hooks'] or not isinstance(config['hooks']['pre_build'], list):
                config['hooks']['pre_build'] = []
            if 'post_build' not in config['hooks'] or not isinstance(config['hooks']['post_build'],list):
                config['hooks']['post_build'] = []
                
            pre = config['hooks']['pre_build']
            post = config['hooks']['post_build']
            
            if prompt_bool(config, "Configurer hooks?", ['__dummy_h'], bool(pre or post)):
                print(f"{INFO_COLOR}Commandes Pré-build (vide=fin):{RESET_STYLE}")
                new_pre = []
                
                while True:
                    cmd = input("Pré : ").strip()
                    if not cmd:
                        break
                    new_pre.append(cmd)
                    print(f" {SUCCESS_COLOR}✓{RESET_STYLE} Ajouté: '{cmd}'")
                    
                config['hooks']['pre_build'] = new_pre
                
                print(f"\n{INFO_COLOR}Commandes Post-build (vide=fin):{RESET_STYLE}")
                new_post = []
                
                while True:
                    cmd = input("Post: ").strip()
                    if not cmd:
                        break
                    new_post.append(cmd)
                    print(f" {SUCCESS_COLOR}✓{RESET_STYLE} Ajouté: '{cmd}'")
                    
                config['hooks']['post_build'] = new_post
            else:
                print("Hooks ignorés.")
                
            config.pop('__dummy_h', None)
            config.pop('_config_dir', None)
            [config.pop(k) for k in list(config.keys()) if k.startswith('__dummy_')]
            
            section_title("Sauvegarde")
            # Animation de sauvegarde
            print(f"{INFO_COLOR}Écriture du fichier de configuration...{RESET_STYLE}")
            for i in range(10):
                progress = (i + 1) * 10
                bar = "▓" * (i + 1) + "░" * (9 - i)
                print(f"\r{DETAIL_COLOR}[{bar}] {progress}%{RESET_STYLE}", end="")
                time.sleep(0.05)
            print("\r" + " " * 30 + "\r", end="")
            
            save_config_yaml(config, config_path)
            
            # Résumé des paramètres de configuration
            print(f"\n{BANNER_COLOR}{HIGHLIGHT_STYLE}╔══════════════════════════════════════════════════════════╗{RESET_STYLE}")
            print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}║                RÉSUMÉ DE LA CONFIGURATION                ║{RESET_STYLE}")
            print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}╚══════════════════════════════════════════════════════════╝{RESET_STYLE}")
            
            option_value("Fichier source", _get_nested(config, ['content']))
            option_value("Script post-extraction", _get_nested(config, ['script']))
            option_value("Fichier sortie", _get_nested(config, ['output', 'path']))
            
            comp_method = _get_nested(config, ['compression', 'method'])
            comp_level = _get_nested(config, ['compression', 'level'])
            comp_info = f"{comp_method}" + (f" (niveau {comp_level})" if comp_method != 'none' and comp_level else "")
            option_value("Compression", comp_info)
            
            is_encrypted = _get_nested(config, ['compression', 'encrypted'], False)
            enc_tool = _get_nested(config, ['compression', 'encryption_tool']) if is_encrypted else "Non"
            option_value("Chiffrement", f"{enc_tool}", important=is_encrypted)
            
            update_enabled = _get_nested(config, ['update', 'enabled'], False)
            update_mode = _get_nested(config, ['update', 'mode']) if update_enabled else "Non"
            option_value("Mise à jour", f"{update_mode}", important=update_enabled)
            
            print(f"\n{SUCCESS_COLOR}{HIGHLIGHT_STYLE}Configuration terminée avec succès !{RESET_STYLE}")
            
        except KeyboardInterrupt:
            print("\nConfiguration interactive annulée.")
        except Exception as e:
            print(f"\n{ERROR_COLOR}Erreur config interactive: {e}{RESET_STYLE}")
            # Afficher le traceback complet uniquement en mode debug
            if debug_mode:
                traceback.print_exc()