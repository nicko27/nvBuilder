
#!/bin/bash
# Options pour un script plus robuste :
set -euo pipefail

# =========================================================================
#  Configuration des couleurs
# =========================================================================
# Définir les couleurs - facile à modifier selon vos préférences
COLOR_RED="\033[0;31m"        # Erreurs
COLOR_GREEN="\033[0;32m"      # Succès
COLOR_YELLOW="\033[0;33m"     # Avertissements
COLOR_BLUE="\033[0;34m"       # Informations
COLOR_MAGENTA="\033[0;35m"    # Mises à jour
COLOR_CYAN="\033[0;36m"       # Détails
COLOR_GRAY="\033[0;90m"       # Debug
COLOR_BOLD="\033[1m"          # Texte en gras
COLOR_RESET="\033[0m"         # Réinitialisation

# Définir des alias pour compatibilité avec le code existant
RED=$COLOR_RED
GREEN=$COLOR_GREEN
YELLOW=$COLOR_YELLOW
BLUE=$COLOR_BLUE
MAGENTA=$COLOR_MAGENTA
CYAN=$COLOR_CYAN
GRAY=$COLOR_GRAY
BOLD=$COLOR_BOLD
RESET=$COLOR_RESET

# Désactiver les couleurs si sortie non-terminal ou si variable NO_COLOR est définie
if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ]; then
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_YELLOW=""
    COLOR_BLUE=""
    COLOR_MAGENTA=""
    COLOR_CYAN=""
    COLOR_GRAY=""
    COLOR_BOLD=""
    COLOR_RESET=""
    
    # Mettre à jour les alias aussi
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    CYAN=""
    GRAY=""
    BOLD=""
    RESET=""
fi


# Message initial toujours affiché
# echo -e "${COLOR_BLUE}${COLOR_BOLD}NVBuilder Script v%%NVBUILDER_VERSION%% (Build %%BUILD_VERSION%%) - Initialisation...${COLOR_RESET}"

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
        echo -e "${COLOR_GRAY}DEBUG:${COLOR_RESET} $*" >&2
    fi
}
debug_log "Configuration des couleurs OK."

# Fonctions d'affichage améliorées
info() { echo -e "${COLOR_BLUE}$*${COLOR_RESET}"; }
success() { echo -e "${COLOR_GREEN}$*${COLOR_RESET}"; }
warning() { echo -e "${COLOR_YELLOW}$*${COLOR_RESET}" >&2; }
error() { echo -e "${COLOR_RED}$*${COLOR_RESET}" >&2; }
update_info() { echo -e "${COLOR_MAGENTA}$*${COLOR_RESET}"; }
detail() { echo -e "${COLOR_CYAN}$*${COLOR_RESET}"; }
header() { echo -e "${COLOR_BOLD}$*${COLOR_RESET}"; }

# Fonction pour afficher une belle bannière ASCII
display_banner() {
    local simple_mode=$1  # 1 = mode simple, 0 = mode complet
    
    echo -e "${COLOR_CYAN}${COLOR_BOLD}╔══════════════════════════════════════════════════════════╗${COLOR_RESET}"
    echo -e "${COLOR_CYAN}${COLOR_BOLD}║                      ${COLOR_GREEN}NV${COLOR_BLUE}BUILDER${COLOR_CYAN}                         ║${COLOR_RESET}"
    echo -e "${COLOR_CYAN}${COLOR_BOLD}╚══════════════════════════════════════════════════════════╝${COLOR_RESET}"
    
    if [ "$simple_mode" -eq 1 ]; then
        # Mode simple - afficher seulement les informations essentielles
        echo -e " ${COLOR_BOLD}Version:${COLOR_RESET} ${COLOR_GREEN}v${NVBUILDER_VERSION} ${COLOR_RESET}(Build ${COLOR_CYAN}${BUILD_VERSION}${COLOR_RESET})"
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
            echo -e " ${COLOR_BOLD}Chiffrement:${COLOR_RESET} ${COLOR_GREEN}Activé${COLOR_RESET} (${ENCRYPTION_TOOL:-openssl})"
        fi
        echo -e " ${COLOR_BOLD}Script:${COLOR_RESET} ${COLOR_CYAN}${POST_EXTRACTION_SCRIPT}${COLOR_RESET}"
        echo
    else
        # Mode détaillé pour --info ou mode debug
        echo -e " ${COLOR_BOLD}Version:${COLOR_RESET}      ${COLOR_GREEN}v${NVBUILDER_VERSION}${COLOR_RESET} (Build ${COLOR_CYAN}${BUILD_VERSION}${COLOR_RESET})"
        echo -e " ${COLOR_BOLD}Créé le:${COLOR_RESET}      %%CREATED_AT%%"
        echo -e " ${COLOR_BOLD}Par:${COLOR_RESET}          %%BUILD_USER_HOST%%"
        
        echo -e " ${COLOR_BOLD}Source:${COLOR_RESET}       ${COLOR_CYAN}%%CONTENT_SOURCE_DIR%%${COLOR_RESET}"
        echo -e " ${COLOR_BOLD}Script:${COLOR_RESET}       ${COLOR_CYAN}${POST_EXTRACTION_SCRIPT}${COLOR_RESET}"
        echo -e " ${COLOR_BOLD}Compression:${COLOR_RESET}  %%COMPRESSION_DISPLAY%%"
        
        echo -ne " ${COLOR_BOLD}Chiffrement:${COLOR_RESET}  "
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
            echo -e "${COLOR_GREEN}Activé${COLOR_RESET} (%%ENCRYPTION_TOOL_DISPLAY%%)"
        else
            echo -e "${COLOR_YELLOW}Désactivé${COLOR_RESET}"
        fi
        
        echo -ne " ${COLOR_BOLD}Mises à jour:${COLOR_RESET} "
        if %%BASH_UPDATE_ENABLED_BOOL%%; then
            echo -e "${COLOR_GREEN}Activées${COLOR_RESET} (Mode: ${UPDATE_MODE})"
        else
            echo -e "${COLOR_YELLOW}Désactivées${COLOR_RESET}"
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
    echo -e "${COLOR_BLUE}${COLOR_BOLD}+------------------------------------------------------+${COLOR_RESET}"
    echo -e "${COLOR_BLUE}${COLOR_BOLD}| Informations techniques détaillées                   |${COLOR_RESET}"
    echo -e "${COLOR_BLUE}${COLOR_BOLD}+------------------------------------------------------+${COLOR_RESET}"
    echo -e "${COLOR_CYAN} Plateforme (build)  : ${COLOR_RESET}%%PLATFORM_BUILD%%"
    echo -e "${COLOR_CYAN} Python (build)      : ${COLOR_RESET}%%PYTHON_VERSION_DISPLAY%%"
    
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then 
        echo -e "${COLOR_CYAN} Checksum (chiffré): ${COLOR_RESET}%%ENCRYPTED_CHECKSUM%%"
    fi
    echo -e "${COLOR_CYAN} Checksum (original): ${COLOR_RESET}%%ARCHIVE_CHECKSUM%%"
    
    if %%BASH_UPDATE_ENABLED_BOOL%%; then 
        echo -e "${COLOR_CYAN} URL Version        : ${COLOR_RESET}%%UPDATE_VERSION_URL%%"
        echo -e "${COLOR_CYAN} URL Package        : ${COLOR_RESET}%%UPDATE_PACKAGE_URL%%"
    fi
    
    echo -e "${COLOR_BLUE}${COLOR_BOLD}+------------------------------------------------------+${COLOR_RESET}"
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
            echo -e "Nettoyage temp: ${COLOR_CYAN}${WORK_DIR}${COLOR_RESET}"
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
    
    [ $exit_code -ne 0 ] && echo -e "Cleanup terminé (code sortie original: $exit_code)."
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
    echo "Vérification MàJ depuis $VERSION_URL..."
    local downloader="" remote_json="" latest_version="" script_checksum="" update_success=0 replace_success=0
    local original_args=("$@")  # Sauvegarder les arguments originaux pour la relance
    
    debug_log "Mode de mise à jour configuré: $UPDATE_MODE"

    # Déterminer téléchargeur
    if command -v curl &>/dev/null; then 
        downloader="curl -fsSL --retry 3"
    elif command -v wget &>/dev/null; then 
        downloader="wget --quiet --tries=3 -O-"
    else 
        echo "${COLOR_YELLOW}Avertissement: curl/wget absents.${COLOR_RESET}" >&2
        echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
        return 0
    fi

    # Récupérer JSON distant
    debug_log "Tentative récupération: $VERSION_URL"
    if ! remote_json=$($downloader "$VERSION_URL"); then 
        echo "${COLOR_YELLOW}Avertissement: Échec récupération $VERSION_URL.${COLOR_RESET}" >&2
        echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
        return 0
    fi
    if [ -z "$remote_json" ]; then 
        echo "${COLOR_YELLOW}Avertissement: Réponse vide de $VERSION_URL.${COLOR_RESET}" >&2
        echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
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
        echo "${COLOR_YELLOW}Avertissement: build_version distante non trouvée.${COLOR_RESET}" >&2
        echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
        return 0
    fi
    
    echo -e "Actuelle: ${COLOR_CYAN}$CURRENT_BUILD_VERSION${COLOR_RESET} / Distante: ${COLOR_CYAN}$latest_version${COLOR_RESET}"

    # Comparer versions
    if [ "$latest_version" == "$CURRENT_BUILD_VERSION" ] && [ "$FORCE_DOWNLOAD" -eq 0 ]; then 
        echo "${COLOR_GREEN}Version à jour.${COLOR_RESET}"
        return 0
    fi
    
    if [ "$FORCE_DOWNLOAD" -eq 1 ]; then 
        echo "Téléchargement forcé..."
    else 
        echo "Nouvelle version $latest_version disponible."
    fi

    # Vérification mot de passe si nécessaire
    local password_ok=1
    local user_password=""
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
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
                echo "${COLOR_RED}Mdp vide.${COLOR_RESET}"
                rm -f "$token_tmp_file"
                echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
                return 0
            fi
            
            # Stocker le mot de passe pour une utilisation ultérieure
            user_password="$pass"
            
            debug_log "Décodage B64 du jeton..."
            if ! echo "$token_b64" | base64 -d > "$token_tmp_file"; then 
                echo "${COLOR_RED}Erreur décodage B64 du jeton.${COLOR_RESET}"
                rm -f "$token_tmp_file"
                unset pass
                echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
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
                echo "${COLOR_GREEN}Vérification mot de passe OK.${COLOR_RESET}"
                password_ok=1
            else
                echo "${COLOR_RED}ERREUR: Vérification mot de passe échouée (mdp incorrect ou jeton invalide).${COLOR_RESET}" >&2
                debug_log "Jeton déchiffré (si erreur): '$token_decrypted' vs Attendu: '$PASSWORD_CHECK_TOKEN'"
                password_ok=0
                unset pass
                echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
                return 0
            fi
            unset pass
        else
            echo "${COLOR_YELLOW}Avertissement: Jeton vérif mdp absent distant. Continuer ? [o/N]${COLOR_RESET}" >&2
            local user_confirm=""
            read -r user_confirm </dev/tty
            if [[ ! "$user_confirm" =~ ^[OoYy]$ ]]; then 
                echo "Abandon."
                echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
                return 0
            fi
        fi
    fi

    # Téléchargement du script
    echo "Téléchargement depuis $PACKAGE_URL..."
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
        echo "${COLOR_RED}Erreur: Téléchargement échoué.${COLOR_RESET}" >&2
        rm -f "$target_file" 2>/dev/null
        echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
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
                echo "${COLOR_GREEN}Checksum script OK.${COLOR_RESET}"
            else 
                echo "${COLOR_RED}ERREUR: Checksum script invalide!${COLOR_RESET}" >&2
                debug_log "Attendu: $script_checksum"
                rm -f "$target_file" 2>/dev/null
                echo "${COLOR_YELLOW}Poursuite de l'extraction normale.${COLOR_RESET}"
                return 0
            fi
        else
            echo "${COLOR_YELLOW}Avertissement: 'sha256sum' non trouvé, vérification ignorée.${COLOR_RESET}" >&2
        fi
    else
        echo "${COLOR_YELLOW}Avertissement: Checksum script distant absent.${COLOR_RESET}" >&2
    fi

    chmod +x "$target_file" 2>/dev/null
    update_success=1
    echo "${COLOR_GREEN}Téléchargement vérifié: $target_file${COLOR_RESET}"
    
    # Mode de mise à jour selon configuration
    debug_log "Mode update configuré: $UPDATE_MODE (NO_AUTO_UPDATE=$NO_AUTO_UPDATE)"
    if [ "$UPDATE_MODE" == "auto-replace" ] && [ "$NO_AUTO_UPDATE" -eq 0 ]; then
        echo "Mode Auto-Replace activé - Remplacement du script en cours..."
        local backup_file="$SCRIPT_PATH.bak"
        
        # Créer une sauvegarde
        if ! cp "$SCRIPT_PATH" "$backup_file"; then
            echo "${COLOR_YELLOW}Avertissement: Échec création sauvegarde.${COLOR_RESET}" >&2
        else
            chmod +x "$backup_file" 2>/dev/null
            echo "Sauvegarde créée: $backup_file"
        fi
        
        # Remplacer le script actuel
        if cp "$target_file" "$SCRIPT_PATH"; then
            chmod +x "$SCRIPT_PATH" 2>/dev/null
            replace_success=1
            echo "${COLOR_GREEN}Remplacement réussi.${COLOR_RESET}"
            
            # Si le script est en cours d'exécution, quitter pour le relancer
            if [ "$replace_success" -eq 1 ]; then
                echo "${COLOR_GREEN}Relance du script avec la nouvelle version...${COLOR_RESET}"
                # Exécuter le nouveau script avec les mêmes arguments mais en désactivant la vérification
                # pour éviter une boucle infinie
                exec "$SCRIPT_PATH" --no-update-check "${original_args[@]}"
                # exec ne retourne jamais si réussi, sinon on continue
                echo "${COLOR_YELLOW}Échec de relance. Poursuite avec l'extraction.${COLOR_RESET}" >&2
            fi
        else
            echo "${COLOR_RED}Échec du remplacement. L'extraction va se poursuivre.${COLOR_RESET}" >&2
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
    debug_log "Entrée dans main()..."
    get_script_path
    
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
        update_info "Vérification des mises à jour activée..."
        if [ "$NO_UPDATE_CHECK" -eq 0 ]; then
            if type check_for_updates_and_download_if_needed >/dev/null 2>&1; then
                check_for_updates_and_download_if_needed "$@"
            else
                warning "Avertissement: Fonction de mise à jour non disponible."
            fi
        else
            warning "Vérification des mises à jour désactivée par option --no-update-check."
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
        info "Extraction vers '${COLOR_CYAN}$EXTRACT_DEST${COLOR_RESET}' (via '${COLOR_GRAY}$WORK_DIR${COLOR_RESET}')..."
        need_intermediate_temp=1
    elif [ "$EXTRACT_ONLY" -eq 1 ]; then
        local ts; ts=$(date +%Y%m%d_%H%M%S); local base; base="${SCRIPT_NAME%.sh}"; local ed; ed="./${base}_ext_${ts}_$$"
        if ! mkdir -p "$ed"; then error "Erreur: Création dossier extract '$ed' échouée."; exit 1; fi
        EXTRACT_DEST=$(cd "$ed" && pwd); WORK_DIR="$EXTRACT_DEST"
        info "Extraction seule vers : ${COLOR_CYAN}$EXTRACT_DEST${COLOR_RESET}"
    else
        if ! WORK_DIR=$(mktemp -d "/tmp/nvb_${SCRIPT_NAME}_$.XXXXXX"); then 
            warning "Avert: Création temp /tmp échouée, essai PWD..."
            if ! WORK_DIR=$(mktemp -d "./nvb_temp_$.XXXXXX"); then 
                error "Erreur: Création temp PWD échouée."
                exit 1
            fi
        fi
        EXTRACT_DEST="$WORK_DIR"
        info "Extraction vers temp : ${COLOR_CYAN}$WORK_DIR${COLOR_RESET}"
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
    info "Extraction B64 interne..."
    local awk_output_file="$WORK_DIR/awk_output.tmp"
    debug_log "Commande awk: awk \"NR >= $data_start_line\" \"$SCRIPT_PATH\" > \"$awk_output_file\""
    if ! awk "NR >= $data_start_line" "$SCRIPT_PATH" > "$awk_output_file"; then 
        error "Erreur: awk échoué ($?)."
        exit 1
    fi
    
    debug_log "Vérification sortie awk:"
    ls -l "$awk_output_file" 2>/dev/null || true
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
    
    info "Décodage B64..."
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
    
    success "Décodage B64 OK."
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
    
    info "Décompression '${COLOR_CYAN}$tar_input_src_fname${COLOR_RESET}'..."
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
    
    success "Décompression OK."

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
                header "Exécution $POST_EXTRACTION_SCRIPT..."
                (cd "$EXTRACT_DEST" && "./$POST_EXTRACTION_SCRIPT" "$@")
            fi
            script_exit=$?
            
            if [ $script_exit -ne 0 ]; then
                warning "Script terminé avec code non-zéro: $script_exit"
            else
                success "Script terminé avec succès!"
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

# NVBUILDER_MARKER_LINE: %%ARCHIVE_MARKER%%