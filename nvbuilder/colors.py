# nvbuilder/colors.py
"""Définition centralisée des couleurs pour l'affichage."""

# Importation conditionnelle de colorama pour éviter les erreurs si non installé
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    
    # Classe pour simuler colorama si non disponible
    class DummyColorama:
        def __getattr__(self, name): return ""
    Fore = Style = DummyColorama()
    Style.RESET_ALL = ""

# =====================================================================
# CONFIGURATION DES COULEURS - Modifiez ces valeurs selon vos préférences
# =====================================================================

# Couleurs par fonction sémantique - modifiez selon vos préférences
ERROR_COLOR = Fore.RED         # Couleur pour les erreurs
SUCCESS_COLOR = Fore.GREEN     # Couleur pour les succès/validations
WARNING_COLOR = Fore.YELLOW    # Couleur pour les avertissements
INFO_COLOR = Fore.BLUE         # Couleur pour les informations générales
DETAIL_COLOR = Fore.CYAN       # Couleur pour les détails/données
UPDATE_COLOR = Fore.MAGENTA    # Couleur pour les mises à jour
DEBUG_COLOR = Fore.BLUE        # Couleur pour les messages de debug
HEADER_COLOR = Fore.CYAN       # Couleur pour les en-têtes/titres

# Couleurs pour éléments spécifiques
BANNER_COLOR = Fore.CYAN       # Couleur pour les bannières
FILENAME_COLOR = Fore.CYAN     # Couleur pour les noms de fichiers
OPTION_COLOR = Fore.CYAN       # Couleur pour les options de commande
KEY_COLOR = Fore.CYAN          # Couleur pour les clés/propriétés
VALUE_COLOR = Fore.GREEN       # Couleur pour les valeurs
PATH_COLOR = Fore.CYAN         # Couleur pour les chemins de fichiers

# Styles (modifiez ces valeurs pour changer l'apparence)
HIGHLIGHT_STYLE = Style.BRIGHT # Style pour mettre en évidence
SUBTLE_STYLE = Style.DIM       # Style atténué
RESET_STYLE = Style.RESET_ALL  # Réinitialisation du style

# =====================================================================
# Fin de la configuration (ne pas modifier ci-dessous)
# =====================================================================

# Alias pour la compatibilité avec le code existant
RED = ERROR_COLOR
GREEN = SUCCESS_COLOR
YELLOW = WARNING_COLOR
BLUE = INFO_COLOR
CYAN = DETAIL_COLOR
MAGENTA = UPDATE_COLOR
BRIGHT = HIGHLIGHT_STYLE
DIM = SUBTLE_STYLE
RESET = RESET_STYLE

# Fonction pour désactiver toutes les couleurs
def disable_colors():
    """Désactive les couleurs (utile pour les logs ou sorties non-TTY)."""
    global ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR, INFO_COLOR, DETAIL_COLOR
    global UPDATE_COLOR, DEBUG_COLOR, HIGHLIGHT_STYLE, SUBTLE_STYLE, RESET_STYLE
    global RED, GREEN, YELLOW, BLUE, CYAN, MAGENTA, BRIGHT, DIM, RESET
    
    ERROR_COLOR = SUCCESS_COLOR = WARNING_COLOR = INFO_COLOR = DETAIL_COLOR = ""
    UPDATE_COLOR = DEBUG_COLOR = HIGHLIGHT_STYLE = SUBTLE_STYLE = RESET_STYLE = ""
    RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = BRIGHT = DIM = RESET = ""

# Désactiver les couleurs si colorama n'est pas disponible
if not HAS_COLORAMA:
    disable_colors()