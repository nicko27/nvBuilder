#!/bin/bash
# Options pour un script plus robuste :
set -euo pipefail
# Message initial toujours affiché
echo "NVBuilder Script v%%NVBUILDER_VERSION%% (Build %%BUILD_VERSION%%) - Initialisation..."

# =========================================================================
#  Script auto-extractible généré par NVBuilder v%%NVBUILDER_VERSION%%
#  Date de création : %%CREATED_AT%%
#  Build : %%BUILD_USER_HOST%% (Platform: %%PLATFORM_BUILD%%, Python: %%PYTHON_VERSION_DISPLAY%%)
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

# --- Variables globales d'initialisation ---
NO_UPDATE_CHECK=0
FORCE_DOWNLOAD=0
# --- Fin Variables globales d'initialisation ---

# --- Début Variables et Blocs Conditionnels ---
# --- Début Update Vars ---
%%BASH_UPDATE_VARS%%
# --- Fin Update Vars ---
# --- Début Encryption Vars ---
%%BASH_ENCRYPTION_VARS%%
# --- Fin Encryption Vars ---
# --- Fin Variables et Blocs Conditionnels ---

# --- Variables d'exécution ---
SCRIPT_NAME=$(basename "$0")
SCRIPT_PATH="" # Défini par get_script_path
SCRIPT_DIR=""  # Défini par get_script_path
EXTRACT_ONLY=0; SHOW_INFO=0; TARGET_DIR=""; DEBUG_MODE=0

# --- Couleurs ---
if [ -t 1 ]; then RED=$(tput setaf 1 2>/dev/null||echo ''); GREEN=$(tput setaf 2 2>/dev/null||echo ''); YELLOW=$(tput setaf 3 2>/dev/null||echo ''); RESET=$(tput sgr0 2>/dev/null||echo ''); else RED=""; GREEN=""; YELLOW=""; RESET=""; fi

# --- Fonctions Utilitaires ---
debug_log() { if [ "${NVBUILDER_DEBUG_ENABLED:-0}" -eq 1 ]; then echo "${YELLOW}DEBUG:${RESET} $@" >&2; fi; }
debug_log "Assignation couleurs OK."

get_script_path() { local source="$0"; while [ -h "$source" ]; do local dir; dir="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"; source="$(readlink "$source")"; [[ $source != /* ]] && source="$dir/$source"; done; SCRIPT_PATH="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )/$(basename "$source")"; SCRIPT_DIR="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"; export SCRIPT_PATH SCRIPT_DIR; debug_log "SCRIPT_PATH=$SCRIPT_PATH"; }

# --- print_help RESTAUREE (Version v2.0.40) ---
print_help() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] [--] [ARGUMENTS_POUR_SCRIPT_POST_EXTRACTION...]

Ce script extrait une archive intégrée et exécute un script post-extraction.

Options principales :
  --extract-only      Extrait seulement le contenu, sans exécuter '$POST_EXTRACTION_SCRIPT'.
  --target-dir DIR    Extrait le contenu dans le répertoire DIR spécifié. Par défaut, un répertoire temporaire est créé et nettoyé ensuite, sauf si --extract-only est aussi utilisé (auquel cas un dossier ./<nom_script>_ext_<timestamp> est créé).
  --info              Affiche les informations sur cette archive et quitte.
  --debug             Active le mode debug (plus de messages, ne supprime pas le dossier temporaire).
  --help, -h          Affiche cette aide et quitte.
EOF
    if %%BASH_UPDATE_ENABLED_BOOL%%; then
        cat << EOFAJ

Options de mise à jour :
%%BASH_UPDATE_HELP%%
EOFAJ
    fi
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        cat << EOFENC

Note : Un mot de passe sera demandé pour déchiffrer le contenu.
EOFENC
    fi
    cat << EOFEARGS

Tous les arguments après '--' (ou les arguments non reconnus comme options)
seront passés directement au script '$POST_EXTRACTION_SCRIPT'.
EOFEARGS
}
debug_log "Définition print_help OK."

# --- display_info RESTAUREE (Version v2.0.40) ---
display_info() {
    echo "+------------------------------------------------------+"
    echo "| Informations sur l'archive auto-extractible          |"
    echo "+------------------------------------------------------+"
    echo " Généré par          : NVBuilder v%%NVBUILDER_VERSION%%"
    echo " Version du build    : %%BUILD_VERSION%%"
    echo " Date de création    : %%CREATED_AT%%"
    echo " Créé par            : %%BUILD_USER_HOST%%"
    echo " Plateforme (build)  : %%PLATFORM_BUILD%%"
    echo " Python (build)      : %%PYTHON_VERSION_DISPLAY%%"
    echo " Répertoire source   : %%CONTENT_SOURCE_DIR%%"
    echo " Script post-extract : %%POST_EXTRACTION_SCRIPT%%"
    echo " Compression         : %%COMPRESSION_DISPLAY%%"
    echo -n " Chiffrement         : "
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then echo "Oui (%%ENCRYPTION_TOOL_DISPLAY%%)"; else echo "Non"; fi
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then echo "   Checksum (chiffré): %%ENCRYPTED_CHECKSUM%%"; fi
    echo "   Checksum (original): %%ARCHIVE_CHECKSUM%%"
    echo -n " Mise à jour HTTP    : "
    if %%BASH_UPDATE_ENABLED_BOOL%%; then echo "Activées (URL: %%UPDATE_URL_DISPLAY%%)"; else echo "Désactivées"; fi
    echo "+------------------------------------------------------+"
}
debug_log "Définition display_info OK."

# --- cleanup RESTAUREE (Version v2.0.45 avec fix ${VAR:-}) ---
cleanup() {
    local exit_code=$?; local is_temp_dir=0; trap - EXIT TERM INT; debug_log "Cleanup: Vérification awk_output.tmp"
    if [ -n "${WORK_DIR:-}" ] && [ -f "${WORK_DIR:-}/awk_output.tmp" ]; then debug_log "Cleanup: Suppression awk_output.tmp"; rm -f "${WORK_DIR}/awk_output.tmp"; fi
    if [ "${DEBUG_MODE:-0}" -eq 0 ]; then debug_log "Cleanup: Mode non-debug activé."
        if [ -n "${WORK_DIR:-}" ]; then if [[ "${WORK_DIR:-}" == /tmp/nvb_* ]] || ([ -n "${EXTRACT_DEST:-}" ] && [[ "${WORK_DIR:-}" == "${EXTRACT_DEST:-}"/.nvb_temp_* ]]); then is_temp_dir=1; fi; fi
        if [ $is_temp_dir -eq 1 ] && [ -d "${WORK_DIR:-}" ]; then echo "Nettoyage temp: ${WORK_DIR}"; rm -rf "${WORK_DIR}"; fi
        if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then local skip_cleanup=0; if [ "${EXTRACT_ONLY:-0}" -eq 1 ] && [ -n "${EXTRACT_DEST:-}" ]; then local current_pwd; current_pwd=$(pwd); if [[ "${EXTRACT_DEST:-}" == "$current_pwd/"* ]] && [[ "$(basename "${EXTRACT_DEST:-}")" == *_ext_* ]]; then skip_cleanup=1; fi; fi; if [ $skip_cleanup -eq 0 ]; then debug_log "Cleanup: Appel nettoyage déchiffrement..."; %%BASH_DECRYPTION_CLEANUP%%; else debug_log "Cleanup: Nettoyage déchiffrement ignoré (extract-only vers PWD)."; fi; fi
    elif [ -n "${WORK_DIR:-}" ] && [ -d "${WORK_DIR:-}" ]; then echo "${YELLOW}Mode Debug : ${WORK_DIR} non supprimé.${RESET}"; if %%BASH_ENCRYPTION_ENABLED_BOOL%% && [ -f "${WORK_DIR:-}/${DECRYPTED_TMP_FILENAME:-}" ]; then echo "${YELLOW}Mode Debug : Fichier déchiffré conservé${RESET}"; fi; fi
    if [ "${DEBUG_MODE:-0}" -eq 1 ] && [[ $- == *x* ]]; then set +x; fi; [ $exit_code -ne 0 ] && echo "Cleanup terminé (code sortie original: $exit_code)."; exit $exit_code
}
debug_log "Définition cleanup OK."

# --- find_archive_marker_line (Identique v2.0.45) ---
find_archive_marker_line() { local marker_pattern="^# NVBUILDER_MARKER_LINE: $SCRIPT_MARKER_VALUE"; if [ -z "${SCRIPT_PATH:-}" ]; then echo "${RED}Erreur interne: SCRIPT_PATH non défini.${RESET}" >&2; return 1; fi; grep -n -m 1 "$marker_pattern" "$SCRIPT_PATH" | cut -d':' -f1; }
debug_log "Définition find_archive_marker_line OK."

# --- Fonctions conditionnelles (Injectées) ---
debug_log "Définition fonctions injectées..."
# --- Début Fonction Update ---
%%BASH_UPDATE_FUNCTION%%
# --- Fin Fonction Update ---
debug_log "Définition fonctions injectées OK."
# --- Fin Fonctions conditionnelles ---

debug_log "<<< Juste avant définition main() >>>"

# --- Fonction principale (RESTAURÉE - Corps Complet + CORRECTION ";") ---
function main {
    debug_log "Entrée dans main()..."
    get_script_path
    trap cleanup EXIT TERM INT

    if [ "$DEBUG_MODE" -eq 1 ]; then
        echo "${YELLOW}Mode Debug activé (traces Bash actives).${RESET}"
        set -x
    fi
    if [ "$SHOW_INFO" -eq 1 ]; then
        display_info
        exit 0
    fi

    # Préparation des variables d'environnement
    local WORK_DIR="" EXTRACT_DEST="" need_intermediate_temp=0
    # Vérification explicite et visible des mises à jour
    debug_log "Appel vérification MàJ (si activé)..."
    if %%BASH_UPDATE_ENABLED_BOOL%%; then
        echo "Vérification des mises à jour activée..."
        if [ "$NO_UPDATE_CHECK" -eq 0 ]; then
            check_for_updates_and_download_if_needed
        else
            echo "${YELLOW}Vérification des mises à jour désactivée par option --no-update-check.${RESET}"
        fi
    else
        debug_log "Mises à jour HTTP désactivées dans la configuration."
    fi
    debug_log "Appel vérification MàJ (si activé)..."
    if %%BASH_UPDATE_ENABLED_BOOL%% && [ "$NO_UPDATE_CHECK" -eq 0 ]; then
        echo "Vérification des mises à jour activée..."
        # Vérifier que la fonction existe avant de l'appeler
        if type check_for_updates_and_download_if_needed >/dev/null 2>&1; then
            check_for_updates_and_download_if_needed
        else
            echo "${YELLOW}Avertissement: Fonction de mise à jour non disponible.${RESET}"
        fi
    fi
    if [ -n "$TARGET_DIR" ]; then
        local target_dir_resolved
        if [[ "$TARGET_DIR" != /* ]]; then target_dir_resolved="$PWD/$TARGET_DIR"; else target_dir_resolved="$TARGET_DIR"; fi
        if ! mkdir -p "$target_dir_resolved"; then echo "${RED}Erreur: Création dossier cible '$target_dir_resolved' échouée.${RESET}" >&2; exit 1; fi
        EXTRACT_DEST=$(cd "$target_dir_resolved" && pwd)
        if ! WORK_DIR=$(mktemp -d "${EXTRACT_DEST}/.nvb_temp_XXXXXX"); then echo "${RED}Erreur: Création temp dans '$EXTRACT_DEST' échouée.${RESET}" >&2; exit 1; fi
        echo "Extraction vers '$EXTRACT_DEST' (via '$WORK_DIR')..."
        need_intermediate_temp=1
    elif [ "$EXTRACT_ONLY" -eq 1 ]; then
        local ts; ts=$(date +%Y%m%d_%H%M%S); local base; base="${SCRIPT_NAME%.sh}"; local ed; ed="./${base}_ext_${ts}_$$"
        if ! mkdir -p "$ed"; then echo "${RED}Erreur: Création dossier extract '$ed' échouée.${RESET}" >&2; exit 1; fi
        EXTRACT_DEST=$(cd "$ed" && pwd); WORK_DIR="$EXTRACT_DEST"
        echo "Extraction seule vers : $EXTRACT_DEST"
    else
        if ! WORK_DIR=$(mktemp -d "/tmp/nvb_${SCRIPT_NAME}_$$.XXXXXX"); then echo "${YELLOW}Avert: Création temp /tmp échouée, essai PWD...${RESET}" >&2; if ! WORK_DIR=$(mktemp -d "./nvb_temp_$$.XXXXXX"); then echo "${RED}Erreur: Création temp PWD échouée.${RESET}" >&2; exit 1; fi; fi
        EXTRACT_DEST="$WORK_DIR"; echo "Extraction vers temp : $WORK_DIR"
    fi
    export WORK_DIR EXTRACT_DEST; debug_log "WORK_DIR='$WORK_DIR', EXTRACT_DEST='$EXTRACT_DEST'"

    debug_log "Recherche marqueur..."; local archive_start_line; archive_start_line=$(find_archive_marker_line); if [ -z "$archive_start_line" ]; then echo "${RED}Erreur: Marqueur unique non trouvé ('# NVBUILDER_MARKER_LINE: $SCRIPT_MARKER_VALUE').${RESET}" >&2; exit 1; fi; local data_start_line=$((archive_start_line + 1)); debug_log "Marqueur trouvé: L$archive_start_line. Données: L$data_start_line."

    debug_log "Préparation extraction B64..."; echo "Extraction B64 interne..."; local awk_output_file="$WORK_DIR/awk_output.tmp"; debug_log "Commande awk: awk \"NR >= $data_start_line\" \"$SCRIPT_PATH\" > \"$awk_output_file\""; if ! awk "NR >= $data_start_line" "$SCRIPT_PATH" > "$awk_output_file"; then echo "${RED}Erreur: awk échoué ($?).${RESET}" >&2; exit 1; fi; debug_log "Vérification sortie awk:"; ls -l "$awk_output_file"; local awk_file_size; awk_file_size=$(stat -f%z "$awk_output_file" 2>/dev/null || stat -c%s "$awk_output_file" 2>/dev/null || echo 0); if [ "$awk_file_size" -eq 0 ]; then echo "${RED}Erreur: Fichier awk vide.${RESET}" >&2; exit 1; fi; if [ "$DEBUG_MODE" -eq 1 ]; then echo "Début(100o):"; head -c 100 "$awk_output_file"; echo ""; echo "Fin(100o):"; tail -c 100 "$awk_output_file"; echo ""; fi; echo "Décodage B64..."; local target_decoded_file; local decoded_filename; if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then decoded_filename="$ENCRYPTED_TMP_FILENAME"; else decoded_filename="%%ARCHIVE_ORIGINAL_FILENAME%%"; fi; target_decoded_file="$WORK_DIR/$decoded_filename"; debug_log "Commande base64: base64 -d < \"$awk_output_file\" > \"$target_decoded_file\""; if ! base64 -d < "$awk_output_file" > "$target_decoded_file"; then echo "${RED}Erreur: Échec décodage B64.${RESET}" >&2; [ "$DEBUG_MODE" -eq 0 ] && rm -f "$awk_output_file"; rm -f "$target_decoded_file" 2>/dev/null; exit 1; fi; if [ ! -s "$target_decoded_file" ]; then echo "${RED}Erreur: Fichier vide après décodage B64.${RESET}" >&2; exit 1; fi; echo "Décodage B64 OK."; [ "$DEBUG_MODE" -eq 0 ] && rm -f "$awk_output_file"

    debug_log "Préparation déchiffrement..."; local original_pwd; original_pwd=$PWD
    if ! cd "$WORK_DIR"; then echo "${RED}Erreur: cd '$WORK_DIR' échoué.${RESET}" >&2; exit 1; fi
    # --- Bloc if/then/fi CORRIGÉ (multi-lignes) ---
    if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        %%BASH_DECRYPTION_LOGIC%%
    fi
    # --- Fin Bloc if/then/fi ---
    cd "$original_pwd" # Revenir APRÈS le bloc if complet
    # --- FIN CORRECTION ---

    # --- Décompression Tar ---
    local tar_input_src_fname; if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then tar_input_src_fname="$DECRYPTED_TMP_FILENAME"; else tar_input_src_fname="%%ARCHIVE_ORIGINAL_FILENAME%%"; fi; echo "Décompression '$tar_input_src_fname'..."; debug_log "Commande Tar: (cd \"$WORK_DIR\" && tar \"$TAR_COMMAND_FLAGS\" \"$tar_input_src_fname\")"; if ! (cd "$WORK_DIR" && tar "$TAR_COMMAND_FLAGS" "$tar_input_src_fname"); then local tar_exit_code=$?; echo "${RED}Erreur: Tar échoué (code: $tar_exit_code).${RESET}" >&2; ls -lA "$WORK_DIR" >&2; exit 1; fi; echo "Décompression OK."

    # --- Nettoyage tar source ---
    if [ "$DEBUG_MODE" -eq 0 ]; then if [ -f "$WORK_DIR/$tar_input_src_fname" ]; then debug_log "Nettoyage $tar_input_src_fname"; rm -f "$WORK_DIR/$tar_input_src_fname"; fi; if %%BASH_ENCRYPTION_ENABLED_BOOL%%; then if [ -f "$WORK_DIR/$ENCRYPTED_TMP_FILENAME" ]; then debug_log "Nettoyage $ENCRYPTED_TMP_FILENAME"; rm -f "$WORK_DIR/$ENCRYPTED_TMP_FILENAME"; fi; fi; fi

    # --- Déplacement/Copie final ---
    if [ $need_intermediate_temp -eq 1 ]; then echo "Copie vers '$EXTRACT_DEST'... "; if (cd "$WORK_DIR" && cp -a . "$EXTRACT_DEST/") 2>/dev/null; then echo "Copie OK."; elif (cd "$WORK_DIR" && cp -r . "$EXTRACT_DEST/") 2>/dev/null; then echo "${YELLOW}Avert: cp -a échoué, utilisé cp -r.${RESET}"; else local cp_exit_code=$?; echo "${RED}Erreur copie (code $cp_exit_code).${RESET}" >&2; echo "Fichiers dans: $WORK_DIR" >&2; DEBUG_MODE=1; exit 1; fi; fi

    # --- Fin si --extract-only ---
    if [ "$EXTRACT_ONLY" -eq 1 ]; then echo "${GREEN}Extraction terminée: $EXTRACT_DEST${RESET}"; if [[ "$EXTRACT_DEST" == "$PWD/"* ]] && [[ "$(basename "$EXTRACT_DEST")" == *_ext_* ]]; then echo "Nettoyage auto désactivé."; trap - EXIT TERM INT; DEBUG_MODE=1; fi; exit 0; fi

    # --- Exécution post-script ---
    local post_script_result=0; if [ -z "$POST_EXTRACTION_SCRIPT" ]; then echo "Pas de post-script."; else echo "Placement dans '$EXTRACT_DEST'... "; if ! cd "$EXTRACT_DEST"; then echo "${RED}Erreur cd '$EXTRACT_DEST'.${RESET}" >&2; exit 1; fi; local script_to_run=""; local found_script=""; if [ -f "$POST_EXTRACTION_SCRIPT" ]; then script_to_run="./$POST_EXTRACTION_SCRIPT"; else echo "Recherche '$POST_EXTRACTION_SCRIPT'..."; found_script=$(find . -name "$POST_EXTRACTION_SCRIPT" -type f -print -quit); if [ -n "$found_script" ]; then script_to_run="$found_script"; fi; fi; if [ -z "$script_to_run" ]; then echo "${YELLOW}Avert: Script '$POST_EXTRACTION_SCRIPT' non trouvé.${RESET}" >&2; post_script_result=1; else echo "Exécution: $script_to_run ${POST_ARGS[@]:+${POST_ARGS[@]}}"; if ! chmod +x "$script_to_run"; then echo "${YELLOW}Avert: chmod +x échoué.${RESET}" >&2; fi; "$script_to_run" "${POST_ARGS[@]:+${POST_ARGS[@]}}"; post_script_result=$?; echo "Script post-extraction fini (code: $post_script_result)."; fi; fi
    debug_log "Fin main(), sortie avec code $post_script_result."
    exit $post_script_result
}
debug_log "<<< Juste après définition main() >>>"

# --- Traitement des arguments ---
# (Identique v2.0.45)
debug_log "Début traitement arguments..."
NVBUILDER_DEBUG_ENABLED=0; TEMP_ARGS=(); debug_arg_found=0
for arg in "$@"; do 
    if [ "$arg" == "--debug" ]; then 
        DEBUG_MODE=1; NVBUILDER_DEBUG_ENABLED=1; debug_arg_found=1
    fi
    TEMP_ARGS+=("$arg")
done
set -- "${TEMP_ARGS[@]:+${TEMP_ARGS[@]}}"
if [ "$debug_arg_found" -eq 1 ]; then debug_log "Mode Debug activé par argument."; fi
POST_ARGS=()
while [ $# -gt 0 ]; do case "$1" in --extract-only) EXTRACT_ONLY=1; shift ;; --target-dir) if [ -n "$2" ]; then TARGET_DIR="$2"; shift 2; else echo "${RED}Erreur: Argument --target-dir manquant${RESET}" >&2; print_help; exit 1; fi ;; --info) SHOW_INFO=1; shift ;; --debug) shift ;; -h|--help) print_help; exit 0 ;; %%BASH_UPDATE_ARG_PARSING%% --) shift; POST_ARGS+=("$@"); break ;; -?*) echo "${RED}Erreur: Option non reconnue: $1${RESET}" >&2; print_help; exit 1 ;; *) POST_ARGS+=("$@"); break ;; esac; done
debug_log "Fin traitement arguments. Options: EXTRACT_ONLY=$EXTRACT_ONLY, TARGET_DIR='$TARGET_DIR', SHOW_INFO=$SHOW_INFO, DEBUG_MODE=$DEBUG_MODE"
debug_log "Arguments post-script: ${POST_ARGS[@]:+${POST_ARGS[@]}}"
if [ "$DEBUG_MODE" -eq 1 ]; then set -x; fi

# --- Lancement ---
debug_log "Appel de main()..."
main
echo "${RED}ERREUR: Sortie inattendue après main().${RESET}" >&2
exit 255

# =========================================================================
# MARQUEUR DE DEBUT DE L'ARCHIVE - NE PAS SUPPRIMER NI MODIFIER CETTE LIGNE
# NVBUILDER_MARKER_LINE: %%ARCHIVE_MARKER%%