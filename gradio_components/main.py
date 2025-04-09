import os
import sys
import traceback

# Import compatibility helpers using absolute imports
try:
    from gradio_components.compat import (
        is_gradio_available, 
        is_blocks_available, 
        create_blocks,
        get_themes,
        get_version_info
    )
    version_info = get_version_info()
    print(f"Using Gradio version {version_info['version']}")
    print(f"Blocks API available: {version_info['has_blocks']}")
    print(f"Themes support available: {version_info['has_themes']}")
    HAS_COMPAT = True
except ImportError as e:
    print(f"Failed to import compatibility layer: {e}")
    HAS_COMPAT = False

# Try importing gradio itself
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import gradio: {e}")
    GRADIO_AVAILABLE = False

# Dictionary to store imported UI components; errors will be logged.
ui_components = {}
import_errors = []

def safe_import(module_name):
    try:
        module = __import__(module_name, fromlist=['*'])
        return module
    except ImportError as e:
        import_errors.append(f"Failed to import {module_name}: {e}")
        return None

def run_interface():
    """
    Run the enhanced Gradio interface for the adaptive compression algorithm.
    """
    if not GRADIO_AVAILABLE:
        print("Error: Gradio is not installed")
        print("Please install Gradio: pip install gradio>=3.0.0")
        sys.exit(1)
    
    # Map of UI modules using absolute imports
    ui_modules = {
        'about': 'gradio_components.tabs.about',
        'compress': 'gradio_components.tabs.compress',
        'decompress': 'gradio_components.tabs.decompress',
        'analysis': 'gradio_components.tabs.analysis',
        'file_format': 'gradio_components.tabs.file_format',
        'help': 'gradio_components.tabs.help',
        'utils': 'gradio_components.utils',
        'interface': 'gradio_components.interface'
    }
    
    for key, module_name in ui_modules.items():
        module = safe_import(module_name)
        ui_components[key] = module
    
    all_components_available = all(ui_components.values())
    
    if not all_components_available:
        print("\nUI component import errors:")
        for error in import_errors:
            print(f"  - {error}")
        print("Error: Some required UI components are not available. Please check your installation.")
        sys.exit(1)
    
    print("Successfully imported all UI components")
    
    # Import the enhanced interface class using an absolute import
    try:
        from gradio_components.interface import EnhancedGradioInterface
    except Exception as e:
        print(f"Error importing EnhancedGradioInterface: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    try:
        interface = EnhancedGradioInterface()
        interface.run()
    except Exception as e:
        print(f"Error running enhanced interface: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_interface()
