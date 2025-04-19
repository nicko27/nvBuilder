#!/usr/bin/env python3
# nvbuilder.py - Script exécutable pour NvBuilder
"""
Ce script permet d'exécuter NvBuilder en tant que script autonome plutôt que comme module Python.
Il offre les mêmes fonctionnalités que l'exécution via `python -m nvbuilder`.

Utilisation:
    python nvbuilder.py [OPTIONS]
    ./nvbuilder.py [OPTIONS]  # Si le script est rendu exécutable (chmod +x nvbuilder.py)

Ce script doit être placé à la racine du projet NvBuilder, où se trouve le dossier du module `nvbuilder`.
"""

import sys
import os
from pathlib import Path

# Obtenir le chemin absolu du répertoire contenant ce script
script_dir = Path(__file__).parent.absolute()

# Vérifier que la structure du module est correcte
nvbuilder_package_dir = script_dir / "nvbuilder"
nvbuilder_main = nvbuilder_package_dir / "__main__.py"

if not nvbuilder_package_dir.is_dir() or not nvbuilder_main.is_file():
    print("Structure de package incohérente. Ce script doit être exécuté depuis la racine du projet NvBuilder.", file=sys.stderr)
    sys.exit(1)

# Ajouter le répertoire au chemin d'importation Python
sys.path.insert(0, str(script_dir))

try:
    # Importer et exécuter la fonction main du module
    from nvbuilder.__main__ import main
    
    if __name__ == "__main__":
        main()  # La fonction main() utilise sys.exit() en interne
except ImportError as e:
    print(f"Erreur d'importation: {e}", file=sys.stderr)
    print("Assurez-vous que le module nvbuilder est accessible depuis ce répertoire.", file=sys.stderr)
    sys.exit(1)