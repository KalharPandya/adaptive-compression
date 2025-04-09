"""
Compatibility layer for different versions of gradio.
This module provides functions to check for gradio features and version compatibility.
"""

import sys
import importlib
import importlib.util
import pkg_resources

def get_version_info():
    """
    Get detailed information about the installed gradio version and features.
    
    Returns:
        dict: Information about the gradio installation
    """
    info = {
        'version': 'unknown',
        'has_blocks': False,
        'has_themes': False,
        'error': None
    }
    
    try:
        # Try to get version via pkg_resources first
        try:
            info['version'] = pkg_resources.get_distribution("gradio").version
        except (pkg_resources.DistributionNotFound, Exception):
            # Fall back to direct import
            try:
                import gradio
                info['version'] = getattr(gradio, '__version__', 'unknown')
            except ImportError:
                info['error'] = "Gradio not installed"
                return info
        
        # Check for Blocks API
        try:
            import gradio as gr
            info['has_blocks'] = hasattr(gr, 'Blocks')
        except (ImportError, AttributeError):
            pass
        
        # Check for themes
        try:
            import gradio as gr
            info['has_themes'] = hasattr(gr, 'themes') or hasattr(gr, 'Theme')
        except (ImportError, AttributeError):
            pass
            
    except Exception as e:
        info['error'] = str(e)
    
    return info

def is_gradio_available():
    """
    Check if gradio is available in the current environment.
    
    Returns:
        bool: True if gradio is available, False otherwise
    """
    try:
        import gradio
        return True
    except ImportError:
        return False

def is_blocks_available():
    """
    Check if gradio.Blocks is available.
    
    Returns:
        bool: True if gradio.Blocks is available, False otherwise
    """
    try:
        import gradio as gr
        return hasattr(gr, 'Blocks')
    except (ImportError, AttributeError):
        return False

def create_blocks(*args, **kwargs):
    """
    Create a gradio Blocks object with compatibility across versions.
    
    Returns:
        object: A gradio Blocks object or None if not available
    """
    if not is_blocks_available():
        return None
        
    try:
        import gradio as gr
        return gr.Blocks(*args, **kwargs)
    except Exception:
        return None

def get_themes():
    """
    Get available themes in a version-compatible way.
    
    Returns:
        dict: Available themes or empty dict if not supported
    """
    themes = {}
    
    try:
        import gradio as gr
        # Try new style themes
        if hasattr(gr, 'themes'):
            for name in dir(gr.themes):
                if name.startswith('__'):
                    continue
                themes[name] = getattr(gr.themes, name)
        # Try old style Theme class
        elif hasattr(gr, 'Theme'):
            themes['default'] = None
    except (ImportError, AttributeError):
        pass
        
    return themes

def gradio_version_at_least(version_str):
    """
    Check if the installed gradio version is at least the specified version.
    
    Args:
        version_str (str): Version string to check against (e.g., "3.0.0")
        
    Returns:
        bool: True if installed version is >= the specified version
    """
    try:
        installed_version = pkg_resources.get_distribution("gradio").version
        installed = pkg_resources.parse_version(installed_version)
        required = pkg_resources.parse_version(version_str)
        return installed >= required
    except Exception:
        return False

def import_with_fallback(module_path, fallback=None):
    """
    Try to import a module, return fallback if it fails.
    
    Args:
        module_path (str): Dotted path to the module
        fallback: Value to return if import fails
        
    Returns:
        module or fallback: The imported module or fallback value
    """
    try:
        return importlib.import_module(module_path)
    except ImportError:
        return fallback
