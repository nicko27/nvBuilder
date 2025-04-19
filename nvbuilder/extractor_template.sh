#!/bin/bash
# Options pour un script plus robuste :
set -euo pipefail

# =========================================================================
#  Configuration des couleurs - MODIFIEZ SELON VOS PRÉFÉRENCES
# =========================================================================
# Couleurs par fonction sémantique - modifiez les valeurs ici
ERROR_COLOR="\033[0;31m"      # Couleur pour les erreurs (rouge)
SUCCESS_COLOR="\033[0;32m"    # Couleur pour les succès/validations (vert)
WARNING_COLOR="\033[0;33m"    # Couleur pour les avertissements (jaune)
INFO_COLOR="\033[0;34m"       # Couleur pour les informations (bleu)
DETAIL_COLOR="\033[0;36m"     # Couleur pour les détails/données (cyan)
UPDATE_COLOR="\033[0;35m"     # Couleur pour les mises à jour (magenta)
DEBUG_COLOR="\033[0;90m"      # Couleur pour les messages debug (gris)

# Couleurs pour éléments spécifiques
BANNER_COLOR="\033[0;36m"     # Couleur pour les bannières (cyan)
HEADER_COLOR="\033[0;36m"     # Couleur pour les en-têtes (cyan)
FILENAME_COLOR="\033[0;36m"   # Couleur pour les noms de fichiers (cyan)
OPTION_COLOR="\033[0;36m"     # Couleur pour les options (cyan)
PATH_COLOR="\033[0;36m"       # Couleur pour les chemins (cyan)
KEY_COLOR="\033[0;36m"        # Couleur pour les clés (cyan)
VALUE_COLOR="\033[0;32m"      # Couleur pour les valeurs (vert)

# Styles
HIGHLIGHT_STYLE="\033[1m"     # Style pour mise en évidence (gras)
SUBTLE_STYLE="\033[0;90m"     # Style atténué (gris)
RESET_STYLE="\033[0m"         # Réinitialiser toute mise en forme

# Rétrocompatibilité pour le code existant
RED=$ERROR_COLOR
GREEN=$SUCCESS_COLOR
YELLOW=$WARNING_COLOR
BLUE=$INFO_COLOR
CYAN=$DETAIL_COLOR
MAGENTA=$UPDATE_COLOR
GRAY=$DEBUG_COLOR
BOLD=$HIGHLIGHT_STYLE
DIM=$SUBTLE_STYLE
RESET=$RESET_STYLE

# Désactiver les couleurs si sortie non-terminal ou si variable NO_COLOR est définie
if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ]; then
    ERROR_COLOR=""
    SUCCESS_COLOR=""
    WARNING_COLOR=""
    INFO_COLOR=""
    DETAIL_COLOR=""
    UPDATE_COLOR=""
    DEBUG_COLOR=""
    BANNER_COLOR=""
    HEADER_COLOR=""
    FILENAME_COLOR=""
    OPTION_COLOR=""
    PATH_COLOR=""
    KEY_COLOR=""
    VALUE_COLOR=""
    HIGHLIGHT_STYLE=""
    SUBTLE_STYLE=""
    RESET_STYLE=""
    
    # Mettre à jour les alias aussi
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    CYAN=""
    MAGENTA=""
    GRAY=""
    BOLD=""
    DIM=""
    RESET=""
fi


# Message initial toujours affiché
# echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}NVBuilder Script v%%NVBUILDER_VERSION%% (Build %%BUILD_VERSION%%) - Initialisation...${RESET_STYLE}"

# =========================================================================
#  Script auto-extractible généré par NVBuilder v%%NVBUILDER_VERSION%%
#  Date de création : %%CREATED_AT%%
#  Build : %%BUILD_VERSION%% (%%BUILD_USER_HOST%%)
# =========================================================================

# --- Configuration Interne ---
NVBUILDER_VERSION="%%NVBUILDER_VERSION%%"
BUILD_VERSION="%%BUILD_VERSION%%"
SCRIPT_MARKER_VALUE="%%ARCHIVE_MARKER%%"
TAR_COMMAND_FLAGS="%%TAR_COMMAND_FLAGS%%"
POST_EXTRACTION_SCRIPT="%%POST_EXTRACTION_SCRIPT%%"
CONTENT_SOURCE_DIR="%%CONTENT_SOURCE_DIR%%"
ARCHIVE_CHECKSUM="%%ARCHIVE_CHECKSUM%%"
ENCRYPTED_CHECKSUM="%%ENCRYPTED_CHECKSUM%%"
PASSWORD_CHECK_TOKEN="nvbuilder_passwd_ok_v1"
NEED_ROOT="%%NEED_ROOT_BOOL%%"
# --- Fin Configuration Interne ---

# --- Variables de mise à jour (seront remplacées par les valeurs réelles) ---
CURRENT_BUILD_VERSION="%%BUILD_VERSION%%"
VERSION_URL="%%UPDATE_VERSION_URL%%"
PACKAGE_URL="%%UPDATE_PACKAGE_URL%%"
UPDATE_MODE="%%UPDATE_MODE%%"
# --- Fin variables de mise à jour ---

# --- Variables globales d'initialisation ---
NO_UPDATE_CHECK=0
FORCE_DOWNLOAD=0
NO_AUTO_UPDATE=0
# --- Fin Variables globales d'initialisation ---

# --- Début Variables et Blocs Conditionnels ---
# --- Début Encryption Vars ---
%%BASH_ENCRYPTION_VARS%%
# --- Fin Encryption Vars ---
# --- Fin Variables et Blocs Conditionnels ---

# --- Variables d'exécution ---
SCRIPT_NAME=$(basename "$0")
SCRIPT_PATH="" # Défini par get_script_path
SCRIPT_DIR=""  # Défini par get_script_path
EXTRACT_ONLY=0; SHOW_INFO=0; TARGET_DIR=""; DEBUG_MODE=0
# Variables pré-initialisées pour éviter les erreurs
WORK_DIR="/tmp/nvb_temp_$$"  # Sera écrasé mais pré-initialisé pour sécurité
EXTRACT_DEST="$WORK_DIR"     # Idem

# --- Fonctions Utilitaires ---
debug_log() { 
    if [ "${NVBUILDER_DEBUG_ENABLED:-0}" -eq 1 ] || [ "${DEBUG_MODE:-0}" -eq 1 ]; then 
        echo -e "${DEBUG_COLOR}DEBUG:${RESET_STYLE} $*" >&2
    fi
}
debug_log "Configuration des couleurs OK."

# Fonctions d'affichage améliorées
info() { echo -e "${INFO_COLOR}$*${RESET_STYLE}"; }
success() { echo -e "${SUCCESS_COLOR}$*${RESET_STYLE}"; }
warning() { echo -e "${WARNING_COLOR}$*${RESET_STYLE}" >&2; }
error() { echo -e "${ERROR_COLOR}$*${RESET_STYLE}" >&2; }
update_info() { echo -e "${UPDATE_COLOR}$*${RESET_STYLE}"; }
detail() { echo -e "${DETAIL_COLOR}$*${RESET_STYLE}"; }
header() { echo -e "${HEADER_COLOR}${HIGHLIGHT_STYLE}$*${RESET_STYLE}"; }

# Fonction pour afficher une belle bannière ASCII
display_banner() {
    local simple_mode=$1  # 1 = mode simple, 0 = mode complet
    
    # En mode normal (non-debug), afficher une bannière minimale ou rien du tout
    if [ "$DEBUG_MODE" -eq 0 ] && [ "$SHOW_INFO" -eq 0 ]; then
        # Afficher uniquement un message minimal si le script a un nom personnalisé
        if [ -n "$POST_EXTRACTION_SCRIPT" ]; then
            echo -e "${HIGHLIGHT_STYLE}• Initialisation...${RESET_STYLE}"
        fi
        return
    fi
    
    # Sinon, en mode debug ou info, afficher la bannière complète
    echo -e "${BANNER_COLOR}${HIGHLIGHT_STYLE}╔══════════════════════════════════════════════════════════╗${RESET_STYLE}"
    echo -e "${BANNER_COLOR}${HIGHLIGHT_STYLE}║                      ${INFO_COLOR}NV$BUILDER${BANNER_COLOR}                         ║${RESET_STYLE}"
    echo -e "${BANNER_COLOR}${HIGHLIGHT_STYLE}╚══════════════════════════════════════════════════════════╝${RESET_STYLE}"
    
    if [ "$simple_mode" -eq 1 ]; then
        # Mode simple - afficher seulement les informations essentielles
        echo -e " ${HIGHLIGHT_STYLE}Version:${RESET_STYLE} ${SUCCESS_COLOR}v${NVBUILDER_VERSION} ${RESET_STYLE}(Build ${DETAIL_COLOR}${BUILD_VERSION}${RESET_STYLE})"
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
            echo -e " ${HIGHLIGHT_STYLE}Chiffrement:${RESET_STYLE} ${SUCCESS_COLOR}Activé${RESET_STYLE} (${ENCRYPTION_TOOL:-openssl})"
        fi
        if [ "$NEED_ROOT" = "true" ]; then
            echo -e " ${HIGHLIGHT_STYLE}Droits:${RESET_STYLE} ${SUCCESS_COLOR}Administrateur requis${RESET_STYLE}"
        fi
        echo -e " ${HIGHLIGHT_STYLE}Script:${RESET_STYLE} ${DETAIL_COLOR}${POST_EXTRACTION_SCRIPT}${RESET_STYLE}"
        echo
    else
        # Mode détaillé pour --info ou mode debug
        echo -e " ${HIGHLIGHT_STYLE}Version:${RESET_STYLE}      ${SUCCESS_COLOR}v${NVBUILDER_VERSION}${RESET_STYLE} (Build ${DETAIL_COLOR}${BUILD_VERSION}${RESET_STYLE})"
        echo -e " ${HIGHLIGHT_STYLE}Créé le:${RESET_STYLE}      %%CREATED_AT%%"
        echo -e " ${HIGHLIGHT_STYLE}Par:${RESET_STYLE}          %%BUILD_USER_HOST%%"
        
        echo -e " ${HIGHLIGHT_STYLE}Source:${RESET_STYLE}       ${DETAIL_COLOR}%%CONTENT_SOURCE_DIR%%${RESET_STYLE}"
        echo -e " ${HIGHLIGHT_STYLE}Script:${RESET_STYLE}       ${DETAIL_COLOR}${POST_EXTRACTION_SCRIPT}${RESET_STYLE}"
        echo -e " ${HIGHLIGHT_STYLE}Compression:${RESET_STYLE}  %%COMPRESSION_DISPLAY%%"
        
        echo -ne " ${HIGHLIGHT_STYLE}Chiffrement:${RESET_STYLE}  "
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
            echo -e "${SUCCESS_COLOR}Activé${RESET_STYLE} (%%ENCRYPTION_TOOL_DISPLAY%%)"
        else
            echo -e "${WARNING_COLOR}Désactivé${RESET_STYLE}"
        fi
        
        echo -ne " ${HIGHLIGHT_STYLE}Mises à jour:${RESET_STYLE} "
        if %%BASH_UPDATE_ENABLED_BOOL%%; then
            echo -e "${SUCCESS_COLOR}Activées${RESET_STYLE} (Mode: ${UPDATE_MODE})"
        else
            echo -e "${WARNING_COLOR}Désactivées${RESET_STYLE}"
        fi
        echo
    fi
}

get_script_path() { 
    local source="$0"
    while [ -h "$source" ]; do 
        local dir
        dir="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    SCRIPT_PATH="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )/$(basename "$source")"
    SCRIPT_DIR="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
    export SCRIPT_PATH SCRIPT_DIR
    debug_log "SCRIPT_PATH=$SCRIPT_PATH"
}

check_root_privileges() {
    if [ "$NEED_ROOT" = "true" ] && [ "$(id -u)" -ne 0 ]; then
        echo -e "${WARNING_COLOR}${HIGHLIGHT_STYLE}Privilèges administrateur requis${RESET_STYLE}"
        echo -e "• Relance avec sudo...${RESET_STYLE}"
        
        # Vérifier si sudo est disponible
        if ! command -v sudo &>/dev/null; then
            echo -e "${ERROR_COLOR}Erreur: 'sudo' n'est pas disponible.${RESET_STYLE}" >&2
            echo -e "${ERROR_COLOR}Veuillez exécuter ce script en tant que root.${RESET_STYLE}" >&2
            exit 1
        fi
        
        # Relancer le script avec sudo, en préservant tous les arguments
        exec sudo "$SCRIPT_PATH" "$@"
        
        # Si exec échoue, arrêter l'exécution
        echo -e "${ERROR_COLOR}Échec de la relance avec sudo.${RESET_STYLE}" >&2
        exit 1
    fi
}

print_help() {
    cat << EOF
$(header "Usage: $SCRIPT_NAME [OPTIONS] [--] [ARGUMENTS_POUR_SCRIPT_POST_EXTRACTION...]")

Ce script extrait une archive intégrée et exécute un script post-extraction.

$(header "Options principales :")
  --extract-only      Extrait seulement le contenu, sans exécuter '$POST_EXTRACTION_SCRIPT'.
  --target-dir DIR    Extrait le contenu dans le répertoire DIR spécifié. Par défaut, un répertoire temporaire est créé et nettoyé ensuite, sauf si --extract-only est aussi utilisé (auquel cas un dossier ./<nom_script>_ext_<timestamp> est créé).
  --info              Affiche les informations détaillées sur cette archive et quitte.
  --debug             Active le mode debug (plus de messages, ne supprime pas le dossier temporaire).
  --help, -h          Affiche cette aide et quitte.
EOF
    if %%BASH_UPDATE_ENABLED_BOOL%%; then
        cat << EOFAJ

$(header "Options de mise à jour :")
  --force-download      Forcer le téléchargement de la dernière version.
  --no-update-check     Ne pas vérifier les mises à jour.
  --no-auto-update      Désactiver le remplacement automatique pour cette exécution.
EOFAJ
    fi
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        cat << EOFENC

$(warning "Note : Un mot de passe sera demandé pour déchiffrer le contenu.")
EOFENC
    fi
    if [ "$NEED_ROOT" = "true" ]; then
        cat << EOFROOT

$(warning "Ce script nécessite des privilèges administrateur et tentera de s'exécuter avec sudo si nécessaire.")
EOFROOT
    fi
    cat << EOFEARGS

Tous les arguments après '--' (ou les arguments non reconnus comme options)
seront passés directement au script '$POST_EXTRACTION_SCRIPT'.
EOFEARGS
}
debug_log "Définition print_help OK."

display_info() {
    # Afficher la bannière en mode détaillé
    display_banner 0
    
    # Informations supplémentaires très détaillées
    echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}+------------------------------------------------------+${RESET_STYLE}"
    echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}| Informations techniques détaillées                   |${RESET_STYLE}"
    echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}+------------------------------------------------------+${RESET_STYLE}"
    echo -e "${DETAIL_COLOR} Plateforme (build)  : ${RESET_STYLE}%%PLATFORM_BUILD%%"
    echo -e "${DETAIL_COLOR} Python (build)      : ${RESET_STYLE}%%PYTHON_VERSION_DISPLAY%%"
    echo -e "${DETAIL_COLOR} Exécution root      : ${RESET_STYLE}$([ "$NEED_ROOT" = "true" ] && echo "${SUCCESS_COLOR}Requise${RESET_STYLE}" || echo "${WARNING_COLOR}Non requise${RESET_STYLE}")"
    
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
        echo -e "${DETAIL_COLOR} Checksum (chiffré): ${RESET_STYLE}%%ENCRYPTED_CHECKSUM%%"
    fi
    echo -e "${DETAIL_COLOR} Checksum (original): ${RESET_STYLE}%%ARCHIVE_CHECKSUM%%"
    
    if %%BASH_UPDATE_ENABLED_BOOL%%; then 
        echo -e "${DETAIL_COLOR} URL Version        : ${RESET_STYLE}%%UPDATE_VERSION_URL%%"
        echo -e "${DETAIL_COLOR} URL Package        : ${RESET_STYLE}%%UPDATE_PACKAGE_URL%%"
    fi
    
    echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}+------------------------------------------------------+${RESET_STYLE}"
}
debug_log "Définition display_info OK."

cleanup() {
    local exit_code=$?
    local is_temp_dir=0
    trap - EXIT TERM INT
    debug_log "Cleanup: Démarrage avec code $exit_code"
    
    # Protection contre variables non définies
    if [ -z "${WORK_DIR:-}" ]; then
        debug_log "Cleanup: WORK_DIR non défini, sortie immédiate"
        exit $exit_code
    fi
    
    if [ -f "${WORK_DIR:-}/awk_output.tmp" ]; then 
        debug_log "Cleanup: Suppression awk_output.tmp"
        rm -f "${WORK_DIR}/awk_output.tmp"
    fi
    
    if [ "${DEBUG_MODE:-0}" -eq 0 ]; then 
        debug_log "Cleanup: Mode non-debug activé."
        if [ -n "${WORK_DIR:-}" ]; then 
            if [[ "${WORK_DIR:-}" == /tmp/nvb_* ]] || ([ -n "${EXTRACT_DEST:-}" ] && [[ "${WORK_DIR:-}" == "${EXTRACT_DEST:-}"/.nvb_temp_* ]]); then 
                is_temp_dir=1
            fi
        fi
        
        if [ $is_temp_dir -eq 1 ] && [ -d "${WORK_DIR:-}" ]; then 
            [ "$DEBUG_MODE" -eq 1 ] && echo -e "Nettoyage temp: ${DETAIL_COLOR}${WORK_DIR}${RESET_STYLE}"
            rm -rf "${WORK_DIR}"
        fi
        
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
            local skip_cleanup=0
            if [ "${EXTRACT_ONLY:-0}" -eq 1 ] && [ -n "${EXTRACT_DEST:-}" ]; then 
                local current_pwd
                current_pwd=$(pwd)
                if [[ "${EXTRACT_DEST:-}" == "$current_pwd/"* ]] && [[ "$(basename "${EXTRACT_DEST:-}")" == *_ext_* ]]; then 
                    skip_cleanup=1
                fi
            fi
            
            if [ $skip_cleanup -eq 0 ]; then 
                debug_log "Cleanup: Appel nettoyage déchiffrement..."
                %%BASH_DECRYPTION_CLEANUP%%
            else 
                debug_log "Cleanup: Nettoyage déchiffrement ignoré (extract-only vers PWD)."
            fi
        fi
    elif [ -n "${WORK_DIR:-}" ] && [ -d "${WORK_DIR:-}" ]; then 
        warning "Mode Debug : ${WORK_DIR} non supprimé."
        if %%BASH_ENCRYPTION_ENABLED_BOOL%% && [ -f "${WORK_DIR:-}/${DECRYPTED_TMP_FILENAME:-}" ]; then 
            warning "Mode Debug : Fichier déchiffré conservé"
        fi
    fi
    
    if [ "${DEBUG_MODE:-0}" -eq 1 ] && [[ $- == *x* ]]; then 
        set +x
    fi
    
    [ $exit_code -ne 0 ] && echo -e "• ${HIGHLIGHT_STYLE}Nettoyage des fichiers terminés (code sortie original: $exit_code).${RESET_STYLE}"
    exit $exit_code
}
debug_log "Définition cleanup OK."

find_archive_marker_line() { 
    local marker_pattern="^# NVBUILDER_MARKER_LINE: $SCRIPT_MARKER_VALUE"
    if [ -z "${SCRIPT_PATH:-}" ]; then 
        error "Erreur interne: SCRIPT_PATH non défini."
        return 1
    fi
    grep -n -m 1 "$marker_pattern" "$SCRIPT_PATH" | cut -d':' -f1
}
debug_log "Définition find_archive_marker_line OK."

# --- Fonctions conditionnelles (Injectées) ---
debug_log "Définition fonctions injectées..."
# --- Début Fonction Update ---
check_for_updates_and_download_if_needed() {
    # Masquer les messages en mode normal, sauf en cas d'erreur ou nouvelle version
    local QUIET_MODE=0
    [ "$DEBUG_MODE" -eq 0 ] && QUIET_MODE=1
    
    debug_log "Vérification MàJ depuis $VERSION_URL..."
    debug_log "URL Package: $PACKAGE_URL"
    debug_log "Mode update: $UPDATE_MODE"
    local downloader="" remote_json="" latest_version="" script_checksum="" update_success=0 replace_success=0
    local original_args=("$@")  # Sauvegarder les arguments originaux pour la relance

    # Déterminer téléchargeur
    if command -v curl &>/dev/null; then 
        downloader="curl -fsSL --retry 3"
    elif command -v wget &>/dev/null; then 
        downloader="wget --quiet --tries=3 -O-"
    else 
        [ "$QUIET_MODE" -eq 0 ] && echo -e "${WARNING_COLOR}Avertissement: curl/wget absents.${RESET_STYLE}" >&2
        [ "$QUIET_MODE" -eq 0 ] && echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi

    # Récupérer JSON distant
    echo -e "${HIGHLIGHT_STYLE}• Vérification des mises à jour...${RESET_STYLE}"
    debug_log "Tentative récupération: $VERSION_URL"
    if ! remote_json=$($downloader "$VERSION_URL"); then 
        echo -e "${WARNING_COLOR}Avertissement: Échec récupération $VERSION_URL.${RESET_STYLE}" >&2
        echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi
    if [ -z "$remote_json" ]; then 
        echo -e "${WARNING_COLOR}Avertissement: Réponse vide de $VERSION_URL.${RESET_STYLE}" >&2
        echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi
    debug_log "JSON distant reçu: $remote_json"

    # Parser JSON (méthode simple)
    # Fonction helper interne pour parser (suppose format "key": "value" ou "key": number)
    _json_extract() { 
        echo "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*:[ ]*"\(.*\)".*/\1/' | head -1 || \
        echo "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*[0-9][^,}]*" | sed 's/.*:[ ]*\([0-9][^,}]*\).*/\1/' | head -1
    }
    
    latest_version=$(_json_extract "$remote_json" "build_version")
    script_checksum=$(_json_extract "$remote_json" "script_checksum_sha256")
    local token_b64=$(_json_extract "$remote_json" "password_check_token_b64")
    
    if [ -z "$latest_version" ]; then 
        echo -e "${WARNING_COLOR}Avertissement: build_version distante non trouvée.${RESET_STYLE}" >&2
        echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi
    
    echo -en "  • ${HIGHLIGHT_STYLE}Actuelle: ${INFO_COLOR}$CURRENT_BUILD_VERSION${RESET_STYLE} / ${HIGHLIGHT_STYLE}Distante: ${INFO_COLOR}$latest_version${RESET_STYLE} "

    # Comparer versions
    if [ "$latest_version" == "$CURRENT_BUILD_VERSION" ] && [ "$FORCE_DOWNLOAD" -eq 0 ]; then 
        echo -e "${SUCCESS_COLOR}${HIGHLIGHT_STYLE}Version à jour.${RESET_STYLE}"
        return 0
    fi
    
    # À partir d'ici, montrer les messages même en mode silencieux car une nouvelle version est détectée
    if [ "$FORCE_DOWNLOAD" -eq 1 ]; then 
        echo -e "${RED}${HIGHLIGHT_STYLE}Téléchargement forcé...${RESET_STYLE}"
    else 
        echo -e "${SUCCESS_COLOR}Nouvelle version $latest_version disponible.${RESET_STYLE}"
    fi
    
    # Vérifions que l'URL de téléchargement est correcte
    if [ -z "$PACKAGE_URL" ] || [ "$PACKAGE_URL" = "N/A" ] || [ "$PACKAGE_URL" = "http://localhost/" ]; then
        echo -e "${ERROR_COLOR}Erreur: URL de téléchargement ($PACKAGE_URL) invalide ou non configurée.${RESET_STYLE}" >&2
        echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi

    # Vérification mot de passe si nécessaire (sauf en mode auto-replace-always)
    local password_ok=1
    local user_password=""
    
    # En mode auto-replace-always, définir user_password vide mais valide
    if [[ "$UPDATE_MODE" == "auto-replace-always" ]] && %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        password_ok=1
        user_password="auto_replace_always_bypass"
        echo -e "${WARNING_COLOR}Mode auto-replace-always activé - Vérification de mot de passe ignorée${RESET_STYLE}"
    elif %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        debug_log "Mode chiffré détecté, vérification jeton..."
        if [ -n "$token_b64" ] && [ "$token_b64" != "null" ]; then
            echo "Vérification du mot de passe via jeton chiffré..."
            local pass="" token_decrypted="" token_tmp_file=""
            token_tmp_file=$(mktemp "/tmp/nvb_token.XXXXXX" 2>/dev/null || mktemp -t nvb_token.XXXXXX)
            debug_log "Fichier temporaire pour jeton: $token_tmp_file"

            echo -n "Entrez le mot de passe (pour vérification jeton): " >&2
            read -s pass </dev/tty
            echo "" >&2
            if [ -z "$pass" ]; then 
                echo -e "${ERROR_COLOR}Mdp vide.${RESET_STYLE}"
                rm -f "$token_tmp_file"
                echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
                return 0
            fi
            
            # Stocker le mot de passe pour une utilisation ultérieure
            user_password="$pass"
            
            debug_log "Décodage B64 du jeton..."
            if ! echo "$token_b64" | base64 -d > "$token_tmp_file"; then 
                echo -e "${ERROR_COLOR}Erreur décodage B64 du jeton.${RESET_STYLE}"
                rm -f "$token_tmp_file"
                unset pass
                echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
                return 0
            fi
            
            debug_log "Taille jeton décodé: $(stat -f%z "$token_tmp_file" 2>/dev/null || stat -c%s "$token_tmp_file" 2>/dev/null || echo '?')"

            local decrypt_cmd="" decrypt_code=1
            debug_log "Tentative déchiffrement jeton avec outil: ${ENCRYPTION_TOOL:-openssl}"
            if [ "${ENCRYPTION_TOOL:-openssl}" == "openssl" ]; then
                export NVBUILDER_TOKEN_PASS="$pass"
                decrypt_cmd="openssl enc -d -${OPENSSL_CIPHER:-aes-256-cbc} -pbkdf2 -iter ${OPENSSL_ITER:-10000} -in '$token_tmp_file' -pass env:NVBUILDER_TOKEN_PASS 2>/dev/null"
            elif [ "${ENCRYPTION_TOOL:-openssl}" == "gpg" ]; then
                decrypt_cmd="gpg --quiet --batch --yes --pinentry-mode loopback ${GPG_S2K_OPTIONS:---s2k-mode 3 --s2k-digest-algo SHA512 --s2k-count 65011712} --passphrase '$pass' --decrypt '$token_tmp_file' 2>/dev/null || gpg --quiet --batch --yes --pinentry-mode loopback --passphrase '$pass' --decrypt '$token_tmp_file' 2>/dev/null"
            fi

            # Exécuter et récupérer la sortie (le texte déchiffré)
            token_decrypted=$(eval $decrypt_cmd)
            decrypt_code=$?
            [ "${ENCRYPTION_TOOL:-openssl}" == "openssl" ] && unset NVBUILDER_TOKEN_PASS
            rm -f "$token_tmp_file"
            debug_log "Code retour déchiffrement jeton: $decrypt_code"

            if [ $decrypt_code -eq 0 ] && [ "$token_decrypted" == "$PASSWORD_CHECK_TOKEN" ]; then
                echo -e "${SUCCESS_COLOR}Vérification mot de passe OK.${RESET_STYLE}"
                password_ok=1
            else
                echo -e "${ERROR_COLOR}ERREUR: Vérification mot de passe échouée (mdp incorrect ou jeton invalide).${RESET_STYLE}" >&2
                debug_log "Jeton déchiffré (si erreur): '$token_decrypted' vs Attendu: '$PASSWORD_CHECK_TOKEN'"
                password_ok=0
                unset pass
                echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
                return 0
            fi
            unset pass
        else
            echo -e "${WARNING_COLOR}Avertissement: Jeton vérif mdp absent distant. Continuer ? [o/N]${RESET_STYLE}" >&2
            local user_confirm=""
            read -r user_confirm </dev/tty
            if [[ ! "$user_confirm" =~ ^[OoYy]$ ]]; then 
                echo "Abandon."
                echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
                return 0
            fi
        fi
    fi

    # Téléchargement du script
    echo -e "${INFO_COLOR}Téléchargement depuis $PACKAGE_URL...${RESET_STYLE}"
    local url_basename
    url_basename=$(basename "$PACKAGE_URL")
    [ -z "$url_basename" ] || [[ "$url_basename" == "."* ]] && url_basename="$(basename "$0")_new"
    local target_file="$SCRIPT_DIR/$url_basename"
    debug_log "Fichier cible: $target_file"

    local dl_cmd=""
    if [[ "$downloader" == "curl"* ]]; then 
        dl_cmd="curl -fSL --retry 3 -o '$target_file' '$PACKAGE_URL'"
    else 
        dl_cmd="wget --quiet --tries=3 -O '$target_file' '$PACKAGE_URL'"
    fi
    debug_log "Commande téléchargement: $dl_cmd"
    
    if ! eval $dl_cmd; then 
        echo -e "${ERROR_COLOR}Erreur: Téléchargement échoué.${RESET_STYLE}" >&2
        rm -f "$target_file" 2>/dev/null
        echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
        return 0
    fi

    # Vérification Checksum Script
    if [ -n "$script_checksum" ] && [ "$script_checksum" != "null" ]; then
        if command -v sha256sum &>/dev/null; then
            echo "Vérification checksum script ($script_checksum)..."
            local actual_checksum
            actual_checksum=$(sha256sum "$target_file" | cut -d' ' -f1)
            debug_log "Checksum calculé: $actual_checksum"
            
            if [ "$actual_checksum" == "$script_checksum" ]; then 
                echo -e "${SUCCESS_COLOR}Checksum script OK.${RESET_STYLE}"
            else 
                echo -e "${ERROR_COLOR}ERREUR: Checksum script invalide!${RESET_STYLE}" >&2
                debug_log "Attendu: $script_checksum"
                rm -f "$target_file" 2>/dev/null
                echo -e "${WARNING_COLOR}Poursuite de l'extraction normale.${RESET_STYLE}"
                return 0
            fi
        else
            echo -e "${WARNING_COLOR}Avertissement: 'sha256sum' non trouvé, vérification ignorée.${RESET_STYLE}" >&2
        fi
    else
        echo -e "${WARNING_COLOR}Avertissement: Checksum script distant absent.${RESET_STYLE}" >&2
    fi

    chmod +x "$target_file" 2>/dev/null
    update_success=1
    echo -e "${SUCCESS_COLOR}▶ Téléchargement réussi: $target_file${RESET_STYLE}"
    echo -e "${DETAIL_COLOR}▶ Taille: $(stat -f%z "$target_file" 2>/dev/null || stat -c%s "$target_file" 2>/dev/null || echo 'inconnue') octets${RESET_STYLE}"
    
    # Mode de mise à jour selon configuration
    debug_log "Mode update configuré: $UPDATE_MODE (NO_AUTO_UPDATE=$NO_AUTO_UPDATE)"
    if [[ "$UPDATE_MODE" == "auto-replace"* ]] && [ "$NO_AUTO_UPDATE" -eq 0 ]; then
        # Afficher un message plus détaillé pour auto-replace-always
        if [[ "$UPDATE_MODE" == "auto-replace-always" ]]; then
            echo -e "${UPDATE_COLOR}Mode auto-replace-always - Installation automatique de la mise à jour...${RESET_STYLE}"
        else
            echo "Mode auto-replace - Remplacement du script en cours..."
        fi
        
        local backup_file="$SCRIPT_PATH.bak"
        
        # Créer une sauvegarde
        if ! cp "$SCRIPT_PATH" "$backup_file"; then
            echo -e "${WARNING_COLOR}Avertissement: Échec création sauvegarde.${RESET_STYLE}" >&2
        else
            chmod +x "$backup_file" 2>/dev/null
            echo "Sauvegarde créée: $backup_file"
        fi
        
        # Remplacer le script actuel
        if cp "$target_file" "$SCRIPT_PATH"; then
            chmod +x "$SCRIPT_PATH" 2>/dev/null
            replace_success=1
            if [[ "$UPDATE_MODE" == "auto-replace-always" ]]; then
                echo -e "${SUCCESS_COLOR}╔═══════════════════════════════════════════════════════╗${RESET_STYLE}"
                echo -e "${SUCCESS_COLOR}║  MISE À JOUR INSTALLÉE AVEC SUCCÈS                    ║${RESET_STYLE}"
                echo -e "${SUCCESS_COLOR}╚═══════════════════════════════════════════════════════╝${RESET_STYLE}"
                echo -e "${DETAIL_COLOR}• Nouvelle version: $latest_version${RESET_STYLE}"
                echo -e "${DETAIL_COLOR}• Mode: $UPDATE_MODE${RESET_STYLE}"
                echo -e "${DETAIL_COLOR}• Fichier: $SCRIPT_PATH${RESET_STYLE}"
            else
                echo -e "${SUCCESS_COLOR}Remplacement réussi.${RESET_STYLE}"
            fi
            
            # Si le script est en cours d'exécution, quitter pour le relancer
            if [ "$replace_success" -eq 1 ]; then
                echo -e "${SUCCESS_COLOR}Relance du script avec la nouvelle version...${RESET_STYLE}"
                # Exécuter le nouveau script avec les mêmes arguments mais en désactivant la vérification
                # pour éviter une boucle infinie
                if [ ${#original_args[@]} -gt 0 ]; then
                    # Relancer avec les arguments originaux si présents
                    exec "$SCRIPT_PATH" --no-update-check "${original_args[@]}"
                else
                    # Relancer sans arguments supplémentaires
                    exec "$SCRIPT_PATH" --no-update-check
                fi
                # exec ne retourne jamais si réussi, sinon on continue
                echo -e "${WARNING_COLOR}Échec de relance. Poursuite avec l'extraction.${RESET_STYLE}" >&2
            fi
        else
            echo -e "${ERROR_COLOR}Échec du remplacement. L'extraction va se poursuivre.${RESET_STYLE}" >&2
        fi
    elif [ "$UPDATE_MODE" == "download-only" ]; then
        echo "Mode Download-Only - Le script a été téléchargé à côté du script actuel."
        echo "Veuillez remplacer manuellement '$SCRIPT_PATH' par '$target_file' si vous le souhaitez."
    else
        echo "Mode Check-Only - Aucun remplacement automatique."
        echo "Veuillez remplacer manuellement '$SCRIPT_PATH' par '$target_file' si vous le souhaitez."
    fi
    
    # Continuer avec l'extraction
    return 0
}
# --- Fin Fonction Update ---
debug_log "Définition fonctions injectées OK."
# --- Fin Fonctions conditionnelles ---

debug_log "<<< Juste avant définition main() >>>"

# --- Fonction principale ---
function main {
    echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}Démarrage de ${HIGHLIGHT_STYLE}${SCRIPT_NAME}${RESET} v${HIGHLIGHT_STYLE}%%BUILD_VERSION%%${RESET}"
    debug_log "Entrée dans main()..."
    get_script_path
    check_root_privileges "$@"
    
    # Définir les variables d'environnement immédiatement pour éviter les erreurs
    # Ces variables sont cruciales pour le fonctionnement du script et la gestion des erreurs
    local WORK_DIR="" EXTRACT_DEST="" need_intermediate_temp=0
    export WORK_DIR EXTRACT_DEST
    
    # Installer le gestionnaire après avoir défini les variables cruciales
    trap cleanup EXIT TERM INT

    # Afficher la bannière au début
    if [ "$SHOW_INFO" -eq 0 ]; then
        # Affichage standard (simple ou détaillé selon mode debug)
        local simple_mode=1
        [ "$DEBUG_MODE" -eq 1 ] && simple_mode=0
        display_banner "$simple_mode"
    fi
    
    if [ "$DEBUG_MODE" -eq 1 ]; then
        warning "Mode Debug activé (traces Bash actives)."
        NVBUILDER_DEBUG_ENABLED=1
        export NVBUILDER_DEBUG_ENABLED
        set -x
    fi
    
    if [ "$SHOW_INFO" -eq 1 ]; then
        display_info
        exit 0
    fi

    # Vérification explicite et visible des mises à jour
    debug_log "Appel vérification MàJ (si activé)..."
    if %%BASH_UPDATE_ENABLED_BOOL%%; then
        [ "$DEBUG_MODE" -eq 1 ] && update_info "Vérification des mises à jour activée..."
        if [ "$NO_UPDATE_CHECK" -eq 0 ]; then
            if type check_for_updates_and_download_if_needed >/dev/null 2>&1; then
                check_for_updates_and_download_if_needed "$@"
            else
                [ "$DEBUG_MODE" -eq 1 ] && warning "Avertissement: Fonction de mise à jour non disponible."
            fi
        else
            [ "$DEBUG_MODE" -eq 1 ] && warning "Vérification des mises à jour désactivée par option --no-update-check."
        fi
    else
        debug_log "Mises à jour HTTP désactivées dans la configuration."
    fi

    # Initialisation des répertoires de travail
    if [ -n "$TARGET_DIR" ]; then
        local target_dir_resolved
        if [[ "$TARGET_DIR" != /* ]]; then target_dir_resolved="$PWD/$TARGET_DIR"; else target_dir_resolved="$TARGET_DIR"; fi
        if ! mkdir -p "$target_dir_resolved"; then error "Erreur: Création dossier cible '$target_dir_resolved' échouée."; exit 1; fi
        EXTRACT_DEST=$(cd "$target_dir_resolved" && pwd)
        if ! WORK_DIR=$(mktemp -d "${EXTRACT_DEST}/.nvb_temp_XXXXXX"); then error "Erreur: Création temp dans '$EXTRACT_DEST' échouée."; exit 1; fi
        [ "$DEBUG_MODE" -eq 1 ] && info "Extraction vers '${DETAIL_COLOR}$EXTRACT_DEST${RESET_STYLE}' (via '${DEBUG_COLOR}$WORK_DIR${RESET_STYLE}')..."
        need_intermediate_temp=1
    elif [ "$EXTRACT_ONLY" -eq 1 ]; then
        local ts; ts=$(date +%Y%m%d_%H%M%S); local base; base="${SCRIPT_NAME%.sh}"; local ed; ed="./${base}_ext_${ts}_$$"
        if ! mkdir -p "$ed"; then error "Erreur: Création dossier extract '$ed' échouée."; exit 1; fi
        EXTRACT_DEST=$(cd "$ed" && pwd); WORK_DIR="$EXTRACT_DEST"
        info "Extraction seule vers : ${DETAIL_COLOR}$EXTRACT_DEST${RESET_STYLE}"
    else
        if ! WORK_DIR=$(mktemp -d "/tmp/nvb_${SCRIPT_NAME}_$.XXXXXX"); then 
            warning "Avert: Création temp /tmp échouée, essai PWD..."
            if ! WORK_DIR=$(mktemp -d "./nvb_temp_$.XXXXXX"); then 
                error "Erreur: Création temp PWD échouée."
                exit 1
            fi
        fi
        EXTRACT_DEST="$WORK_DIR"
        [ "$DEBUG_MODE" -eq 1 ] && info "Extraction vers temp : ${DETAIL_COLOR}$WORK_DIR${RESET_STYLE}"
    fi
    
    # Mettre à jour les variables exportées
    export WORK_DIR EXTRACT_DEST
    debug_log "WORK_DIR='$WORK_DIR', EXTRACT_DEST='$EXTRACT_DEST'"

    # Recherche du marqueur d'archive
    debug_log "Recherche marqueur..."
    local archive_start_line
    archive_start_line=$(find_archive_marker_line)
    if [ -z "$archive_start_line" ]; then 
        error "Erreur: Marqueur unique non trouvé ('# NVBUILDER_MARKER_LINE: $SCRIPT_MARKER_VALUE')."
        exit 1
    fi
    local data_start_line=$((archive_start_line + 1))
    debug_log "Marqueur trouvé: L$archive_start_line. Données: L$data_start_line."

    # Extraction des données base64
    debug_log "Préparation extraction B64..."
    [ "$DEBUG_MODE" -eq 1 ] && info "Extraction B64 interne..."
    local awk_output_file="$WORK_DIR/awk_output.tmp"
    debug_log "Commande awk: awk \"NR >= $data_start_line\" \"$SCRIPT_PATH\" > \"$awk_output_file\""
    if ! awk "NR >= $data_start_line" "$SCRIPT_PATH" > "$awk_output_file"; then 
        error "Erreur: awk échoué ($?)."
        exit 1
    fi
    
    debug_log "Vérification sortie awk:"
    [ "$DEBUG_MODE" -eq 1 ] && ls -l "$awk_output_file" 2>/dev/null || true
    local awk_file_size
    awk_file_size=$(stat -f%z "$awk_output_file" 2>/dev/null || stat -c%s "$awk_output_file" 2>/dev/null || echo 0)
    if [ "$awk_file_size" -eq 0 ]; then 
        error "Erreur: Fichier awk vide."
        exit 1
    fi
    
    if [ "$DEBUG_MODE" -eq 1 ]; then 
        detail "Début(100o):"
        head -c 100 "$awk_output_file"
        echo ""
        detail "Fin(100o):"
        tail -c 100 "$awk_output_file"
        echo ""
    fi
    
    [ "$DEBUG_MODE" -eq 1 ] && info "Décodage B64..."
    local target_decoded_file
    local decoded_filename
    
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
        decoded_filename="$ENCRYPTED_TMP_FILENAME"
    else 
        decoded_filename="%%ARCHIVE_ORIGINAL_FILENAME%%"
    fi
    
    target_decoded_file="$WORK_DIR/$decoded_filename"
    debug_log "Commande base64: base64 -d < \"$awk_output_file\" > \"$target_decoded_file\""
    
    if ! base64 -d < "$awk_output_file" > "$target_decoded_file"; then 
        error "Erreur: Échec décodage B64."
        [ "$DEBUG_MODE" -eq 0 ] && rm -f "$awk_output_file"
        rm -f "$target_decoded_file" 2>/dev/null
        exit 1
    fi
    
    if [ ! -s "$target_decoded_file" ]; then 
        error "Erreur: Fichier vide après décodage B64."
        exit 1
    fi
    
    [ "$DEBUG_MODE" -eq 1 ] && success "Décodage B64 OK."
    [ "$DEBUG_MODE" -eq 0 ] && rm -f "$awk_output_file"

    # Déchiffrement si nécessaire
    debug_log "Préparation déchiffrement..."
    local original_pwd
    original_pwd=$PWD
    
    if ! cd "$WORK_DIR"; then 
        error "Erreur: cd '$WORK_DIR' échoué."
        exit 1
    fi
    
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        %%BASH_DECRYPTION_LOGIC%%
    fi
    
    cd "$original_pwd" # Revenir APRÈS le bloc if complet

    # --- Décompression Tar ---
    local tar_input_src_fname
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
        tar_input_src_fname="$DECRYPTED_TMP_FILENAME"
    else 
        tar_input_src_fname="%%ARCHIVE_ORIGINAL_FILENAME%%"
    fi
    
    [ "$DEBUG_MODE" -eq 1 ] && info "Décompression '${DETAIL_COLOR}$tar_input_src_fname${RESET_STYLE}'..."
    debug_log "Commande Tar: (cd \"$WORK_DIR\" && tar \"$TAR_COMMAND_FLAGS\" \"$tar_input_src_fname\")"
    
    if ! (cd "$WORK_DIR" && tar "$TAR_COMMAND_FLAGS" "$tar_input_src_fname"); then 
        local tar_exit_code=$?
        error "Erreur: Tar échoué (code: $tar_exit_code)."
        if [ "$DEBUG_MODE" -eq 1 ]; then
            detail "Contenu du répertoire de travail:"
            ls -lA "$WORK_DIR" >&2
        fi
        exit 1
    fi
    
    [ "$DEBUG_MODE" -eq 1 ] && success "Décompression OK."

    # --- Nettoyage tar source ---
    if [ "$DEBUG_MODE" -eq 0 ]; then 
        if [ -f "$WORK_DIR/$tar_input_src_fname" ]; then 
            debug_log "Nettoyage $tar_input_src_fname"
            rm -f "$WORK_DIR/$tar_input_src_fname"
        fi
        
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
            if [ -f "$WORK_DIR/$ENCRYPTED_TMP_FILENAME" ]; then 
                debug_log "Nettoyage $ENCRYPTED_TMP_FILENAME"
                rm -f "$WORK_DIR/$ENCRYPTED_TMP_FILENAME"
            fi
        fi
    fi

    # --- Exécution du script post-extraction ---
    if [ "$EXTRACT_ONLY" -eq 0 ]; then
        if [ -z "$POST_EXTRACTION_SCRIPT" ]; then
            warning "Aucun script post-extraction configuré."
        elif [ ! -f "$EXTRACT_DEST/$POST_EXTRACTION_SCRIPT" ]; then
            error "Script '$POST_EXTRACTION_SCRIPT' non trouvé dans '$EXTRACT_DEST'."
            exit 1
        elif [ ! -x "$EXTRACT_DEST/$POST_EXTRACTION_SCRIPT" ]; then
            warning "'$POST_EXTRACTION_SCRIPT' non exécutable, ajout +x..."
            chmod +x "$EXTRACT_DEST/$POST_EXTRACTION_SCRIPT" || true
        fi
        
        if [ -f "$EXTRACT_DEST/$POST_EXTRACTION_SCRIPT" ]; then
            if [ "$DEBUG_MODE" -eq 1 ]; then
                header "Exécution script: $POST_EXTRACTION_SCRIPT (pwd: $EXTRACT_DEST)"
                (cd "$EXTRACT_DEST" && "./$POST_EXTRACTION_SCRIPT" "$@")
            else
                echo -e "${INFO_COLOR}${HIGHLIGHT_STYLE}• Lancement du script...${RESET_STYLE}"
                (cd "$EXTRACT_DEST" && "./$POST_EXTRACTION_SCRIPT" "$@")
            fi
            script_exit=$?
            
            if [ $script_exit -ne 0 ]; then
                warning "Script terminé avec code non-zéro: $script_exit"
            else
                [ "$DEBUG_MODE" -eq 1 ] && success "Script terminé avec succès!"
            fi
        fi
    else
        success "Extraction terminée dans '$EXTRACT_DEST'!"
    fi
}
# --- Analyse des arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        --extract-only) EXTRACT_ONLY=1; shift ;;
        --target-dir) 
            if [ -n "$2" ]; then TARGET_DIR="$2"; shift 2; 
            else error "Option --target-dir requiert un argument."; exit 1; fi ;;
        --target-dir=*) TARGET_DIR="${1#*=}"; shift ;;
        --info) SHOW_INFO=1; shift ;;
        --debug) DEBUG_MODE=1; shift ;;
        --help|-h) print_help; exit 0 ;;
        --force-download) FORCE_DOWNLOAD=1; shift ;;
        --no-update-check) NO_UPDATE_CHECK=1; shift ;;
        --no-auto-update) NO_AUTO_UPDATE=1; shift ;;
        --) shift; break ;;
        -*) warning "Option inconnue: $1 (traité comme un argument post-extraction)"; break ;;
        *) break ;;
    esac
done

# --- Appel de la fonction principale ---
main "$@"
exit $?

# NVBUILDER_MARKER_LINE: %%ARCHIVE_MARKER%%