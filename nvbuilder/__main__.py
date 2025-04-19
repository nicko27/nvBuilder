# nvbuilder/__main__.py
"""Point d'entrée CLI."""

import argparse
import sys
import logging
import platform
import traceback
import time
from pathlib import Path

# Imports relatifs au package
from .builder import NvBuilder
from .constants import VERSION, DEFAULT_CONFIG_FILENAME
from .exceptions import NvBuilderError
from .utils import get_standard_exclusions

# Import des couleurs sémantiques
from .colors import (
    ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, INFO_COLOR, DETAIL_COLOR,
    UPDATE_COLOR, DEBUG_COLOR, HEADER_COLOR, BANNER_COLOR, FILENAME_COLOR,
    PATH_COLOR, OPTION_COLOR, KEY_COLOR, VALUE_COLOR, 
    HIGHLIGHT_STYLE, SUBTLE_STYLE, RESET_STYLE
)

# Dépendances optionnelles
try: 
    import yaml; 
    HAS_YAML = True; 
except ImportError: 
    HAS_YAML = False
try: 
    import colorama; 
    HAS_COLORAMA = True; 
except ImportError: 
    HAS_COLORAMA = False
try: 
    import requests; 
    HAS_REQUESTS = True; 
except ImportError: 
    HAS_REQUESTS = False

def display_banner():
    """Affiche une bannière ASCII colorée."""
    print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}╔═══════════════════════════════════════════════════════════╗{RESET_STYLE}")
    print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}║                {INFO_COLOR}NVBUILDER v{VERSION}{BANNER_COLOR}                             ║{RESET_STYLE}")
    print(f"{BANNER_COLOR}{HIGHLIGHT_STYLE}╚═══════════════════════════════════════════════════════════╝{RESET_STYLE}")
    print()

def check_python_version():
    """Vérifie la version Python."""
    if not sys.version_info >= (3, 7):
        print(f"{ERROR_COLOR}Erreur: Python 3.7+ requis (v{platform.python_version()} détectée).{RESET_STYLE}", file=sys.stderr)
        sys.exit(1)

def check_python_dependencies(debug=False):
    """Vérifie les dépendances Python essentielles."""
    if debug:
        print(f"{HIGHLIGHT_STYLE}Vérification des dépendances Python...{RESET_STYLE}")
    
    missing = []
    if not HAS_YAML: missing.append("PyYAML")
    if not HAS_COLORAMA: missing.append("colorama")
    
    if missing:
        print(f"{ERROR_COLOR}Erreur: Modules manquants: {', '.join(missing)}{RESET_STYLE}", file=sys.stderr)
        print(f"•  Installation via pip: {WARNING_COLOR}pip install {' '.join(missing)}{RESET_STYLE}", file=sys.stderr)
        try: 
            req_file = Path(__file__).parent.parent/'requirements.txt'
            if req_file.is_file(): 
                print(f"   Ou via: {WARNING_COLOR}pip install -r {req_file}{RESET_STYLE}", file=sys.stderr)
        except: pass
        sys.exit(1)
    
    if debug:
        print(f"{SUCCESS_COLOR}✓ Dépendances essentielles OK.{RESET_STYLE}")

def list_standard_exclusions(): 
    """Liste les exclusions standard."""
    print(f"{SUCCESS_COLOR}{HIGHLIGHT_STYLE}--- Exclusions Standard ---{RESET_STYLE}")
    total = 0
    exclusions = get_standard_exclusions()
    
    for category, patterns in exclusions.items(): 
        print(f"\n{WARNING_COLOR}{HIGHLIGHT_STYLE}{category}{RESET_STYLE}:") 
        for p in patterns:
            print(f"  • {FILENAME_COLOR}{p}{RESET_STYLE}") 
        total += len(patterns)
    
    print(f"\n{SUCCESS_COLOR}Total: {HIGHLIGHT_STYLE}{total}{RESET_STYLE} motifs.")

def run_interactive_config(config_path_arg: str, debug=False): 
    """Lance la configuration interactive."""
    try: 
        from .config import ConfigLoader
        ConfigLoader.interactive_create(config_path_arg, debug)
    except NotImplementedError: 
        print(f"{ERROR_COLOR}Mode interactif non implémenté.{RESET_STYLE}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt: 
        print("\nConfiguration interactive annulée.")
        sys.exit(0)
    except Exception as e: 
        print(f"{ERROR_COLOR}Erreur config interactive: {e}{RESET_STYLE}", file=sys.stderr)
        traceback.print_exc() if debug else None
        sys.exit(1)

def show_progress_spinner(message="Traitement en cours", duration=3):
    """Affiche un spinner de progression pour les démos."""
    # Ne pas utiliser en production
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    end_time = time.time() + duration
    i = 0
    
    while time.time() < end_time:
        i = (i + 1) % len(spinner)
        print(f"\r{INFO_COLOR}{spinner[i]} {message}...{RESET_STYLE}", end="")
        time.sleep(0.1)
    
    print("\r" + " " * (len(message) + 15) + "\r", end="")

def main():
    """Fonction principale CLI."""
    # Parser d'arguments avec ajout de l'option debug
    parser = argparse.ArgumentParser(description=f"NVBuilder v{VERSION} - Créateur d'archives auto-extractibles Bash.", 
                                     formatter_class=argparse.RawTextHelpFormatter, 
                                     prog="nvbuilder")
    parser.add_argument('--config', '-c', default=DEFAULT_CONFIG_FILENAME, help=f"Fichier config YAML (défaut: {DEFAULT_CONFIG_FILENAME}).")
    parser.add_argument('--interactive', '-i', action='store_true', help="Mode interactif pour config.")
    parser.add_argument('--exclude-standard', '-e', action='store_true', help="Ajoute exclusions standard.")
    parser.add_argument('--list-standard-exclusions', '-l', action='store_true', help="Liste exclusions standard.")
    parser.add_argument('--debug', '-d', action='store_true', help="Active le mode debug (logs détaillés).")
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s v{VERSION}')
    args = parser.parse_args()

    # Afficher la bannière ASCII
    display_banner()

    # Vérifications préalables
    check_python_version()
    check_python_dependencies(args.debug)

    # Gestion des différentes actions
    if args.list_standard_exclusions: 
        list_standard_exclusions()
        sys.exit(0)

    if args.interactive: 
        print(f"{WARNING_COLOR}Lancement mode interactif...{RESET_STYLE}")
        run_interactive_config(args.config, args.debug)
        sys.exit(0)

    # Mode Build 
    exit_code = 1 # Défaut = échec
    try:
        if args.debug:
            print(f"{DETAIL_COLOR}• Mode debug activé")
            if args.exclude_standard:
                print(f"{DETAIL_COLOR}• Exclusions standard activées")
            print(f"{DETAIL_COLOR}• Fichier de config: {args.config}")
        else:
            if args.exclude_standard:
                print(f"{SUBTLE_STYLE}Exclusions standard activées{RESET_STYLE}")

        # Passer le mode debug au NvBuilder
        builder = NvBuilder(
            config_path_str=args.config, 
            use_standard_exclusions=args.exclude_standard,
            debug_mode=args.debug
        )
        output_script_path = builder.build()
        
        if output_script_path:
            # Message de succès avec barre horizontale
            final_size_mb = output_script_path.stat().st_size / (1024 * 1024)
            print("\n")
            print(f"{SUCCESS_COLOR}{HIGHLIGHT_STYLE}✅ Build terminé avec succès !{RESET_STYLE}")
            print(f"   • {HIGHLIGHT_STYLE}Script généré : {INFO_COLOR}{output_script_path}{RESET_STYLE} ({final_size_mb:.2f} Mo)")
            
            if builder.metadata_manager.get('encryption_enabled'):
                print(f"   • {HIGHLIGHT_STYLE}Chiffrement  :  {SUCCESS_COLOR}Activé{RESET_STYLE} ({builder.metadata_manager.get('encryption_tool', 'openssl')})")
            
            if builder.metadata_manager.get('update_enabled'):
                update_mode = builder.metadata_manager.get('update_mode', 'check-only')
                print(f"   • {HIGHLIGHT_STYLE}Mise à jour  :  {SUCCESS_COLOR}Activée{RESET_STYLE} (Mode: {update_mode})")
            
            exit_code = 0 # Succès
        else:
            # Message minimal d'échec
            print(f"\n{ERROR_COLOR}>>> Échec du Build.{RESET_STYLE}")
            exit_code = 1 # Échec

    except NvBuilderError as e: 
        print(f"\n{ERROR_COLOR}ERREUR: {e}{RESET_STYLE}", file=sys.stderr)
        exit_code = 1
    except Exception as e: 
        print(f"\n{ERROR_COLOR}ERREUR INATTENDUE: {e}{RESET_STYLE}", file=sys.stderr)
        # Traceback complet seulement en mode debug
        traceback.print_exc() if args.debug else None
        exit_code = 1
    except KeyboardInterrupt:
        print(f"\n{WARNING_COLOR}Opération annulée.{RESET_STYLE}")
        exit_code = 130
    finally:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()