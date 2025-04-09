import os
import sys
import time
import tempfile
import json
import traceback
import hashlib
import numpy as np
from PIL import Image
import io

from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

# Check if gradio is available
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError as e:
    print(f"Gradio not available: {e}")
    GRADIO_AVAILABLE = False

# For enhanced UI access
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
        # Check if gradio is available
        if not GRADIO_AVAILABLE:
            print("Error: Gradio is not installed.")
            print("Please install it with: pip install gradio>=3.0.0")
            sys.exit(1)
            
        # For the enhanced interface, we'll import the relevant modules from the gradio_components package
        try:
            # Add the current directory to the path to ensure imports work
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            # First attempt to check if the gradio_components package is importable at all
            try:
                import gradio_components
                # Try to run the interface through the components package
                gradio_components.run_interface()
            except (ImportError, AttributeError) as e:
                print(f"Warning: Enhanced UI not fully available: {e}")
                print("Falling back to basic interface.")
                self._run_basic_interface()
        except Exception as e:
            print(f"Error importing enhanced interface: {e}")
            print("Traceback:")
            traceback.print_exc()
            print("Falling back to basic interface...")
            self._run_basic_interface()
    
    def _run_basic_interface(self):
        """Fallback to basic Gradio interface if enhanced UI fails"""
        # Create a basic Gradio interface with minimal dependencies
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


# Legacy interface for backwards compatibility
class GradioInterface(EnhancedGradioInterface):
    """Legacy interface class for backward compatibility"""
    pass


# Direct execution
if __name__ == "__main__":
    interface = EnhancedGradioInterface()
    interface.run()
