#!/bin/bash
set -e

# Version du script
VERSION="1.0.0"

# Couleurs et formatage
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

# Fonction d'aide
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Affiche cette aide"
    echo "  -c, --config FILE    Utilise le fichier de configuration spécifié"
    echo "  -d, --dir DIR        Spécifie le répertoire d'extraction"
    echo "  -x, --extract-only   Extrait uniquement l'archive sans exécuter le script"
    echo "      --debug          Active le mode debug"
    echo "      --skip-version   Désactive la vérification de version"
}

# Fonction de compression
compress_files() {
    local content_dir="$1"
    local output_file="$2"
    local temp_dir=$(mktemp -d)
    local archive_file="$temp_dir/archive.tar"
    
    echo -e "  ${BLUE}${BOLD}→${RESET} Compression des fichiers..."
    
    # Construire la commande tar avec les patterns
    local tar_opts=()
    [ "$VERBOSITY" -gt 1 ] && tar_opts+=("v")
    
    # Ajouter les patterns d'inclusion
    local include_args=()
    for pattern in "${INCLUDE_PATTERNS[@]}"; do
        include_args+=("--include=$pattern")
    done
    
    # Ajouter les patterns d'exclusion
    local exclude_args=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_args+=("--exclude=$pattern")
    done
    
    # Créer l'archive
    if ! tar "c${tar_opts[@]}f" "$archive_file" "${include_args[@]}" "${exclude_args[@]}" -C "$content_dir" . >/dev/null 2>&1; then
        echo -e "  ${RED}${BOLD}✗${RESET} Erreur lors de la création de l'archive"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Compresser selon la méthode choisie
    case "$COMPRESSION" in
        "bzip2")
            if ! bzip2 "$archive_file"; then
                echo -e "  ${RED}${BOLD}✗${RESET} Erreur lors de la compression bzip2"
                rm -rf "$temp_dir"
                exit 1
            fi
            archive_file="$archive_file.bz2"
            ;;
        "gzip")
            if ! gzip "$archive_file"; then
                echo -e "  ${RED}${BOLD}✗${RESET} Erreur lors de la compression gzip"
                rm -rf "$temp_dir"
                exit 1
            fi
            archive_file="$archive_file.gz"
            ;;
        *)
            echo -e "  ${RED}${BOLD}✗${RESET} Méthode de compression non supportée: $COMPRESSION"
            rm -rf "$temp_dir"
            exit 1
            ;;
    esac
    
    local archive_size=$(stat -f %z "$archive_file" 2>/dev/null || stat -c %s "$archive_file")
    echo -e "  ${GREEN}${BOLD}✓${RESET} Archive créée avec succès ($archive_size octets)"
    
    echo -e "  ${BLUE}${BOLD}→${RESET} Génération du script auto-extractible..."
    
    # Copier le script actuel jusqu'à la marque
    sed '/^__ARCHIVE_BELOW__$/,$d' "$0" > "$output_file"
    
    # Ajouter la marque
    echo "__ARCHIVE_BELOW__" >> "$output_file"
    
    # Ajouter l'archive
    cat "$archive_file" >> "$output_file"
    
    chmod +x "$output_file"
    echo -e "  ${GREEN}${BOLD}✓${RESET} Script auto-extractible généré : $output_file"
    
    rm -rf "$temp_dir"
}

# Variables par défaut
EXTRACT_DIR=""
EXTRACT_ONLY=0
NEED_ROOT=1
VERSION_URL="http://localhost/newInstall.sh.version"
VERSION_CHECK=1
SCRIPT_EXEC="start.sh"
DEBUG=0
SKIP_VERSION_CHECK=0
CONFIG_FILE=""
VERBOSITY=1
COMPRESSION="bzip2"
BACKUP=1
INCLUDE_PATTERNS=()
EXCLUDE_PATTERNS=()
SEND_CALLING_DIR=0

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dir)
            EXTRACT_DIR="$2"
            shift 2
            ;;
        -x|--extract-only)
            EXTRACT_ONLY=1
            shift
            ;;
        --debug)
            DEBUG=1
            shift
            ;;
        --skip-version)
            SKIP_VERSION_CHECK=1
            shift
            ;;
        *)
            echo "Option invalide : $1"
            show_help
            exit 1
            ;;
    esac
done

# Charger la configuration si spécifiée
if [ -n "$CONFIG_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "  ${RED}${BOLD}✗${RESET} Fichier de configuration non trouvé : $CONFIG_FILE"
        exit 1
    fi
    echo -e "  ${BLUE}${BOLD}→${RESET} Chargement de la configuration depuis $CONFIG_FILE"
    
    # Utiliser yq pour parser le YAML si disponible
    if command -v yq >/dev/null 2>&1; then
        # Lecture des paramètres simples
        OUTPUT_FILE=$(yq e '.output_file' "$CONFIG_FILE")
        CONTENT_DIR=$(yq e '.content_dir' "$CONFIG_FILE")
        SCRIPT_EXEC=$(yq e '.script_exec' "$CONFIG_FILE")
        COMPRESSION=$(yq e '.compression // "bzip2"' "$CONFIG_FILE")
        VERBOSITY=$(yq e '.verbosity // 1' "$CONFIG_FILE")
        
        # Lecture des booléens
        [ "$(yq e '.need_root // true' "$CONFIG_FILE")" = "true" ] && NEED_ROOT=1 || NEED_ROOT=0
        [ "$(yq e '.version_check // true' "$CONFIG_FILE")" = "true" ] && VERSION_CHECK=1 || VERSION_CHECK=0
        [ "$(yq e '.debug // false' "$CONFIG_FILE")" = "true" ] && DEBUG=1 || DEBUG=0
        [ "$(yq e '.backup // true' "$CONFIG_FILE")" = "true" ] && BACKUP=1 || BACKUP=0
        [ "$(yq e '.send_calling_dir // false' "$CONFIG_FILE")" = "true" ] && SEND_CALLING_DIR=1 || SEND_CALLING_DIR=0
        
        # Lecture des patterns
        readarray -t INCLUDE_PATTERNS < <(yq e '.include_patterns[]' "$CONFIG_FILE")
        readarray -t EXCLUDE_PATTERNS < <(yq e '.exclude_patterns[]' "$CONFIG_FILE")
        
        VERSION_URL=$(yq e '.version_url // "http://localhost/newInstall.sh.version"' "$CONFIG_FILE")
    else
        # Fallback: parser basique ligne par ligne si yq n'est pas disponible
        while IFS=: read -r key value; do
            # Supprimer les espaces au début et à la fin
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            case "$key" in
                "output_file") OUTPUT_FILE="$value" ;;
                "content_dir") CONTENT_DIR="$value" ;;
                "script_exec") SCRIPT_EXEC="$value" ;;
                "compression") COMPRESSION="$value" ;;
                "verbosity") VERBOSITY="$value" ;;
                "need_root") [ "$value" = "true" ] && NEED_ROOT=1 || NEED_ROOT=0 ;;
                "version_check") [ "$value" = "true" ] && VERSION_CHECK=1 || VERSION_CHECK=0 ;;
                "version_url") VERSION_URL="$value" ;;
                "debug") [ "$value" = "true" ] && DEBUG=1 || DEBUG=0 ;;
                "backup") [ "$value" = "true" ] && BACKUP=1 || BACKUP=0 ;;
                "send_calling_dir") [ "$value" = "true" ] && SEND_CALLING_DIR=1 || SEND_CALLING_DIR=0 ;;
            esac
        done < "$CONFIG_FILE"
    fi
    
    # Vérifier les variables obligatoires
    if [ -z "$OUTPUT_FILE" ] || [ -z "$CONTENT_DIR" ]; then
        echo -e "  ${RED}${BOLD}✗${RESET} Configuration invalide : output_file et content_dir sont requis"
        exit 1
    fi
    
    # Nettoyer et normaliser les valeurs de configuration
    CONTENT_DIR=$(echo "$CONTENT_DIR" | sed 's/"//g')
    OUTPUT_FILE=$(echo "$OUTPUT_FILE" | sed 's/"//g')
    COMPRESSION=$(echo "$COMPRESSION" | sed 's/"//g')
    SCRIPT_EXEC=$(echo "$SCRIPT_EXEC" | sed 's/"//g')
    VERSION_URL=$(echo "$VERSION_URL" | sed 's/"//g')
    
    # Convertir les chemins relatifs en absolus
    if [[ "$CONTENT_DIR" != /* ]]; then
        CONTENT_DIR="$(pwd)/$CONTENT_DIR"
    fi
    if [[ "$OUTPUT_FILE" != /* ]]; then
        OUTPUT_FILE="$(pwd)/$OUTPUT_FILE"
    fi
    
    [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Chemin source absolu : $CONTENT_DIR"
    [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Chemin sortie absolu : $OUTPUT_FILE"
    
    # Vérifier que le dossier source existe
    if [ ! -d "$CONTENT_DIR" ]; then
        echo -e "  ${RED}${BOLD}✗${RESET} Dossier source non trouvé : $CONTENT_DIR"
        exit 1
    fi
    
    # Compresser les fichiers
    compress_files "$CONTENT_DIR" "$OUTPUT_FILE"
    echo -e "  ${GREEN}${BOLD}✓${RESET} Script généré avec succès : $OUTPUT_FILE"
    exit 0
fi

# Afficher la configuration en mode debug
[ "$DEBUG" -eq 1 ] && {
    echo -e "  ${BLUE}${BOLD}→${RESET} Configuration :"
    echo -e "    - EXTRACT_DIR: $EXTRACT_DIR"
    echo -e "    - EXTRACT_ONLY: $EXTRACT_ONLY"
    echo -e "    - DEBUG: $DEBUG"
    echo -e "    - SKIP_VERSION_CHECK: $SKIP_VERSION_CHECK"
    echo -e "    - SCRIPT_EXEC: $SCRIPT_EXEC"
    echo -e "    - VERSION_CHECK: $VERSION_CHECK"
    echo -e "    - VERSION_URL: $VERSION_URL"
}

# Vérifier les droits root si nécessaire
if [ "$NEED_ROOT" -eq 1 ] && [ "$EUID" -ne 0 ]; then
    echo -e "  ${BLUE}${BOLD}→${RESET} Ce script nécessite les droits administrateur"
    echo -e "  ${BLUE}${BOLD}→${RESET} Veuillez exécuter le script avec sudo"
    exit 1
fi

# Créer le répertoire d'extraction
if [ -z "$EXTRACT_DIR" ]; then
    EXTRACT_DIR=$(mktemp -d)
fi

# Vérifier la version si c'est activé et que ce n'est pas désactivé par l'option
if [ "$VERSION_CHECK" -eq 1 ] && [ -n "$VERSION_URL" ] && [ "$EXTRACT_ONLY" -eq 0 ] && [ "$SKIP_VERSION_CHECK" -eq 0 ]; then
    echo -e "  ${BLUE}${BOLD}→${RESET} Vérification des mises à jour..."
    [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Version locale : $VERSION"
    [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} URL de vérification : $VERSION_URL"

    if ! remote_info=$(wget -qO- "$VERSION_URL" 2>/dev/null); then
        echo -e "  ${YELLOW}${BOLD}⚠${RESET} Impossible de vérifier les mises à jour"
        [ "$DEBUG" -eq 1 ] && echo -e "  ${RED}${BOLD}✗${RESET} Erreur de connexion à $VERSION_URL"
    else
        [ "$DEBUG" -eq 1 ] && echo -e "  ${GREEN}${BOLD}✓${RESET} Réponse reçue du serveur"
        [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Réponse brute : $remote_info"

        if ! remote_version=$(echo "$remote_info" | grep -o '"version":"[^"]*"' | cut -d'"' -f4); then
            echo -e "  ${YELLOW}${BOLD}⚠${RESET} Format de version invalide"
            [ "$DEBUG" -eq 1 ] && echo -e "  ${RED}${BOLD}✗${RESET} Impossible d'extraire la version de la réponse"
        else
            [ "$DEBUG" -eq 1 ] && echo -e "  ${GREEN}${BOLD}✓${RESET} Version distante extraite : $remote_version"
            remote_url=$(echo "$remote_info" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
            
            # Comparer les versions
            if [ -n "$remote_version" ]; then
                if [ "$remote_version" != "$VERSION" ]; then
                    echo -e "  ${YELLOW}${BOLD}⚠${RESET} Une nouvelle version est disponible : $remote_version"
                    echo -e "  ${BLUE}${BOLD}→${RESET} Version actuelle : $VERSION"
                    if [ -n "$remote_url" ]; then
                        echo -e "  ${BLUE}${BOLD}→${RESET} URL de téléchargement : $remote_url"
                    fi
                    exit 1
                else
                    echo -e "  ${GREEN}${BOLD}✓${RESET} Version à jour ($VERSION)"
                fi
            fi
        fi
    fi
fi

# Extraire l'archive
echo -e "  ${BLUE}${BOLD}→${RESET} Recherche du début de l'archive..."
ARCHIVE_START=$(awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' "$0")
[ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Début de l'archive à la ligne : $ARCHIVE_START"

echo -e "  ${BLUE}${BOLD}→${RESET} Extraction de l'archive..."
tail -n +"$ARCHIVE_START" "$0" | tar xj -C "$EXTRACT_DIR" >/dev/null 2>&1
[ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Extraction terminée dans : $EXTRACT_DIR"

# Exécuter le script principal si présent et si on n'est pas en mode extraction seule
if [ -n "$SCRIPT_EXEC" ] && [ "$EXTRACT_ONLY" -eq 0 ]; then
    [ "$DEBUG" -eq 1 ] && echo -e "  ${BLUE}${BOLD}→${RESET} Vérification du script $SCRIPT_EXEC"
    if [ ! -f "$EXTRACT_DIR/$SCRIPT_EXEC" ]; then
        echo -e "  ${RED}${BOLD}✗${RESET} Script $SCRIPT_EXEC non trouvé dans le répertoire d'extraction"
        exit 1
    fi
    [ "$DEBUG" -eq 1 ] && echo -e "  ${GREEN}${BOLD}✓${RESET} Script trouvé"

    echo -e "  ${BLUE}${BOLD}→${RESET} Lancement du script $SCRIPT_EXEC"
    chmod +x "$EXTRACT_DIR/$SCRIPT_EXEC"
    cd "$EXTRACT_DIR"
    echo -e "  ${BLUE}${BOLD}→${RESET} Exécution de ./$SCRIPT_EXEC"
    
    # Construire les options
    script_opts=()
    [ "$DEBUG" -eq 1 ] && script_opts+=("--debug")
    [ "$SKIP_VERSION_CHECK" -eq 1 ] && script_opts+=("--skip-version")
    
    # Exécuter le script
    if ! "./$SCRIPT_EXEC" "${script_opts[@]}"; then
        echo -e "  ${RED}${BOLD}✗${RESET} Erreur lors de l'exécution du script"
        exit 1
    fi
    echo -e "  ${GREEN}${BOLD}✓${RESET} Script exécuté avec succès"
fi

echo -e "  ${GREEN}${BOLD}✓${RESET} Terminé"
exit 0

__ARCHIVE_BELOW__
