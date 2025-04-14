# nvbuilder/__main__.py
"""Point d'entrée CLI."""

import argparse
import sys
import logging
import platform
import traceback
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
    colorama.init(autoreset=True) # Autoreset simplifie l'usage
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    BRIGHT = colorama.Style.BRIGHT
    RESET = colorama.Style.RESET_ALL
else:
    RED = GREEN = YELLOW = BRIGHT = RESET = ""

# Logger minimal pour erreurs précoces
early_logger = logging.getLogger("nvbuilder_early")
if not early_logger.hasHandlers():
    early_handler = logging.StreamHandler(sys.stderr)
    # Format plus simple pour les erreurs précoces
    early_formatter = logging.Formatter(f"{YELLOW}%(levelname)s:{RESET} %(message)s")
    early_handler.setFormatter(early_formatter)
    early_logger.addHandler(early_handler)
    early_logger.setLevel(logging.INFO)

def check_python_version():
    """Vérifie la version Python."""
    if not sys.version_info >= (3, 7):
        print(f"{RED}Erreur: Python 3.7+ requis (v{platform.python_version()} détectée).{RESET}", file=sys.stderr)
        sys.exit(1)

def check_python_dependencies():
    """Vérifie les dépendances Python essentielles."""
    print(f"{BRIGHT}Vérification des dépendances Python...{RESET}")
    missing = []
    if not HAS_YAML: missing.append("PyYAML")
    if not HAS_COLORAMA: missing.append("colorama") # Requis pour bel affichage
    if missing:
        print(f"{RED}Erreur: Modules manquants: {', '.join(missing)}{RESET}", file=sys.stderr)
        print(f"-> Installation via pip: {YELLOW}pip install {' '.join(missing)}{RESET}", file=sys.stderr)
        try: 
            req_file = Path(__file__).parent.parent/'requirements.txt';
            if req_file.is_file(): print(f"   Ou via: {YELLOW}pip install -r {req_file}{RESET}", file=sys.stderr)
        except: pass
        sys.exit(1)
    # Check 'requests' seulement si --update est activé (fait dans NvBuilder/bash_snippets)
    print(f"{GREEN}Dépendances essentielles OK.{RESET}")


def list_standard_exclusions(): # Inchangé
    print(f"{GREEN}--- Exclusions Standard ---{RESET}"); total = 0; exclusions = get_standard_exclusions()
    for category, patterns in exclusions.items(): print(f"\n{YELLOW}{category}{RESET}:"); [print(f"  - {p}") for p in patterns]; total += len(patterns)
    print(f"\n{GREEN}Total: {total} motifs.{RESET}")

def run_interactive_config(config_path_arg: str): # Inchangé
    try: from .config import ConfigLoader; ConfigLoader.interactive_create(config_path_arg)
    except NotImplementedError: print(f"{RED}Mode interactif non implémenté.{RESET}", file=sys.stderr); sys.exit(1)
    except KeyboardInterrupt: print("\nConfiguration interactive annulée."); sys.exit(0)
    except Exception as e: print(f"{RED}Erreur config interactive: {e}{RESET}", file=sys.stderr); traceback.print_exc(); sys.exit(1)

def main():
    """Fonction principale CLI."""
    check_python_version(); check_python_dependencies() # Checks initiaux
    parser = argparse.ArgumentParser(description=f"NVBuilder v{VERSION} - Créateur d'archives auto-extractibles Bash.", formatter_class=argparse.RawTextHelpFormatter, prog="nvbuilder")
    parser.add_argument('--config', '-c', default=DEFAULT_CONFIG_FILENAME, help=f"Fichier config YAML (défaut: {DEFAULT_CONFIG_FILENAME}).")
    parser.add_argument('--interactive', '-i', action='store_true', help="Mode interactif pour config.")
    parser.add_argument('--exclude-standard', '-e', action='store_true', help="Ajoute exclusions standard.")
    parser.add_argument('--list-standard-exclusions', '-l', action='store_true', help="Liste exclusions standard.")
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s v{VERSION}')
    args = parser.parse_args()

    if args.list_standard_exclusions: list_standard_exclusions(); sys.exit(0)
    if args.interactive: print(f"{YELLOW}Lancement mode interactif...{RESET}"); run_interactive_config(args.config); sys.exit(0)

    # --- Mode Build ---
    exit_code = 1 # Défaut = échec
    try:
        # NvBuilder gère maintenant son propre logging détaillé
        builder = NvBuilder(config_path_str=args.config, use_standard_exclusions=args.exclude_standard)
        output_script_path = builder.build()
        if output_script_path:
            # Afficher un message final clair sur la console (même si log INFO désactivé)
            print(f"\n{GREEN}>>> Build terminé avec succès !{RESET}")
            print(f"Script généré : {GREEN}{output_script_path}{RESET}")
            exit_code = 0 # Succès
        else:
            # L'erreur spécifique a déjà été logguée par NvBuilder
            print(f"\n{RED}>>> Échec du Build.{RESET}")
            print(f"{YELLOW}Consultez les messages ci-dessus ou le fichier log pour les détails.{RESET}")
            exit_code = 1 # Échec

    except NvBuilderError as e: # Erreurs prévues par NvBuilder
        print(f"\n{RED}ERREUR NVBUILDER: {e}{RESET}", file=sys.stderr)
        exit_code = 1
    except Exception as e: # Erreurs Python inattendues
        print(f"\n{RED}ERREUR INATTENDUE: {e}{RESET}", file=sys.stderr)
        # Afficher traceback complet pour ces erreurs
        traceback.print_exc()
        exit_code = 1
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Opération annulée par l'utilisateur.{RESET}")
        exit_code = 130
    finally:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()