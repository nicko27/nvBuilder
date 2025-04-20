# NvBuilder - Créateur d'Archives Auto-Extractibles

![Version](https://img.shields.io/badge/version-1.0-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)

NvBuilder est un outil Python permettant de créer facilement des archives auto-extractibles pour les systèmes Linux/Unix. L'outil génère des scripts Bash autonomes qui contiennent l'archive et qui peuvent l'extraire et exécuter un script post-extraction.

## 🚀 Fonctionnalités principales

- ✅ Création d'archives tar compressées (gzip, bzip2, xz)
- ✅ Chiffrement optionnel avec OpenSSL ou GPG
- ✅ Système de mise à jour intégré via HTTP
- ✅ Exécution automatique d'un script post-extraction
- ✅ Assistant de configuration interactif
- ✅ Personnalisation complète via fichier YAML
- ✅ Hooks pre/post build pour automatisation

## 📋 Prérequis

- Python 3.7 ou supérieur
- Dépendances (installées automatiquement):
  - PyYAML
  - Colorama

Pour le chiffrement (optionnel):
- OpenSSL ou GPG installé sur le système

## 💾 Installation

```bash

# Depuis les sources
git clone https://github.com/nicko27/nvbuilder.git
cd nvbuilder
pip3 install -r requirements.txt
```

## 🛠️ Utilisation rapide

### Mode interactif

```bash
nvbuilder --interactive
```

L'assistant vous guidera à travers la création d'un fichier de configuration.

### Ligne de commande

```bash
# Construction avec un fichier de configuration existant
nvbuilder --config mon_config.yaml

# Ajout des exclusions standard (comme .git/, __pycache__/, etc.)
nvbuilder --config mon_config.yaml --exclude-standard

# Mode interactif pour créer ou modifier le fichier yaml
nvbuilder --interactive

# Lister les exclusions standard
nvbuilder --list-standard-exclusions

# Mode debug (logs détaillés)
nvbuilder --debug
```

## 📝 Configuration

Le fichier de configuration YAML définit tous les aspects de votre archive auto-extractible.

```yaml
# Fichier source à archiver
content: "./monapp"

# Script à exécuter après extraction
script: "install.sh"

# Configuration de sortie
output:
  path: "monapp-installer.sh"
  need_root: false

# Compression et sécurité
compression:
  method: "gz"  # gz, bz2, xz ou none
  level: 9      # Niveau de compression (1-9)
  encrypted: true
  encryption_tool: "openssl"  # ou "gpg"

# Motifs d'exclusion
exclude:
  patterns:
    - "*.log"
    - ".git/"
    - "node_modules/"
  ignore_case: true

# Configuration de mise à jour HTTP
update:
  enabled: true
  mode: "check-only"  # check-only, download-only, auto-replace, auto-replace-always
  version_url: "https://example.com/version.json"
  package_url: "https://example.com/latest.sh"
  version_file_path: "./version.json"

# Hooks d'automatisation
hooks:
  pre_build:
    - "echo 'Début du build'"
    - "./scripts/pre_build.sh"
  post_build:
    - "echo 'Build terminé'"
    - "./scripts/post_build.sh"

# Génère un fichier JSON de métadonnées
generate_metadata_file: true
```

## 📋 Modes de mise à jour

NvBuilder propose plusieurs modes de mise à jour:

- **check-only**: Vérifie uniquement si une mise à jour est disponible
- **download-only**: Télécharge la nouvelle version sans l'installer
- **auto-replace**: Remplace automatiquement le script en demandant confirmation
- **auto-replace-always**: Remplace automatiquement le script sans demander de confirmation (compatible avec le chiffrement)

## 🔒 Chiffrement

Lorsque l'option `encrypted` est activée, l'archive intégrée est chiffrée. Le mot de passe sera demandé:
- Au moment de la création (pour le chiffrement)
- À l'exécution (pour le déchiffrement)

Deux outils de chiffrement sont supportés:
- **OpenSSL**: Utilise AES-256-CBC par défaut
- **GPG**: Symétrique, recommandé pour une meilleure compatibilité

## 🧰 Avancé: Documentation du fichier version.json

Le système de mise à jour utilise un fichier JSON pour vérifier les informations de version:

```json
{
  "build_version": "20230315123456",
  "generated_at": "2023-03-15T12:34:56.789012",
  "script_checksum_sha256": "abcdef1234567890...",
  "password_check_token_b64": "base64_encoded_encrypted_token...",
  "archive_info": {
    "size": 12345678,
    "files_included_count": 123,
    "post_extraction_script": "install.sh",
    "compression_method": "gz",
    "encryption_enabled": true,
    "encryption_tool": "openssl",
    "build_platform": "linux",
    "archive_checksum_sha256": "abcdef1234567890...",
    "encrypted_archive_checksum_sha256": "abcdef1234567890..."
  }
}
```

## 📊 Performances

Les performances dépendent principalement de la taille des fichiers et de la méthode de compression:

| Méthode | Niveau | Vitesse | Ratio |
|---------|--------|---------|-------|
| none    | -      | ★★★★★  | ★     |
| gz      | 1      | ★★★★   | ★★★   |
| gz      | 9      | ★★     | ★★★★  |
| bz2     | 9      | ★      | ★★★★★ |
| xz      | 9      | ★      | ★★★★★ |

## 🔍 Résolution des problèmes

### Logs détaillés

Pour obtenir des logs détaillés, utilisez l'option `--debug`:

```bash
nvbuilder --debug
```

### Problèmes de chiffrement

Si vous rencontrez des erreurs de chiffrement:

1. Vérifiez que l'outil de chiffrement (OpenSSL ou GPG) est installé
2. Pour GPG, assurez-vous que la version supporte l'option `--pinentry-mode loopback`

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.

## 🙏 Contributions

Les contributions sont les bienvenues! N'hésitez pas à ouvrir une issue ou une pull request.

---

Développé avec ❤️ pour simplifier la distribution d'applications Linux