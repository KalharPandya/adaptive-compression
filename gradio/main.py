import os
import sys
import gradio as gr

# Import compatibility helpers
try:
    from .compat import is_blocks_available, create_blocks, get_themes
    HAS_COMPAT = True
except ImportError:
    HAS_COMPAT = False

# Import UI components
from .tabs.about import create_about_tab
from .tabs.compress import create_compress_tab
from .tabs.decompress import create_decompress_tab
from .tabs.analysis import create_analysis_tab
from .tabs.file_format import create_file_format_tab
from .tabs.help import create_help_tab
from .utils import create_header
from .interface import EnhancedGradioInterface

def run_interface():
    """
    Run the enhanced Gradio interface for the adaptive compression algorithm
    """
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
        print("Falling back to basic interface...")
        from gradio_interface import GradioInterface
        basic_interface = GradioInterface()
        basic_interface.run()

if __name__ == "__main__":
    run_interface()
