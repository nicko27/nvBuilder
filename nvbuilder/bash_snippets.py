# nvbuilder/bash_snippets.py
"""Génère les snippets Bash conditionnels pour le template."""

import logging
from typing import Dict, Any

# Importer constantes et exceptions
from .constants import (DEFAULT_OPENSSL_CIPHER, DEFAULT_OPENSSL_ITER,
                        DEFAULT_GPG_CIPHER_ALGO, DEFAULT_GPG_S2K_OPTIONS,
                        PASSWORD_CHECK_TOKEN) # Importer le jeton en clair
from .exceptions import NvBuilderError

logger = logging.getLogger("nvbuilder")

try:
    from typing import TypedDict
    class BashSnippetsDict(TypedDict):
        update_vars: str; update_arg_parsing: str; update_help: str
        update_check_call: str; update_function: str
        encryption_vars: str; decryption_logic: str; decryption_cleanup: str
except ImportError:
    BashSnippetsDict = Dict[str, str]


# --- generate_update_snippets MODIFIÉE ---
def generate_update_snippets(config: Dict[str, Any], metadata: Dict[str, Any]) -> BashSnippetsDict:
    """Génère les snippets Bash relatifs à la mise à jour HTTP (avec jeton + hash)."""
    snippets: BashSnippetsDict = {key: "" for key in BashSnippetsDict.__annotations__}
    update_config = config.get('update', {})
    update_enabled = metadata.get('update_enabled', False)
    build_version = metadata.get('build_version', 'unknown')
    encryption_enabled = metadata.get('encryption_enabled', False) # Pour conditionner la logique Bash

    if update_enabled:
        version_url = update_config.get('version_url', '')
        package_url = update_config.get('package_url', '')
        try:
            import requests # Vérifier si dispo pour prévenir l'utilisateur
            HAS_REQUESTS = True
        except ImportError:
            HAS_REQUESTS = False
            # Log l'avertissement au moment du build si requests manque
            logger.warning("Module 'requests' manquant, nécessaire pour le build si MàJ activées.")
            # On ne bloque pas le build, mais la fonction MàJ échouera si requests n'est pas là
            # La vérification est faite dans __main__.py avant le build

        if not version_url or not package_url:
             logger.warning("MàJ activées mais URLs manquantes -> Snippets MàJ vides.")
             return snippets

        # Snippets pour arguments et aide (inchangés)
        snippets["update_vars"] = f'CURRENT_BUILD_VERSION="{build_version}"\nVERSION_URL="{version_url}"\nPACKAGE_URL="{package_url}"\nPASSWORD_CHECK_TOKEN="{PASSWORD_CHECK_TOKEN}"' # Ajouter jeton clair
        snippets["update_arg_parsing"] = '        --force-download) FORCE_DOWNLOAD=1; shift ;;\n        --no-update-check) NO_UPDATE_CHECK=1; shift ;;'
        snippets["update_help"] = ('  --force-download      Forcer le téléchargement de la dernière version.\n'
                                   '  --no-update-check     Ne pas vérifier les mises à jour.')
        
        # CORRECTION: S'assurer que update_check_call est toujours défini, même avec chiffrement
        snippets["update_check_call"] = 'if [ "$NO_UPDATE_CHECK" -eq 0 ]; then\n    check_for_updates_and_download_if_needed\nfi'

        # Fonction Bash complète avec logique jeton + hash
        bash_encryption_check = "true" if encryption_enabled else "false"
        # Récupérer les params de chiffrement globaux pour le fallback déchiffrement jeton
        enc_tool_global = metadata.get('encryption_tool', 'openssl')
        openssl_cipher_global = config.get('compression',{}).get('openssl_cipher', DEFAULT_OPENSSL_CIPHER)
        openssl_iter_global = config.get('compression',{}).get('openssl_iter', DEFAULT_OPENSSL_ITER)
        gpg_s2k_global = DEFAULT_GPG_S2K_OPTIONS

        snippets["update_function"] = f"""
# Fonction pour vérifier et télécharger les mises à jour (v2: Jeton + Hash)
check_for_updates_and_download_if_needed() {{
    echo "Vérification MàJ depuis $VERSION_URL..."
    local downloader="" remote_json="" latest_version="" script_checksum="" token_b64="" token_params_json=""
    local token_tool="{enc_tool_global}" # Outil par défaut
    local token_cipher="{openssl_cipher_global}" # Cipher par défaut
    local token_iter="{openssl_iter_global}" # Iter par défaut
    local token_s2k="{gpg_s2k_global}" # S2K par défaut
    local target_file=""

    # Déterminer téléchargeur
    if command -v curl &>/dev/null; then downloader="curl -fsSL --retry 3";
    elif command -v wget &>/dev/null; then downloader="wget --quiet --tries=3 -O-";
    else echo "${{YELLOW}}Avertissement: curl/wget absents.${{RESET}}" >&2; return 1; fi

    # Récupérer JSON distant
    if ! remote_json=$($downloader "$VERSION_URL"); then echo "${{YELLOW}}Avertissement: Échec récupération $VERSION_URL.${{RESET}}" >&2; return 1; fi
    if [ -z "$remote_json" ]; then echo "${{YELLOW}}Avertissement: Réponse vide de $VERSION_URL.${{RESET}}" >&2; return 1; fi
    debug_log "JSON distant reçu: $remote_json"

    # Parser JSON (méthode simple)
    # Fonction helper interne pour parser (suppose format "key": "value" ou "key": number)
    _json_extract() {{ echo "$1" | grep -o '"'$2'"\s*:\s*[^,}}]*' | sed -n 's/.*:\s*"\?\([^"]*\)"\?.*/\\1/p' | head -n 1; }}
    latest_version=$(_json_extract "$remote_json" "build_version")
    script_checksum=$(_json_extract "$remote_json" "script_checksum_sha256")
    token_b64=$(_json_extract "$remote_json" "password_check_token_b64")
    # TODO: Extraire token_encryption_params (nécessite parseur JSON plus robuste comme jq ou approche plus complexe avec grep/sed)
    # Pour l'instant, on utilisera les paramètres globaux définis plus haut.

    if [ -z "$latest_version" ]; then echo "${{YELLOW}}Avertissement: build_version distante non trouvée.${{RESET}}" >&2; return 1; fi
    echo "Actuelle: $CURRENT_BUILD_VERSION / Distante: $latest_version"

    # Comparer versions
    if [ "$latest_version" == "$CURRENT_BUILD_VERSION" ] && [ "$FORCE_DOWNLOAD" -eq 0 ]; then echo "${{GREEN}}Version à jour.${{RESET}}"; return 0; fi
    if [ "$FORCE_DOWNLOAD" -eq 1 ]; then echo "Téléchargement forcé..."; else echo "Nouvelle version $latest_version disponible."; fi

    # --- Vérification Jeton si Chiffré ---
    local password_ok=1 # Supposer OK si non chiffré ou pas de jeton
    if {bash_encryption_check}; then
        debug_log "Mode chiffré détecté, vérification jeton..."
        if [ -z "$token_b64" ] || [ "$token_b64" == "null" ]; then
             echo "${{YELLOW}}Avertissement: Jeton vérif mdp absent distant. Continuer ? [o/N]${{RESET}}" >&2
             local user_confirm=""
             read -r user_confirm </dev/tty
             if [[ ! "$user_confirm" =~ ^[OoYy]$ ]]; then echo "Abandon."; return 1; fi
             password_ok=1 # L'utilisateur force, on suppose OK mais c'est risqué
        else
             echo "Vérification du mot de passe via jeton chiffré..."
             local pass="" token_decrypted="" token_tmp_file=""
             token_tmp_file=$(mktemp "/tmp/nvb_token.XXXXXX")
             debug_log "Fichier temporaire pour jeton: $token_tmp_file"

             echo -n "Entrez le mot de passe (pour vérification jeton): " >&2; read -s pass </dev/tty; echo "" >&2
             if [ -z "$pass" ]; then echo "${{RED}}Mdp vide.${{RESET}}"; rm -f "$token_tmp_file"; return 1; fi

             debug_log "Décodage B64 du jeton..."
             if ! echo "$token_b64" | base64 -d > "$token_tmp_file"; then echo "${{RED}}Erreur décodage B64 du jeton.${{RESET}}"; rm -f "$token_tmp_file"; unset pass; return 1; fi
             debug_log "Taille jeton décodé: $(stat -f%z "$token_tmp_file" 2>/dev/null || stat -c%s "$token_tmp_file" 2>/dev/null || echo '?')"

             local decrypt_cmd="" decrypt_code=1
             debug_log "Tentative déchiffrement jeton avec outil: $ENCRYPTION_TOOL"
             if [ "$ENCRYPTION_TOOL" == "openssl" ]; then
                  export NVBUILDER_TOKEN_PASS="$pass"
                  decrypt_cmd="openssl enc -d -${{OPENSSL_CIPHER}} -pbkdf2 -iter ${{OPENSSL_ITER}} -in '$token_tmp_file' -pass env:NVBUILDER_TOKEN_PASS 2>/dev/null"
             elif [ "$ENCRYPTION_TOOL" == "gpg" ]; then
                  # Essayer avec puis sans S2K
                  decrypt_cmd="gpg --quiet --batch --yes --pinentry-mode loopback ${{GPG_S2K_OPTIONS}} --passphrase '$pass' --decrypt '$token_tmp_file' 2>/dev/null || gpg --quiet --batch --yes --pinentry-mode loopback --passphrase '$pass' --decrypt '$token_tmp_file' 2>/dev/null"
             fi

             # Exécuter et récupérer la sortie (le texte déchiffré)
             token_decrypted=$(eval $decrypt_cmd)
             decrypt_code=$?
             unset pass; [ "$ENCRYPTION_TOOL" == "openssl" ] && unset NVBUILDER_TOKEN_PASS; rm -f "$token_tmp_file"
             debug_log "Code retour déchiffrement jeton: $decrypt_code"

             if [ $decrypt_code -eq 0 ] && [ "$token_decrypted" == "$PASSWORD_CHECK_TOKEN" ]; then
                  echo "${{GREEN}}Vérification mot de passe OK.${{RESET}}"
                  password_ok=1
             else
                  echo "${{RED}}ERREUR: Vérification mot de passe échouée (mdp incorrect ou jeton invalide).${{RESET}}" >&2
                  debug_log "Jeton déchiffré (si erreur): '$token_decrypted' vs Attendu: '$PASSWORD_CHECK_TOKEN'"
                  password_ok=0
                  return 1 # Arrêter ici si le jeton ne correspond pas
             fi
        fi
    fi
    # --- Fin Vérification Jeton ---

    if [ $password_ok -eq 0 ]; then return 1; fi # Sécurité double check

    echo "Téléchargement depuis $PACKAGE_URL..."
    local url_basename; url_basename=$(basename "$PACKAGE_URL"); [ -z "$url_basename" ] || [[ "$url_basename" == "."* ]] && url_basename="$(basename "$0")_new"
    target_file="$SCRIPT_DIR/$url_basename" # Télécharge à côté
    debug_log "Fichier cible: $target_file"

    # Télécharger
    local dl_cmd=""; if [[ "$downloader" == "curl"* ]]; then dl_cmd="curl -fSL --retry 3 -o '$target_file' '$PACKAGE_URL'"; else dl_cmd="wget --quiet --tries=3 -O '$target_file' '$PACKAGE_URL'"; fi
    debug_log "Commande téléchargement: $dl_cmd"
    if ! eval $dl_cmd; then echo "${{RED}}Erreur: Téléchargement échoué ($?).${{RESET}}" >&2; rm -f "$target_file" 2>/dev/null; return 1; fi

    # Vérification Checksum Script
    if [ -z "$script_checksum" ] || [ "$script_checksum" == "null" ]; then echo "${{YELLOW}}Avertissement: Checksum script distant absent.${{RESET}}" >&2;
    elif ! command -v sha256sum &>/dev/null; then echo "${{YELLOW}}Avertissement: 'sha256sum' non trouvé.${{RESET}}" >&2;
    else
        echo "Vérification checksum script ($script_checksum)..."
        local actual_checksum; actual_checksum=$(sha256sum "$target_file" | cut -d' ' -f1)
        debug_log "Checksum calculé: $actual_checksum"
        if [ "$actual_checksum" == "$script_checksum" ]; then echo "${{GREEN}}Checksum script OK.${{RESET}}";
        else echo "${{RED}}ERREUR: Checksum script invalide!${{RESET}}" >&2; debug_log "Attendu: $script_checksum"; rm -f "$target_file" 2>/dev/null; return 1; fi
    fi

    echo "${{GREEN}}Téléchargement vérifié: $target_file${{RESET}}"
    chmod +x "$target_file" 2>/dev/null
    echo "Veuillez remplacer manuellement '$SCRIPT_PATH' par ce nouveau fichier si vous le souhaitez."
    # Important: Ne PAS faire 'exit 0' ici, on veut que l'extraction continue.
    return 1 # Indiquer qu'on n'a pas quitté pour MàJ mais que le DL est fini.
}}
"""
    return snippets
# --- FIN generate_update_snippets MODIFIÉE ---

# --- generate_encryption_snippets (Identique v2.0.29) ---
def generate_encryption_snippets(config: Dict[str, Any], metadata: Dict[str, Any], archive_original_filename: str) -> BashSnippetsDict:
    snippets: BashSnippetsDict = {key: "" for key in BashSnippetsDict.__annotations__}
    encryption_enabled = metadata.get('encryption_enabled', False); encryption_tool = metadata.get('encryption_tool')
    if encryption_enabled and encryption_tool:
        enc_fname="archive."+("enc" if encryption_tool=="openssl" else "gpg"); dec_fname=archive_original_filename
        ossl_c=config.get('compression',{}).get('openssl_cipher', DEFAULT_OPENSSL_CIPHER); ossl_i=config.get('compression',{}).get('openssl_iter', DEFAULT_OPENSSL_ITER); gpg_s2k=DEFAULT_GPG_S2K_OPTIONS
        var_lines=[f'ENCRYPTION_TOOL="{encryption_tool}"', f'ENCRYPTED_TMP_FILENAME="{enc_fname}"', f'DECRYPTED_TMP_FILENAME="{dec_fname}"', f'OPENSSL_CIPHER="{ossl_c}"', f'OPENSSL_ITER="{ossl_i}"', f'GPG_S2K_OPTIONS="{gpg_s2k}"']
        snippets["encryption_vars"] = "\n".join(var_lines)
        snippets["decryption_logic"] = f"""
    echo "Vérification outil: $ENCRYPTION_TOOL..."; if ! command -v $ENCRYPTION_TOOL &>/dev/null; then echo "${{RED}}Erreur: Outil '$ENCRYPTION_TOOL' absent.${{RESET}}" >&2; exit 1; fi
    local attempts=0 max_attempts=3 code=1 cmd="" pass=""; while [ $attempts -lt $max_attempts ]; do
        echo -n "Mot de passe déchiffrement : " >&2; read -s pass </dev/tty; echo "" >&2; if [ -z "$pass" ]; then echo "${{YELLOW}}Mdp vide.${{RESET}}"; continue; fi
        echo "Tentative $((attempts + 1))..."; if [ "$ENCRYPTION_TOOL" == "openssl" ]; then export NVBUILDER_DEC_PASS="$pass"; cmd="openssl enc -d -${{OPENSSL_CIPHER}} -pbkdf2 -iter ${{OPENSSL_ITER}} -in '$ENCRYPTED_TMP_FILENAME' -out '$DECRYPTED_TMP_FILENAME' -pass env:NVBUILDER_DEC_PASS";
        elif [ "$ENCRYPTION_TOOL" == "gpg" ]; then cmd="gpg --quiet --batch --yes --pinentry-mode loopback ${{GPG_S2K_OPTIONS}} --passphrase '$pass' --output '$DECRYPTED_TMP_FILENAME' --decrypt '$ENCRYPTED_TMP_FILENAME' 2>/dev/null"; cmd+=" || "; cmd+="gpg --quiet --batch --yes --pinentry-mode loopback --passphrase '$pass' --output '$DECRYPTED_TMP_FILENAME' --decrypt '$ENCRYPTED_TMP_FILENAME' 2>/dev/null"; fi
        eval $cmd; code=$?; unset pass; [ "$ENCRYPTION_TOOL" == "openssl" ] && unset NVBUILDER_DEC_PASS; if [ $code -eq 0 ]; then echo "${{GREEN}}Déchiffrement OK.${{RESET}}"; break; fi
        echo "${{RED}}Échec (code $code). Mdp incorrect ?${{RESET}}" >&2; rm -f "$DECRYPTED_TMP_FILENAME" 2>/dev/null; attempts=$((attempts + 1)); if [ $attempts -ge $max_attempts ]; then echo "${{RED}}Trop d'échecs.${{RESET}}"; exit 1; fi; echo "$((max_attempts - attempts)) tentatives restantes." >&2;
    done; if [ $code -ne 0 ]; then exit 1; fi
"""
        snippets["decryption_cleanup"] = 'if [ "$DEBUG_MODE" -eq 0 ] && [ -f "$WORK_DIR/$DECRYPTED_TMP_FILENAME" ]; then rm -f "$WORK_DIR/$DECRYPTED_TMP_FILENAME"; fi'
    return snippets