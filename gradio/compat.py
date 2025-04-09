"""
Compatibility layer for Gradio interfaces.

This module provides helper functions and classes to ensure compatibility 
across different versions of Gradio.
"""

import sys
import importlib.util

# Check if Gradio is installed and which version we're using
try:
    import gradio as gr
    GRADIO_VERSION = getattr(gr, '__version__', '0.0.0')
    # Check if Blocks is available directly (newer Gradio versions)
    HAS_BLOCKS = hasattr(gr, 'Blocks')
    # If not, try to import from gradio.blocks (older versions)
    if not HAS_BLOCKS:
        try:
            from gradio import blocks
            gr.Blocks = blocks.Blocks
            HAS_BLOCKS = True
            print(f"Using compatibility layer for Gradio {GRADIO_VERSION}")
        except (ImportError, AttributeError):
            HAS_BLOCKS = False
            print(f"Warning: Your Gradio version {GRADIO_VERSION} doesn't support Blocks interface")
except ImportError:
    GRADIO_VERSION = None
    HAS_BLOCKS = False
    print("Warning: Gradio is not installed. GUI features will not be available.")

def is_gradio_available():
    """Check if Gradio is available and properly installed"""
    return GRADIO_VERSION is not None

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
            from gradio import blocks
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
