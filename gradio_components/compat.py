"""
Compatibility layer for Gradio interfaces.

This module provides helper functions and classes to ensure compatibility 
across different versions of Gradio.
"""

import sys
import importlib
import importlib.util
import pkg_resources

# Get Gradio version using pkg_resources if possible
try:
    GRADIO_VERSION = pkg_resources.get_distribution("gradio").version
    print(f"Detected Gradio version {GRADIO_VERSION} using pkg_resources")
except (pkg_resources.DistributionNotFound, Exception):
    GRADIO_VERSION = "unknown"

# Check if Gradio is installed and which version we're using
try:
    import gradio_components as gr
    
    # Try to get version directly from module if not already found
    if GRADIO_VERSION == "unknown":
        if hasattr(gr, "__version__"):
            GRADIO_VERSION = gr.__version__
            print(f"Detected Gradio version {GRADIO_VERSION} from module attribute")
        else:
            # Try to find version from package metadata
            try:
                # Use importlib.metadata for Python 3.8+
                if sys.version_info >= (3, 8):
                    import importlib.metadata
                    GRADIO_VERSION = importlib.metadata.version("gradio")
                    print(f"Detected Gradio version {GRADIO_VERSION} from importlib.metadata")
                # Fallback to pkg_resources for older Python versions
                else:
                    GRADIO_VERSION = "unknown"
            except ImportError:
                GRADIO_VERSION = "unknown"
    
    # Check if Blocks is available directly (newer Gradio versions >= 3.0)
    HAS_BLOCKS = hasattr(gr, 'Blocks')
    if HAS_BLOCKS:
        print(f"Gradio {GRADIO_VERSION} has native Blocks support")
    # If not, try to import from gradio.blocks (older versions < 3.0)
    else:
        try:
            from gradio_components import blocks
            gr.Blocks = blocks.Blocks
            HAS_BLOCKS = True
            print(f"Using compatibility layer for Gradio {GRADIO_VERSION}")
        except (ImportError, AttributeError) as e:
            HAS_BLOCKS = False
            print(f"Warning: Gradio {GRADIO_VERSION} doesn't support Blocks interface: {e}")
except ImportError as e:
    GRADIO_VERSION = None
    HAS_BLOCKS = False
    print(f"Warning: Gradio is not installed or not importable: {e}")

def is_gradio_available():
    """Check if Gradio is available and properly installed"""
    return GRADIO_VERSION is not None and GRADIO_VERSION != "unknown"

def is_blocks_available():
    """Check if the Blocks interface is available"""
    return HAS_BLOCKS

def create_blocks(*args, **kwargs):
    """
    Create a Blocks interface with appropriate compatibility 
    between different Gradio versions
    """
    if not HAS_BLOCKS:
        raise ImportError("Gradio Blocks interface is not available")
    
    # Handle theme compatibility
    if 'theme' in kwargs and not hasattr(gr, 'themes'):
        # Remove theme argument if themes are not supported
        print("Removing 'theme' argument as it's not supported in this Gradio version")
        kwargs.pop('theme')
    
    return gr.Blocks(*args, **kwargs)

def get_themes():
    """Get available themes or None if not supported"""
    return getattr(gr, 'themes', None)

def create_tab_interface():
    """Create a tab interface that works across Gradio versions"""
    if not HAS_BLOCKS:
        raise ImportError("Gradio Blocks interface is not available")
    
    # In newer versions, Tabs is directly under gr
    # In older versions, it might be under blocks
    if hasattr(gr, 'Tabs'):
        return gr.Tabs()
    else:
        try:
            from gradio_components import blocks
            return blocks.Tabs()
        except (ImportError, AttributeError):
            raise ImportError("Tabs interface not available in this Gradio version")

def get_version_info():
    """Get Gradio version and capability information"""
    return {
        "version": GRADIO_VERSION,
        "has_blocks": HAS_BLOCKS,
        "has_themes": hasattr(gr, 'themes') if GRADIO_VERSION else False,
        "has_tabs": hasattr(gr, 'Tabs') if GRADIO_VERSION else False
    }
