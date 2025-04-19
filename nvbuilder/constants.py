# nvbuilder/constants.py
"""Constantes partagées pour nvBuilder."""
APP_NAME = "NvBuilder"
VERSION = "1.0" # Version mise à jour
ARCHIVE_MARKER = "__NVBUILDER_ARCHIVE_BELOW__" # Marqueur unique
TEMPLATE_FILENAME = "extractor_template.sh"
DEFAULT_CONFIG_FILENAME = "config.yaml"
DEFAULT_LOG_FILENAME = "nvbuilder.log"
DEFAULT_ENCRYPTION_TOOL = "openssl"
DEFAULT_OPENSSL_ITER = 10000
DEFAULT_OPENSSL_CIPHER = "aes-256-cbc"
DEFAULT_GPG_CIPHER_ALGO = "AES256"
DEFAULT_GPG_S2K_OPTIONS = "--s2k-mode 3 --s2k-digest-algo SHA512 --s2k-count 65011712"

# --- Constante pour le jeton ---
PASSWORD_CHECK_TOKEN = "nvbuilder_passwd_ok_v1" # Chaîne à chiffrer/vérifier

# Modes de mise à jour
UPDATE_MODES = ["check-only", "download-only", "auto-replace", "auto-replace-always"]
DEFAULT_UPDATE_MODE = "check-only"

# Clés de configuration attendues et valeurs par défaut
DEFAULT_CONFIG = {
    'content': './content',
    'script': 'start.sh',
    'output': {'path': 'autoextract.sh', 'need_root': False},
    'compression': {'method': 'gz', 'level': 9, 'encrypted': False, 'encryption_tool': DEFAULT_ENCRYPTION_TOOL},
    'exclude': {'patterns': [], 'ignore_case': True},
    'update': {'enabled': False, 'version_url': '', 'package_url': '', 'version_file_path': '', 'mode': DEFAULT_UPDATE_MODE},
    'hooks': {'pre_build': [], 'post_build': []},
    'logging': {'file': DEFAULT_LOG_FILENAME, 'level': 'INFO', 'format': '%(asctime)s - %(levelname)s - %(message)s', 'max_size': 10485760, 'backup_count': 3},
    'generate_metadata_file': True
}