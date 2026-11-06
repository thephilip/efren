"""efren — The Magician: composable inventor-mind suite."""

__version__ = "0.1.0"
from efren.core.mind import Mind
from efren.core.style import Style
from efren.core.composer import Composer
from efren.core.corpus import Corpus

__all__ = ["Mind", "Style", "Composer", "Corpus"]
