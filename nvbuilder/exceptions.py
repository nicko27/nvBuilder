# nvbuilder/exceptions.py
"""Exceptions personnalisées pour nvBuilder."""

class NvBuilderError(Exception):
    """Classe de base pour les erreurs spécifiques à nvBuilder."""
    def __init__(self, message="Une erreur inattendue est survenue dans NVBuilder.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class ConfigError(NvBuilderError):
    """Erreur liée au chargement ou à la validation de la configuration."""
    def __init__(self, message="Erreur dans la configuration du script.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class ArchiveError(NvBuilderError):
    """Erreur lors de la création de l'archive tar."""
    def __init__(self, message="Impossible de créer l'archive.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class EncryptionError(NvBuilderError):
    """Erreur lors du chiffrement de l'archive."""
    def __init__(self, message="Échec du chiffrement de l'archive.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class ToolNotFoundError(NvBuilderError):
    """Erreur indiquant qu'un outil externe requis est introuvable."""
    def __init__(self, tool_name: str, message: str = ""):
        self.tool_name = tool_name
        full_message = message or f"L'outil externe requis '{tool_name}' n'a pas été trouvé dans le PATH."
        super().__init__(full_message)

class TemplateError(NvBuilderError):
    """Erreur liée au template Bash."""
    def __init__(self, message="Erreur dans le template Bash.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class BuildProcessError(NvBuilderError):
    """Erreur générale pendant le processus de build."""
    def __init__(self, message="Échec du processus de build.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

# Classes dupliquées pour compatibilité avec d'éventuels anciens codes
NVBuilderArchiveError = ArchiveError
NVBuilderConfigError = ConfigError
NVBuilderBuildError = BuildProcessError
NVBuilderException = NvBuilderError