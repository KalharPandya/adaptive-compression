import os
import gradio as gr
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
    # Create and run the interface
    interface = EnhancedGradioInterface()
    interface.run()
