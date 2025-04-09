import os
import sys
import traceback

# Import compatibility helpers
try:
    from .compat import (
        is_gradio_available, 
        is_blocks_available, 
        create_blocks,
        get_themes,
        get_version_info
    )
    # Print detailed version info
    version_info = get_version_info()
    print(f"Using Gradio version {version_info['version']}")
    print(f"Blocks API available: {version_info['has_blocks']}")
    print(f"Themes support available: {version_info['has_themes']}")
    HAS_COMPAT = True
except ImportError as e:
    print(f"Failed to import compatibility layer: {e}")
    HAS_COMPAT = False

# First try importing gradio itself
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import gradio: {e}")
    GRADIO_AVAILABLE = False

# Initialize UI components dictionary to be populated later
ui_components = {}
import_errors = []

# Use a function to handle each import separately
def safe_import(module_name):
    try:
        module = __import__(module_name, fromlist=['*'])
        return module
    except ImportError as e:
        import_errors.append(f"Failed to import {module_name}: {e}")
        return None

def run_interface():
    """
    Run the enhanced Gradio interface for the adaptive compression algorithm
    """
    global ui_components, import_errors
    
    # First check if Gradio is available
    if not GRADIO_AVAILABLE:
        print("Error: Gradio is not installed")
        print("Please install Gradio: pip install gradio>=3.0.0")
        sys.exit(1)
    
    # Now try importing other UI components
    ui_modules = {
        'about': '.tabs.about',
        'compress': '.tabs.compress',
        'decompress': '.tabs.decompress',
        'analysis': '.tabs.analysis',
        'file_format': '.tabs.file_format',
        'help': '.tabs.help',
        'utils': '.utils',
        'interface': '.interface'
    }
    
    # Import all modules and populate ui_components
    for key, module_name in ui_modules.items():
        module = safe_import(module_name)
        ui_components[key] = module
    
    # Check if we have all required components
    all_components_available = all(ui_components.values())
    
    if all_components_available:
        print("Successfully imported all UI components")
        
        # Now import the interface module specifically
        from .interface import EnhancedGradioInterface
        
        # Create and run the interface
        try:
            interface = EnhancedGradioInterface()
            interface.run()
        except Exception as e:
            print(f"Error running enhanced interface: {e}")
            print("Traceback:")
            traceback.print_exc()
            
            # Attempt to fall back to basic interface
            try:
                print("Falling back to basic interface...")
                from gradio_interface import GradioInterface
                basic_interface = GradioInterface()
                basic_interface.run()
            except Exception as fallback_error:
                print(f"Error running basic interface: {fallback_error}")
                print("No functioning interface available. Exiting.")
                sys.exit(1)
    else:
        # Log the specific import errors
        print("\nUI component import errors:")
        for error in import_errors:
            print(f"  - {error}")
        
        print("Error: Some required modules are not available")
        print("Please check your installation. The enhanced UI may not work correctly.")

if __name__ == "__main__":
    run_interface()
