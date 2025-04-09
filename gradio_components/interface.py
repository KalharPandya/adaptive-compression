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
            return tuple(self._ensure_serializable(v) for v in tuple)
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
            self._run_basic_interface()
            return

        # Add the gradio_components directory to the path to help with imports
        components_path = os.path.dirname(os.path.abspath(__file__))
        if components_path not in sys.path:
            sys.path.append(components_path)
        
        # Try to find the tab modules directly without relying on package imports
        tab_modules = {}
        
        # First try direct imports
        try:
            # Safe import helper
            def safe_import(module_name):
                try:
                    if module_name.startswith("."):
                        # Package relative import
                        module = __import__(module_name[1:], fromlist=['*'])
                    else:
                        # Direct import
                        module = __import__(module_name, fromlist=['*'])
                    print(f"Successfully imported {module_name}")
                    return module
                except ImportError as e:
                    print(f"Failed to import {module_name}: {e}")
                    return None

            # Try importing from the tabs directory directly
            tabs_path = os.path.join(components_path, "tabs")
            if os.path.exists(tabs_path) and os.path.isdir(tabs_path):
                # Add tabs directory to path
                if tabs_path not in sys.path:
                    sys.path.append(tabs_path)
                
                # Try to import each module
                module_names = ["about", "compress", "decompress", "analysis", "file_format", "help"]
                for name in module_names:
                    # Try direct import
                    tab_modules[name] = safe_import(name)
                    
                    # If that fails, try relative import
                    if tab_modules[name] is None:
                        tab_modules[name] = safe_import(f"tabs.{name}")
                
                # Try to import utils
                utils_module = safe_import("utils")
                if utils_module is None:
                    utils_module = safe_import(".utils")
                        
                # Check if we have enough modules
                if all(tab_modules.values()) and utils_module:
                    # We have all modules - build enhanced UI
                    self._build_enhanced_ui(tab_modules, utils_module)
                    return
        
        except Exception as e:
            print(f"Error loading UI modules: {e}")
            traceback.print_exc()
        
        # If we reach here, fallback to basic interface
        print("Some modules could not be loaded. Falling back to basic interface.")
        self._run_basic_interface()
    
    def _build_enhanced_ui(self, tab_modules, utils_module):
        """
        Build the enhanced UI with the provided modules
        
        Args:
            tab_modules (dict): Dictionary of tab modules
            utils_module: Utils module
        """
        try:
            # Extract required functions from modules
            about = tab_modules['about']
            compress = tab_modules['compress']
            decompress = tab_modules['decompress']
            analysis = tab_modules['analysis']
            file_format = tab_modules['file_format']
            help_mod = tab_modules['help']
            
            create_about_tab = getattr(about, 'create_about_tab')
            create_compress_tab = getattr(compress, 'create_compress_tab')
            compress_file_enhanced = getattr(compress, 'compress_file_enhanced')
            create_decompress_tab = getattr(decompress, 'create_decompress_tab')
            decompress_file_enhanced = getattr(decompress, 'decompress_file_enhanced')
            create_analysis_tab = getattr(analysis, 'create_analysis_tab')
            generate_enhanced_analysis = getattr(analysis, 'generate_enhanced_analysis')
            create_file_format_tab = getattr(file_format, 'create_file_format_tab')
            create_help_tab = getattr(help_mod, 'create_help_tab')
            create_header = getattr(utils_module, 'create_header')
            toggle_detailed_stats = getattr(utils_module, 'toggle_detailed_stats')
            clear_compression_history = getattr(utils_module, 'clear_compression_history')
            
            # Build the UI
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
            print(f"Error building enhanced UI: {e}")
            traceback.print_exc()
            self._run_basic_interface()
    
    def _run_basic_interface(self):
        """Fallback to a more basic interface if the enhanced UI fails"""
        try:
            # Import gradio directly for the basic interface
            import gradio as gr
            
            # Create a basic Gradio interface
            with gr.Blocks(title=self.title) as demo:
                gr.Markdown(f"# {self.title}")
                gr.Markdown("""
                This app demonstrates an adaptive compression algorithm that uses different 
                compression techniques for different parts of a file based on which technique 
                would be most efficient for that particular data pattern.
                
                **Note**: The enhanced UI is not available. Using basic interface.
                """)
                
                with gr.Tab("Compress"):
                    with gr.Row():
                        with gr.Column():
                            input_file = gr.File(label="Input File")
                            chunk_size = gr.Slider(
                                minimum=512, 
                                maximum=65536, 
                                value=4096, 
                                step=512, 
                                label="Chunk Size (bytes)"
                            )
                            compress_btn = gr.Button("Compress File", variant="primary")
                        
                        with gr.Column():
                            output_file = gr.File(label="Compressed File")
                            compression_stats = gr.JSON(label="Compression Statistics")
                            compress_log = gr.Textbox(label="Compression Log", lines=10)
                
                with gr.Tab("Decompress"):
                    with gr.Row():
                        with gr.Column():
                            compressed_file = gr.File(label="Compressed File")
                            decompress_btn = gr.Button("Decompress File", variant="primary")
                        
                        with gr.Column():
                            decompressed_file = gr.File(label="Decompressed File")
                            decompression_stats = gr.JSON(label="Decompression Statistics")
                            decompress_log = gr.Textbox(label="Decompression Log", lines=10)
                
                # Define a basic compress function
                def compress_file_basic(file, chunk_size):
                    if file is None:
                        return None, {"error": "No file provided"}, "Error: No file provided"
                    
                    try:
                        file_path = file.name
                        filename = os.path.basename(file_path)
                        output_path = os.path.join(tempfile.gettempdir(), f"{filename}.ambc")
                        
                        log_output = []
                        log_output.append(f"Starting compression of {filename}...")
                        log_output.append(f"Chunk size: {chunk_size} bytes")
                        
                        # Create custom log capture for output
                        class LogCapture:
                            def __init__(self, log_list):
                                self.log_list = log_list
                                self.original_stdout = sys.stdout
                            def write(self, message):
                                if message.strip():
                                    self.log_list.append(message.strip())
                                    self.original_stdout.write(message)
                            def flush(self):
                                self.original_stdout.flush()
                        
                        # Redirect stdout to capture logs
                        original_stdout = sys.stdout
                        log_capture = LogCapture(log_output)
                        sys.stdout = log_capture
                        
                        try:
                            # Compress the file
                            stats = self.compressor.compress(file_path, output_path)
                        finally:
                            # Restore stdout
                            sys.stdout = original_stdout
                        
                        # Update analyzer
                        self.analyzer.add_result(filename, stats)
                        self.analyzer.save_results(self.results_file)
                        
                        # Make stats JSON-compatible
                        stats = self._ensure_serializable(stats)
                        
                        return output_path, stats, "\n".join(log_output)
                    except Exception as e:
                        error_msg = f"Error during compression: {str(e)}"
                        print(error_msg)
                        traceback.print_exc()
                        return None, {"error": str(e)}, error_msg
                
                # Define a basic decompress function
                def decompress_file_basic(file):
                    if file is None:
                        return None, {"error": "No file provided"}, "Error: No file provided"
                    
                    try:
                        file_path = file.name
                        filename = os.path.basename(file_path)
                        base_name = os.path.splitext(filename)[0]
                        output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_decompressed")
                        
                        log_output = []
                        log_output.append(f"Starting decompression of {filename}...")
                        
                        # Create custom log capture
                        class LogCapture:
                            def __init__(self, log_list):
                                self.log_list = log_list
                                self.original_stdout = sys.stdout
                            def write(self, message):
                                if message.strip():
                                    self.log_list.append(message.strip())
                                    self.original_stdout.write(message)
                            def flush(self):
                                self.original_stdout.flush()
                        
                        # Redirect stdout to capture logs
                        original_stdout = sys.stdout
                        log_capture = LogCapture(log_output)
                        sys.stdout = log_capture
                        
                        try:
                            # Decompress the file
                            stats = self.compressor.decompress(file_path, output_path)
                        finally:
                            # Reset stdout
                            sys.stdout = original_stdout
                        
                        # Make stats JSON-compatible
                        stats = self._ensure_serializable(stats)
                        
                        return output_path, stats, "\n".join(log_output)
                    except Exception as e:
                        error_msg = f"Error during decompression: {str(e)}"
                        print(error_msg)
                        traceback.print_exc()
                        return None, {"error": str(e)}, error_msg
                
                # Connect the UI elements to functions
                compress_btn.click(
                    compress_file_basic, 
                    inputs=[input_file, chunk_size], 
                    outputs=[output_file, compression_stats, compress_log]
                )
                
                decompress_btn.click(
                    decompress_file_basic, 
                    inputs=[compressed_file], 
                    outputs=[decompressed_file, decompression_stats, decompress_log]
                )
            
            # Launch the basic interface
            demo.launch()
        except Exception as e:
            print(f"Error running basic interface: {e}")
            print("Please check your Gradio installation.")
            sys.exit(1)
    
    def _connect_callbacks(self, demo, inputs_compress, outputs_compress, 
                         inputs_decompress, outputs_decompress,
                         inputs_analysis, outputs_analysis):
        """
        Connect all callback functions for the UI components
        """
        # Import needed functions directly from this scope
        from gradio_components.tabs.compress import compress_file_enhanced
        from gradio_components.tabs.decompress import decompress_file_enhanced
        from gradio_components.tabs.analysis import generate_enhanced_analysis
        from gradio_components.utils import toggle_detailed_stats, clear_compression_history
        
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