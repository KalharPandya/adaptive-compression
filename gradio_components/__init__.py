# Gradio interface package for Adaptive Compression

# Prevent circular imports by avoiding direct imports in __init__.py
__all__ = ['run_interface']

# Lazy import function
def run_interface():
    """
    Run the enhanced Gradio interface for the adaptive compression algorithm
    """
    from .main import run_interface as _run
    return _run()
