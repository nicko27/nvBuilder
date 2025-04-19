# nvbuilder/bash_snippets.py
"""Génère les snippets Bash conditionnels pour le template."""

import logging
from typing import Dict, Any

# Importer constantes et exceptions
from .constants import (DEFAULT_OPENSSL_CIPHER, DEFAULT_OPENSSL_ITER,
                       DEFAULT_GPG_CIPHER_ALGO, DEFAULT_GPG_S2K_OPTIONS,
                       PASSWORD_CHECK_TOKEN, DEFAULT_UPDATE_MODE) # Ajout de DEFAULT_UPDATE_MODE

from .exceptions import NvBuilderError

logger = logging.getLogger("nvbuilder")

try:
    from typing import TypedDict
    class BashSnippetsDict(TypedDict):
        encryption_vars: str
        decryption_logic: str
        decryption_cleanup: str
except ImportError:
    BashSnippetsDict = Dict[str, str]

def generate_update_snippets(config: Dict[str, Any], metadata: Dict[str, Any]) -> BashSnippetsDict:
    """
    Génère les snippets Bash relatifs à la mise à jour HTTP.
    """
    snippets: BashSnippetsDict = {}
    update_enabled = metadata.get('update_enabled', False)
    update_mode = metadata.get('update_mode', 'check-only')
    
    if update_enabled:
        version_url = config.get('update', {}).get('version_url', '')
        package_url = config.get('update', {}).get('package_url', '')
        
        # Ajouter la fonction complète de mise à jour
        snippets["update_function"] = """
# Fonction intégrée pour vérifier et télécharger les mises à jour
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
        [ "$QUIET_MODE" -eq 0 ] && echo -e "${YELLOW}Avertissement: curl/wget absents.${RESET}" >&2
        [ "$QUIET_MODE" -eq 0 ] && echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
        return 0
    fi

    # Récupérer JSON distant
    echo "Vérification des mises à jour..."
    debug_log "Tentative récupération: $VERSION_URL"
    if ! remote_json=$($downloader "$VERSION_URL"); then 
        echo -e "${YELLOW}Avertissement: Échec récupération $VERSION_URL.${RESET}" >&2
        echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
        return 0
    fi
    if [ -z "$remote_json" ]; then 
        echo -e "${YELLOW}Avertissement: Réponse vide de $VERSION_URL.${RESET}" >&2
        echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
        return 0
    fi
    debug_log "JSON distant reçu: $remote_json"

    # Parser JSON (méthode simple)
    # Fonction helper interne pour parser (suppose format "key": "value" ou "key": number)
    _json_extract() { 
        echo "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*:[ ]*"\\(.*\\)".*/\\1/' | head -1 || \\
        echo "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*[0-9][^,}]*" | sed 's/.*:[ ]*\\([0-9][^,}]*\\).*/\\1/' | head -1
    }
    
    latest_version=$(_json_extract "$remote_json" "build_version")
    script_checksum=$(_json_extract "$remote_json" "script_checksum_sha256")
    local token_b64=$(_json_extract "$remote_json" "password_check_token_b64")
    
    if [ -z "$latest_version" ]; then 
        echo -e "${YELLOW}Avertissement: build_version distante non trouvée.${RESET}" >&2
        echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
        return 0
    fi
    
    echo -e "Actuelle: ${CYAN}$CURRENT_BUILD_VERSION${RESET} / Distante: ${CYAN}$latest_version${RESET}"

    # Comparer versions
    if [ "$latest_version" == "$CURRENT_BUILD_VERSION" ] && [ "$FORCE_DOWNLOAD" -eq 0 ]; then 
        echo -e "${GREEN}Version à jour.${RESET}"
        return 0
    fi
    
    # À partir d'ici, montrer les messages même en mode silencieux car une nouvelle version est détectée
    if [ "$FORCE_DOWNLOAD" -eq 1 ]; then 
        echo "Téléchargement forcé..."
    else 
        echo -e "${GREEN}Nouvelle version $latest_version disponible.${RESET}"
    fi
    
    # Vérifions que l'URL de téléchargement est correcte
    if [ -z "$PACKAGE_URL" ] || [ "$PACKAGE_URL" = "N/A" ] || [ "$PACKAGE_URL" = "http://localhost/" ]; then
        echo -e "${RED}Erreur: URL de téléchargement ($PACKAGE_URL) invalide ou non configurée.${RESET}" >&2
        echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
        return 0
    fi

    # Vérification mot de passe si nécessaire (sauf en mode auto-replace-always)
    local password_ok=1
    local user_password=""
    
    # En mode auto-replace-always, définir user_password vide mais valide
    if [[ "$UPDATE_MODE" == "auto-replace-always" ]] && %%BASH_ENCRYPTION_ENABLED_BOOL%%; then
        password_ok=1
        user_password="auto_replace_always_bypass"
        echo -e "${YELLOW}Mode auto-replace-always activé - Vérification de mot de passe ignorée${RESET}"
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
                echo -e "${RED}Mdp vide.${RESET}"
                rm -f "$token_tmp_file"
                echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
                return 0
            fi
            
            # Stocker le mot de passe pour une utilisation ultérieure
            user_password="$pass"
            
            debug_log "Décodage B64 du jeton..."
            if ! echo "$token_b64" | base64 -d > "$token_tmp_file"; then 
                echo -e "${RED}Erreur décodage B64 du jeton.${RESET}"
                rm -f "$token_tmp_file"
                unset pass
                echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
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
                echo -e "${GREEN}Vérification mot de passe OK.${RESET}"
                password_ok=1
            else
                echo -e "${RED}ERREUR: Vérification mot de passe échouée (mdp incorrect ou jeton invalide).${RESET}" >&2
                debug_log "Jeton déchiffré (si erreur): '$token_decrypted' vs Attendu: '$PASSWORD_CHECK_TOKEN'"
                password_ok=0
                unset pass
                echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
                return 0
            fi
            unset pass
        else
            echo -e "${YELLOW}Avertissement: Jeton vérif mdp absent distant. Continuer ? [o/N]${RESET}" >&2
            local user_confirm=""
            read -r user_confirm </dev/tty
            if [[ ! "$user_confirm" =~ ^[OoYy]$ ]]; then 
                echo "Abandon."
                echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
                return 0
            fi
        fi
    fi

    # Téléchargement du script
    echo -e "${BLUE}Téléchargement depuis $PACKAGE_URL...${RESET}"
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
        echo -e "${RED}Erreur: Téléchargement échoué.${RESET}" >&2
        rm -f "$target_file" 2>/dev/null
        echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
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
                echo -e "${GREEN}Checksum script OK.${RESET}"
            else 
                echo -e "${RED}ERREUR: Checksum script invalide!${RESET}" >&2
                debug_log "Attendu: $script_checksum"
                rm -f "$target_file" 2>/dev/null
                echo -e "${YELLOW}Poursuite de l'extraction normale.${RESET}"
                return 0
            fi
        else
            echo -e "${YELLOW}Avertissement: 'sha256sum' non trouvé, vérification ignorée.${RESET}" >&2
        fi
    else
        echo -e "${YELLOW}Avertissement: Checksum script distant absent.${RESET}" >&2
    fi

    chmod +x "$target_file" 2>/dev/null
    update_success=1
    echo -e "${GREEN}▶ Téléchargement réussi: $target_file${RESET}"
    echo -e "${CYAN}▶ Taille: $(stat -f%z "$target_file" 2>/dev/null || stat -c%s "$target_file" 2>/dev/null || echo 'inconnue') octets${RESET}"
    
    # Mode de mise à jour selon configuration
    debug_log "Mode update configuré: $UPDATE_MODE (NO_AUTO_UPDATE=$NO_AUTO_UPDATE)"
    if [[ "$UPDATE_MODE" == "auto-replace"* ]] && [ "$NO_AUTO_UPDATE" -eq 0 ]; then
        # Afficher un message plus détaillé pour auto-replace-always
        if [[ "$UPDATE_MODE" == "auto-replace-always" ]]; then
            echo -e "${MAGENTA}Mode auto-replace-always - Installation automatique de la mise à jour...${RESET}"
        else
            echo "Mode auto-replace - Remplacement du script en cours..."
        fi
        
        local backup_file="$SCRIPT_PATH.bak"
        
        # Créer une sauvegarde
        if ! cp "$SCRIPT_PATH" "$backup_file"; then
            echo -e "${YELLOW}Avertissement: Échec création sauvegarde.${RESET}" >&2
        else
            chmod +x "$backup_file" 2>/dev/null
            echo "Sauvegarde créée: $backup_file"
        fi
        
        # Remplacer le script actuel
        if cp "$target_file" "$SCRIPT_PATH"; then
            chmod +x "$SCRIPT_PATH" 2>/dev/null
            replace_success=1
            if [[ "$UPDATE_MODE" == "auto-replace-always" ]]; then
                echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${RESET}"
                echo -e "${GREEN}║  MISE À JOUR INSTALLÉE AVEC SUCCÈS                    ║${RESET}"
                echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${RESET}"
                echo -e "${CYAN}• Nouvelle version: $latest_version${RESET}"
                echo -e "${CYAN}• Mode: $UPDATE_MODE${RESET}"
                echo -e "${CYAN}• Fichier: $SCRIPT_PATH${RESET}"
            else
                echo -e "${GREEN}Remplacement réussi.${RESET}"
            fi
            
            # Si le script est en cours d'exécution, quitter pour le relancer
            if [ "$replace_success" -eq 1 ]; then
                echo -e "${GREEN}Relance du script avec la nouvelle version...${RESET}"
                # Exécuter le nouveau script avec les mêmes arguments mais en désactivant la vérification
                # pour éviter une boucle infinie
                exec "$SCRIPT_PATH" --no-update-check "${original_args[@]}"
                # exec ne retourne jamais si réussi, sinon on continue
                echo -e "${YELLOW}Échec de relance. Poursuite avec l'extraction.${RESET}" >&2
            fi
        else
            echo -e "${RED}Échec du remplacement. L'extraction va se poursuivre.${RESET}" >&2
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
"""
        # Logguer les informations importantes
        logger.info(f"Mode de mise à jour: {update_mode}")
        logger.info(f"URLs de mise à jour configurées: {version_url} / {package_url}")
    
    return snippets

def generate_encryption_snippets(config: Dict[str, Any], metadata: Dict[str, Any], archive_original_filename: str) -> BashSnippetsDict:
    """Génère les snippets Bash relatifs au chiffrement."""
    snippets: BashSnippetsDict = {
        "encryption_vars": "",
        "decryption_logic": "",
        "decryption_cleanup": ""
    }
    
    encryption_enabled = metadata.get('encryption_enabled', False)
    encryption_tool = metadata.get('encryption_tool')
    
    if encryption_enabled and encryption_tool:
        enc_fname = "archive." + ("enc" if encryption_tool == "openssl" else "gpg")
        dec_fname = archive_original_filename
        ossl_c = config.get('compression', {}).get('openssl_cipher', DEFAULT_OPENSSL_CIPHER)
        ossl_i = config.get('compression', {}).get('openssl_iter', DEFAULT_OPENSSL_ITER)
        gpg_s2k = DEFAULT_GPG_S2K_OPTIONS
        
        var_lines = [
            f'ENCRYPTION_TOOL="{encryption_tool}"',
            f'ENCRYPTED_TMP_FILENAME="{enc_fname}"',
            f'DECRYPTED_TMP_FILENAME="{dec_fname}"',
            f'OPENSSL_CIPHER="{ossl_c}"',
            f'OPENSSL_ITER="{ossl_i}"',
            f'GPG_S2K_OPTIONS="{gpg_s2k}"'
        ]
        
        snippets["encryption_vars"] = "\n".join(var_lines)
        
        snippets["decryption_logic"] = f"""
    echo -e "${{HIGHLIGHT_STYLE}}• Vérification outil:${{RESET_STYLE}} ${{HIGHLIGHT_STYLE}}${{INFO_COLOR}}${{HIGHLIGHT_STYLE}}$ENCRYPTION_TOOL...${{RESET_STYLE}}"; if ! command -v $ENCRYPTION_TOOL &>/dev/null; then echo -e "${{RED}}Erreur: Outil '$ENCRYPTION_TOOL' absent.${{RESET}}" >&2; exit 1; fi
    local attempts=0 max_attempts=3 code=1 cmd="" pass=""; while [ $attempts -lt $max_attempts ]; do
        echo -en "• ${{HIGHLIGHT_STYLE}}Mot de passe déchiffrement :${{RESET_STYLE}} " >&2; read -s pass </dev/tty; echo "" >&2; if [ -z "$pass" ]; then echo -e "${{YELLOW}}Mdp vide.${{RESET}}"; continue; fi
        echo -en "${{HIGHLIGHT_STYLE}}• Tentative $((attempts + 1))... "; if [ "$ENCRYPTION_TOOL" == "openssl" ]; then export NVBUILDER_DEC_PASS="$pass"; cmd="openssl enc -d -${{OPENSSL_CIPHER}} -pbkdf2 -iter ${{OPENSSL_ITER}} -in '$ENCRYPTED_TMP_FILENAME' -out '$DECRYPTED_TMP_FILENAME' -pass env:NVBUILDER_DEC_PASS";
        elif [ "$ENCRYPTION_TOOL" == "gpg" ]; then cmd="gpg --quiet --batch --yes --pinentry-mode loopback ${{GPG_S2K_OPTIONS}} --passphrase '$pass' --output '$DECRYPTED_TMP_FILENAME' --decrypt '$ENCRYPTED_TMP_FILENAME' 2>/dev/null"; cmd+=" || "; cmd+="gpg --quiet --batch --yes --pinentry-mode loopback --passphrase '$pass' --output '$DECRYPTED_TMP_FILENAME' --decrypt '$ENCRYPTED_TMP_FILENAME' 2>/dev/null"; fi
        eval $cmd; code=$?; unset pass; [ "$ENCRYPTION_TOOL" == "openssl" ] && unset NVBUILDER_DEC_PASS; if [ $code -eq 0 ]; then echo -e "${{HIGHLIGHT_STYLE}}${{GREEN}}Déchiffrement OK.${{RESET}}"; break; fi
        echo -e "${{RED}}${{HIGHLIGHT_STYLE}}Échec (code $code). Mdp incorrect ?${{RESET}}" >&2; rm -f "$DECRYPTED_TMP_FILENAME" 2>/dev/null; attempts=$((attempts + 1)); if [ $attempts -ge $max_attempts ]; then echo -e "${{RED}}Trop d'échecs.${{RESET}}"; exit 1; fi; echo "$((max_attempts - attempts)) tentatives restantes." >&2;
    done; if [ $code -ne 0 ]; then exit 1; fi
"""
        
        snippets["decryption_cleanup"] = 'if [ "$DEBUG_MODE" -eq 0 ] && [ -f "$WORK_DIR/$DECRYPTED_TMP_FILENAME" ]; then rm -f "$WORK_DIR/$DECRYPTED_TMP_FILENAME"; fi'
    
    return snippets