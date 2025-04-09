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

# Import UI components with robust error handling
try:
    # Try importing gradio first
    import gradio_components as gr
    
    # Now try importing other UI components
    import_errors = []
    
    # Use a function to handle each import separately
    def safe_import(module_name):
        try:
            return __import__(module_name, fromlist=['*'])
        except ImportError as e:
            import_errors.append(f"Failed to import {module_name}: {e}")
            return None
    
    # Import all the modules we need
    about_module = safe_import('.tabs.about')
    compress_module = safe_import('.tabs.compress')
    decompress_module = safe_import('.tabs.decompress')
    analysis_module = safe_import('.tabs.analysis')
    file_format_module = safe_import('.tabs.file_format')
    help_module = safe_import('.tabs.help')
    utils_module = safe_import('.utils')
    interface_module = safe_import('.interface')
    
    # Check if we could import all the required modules
    MODULES_AVAILABLE = all([
        about_module, compress_module, decompress_module,
        analysis_module, file_format_module, help_module,
        utils_module, interface_module
    ])
    
    # Only set imports if all modules are available
    if MODULES_AVAILABLE:
        create_about_tab = about_module.create_about_tab
        create_compress_tab = compress_module.create_compress_tab
        compress_file_enhanced = compress_module.compress_file_enhanced
        create_decompress_tab = decompress_module.create_decompress_tab
        decompress_file_enhanced = decompress_module.decompress_file_enhanced
        create_analysis_tab = analysis_module.create_analysis_tab
        generate_enhanced_analysis = analysis_module.generate_enhanced_analysis
        create_file_format_tab = file_format_module.create_file_format_tab
        create_help_tab = help_module.create_help_tab
        create_header = utils_module.create_header
        toggle_detailed_stats = utils_module.toggle_detailed_stats
        clear_compression_history = utils_module.clear_compression_history
        EnhancedGradioInterface = interface_module.EnhancedGradioInterface
        
        # Log success
        print("Successfully imported all UI components")
    else:
        # Log the specific import errors
        print("\nUI component import errors:")
        for error in import_errors:
            print(f"  - {error}")
except ImportError as e:
    # Main gradio import failed
    print(f"Failed to import gradio: {e}")
    MODULES_AVAILABLE = False

def run_interface():
    """
    Run the enhanced Gradio interface for the adaptive compression algorithm
    """
    # Check if all modules are available
    if not MODULES_AVAILABLE:
        print("Error: Some required modules are not available")
        print("Please check your installation. The enhanced UI may not work correctly.")
        sys.exit(1)
    
    # Check if Gradio Blocks is available
    if not hasattr(gr, 'Blocks'):
        if HAS_COMPAT and is_blocks_available():
            print("Using compatibility layer for Gradio Blocks")
        else:
            print("Error: Your Gradio installation doesn't support Blocks interface")
            print("Please upgrade gradio: pip install --upgrade gradio>=3.0.0")
            sys.exit(1)
    
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

if __name__ == "__main__":
    run_interface()
