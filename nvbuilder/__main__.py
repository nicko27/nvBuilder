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

# Initialisation Colorama
if HAS_COLORAMA:
    colorama.init(autoreset=True)
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    CYAN = colorama.Fore.CYAN
    MAGENTA = colorama.Fore.MAGENTA
    BRIGHT = colorama.Style.BRIGHT
    DIM = colorama.Style.DIM
    RESET = colorama.Style.RESET_ALL
else:
    RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = BRIGHT = DIM = RESET = ""

def display_banner():
    """Affiche une bannière ASCII colorée."""
    print(f"{CYAN}{BRIGHT}╔═══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BRIGHT}║                {BLUE}NVBUILDER v{VERSION}{CYAN}                             ║{RESET}")
    print(f"{CYAN}{BRIGHT}╚═══════════════════════════════════════════════════════════╝{RESET}")
    print()

def check_python_version():
    """Vérifie la version Python."""
    if not sys.version_info >= (3, 7):
        print(f"{RED}Erreur: Python 3.7+ requis (v{platform.python_version()} détectée).{RESET}", file=sys.stderr)
        sys.exit(1)

def check_python_dependencies(debug=False):
    """Vérifie les dépendances Python essentielles."""
    if debug:
        print(f"{BRIGHT}Vérification des dépendances Python...{RESET}")
    
    missing = []
    if not HAS_YAML: missing.append("PyYAML")
    if not HAS_COLORAMA: missing.append("colorama")
    
    if missing:
        print(f"{RED}Erreur: Modules manquants: {', '.join(missing)}{RESET}", file=sys.stderr)
        print(f"-> Installation via pip: {YELLOW}pip install {' '.join(missing)}{RESET}", file=sys.stderr)
        try: 
            req_file = Path(__file__).parent.parent/'requirements.txt'
            if req_file.is_file(): 
                print(f"   Ou via: {YELLOW}pip install -r {req_file}{RESET}", file=sys.stderr)
        except: pass
        sys.exit(1)
    
    if debug:
        print(f"{GREEN}✓ Dépendances essentielles OK.{RESET}")

def list_standard_exclusions(): 
    """Liste les exclusions standard."""
    print(f"{GREEN}{BRIGHT}--- Exclusions Standard ---{RESET}")
    total = 0
    exclusions = get_standard_exclusions()
    
    for category, patterns in exclusions.items(): 
        print(f"\n{YELLOW}{BRIGHT}{category}{RESET}:") 
        for p in patterns:
            print(f"  • {CYAN}{p}{RESET}") 
        total += len(patterns)
    
    print(f"\n{GREEN}Total: {BRIGHT}{total}{RESET} motifs.")

def run_interactive_config(config_path_arg: str, debug=False): 
    """Lance la configuration interactive."""
    try: 
        from .config import ConfigLoader
        ConfigLoader.interactive_create(config_path_arg, debug)
    except NotImplementedError: 
        print(f"{RED}Mode interactif non implémenté.{RESET}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt: 
        print("\nConfiguration interactive annulée.")
        sys.exit(0)
    except Exception as e: 
        print(f"{RED}Erreur config interactive: {e}{RESET}", file=sys.stderr)
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
        print(f"\r{BLUE}{spinner[i]} {message}...{RESET}", end="")
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
        print(f"{YELLOW}Lancement mode interactif...{RESET}")
        run_interactive_config(args.config, args.debug)
        sys.exit(0)

    # Mode Build 
    exit_code = 1 # Défaut = échec
    try:
        if args.debug:
            print(f"{CYAN}• Mode debug activé")
            if args.exclude_standard:
                print(f"{CYAN}• Exclusions standard activées")
            print(f"{CYAN}• Fichier de config: {args.config}")
        else:
            if args.exclude_standard:
                print(f"{DIM}Exclusions standard activées{RESET}")

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
            print(f"\n{CYAN}{'═' * 55}{RESET}")
            print(f"{GREEN}{BRIGHT}  ✅ Build terminé avec succès !{RESET}")
            print(f"{CYAN}{'═' * 55}{RESET}")
            print(f"{BLUE}• Script généré : {BRIGHT}{output_script_path}{RESET} ({final_size_mb:.2f} Mo)")
            
            if builder.metadata_manager.get('encryption_enabled'):
                print(f"{BLUE}• Chiffrement  : {GREEN}Activé{RESET} ({builder.metadata_manager.get('encryption_tool', 'openssl')})")
            
            if builder.metadata_manager.get('update_enabled'):
                update_mode = builder.metadata_manager.get('update_mode', 'check-only')
                print(f"{BLUE}• Mise à jour  : {GREEN}Activée{RESET} (Mode: {update_mode})")
            
            exit_code = 0 # Succès
        else:
            # Message minimal d'échec
            print(f"\n{RED}>>> Échec du Build.{RESET}")
            exit_code = 1 # Échec

    except NvBuilderError as e: 
        print(f"\n{RED}ERREUR: {e}{RESET}", file=sys.stderr)
        exit_code = 1
    except Exception as e: 
        print(f"\n{RED}ERREUR INATTENDUE: {e}{RESET}", file=sys.stderr)
        # Traceback complet seulement en mode debug
        traceback.print_exc() if args.debug else None
        exit_code = 1
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Opération annulée.{RESET}")
        exit_code = 130
    finally:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()