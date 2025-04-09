import os
import sys
import time
import tempfile
import json
import traceback
import numpy as np
import io

# Safely import gradio with version compatibility
try:
    import gradio as gr
    # Check for Blocks API differences between versions
    HAS_BLOCKS = hasattr(gr, 'Blocks')
    if not HAS_BLOCKS:
        try:
            from gradio import blocks
            gr.Blocks = blocks.Blocks
            HAS_BLOCKS = True
            print(f"Using compatibility layer for Gradio {getattr(gr, '__version__', 'unknown')}")
        except (ImportError, AttributeError):
            HAS_BLOCKS = False
            print(f"Warning: Your Gradio version {getattr(gr, '__version__', 'unknown')} doesn't support Blocks interface")
except ImportError:
    print("Error: gradio module not found. Please install it with pip install gradio")
    HAS_BLOCKS = False

# Import matplotlib only when needed to avoid unnecessary dependency
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

# Import UI components - catch ImportError to allow this module to be imported 
# even if the gradio subdirectory structure isn't set up yet
try:
    from .tabs.about import create_about_tab
    from .tabs.compress import create_compress_tab, compress_file_enhanced
    from .tabs.decompress import create_decompress_tab, decompress_file_enhanced
    from .tabs.analysis import create_analysis_tab, generate_enhanced_analysis
    from .tabs.file_format import create_file_format_tab
    from .tabs.help import create_help_tab
    from .utils import create_header, toggle_detailed_stats, clear_compression_history
    HAS_ENHANCED_UI = True
except ImportError:
    # If the import fails, the enhanced UI won't be available, but basic functions still will
    HAS_ENHANCED_UI = False

class EnhancedGradioInterface:
    """
    Enhanced Gradio interface for the adaptive compression algorithm with better
    explanations, visualizations, and user experience.
    """
    
    def __init__(self, title="Adaptive Marker-Based Compression"):
        """
        Initialize the Gradio interface
        
        Args:
            title (str): Title for the interface
        """
        self.title = title
        self.compressor = AdaptiveCompressor()
        self.analyzer = CompressionAnalyzer()
        self.results_dir = "compression_results"
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Try to load previous results
        self.results_file = os.path.join(self.results_dir, "compression_history.json")
        if os.path.exists(self.results_file):
            try:
                self.analyzer.load_results(self.results_file)
                print(f"Loaded {len(self.analyzer.results)} previous compression results")
            except Exception as e:
                print(f"Error loading previous results: {e}")
    
    def _ensure_serializable(self, data):
        """
        Ensure all data is serializable for Gradio JSON component
        
        Args:
            data: The data to ensure is serializable
            
        Returns:
            Serializable version of the data
        """
        if isinstance(data, dict):
            return {str(k): self._ensure_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._ensure_serializable(v) for v in data]
        elif isinstance(data, tuple):
            return tuple(self._ensure_serializable(v) for v in data)
        elif isinstance(data, set):
            return list(self._ensure_serializable(v) for v in data)
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            return str(data)
    
    def run(self):
        """
        Start the Gradio interface with enhanced UI and explanations
        """
        # Check if Gradio Blocks is available
        if not HAS_BLOCKS:
            print("Error: Your Gradio installation doesn't support Blocks interface")
            print("Please upgrade gradio: pip install --upgrade gradio>=3.0.0")
            return

        try:
            # Try to use the enhanced UI with themes support
            with gr.Blocks(title=self.title, theme=gr.themes.Soft() if hasattr(gr, 'themes') else None) as demo:
                # Header with logo and title
                create_header(self.title)
                
                # Main tabs
                with gr.Tabs() as tabs:
                    # About tab
                    about_tab = create_about_tab()
                    
                    # Compress tab
                    compress_tab, inputs_compress, outputs_compress = create_compress_tab()
                    
                    # Decompress tab
                    decompress_tab, inputs_decompress, outputs_decompress = create_decompress_tab()
                    
                    # Analysis tab
                    analysis_tab, inputs_analysis, outputs_analysis = create_analysis_tab()
                    
                    # File Format tab
                    file_format_tab = create_file_format_tab()
                    
                    # Help tab
                    help_tab = create_help_tab()
                
                # Connect button callbacks - passing the interface instance
                self._connect_callbacks(demo, inputs_compress, outputs_compress, 
                                      inputs_decompress, outputs_decompress,
                                      inputs_analysis, outputs_analysis)
                
                # Launch the interface
                demo.launch()
                
        except Exception as e:
            print(f"Error in enhanced UI: {e}")
            print("Falling back to basic interface...")
            self._run_basic_interface()
    
    def _run_basic_interface(self):
        """Fallback to a more basic interface if the enhanced UI fails"""
        try:
            from gradio_interface import GradioInterface
            interface = GradioInterface(self.title)
            interface.run()
        except Exception as e:
            print(f"Error running basic interface: {e}")
            print("Please check your Gradio installation.")
    
    def _connect_callbacks(self, demo, inputs_compress, outputs_compress, 
                         inputs_decompress, outputs_decompress,
                         inputs_analysis, outputs_analysis):
        """
        Connect all callback functions for the UI components
        """
        # Compression callbacks
        inputs_compress["compress_btn"].click(
            lambda *args: compress_file_enhanced(self, *args),
            inputs=[inputs_compress["input_file"], 
                   inputs_compress["chunk_size"], 
                   inputs_compress["use_multithreading"]],
            outputs=[outputs_compress["output_file"], 
                    outputs_compress["result_summary"], 
                    outputs_compress["compression_stats"], 
                    outputs_compress["stats_toggle"], 
                    outputs_compress["method_chart"], 
                    outputs_compress["compress_log"]]
        )
        
        # Decompression callbacks
        inputs_decompress["decompress_btn"].click(
            lambda *args: decompress_file_enhanced(self, *args),
            inputs=[inputs_decompress["compressed_file"]],
            outputs=[outputs_decompress["decompressed_file"], 
                    outputs_decompress["decomp_summary"], 
                    outputs_decompress["decompression_stats"], 
                    outputs_decompress["decomp_stats_toggle"], 
                    outputs_decompress["decompress_log"]]
        )
        
        # Analysis callbacks
        inputs_analysis["analyze_btn"].click(
            lambda: generate_enhanced_analysis(self),
            inputs=[],
            outputs=[outputs_analysis["summary_stats"], 
                    outputs_analysis["ratio_plot"], 
                    outputs_analysis["method_plot"], 
                    outputs_analysis["size_plot"], 
                    outputs_analysis["throughput_plot"], 
                    outputs_analysis["filetype_plot"]]
        )
        
        inputs_analysis["clear_history_btn"].click(
            lambda: clear_compression_history(self),
            inputs=[],
            outputs=[outputs_analysis["summary_stats"]]
        )
        
        # Connect toggle callbacks for showing detailed stats
        outputs_compress["stats_toggle"].change(
            toggle_detailed_stats,
            inputs=[outputs_compress["stats_toggle"]],
            outputs=[outputs_compress["compression_stats"]]
        )
        
        outputs_decompress["decomp_stats_toggle"].change(
            toggle_detailed_stats,
            inputs=[outputs_decompress["decomp_stats_toggle"]],
            outputs=[outputs_decompress["decompression_stats"]]
        )
    
    def format_file_size(self, size_bytes):
        """
        Format file size in bytes to a human-readable format
        
        Args:
            size_bytes (int): Size in bytes
            
        Returns:
            str: Formatted size (e.g. "4.2 MB")
        """
        if size_bytes == 0:
            return "0 B"
            
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"