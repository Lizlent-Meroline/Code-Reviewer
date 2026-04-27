from .python_analyzer import PythonAnalyzer
from .go_analyzer import GoAnalyzer
from .generic import GenericAnalyzer

def get_analyzer(language):
    """Return appropriate analyzer instance based on detected language."""
    if language == "python":
        return PythonAnalyzer()
    elif language == "go":
        return GoAnalyzer()
    else:
        return GenericAnalyzer()