# NvBuilder Python

Une version Python du script nvBuilder pour créer des scripts auto-extractibles.

## Installation

1. Cloner le dépôt
2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Configuration

Le script est entièrement configurable via un fichier YAML (`config.yaml` par défaut) :

```yaml
# Configuration principale
content: ./content  # Dossier de contenu à inclure
script: install.sh  # Script à exécuter après décompression
output: autoextract.sh  # Nom du script de sortie

# Configuration de la compression
compression:
  method: gz  # gz, bz2, xz
  level: 9    # 1-9 pour gz, 1-9 pour bz2, 0-9 pour xz

# Configuration des exclusions
exclude:
  patterns:
    - "*.pyc"           # Fichiers Python compilés
    - "*.pyo"           # Fichiers Python optimisés
    - "*.pyd"           # Fichiers Python DLL
    - "__pycache__"     # Dossier de cache Python
    - "*.log"           # Fichiers de log
    - "*.tmp"           # Fichiers temporaires
    - "*.bak"           # Fichiers de sauvegarde
    - ".git"            # Dossier Git
    - ".svn"            # Dossier Subversion
    - ".DS_Store"       # Fichiers système macOS
    - "Thumbs.db"       # Fichiers système Windows
  ignore_case: true     # Ignorer la casse des patterns

# Configuration de l'intégrité
integrity:
  enabled: true
  checksum: sha256  # sha256, sha512, md5
  verify: true     # Vérifier l'intégrité à l'extraction

# Configuration des mises à jour
update:
  enabled: false
  version_url: ""
  autoupdate_url: ""
  version_file: ""

# Configuration de la sortie
output:
  permissions: 755
  send_calling_dir: false
  need_root: false
  cleanup: true    # Nettoyer les fichiers temporaires après exécution

# Configuration du logging
logging:
  level: INFO
  file: nvbuilder.log
  format: '%(asctime)s - %(levelname)s - %(message)s'
  debug: false
  max_size: 10485760  # 10MB
  backup_count: 5

# Hooks personnalisables
hooks:
  pre_build: []
  post_build: []
  pre_extract: []
  post_extract: []
```

## Utilisation

Le script ne nécessite qu'un seul paramètre optionnel :

```bash
python nvbuilder.py [--config config.yaml]
```

### Options du script généré

Le script généré accepte les options suivantes :

```bash
--no-update      Désactive la mise à jour automatique
--debug          Active le mode debug
--extract-only   Extrait uniquement les fichiers
--no-verify      Désactive la vérification d'intégrité
--list-excluded  Affiche la liste des fichiers exclus
```

## Exemple d'utilisation

```bash
# Utilisation avec la configuration par défaut
python nvbuilder.py

# Utilisation avec une configuration personnalisée
python nvbuilder.py --config ma_config.yaml

# Extraction sans vérification d'intégrité
./autoextract.sh --no-verify

# Afficher la liste des fichiers exclus
./autoextract.sh --list-excluded
```

## Fonctionnalités

- Création de scripts auto-extractibles
- Mise à jour automatique via URL
- Gestion des versions
- Interface utilisateur simple
- Support du mode debug
- Extraction seule ou exécution de script
- Gestion des permissions root
- Configuration via fichier YAML
- Métadonnées avancées (version, date, taille, checksums)
- Vérification d'intégrité des archives et fichiers
- Nettoyage automatique des fichiers temporaires
- Logging configurable avec rotation des fichiers
- Hooks personnalisables (pre/post build/extract)
- Exclusion de fichiers par patterns globaux
- Liste des fichiers exclus

## Métadonnées

Le script généré inclut des métadonnées détaillées :

- Version du script
- Date de création
- Liste des fichiers avec leurs tailles et checksums
- Liste des fichiers exclus
- Checksum de l'archive complète
- Informations système (version Python, plateforme, architecture)

## Notes

- Le script nécessite Python 3.6 ou supérieur
- Le script généré utilise uniquement les bibliothèques standard de Python
- La vérification d'intégrité utilise SHA-256 par défaut
- Les fichiers temporaires sont nettoyés automatiquement après exécution
- Les logs sont automatiquement rotés lorsqu'ils atteignent la taille maximale
- Les patterns d'exclusion supportent les caractères spéciaux globaux (*, ?, [])
- La casse des patterns d'exclusion est ignorée par défaut 