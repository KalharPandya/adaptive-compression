"""
Compatibility layer for Gradio Blocks API across different versions.
"""

import importlib.util
import sys
import warnings

def create_blocks(*args, **kwargs):
    """
    Create a Gradio Blocks object with compatibility across different Gradio versions
    
    Returns:
        object: A Gradio Blocks object or None if not available
    """
    try:
        import gradio as gr
        if hasattr(gr, 'Blocks'):
            return gr.Blocks(*args, **kwargs)
        else:
            # For older versions, try to use gradio.blocks if available
            try:
                if hasattr(gr, 'blocks') and hasattr(gr.blocks, 'Blocks'):
                    warnings.warn("Using legacy Gradio blocks API")
                    return gr.blocks.Blocks(*args, **kwargs)
            except (ImportError, AttributeError):
                pass
            
            # For really old versions, try to use interfaceV2 if available
            try:
                if hasattr(gr, 'interfaceV2'):
                    warnings.warn("Using very old Gradio interface API")
                    return gr.interfaceV2(*args, **kwargs)
            except (ImportError, AttributeError):
                pass
    except ImportError:
        pass
    
    # If we reach here, Blocks API is not available
    print("WARNING: Gradio Blocks API not available. Please upgrade Gradio to 3.0.0 or later.")
    return None

def create_row(*args, **kwargs):
    """Create a Gradio Row component with version compatibility"""
    try:
        import gradio as gr
        if hasattr(gr, 'Row'):
            return gr.Row(*args, **kwargs)
        elif hasattr(gr, 'layouts') and hasattr(gr.layouts, 'Row'):
            return gr.layouts.Row(*args, **kwargs)
    except (ImportError, AttributeError):
        pass
    return None

def create_column(*args, **kwargs):
    """Create a Gradio Column component with version compatibility"""
    try:
        import gradio as gr
        if hasattr(gr, 'Column'):
            return gr.Column(*args, **kwargs)
        elif hasattr(gr, 'layouts') and hasattr(gr.layouts, 'Column'):
            return gr.layouts.Column(*args, **kwargs)
    except (ImportError, AttributeError):
        pass
    return None

def create_tab(*args, **kwargs):
    """Create a Gradio Tab component with version compatibility"""
    try:
        import gradio as gr
        if hasattr(gr, 'Tab'):
            return gr.Tab(*args, **kwargs)
        elif hasattr(gr, 'layouts') and hasattr(gr.layouts, 'Tab'):
            return gr.layouts.Tab(*args, **kwargs)
    except (ImportError, AttributeError):
        pass
    return None

def create_tabbed_interface(*args, **kwargs):
    """Create a Gradio TabbedInterface with version compatibility"""
    try:
        import gradio as gr
        if hasattr(gr, 'TabbedInterface'):
            return gr.TabbedInterface(*args, **kwargs)
    except (ImportError, AttributeError):
        pass
    return None

def get_version():
    """Get the installed Gradio version or 'unknown'"""
    try:
        import gradio
        if hasattr(gradio, '__version__'):
            return gradio.__version__
        
        try:
            import pkg_resources
            return pkg_resources.get_distribution("gradio").version
        except:
            pass
    except ImportError:
        pass
    return "unknown"

def is_blocks_available():
    """Check if Gradio Blocks API is available"""
    try:
        import gradio as gr
        return hasattr(gr, 'Blocks') or (hasattr(gr, 'blocks') and hasattr(gr.blocks, 'Blocks'))
    except ImportError:
        return False
