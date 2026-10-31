__version__ = "0.1.0"

# Identificador de la compilación (lo genera scripts/embed_key.py al crear el exe/AppImage).
try:
    from ownhost._build import BUILD
except ImportError:
    BUILD = "dev"
