# nvbuilder/config.py
"""Gestion de la configuration."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import copy
import logging
import traceback

from .constants import DEFAULT_CONFIG, DEFAULT_CONFIG_FILENAME, VERSION
from .exceptions import ConfigError
from .utils import (get_absolute_path, get_all_standard_exclusions,
                    _get_nested, _set_nested, prompt_string, prompt_bool,
                    save_config_yaml)
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
except ImportError:
    class DummyColorama:
        def __getattr__(self, name): return ""
    Fore = Style = DummyColorama(); Style.RESET_ALL = ""

logger = logging.getLogger("nvbuilder")

class ConfigLoader:
    """Charge, valide et fournit la configuration depuis un fichier YAML."""

    def __init__(self, config_path_str: Optional[str] = None, base_dir: Optional[Path] = None):
        # (Identique v2.0.25)
        self.cwd = Path.cwd()
        self.config_path = self._resolve_config_path(config_path_str, self.cwd)
        self.base_dir = self.config_path.parent
        self.config: Dict[str, Any] = {}

    def _resolve_config_path(self, config_path_str: Optional[str], cwd: Path) -> Path:
        # (Identique v2.0.25)
        path_str = config_path_str or DEFAULT_CONFIG_FILENAME
        return get_absolute_path(path_str, cwd)

    def load(self) -> Dict[str, Any]:
        # (Identique v2.0.25)
        logger.debug(f"Tentative de chargement config: {self.config_path}")
        raw_config = {}
        if self.config_path.is_file():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f: raw_config = yaml.safe_load(f) or {}
                logger.info(f"Config lue: {self.config_path}")
            except yaml.YAMLError as e: raise ConfigError(f"Syntaxe YAML err '{self.config_path}': {e}") from e
            except Exception as e: raise ConfigError(f"Lecture '{self.config_path}' échouée: {e}") from e
        else:
            logger.warning(f"Fichier config '{self.config_path}' non trouvé. Utilisation des défauts.")
            raw_config = {}
        self.config = self._apply_defaults(raw_config); self._validate_config()
        self.config['_config_dir'] = self.base_dir; logger.debug("Configuration chargée et validée."); return self.config

    # --- Méthode _apply_defaults CORRIGÉE ---
    def _apply_defaults(self, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les valeurs par défaut en fusionnant récursivement."""
        config_with_defaults = copy.deepcopy(DEFAULT_CONFIG)

        # Fonction interne récursive pour fusionner les dictionnaires
        def merge_dicts(default: Dict, loaded: Dict) -> Dict:
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
    # --- FIN Méthode _apply_defaults CORRIGÉE ---

    def _validate_config(self):
        # (Identique v2.0.25)
        if not isinstance(self.config.get('content'), str) or not self.config['content']:
             raise ConfigError("'content' requis (chaîne non vide).")
        if 'output' not in self.config or not isinstance(self.config.get('output'), dict) or \
           not isinstance(self.config['output'].get('path'), str) or not self.config['output']['path']:
             raise ConfigError("'output.path' requis (chaîne non vide).")
        if 'compression' not in self.config or not isinstance(self.config.get('compression'), dict):
            raise ConfigError("Section 'compression' manquante ou invalide.")
        comp_method = self.config['compression'].get('method')
        if comp_method not in ['gz', 'bz2', 'xz', 'none']:
             raise ConfigError(f"Méthode compression invalide: '{comp_method}'.")
        logger.debug("Validation config OK.")

    def apply_standard_exclusions(self):
        # (Identique v2.0.25)
        if not self.config: logger.warning("Config non chargée, exclusions std non appliquées."); return
        excl_conf = self.config.setdefault('exclude', copy.deepcopy(DEFAULT_CONFIG['exclude'])) # Assurer existence
        patterns = excl_conf.setdefault('patterns', [])
        if not isinstance(patterns, list): patterns = [] # Assurer type
        excl_conf['patterns'] = patterns # Remettre en place si modifié
        std_list = get_all_standard_exclusions(); added = 0; cur_lower = {p.lower() for p in patterns}; newly_added = []
        for p in std_list: 
            if p.lower() not in cur_lower: patterns.append(p); added += 1; newly_added.append(p)
        if added > 0: logger.info(f"{Fore.CYAN}{added} exclusion(s) standard ajoutée(s).{Style.RESET_ALL}"); logger.debug(f"Ajoutées: {', '.join(newly_added)}"); excl_conf['patterns'] = sorted(patterns)
        else: logger.debug("Aucune exclusion standard à ajouter.")

    # interactive_create (Identique v2.0.25 - déjà décompacté)
    @staticmethod
    def interactive_create(output_path_str: Optional[str] = None): # Inchangé
        try:
            print(f"\n--- Assistant de Configuration Interactif NVBuilder v{VERSION} ---"); default_path = DEFAULT_CONFIG_FILENAME
            config_path_str = input(f"Chemin config (défaut: '{default_path}') : ") or default_path; config_path = get_absolute_path(config_path_str, Path.cwd())
            config: Dict[str, Any] = {};
            if config_path.is_file():
                try: print(f"\n{Fore.GREEN}Chargement config: {config_path}{Style.RESET_ALL}"); f=open(config_path,'r',encoding='utf-8'); loaded_yaml=yaml.safe_load(f); f.close(); config=loaded_yaml if isinstance(loaded_yaml,dict) else {}; print(f"{Fore.YELLOW}(Entrée vide = conserver actuel/défaut){Style.RESET_ALL}")
                except Exception as e: print(f"{Fore.RED}Erreur lecture {config_path}: {e}. Nouvelle config.{Style.RESET_ALL}"); config = {}
            else: print(f"\nCréation config: {config_path}"); config = {}
            defaults_ref = copy.deepcopy(DEFAULT_CONFIG)
            print("\n--- Base ---"); prompt_string(config, "Source contenu", ['content'], defaults_ref['content']); prompt_string(config, "Script post-exec", ['script'], defaults_ref['script']); prompt_string(config, "Fichier sortie", ['output', 'path'], defaults_ref['output']['path']); prompt_bool(config, "Root requis (info)", ['output', 'need_root'], defaults_ref['output']['need_root'])
            print("\n--- Compression ---"); allowed_methods = ['gz','bz2','xz','none']; comp_method = _get_nested(config, ['compression','method'], defaults_ref['compression']['method'])
            while True: 
                method_input=input(f"Méthode ({'/'.join(allowed_methods)}) (actuel: '{comp_method}'): ").lower().strip()
                if not method_input: break
                elif method_input in allowed_methods: 
                    comp_method=method_input; break
                else: 
                    print(f"{Fore.RED}Méthode invalide.{Style.RESET_ALL}")
            _set_nested(config, ['compression','method'], comp_method)
            if comp_method != 'none':
                level_str=""; valid=False; cur_lvl=_get_nested(config,['compression','level'],defaults_ref['compression']['level'])
                while not valid: 
                    level_input=input(f"Niveau (1-9) (actuel: {cur_lvl}): ").strip()
                    if not level_input: 
                        level_str=str(cur_lvl); valid=True
                    else: 
                        try: 
                            lv=int(level_input); assert 1<=lv<=9; level_str=level_input; valid=True; 
                        except: 
                            print(f"{Fore.RED}Niveau invalide (1-9).{Style.RESET_ALL}")
                _set_nested(config, ['compression','level'], int(level_str))
            else: _set_nested(config, ['compression','level'], None)
            is_encrypted = prompt_bool(config, "Chiffrement?", ['compression', 'encrypted'], _get_nested(config,['compression','encrypted'],defaults_ref['compression']['encrypted']))
            if is_encrypted: 
                allowed_tools=['openssl','gpg']
                enc_tool=""
                cur_tool=_get_nested(config,['compression','encryption_tool'],defaults_ref['compression']['encryption_tool'])
                while enc_tool not in allowed_tools: 
                    tool_input=input(f"Outil ({'/'.join(allowed_tools)}) (actuel: '{cur_tool}'): ").lower().strip()
                    if not tool_input: 
                        enc_tool=cur_tool; break
                    elif tool_input in allowed_tools: enc_tool=tool_input; break
                    else: print(f"{Fore.RED}Outil invalide.{Style.RESET_ALL}")
                _set_nested(config,['compression','encryption_tool'], enc_tool); print(f"{Fore.YELLOW}Outil '{enc_tool}' requis sur cible.{Style.RESET_ALL}")
            else: _set_nested(config,['compression','encryption_tool'], defaults_ref['compression']['encryption_tool'])
            print("\n--- Exclusions ---");
            if 'exclude' not in config or not isinstance(config.get('exclude'),dict): config['exclude']=copy.deepcopy(defaults_ref['exclude'])
            if 'patterns' not in config['exclude'] or not isinstance(config['exclude']['patterns'],list): config['exclude']['patterns']=[]
            if 'ignore_case' not in config['exclude']: config['exclude']['ignore_case']=True
            current_patterns = config['exclude']['patterns']
            if prompt_bool(config,"Configurer?",['__dummy_ex'], bool(current_patterns)):
                ignore_case=prompt_bool(config,"Ignorer casse?",['exclude','ignore_case'], config['exclude']['ignore_case']); std_list=get_all_standard_exclusions(); std_lower={p.lower() for p in std_list}; cur_lower={p.lower() for p in current_patterns}; has_std=any(p in cur_lower for p in std_lower); want_std=prompt_bool(config,"Inclure std?",['__dummy_std'], has_std); temp_list=[]; processed_keys=set(); added=0; removed=0
                if want_std:
                    for p in std_list: 
                        key=p.lower() if ignore_case else p
                        if key not in processed_keys: 
                            temp_list.append(p); processed_keys.add(key); 
                            if p.lower() not in cur_lower: 
                                added+=1
                    for p in current_patterns: 
                        key=p.lower() if ignore_case else p
                        if p.lower() not in std_lower and key not in processed_keys: 
                            temp_list.append(p); processed_keys.add(key)
                    if added > 0: 
                        print(f"{Fore.CYAN}{added} std ajoutée(s).{Style.RESET_ALL}")
                else:
                    for p in current_patterns: 
                        key=p.lower() if ignore_case else p
                        if p.lower() not in std_lower: 
                            if key not in processed_keys: 
                                temp_list.append(p); processed_keys.add(key)
                            elif p.lower() in cur_lower: 
                                removed+=1
                    if removed > 0: print(f"{Fore.CYAN}{removed} std retirée(s).{Style.RESET_ALL}")
                current_patterns=temp_list; custom_current=[p for p in current_patterns if p.lower() not in std_lower]; print("\nPerso actuelles:"); [print(f" - {p}") for p in sorted(custom_current)] if custom_current else print("  (aucune)")
                if prompt_bool(config,"Ajouter/modif perso?",['__dummy_cust'],True):
                    print("Motifs perso (vide=fin):"); final_custom=list(custom_current); custom_keys=set(p.lower() if ignore_case else p for p in final_custom)
                    while True: 
                        pat=input("Ajouter: ").strip()
                        if not pat: break
                        key=pat.lower() if ignore_case else pat
                        if key not in custom_keys: 
                            final_custom.append(pat); custom_keys.add(key); print(f" -> Ajouté: '{pat}'")
                        else: print(f"{Fore.YELLOW} -> Existe déjà.{Style.RESET_ALL}")
                    all_final=[]; final_seen={};
                    if want_std:
                        for p in std_list: 
                            key=p.lower() if ignore_case else p
                            if key not in final_seen: 
                                all_final.append(p); final_seen.add(key)
                    for p in final_custom: 
                        key=p.lower() if ignore_case else p
                        if key not in final_seen: 
                            all_final.append(p); final_seen.add(key)
                    config['exclude']['patterns']=sorted(all_final)
                else: config['exclude']['patterns']=sorted(current_patterns)
            else: 
                if not config['exclude']['patterns']: 
                    print("Aucune exclusion.")
                else: 
                    print("Exclusions ignorées.")
            for k in ['__dummy_ex','__dummy_std','__dummy_cust']: config.pop(k, None)
            print("\n--- Mise à jour HTTP ---");
            is_encrypted_final = _get_nested(config, ['compression', 'encrypted']); update_default = _get_nested(config,['update','enabled'],defaults_ref['update']['enabled'])
            if is_encrypted_final: print(f"{Fore.YELLOW}Chiffrement activé -> MàJ Check-Only.{Style.RESET_ALL}"); update_is_enabled = prompt_bool(config,"Activer MàJ (Check-Only)?",['update','enabled'], update_default)
            else: update_is_enabled = prompt_bool(config,"Activer MàJ?",['update','enabled'], update_default)
            if update_is_enabled: prompt_string(config,"URL JSON",['update','version_url'],_get_nested(config,['update','version_url'])); prompt_string(config,"URL paquet",['update','package_url'],_get_nested(config,['update','package_url'])); prompt_string(config,"Chemin local version.json",['update','version_file_path'],_get_nested(config,['update','version_file_path'])); print(f"{Fore.YELLOW}Nécessite curl/wget cible.{Style.RESET_ALL}")
            else: [_set_nested(config,['update',k],'') for k in ['version_url','package_url','version_file_path']]; _set_nested(config, ['update','enabled'], False)
            print("\n--- Hooks Locaux ---");
            if 'hooks' not in config or not isinstance(config.get('hooks'),dict): config['hooks']={'pre_build':[],'post_build':[]}
            if 'pre_build' not in config['hooks'] or not isinstance(config['hooks']['pre_build'],list): config['hooks']['pre_build']=[]
            if 'post_build' not in config['hooks'] or not isinstance(config['hooks']['post_build'],list): config['hooks']['post_build']=[]
            pre=config['hooks']['pre_build']; post=config['hooks']['post_build']
            if prompt_bool(config,"Configurer hooks?",['__dummy_h'], bool(pre or post)):
                 print("Cmds Pre (vide=fin):"); new_pre=[];
                 while True: 
                    cmd=input("Pre: ").strip()
                    if not cmd: break
                    new_pre.append(cmd)
                 print("Cmds Post (vide=fin):"); new_post=[];
                 while True: 
                    cmd=input("Post: ").strip()
                    if not cmd: break; new_post.append(cmd); config['hooks']['post_build']=new_post
            else: print("Hooks ignorés.")
            config.pop('__dummy_h', None)
            config.pop('_config_dir', None); [config.pop(k) for k in list(config.keys()) if k.startswith('__dummy_')]
            print("\n--- Sauvegarde ---"); save_config_yaml(config, config_path)
        except KeyboardInterrupt: print("\nConfig interactive annulée.")
        except Exception as e: print(f"\n{Fore.RED}Erreur config interactive: {e}{Style.RESET_ALL}"); traceback.print_exc()