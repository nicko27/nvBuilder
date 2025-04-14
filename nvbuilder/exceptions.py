# nvbuilder/exceptions.py
"""Exceptions personnalisées pour nvBuilder."""

class NvBuilderError(Exception):
    """Classe de base pour les erreurs spécifiques à nvBuilder."""
    pass

class ConfigError(NvBuilderError):
    """Erreur liée au chargement ou à la validation de la configuration."""
    pass

class ArchiveError(NvBuilderError):
    """Erreur lors de la création de l'archive tar."""
    pass

class EncryptionError(NvBuilderError):
    """Erreur lors du chiffrement de l'archive."""
    pass

class ToolNotFoundError(NvBuilderError):
    """Erreur indiquant qu'un outil externe requis est introuvable."""
    def __init__(self, tool_name: str, message: str = ""):
        self.tool_name = tool_name
        self.message = message or f"L'outil externe requis '{tool_name}' n'a pas été trouvé dans le PATH."
        super().__init__(self.message)

class TemplateError(NvBuilderError):
    """Erreur liée au template Bash."""
    pass

class BuildProcessError(NvBuilderError):
    """Erreur générale pendant le processus de build."""
    pass