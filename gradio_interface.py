import os
import sys
import time
import tempfile
import json
import traceback
import hashlib
import numpy as np

# If you need to do any image or other transformations:
# from PIL import Image
# import io

# Import the newly updated, dynamic chunk-based AdaptiveCompressor
# This is the version that tries multiple chunk sizes and picks
# whichever method+size yields the best ratio for that segment.
from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

# Check if gradio is available
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError as e:
    print(f"Gradio not available: {e}")
    GRADIO_AVAILABLE = False


class EnhancedGradioInterface:
    """
    Enhanced Gradio interface for the dynamic-chunk adaptive compression algorithm.
    This interface no longer requires a user-specified chunk size, as the
    new AdaptiveCompressor does dynamic chunk-size selection automatically.
    """
    
    def __init__(self, title="Adaptive Marker-Based Compression"):
        """
        Initialize the Gradio interface
        
        Args:
            title (str): Title for the interface
        """
        self.title = title
        
        # Our updated dynamic-chunk compressor
        self.compressor = AdaptiveCompressor()

        # We also keep an analyzer for storing historical compression stats
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
            # fallback: convert to string
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
            
        # We attempt to launch any advanced UI from a hypothetical "gradio_components" package.
        # If that fails, we fallback to a simpler Blocks interface below.
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            try:
                import gradio_components
                # If it has a run_interface function:
                gradio_components.run_interface()
            except (ImportError, AttributeError) as e:
                print(f"Warning: Enhanced UI not fully available: {e}")
                print("Falling back to the basic interface.")
                self._run_basic_interface()
        except Exception as e:
            print(f"Error importing enhanced interface: {e}")
            traceback.print_exc()
            print("Falling back to basic interface...")
            self._run_basic_interface()
    
    def _run_basic_interface(self):
        """
        A simplified Gradio interface that does not rely on advanced UI modules.
        Note that we do not ask for chunk_size anymore: 
        the new AdaptiveCompressor picks chunk sizes itself.
        """
        with gr.Blocks(title=self.title) as demo:
            gr.Markdown(f"# {self.title}")
            gr.Markdown("""
            This demonstrates a **dynamic-chunk** adaptive compression algorithm that 
            automatically tries different chunk sizes and multiple compression methods 
            to find the best approach for each segment of your file. 
            
            ### How It Works
            - The file is divided at runtime: for each potential segment, 
              the algorithm tests various chunk sizes (e.g., 1 KB, 2 KB, … up to 128 KB) 
              and tries multiple compression methods on each chunk. 
            - Whichever combination yields the best compression ratio for that chunk 
              is chosen, then the chunk is finalized and appended to the compressed output. 
            - This results in a `.ambc` file that can be decompressed seamlessly. 
            
            **Note**: This is a basic fallback UI for demonstration. 
            If an advanced UI is available, it will be used instead.
            """)

            with gr.Tab("Compress"):
                with gr.Row():
                    with gr.Column():
                        input_file = gr.File(label="Input File to Compress")
                        compress_btn = gr.Button("Compress File", variant="primary")
                    with gr.Column():
                        output_file = gr.File(label="Resulting .ambc File")
                        compression_stats = gr.JSON(label="Compression Statistics")
                        compress_log = gr.Textbox(label="Log Output", lines=10)
            
            with gr.Tab("Decompress"):
                with gr.Row():
                    with gr.Column():
                        compressed_file = gr.File(label="Compressed .ambc File")
                        decompress_btn = gr.Button("Decompress File", variant="primary")
                    with gr.Column():
                        decompressed_file = gr.File(label="Decompressed File")
                        decompression_stats = gr.JSON(label="Decompression Statistics")
                        decompress_log = gr.Textbox(label="Log Output", lines=10)
            
            def compress_file_basic(file):
                """
                Basic compression function with dynamic chunk approach (no user chunk_size).
                """
                if file is None:
                    return None, {"error": "No file provided"}, "Error: No file provided"
                
                log_output = []
                try:
                    file_path = file.name
                    filename = os.path.basename(file_path)
                    output_path = os.path.join(tempfile.gettempdir(), f"{filename}.ambc")
                    
                    log_output.append(f"Starting compression of {filename} using dynamic chunk approach...")
                    
                    # Capture logs
                    class LogCapture:
                        def __init__(self, log_list):
                            self.log_list = log_list
                            self.orig_stdout = sys.stdout
                        def write(self, message):
                            if message.strip():
                                self.log_list.append(message.strip())
                                self.orig_stdout.write(message)
                        def flush(self):
                            self.orig_stdout.flush()
                    
                    original_stdout = sys.stdout
                    logger = LogCapture(log_output)
                    sys.stdout = logger
                    try:
                        stats = self.compressor.compress(file_path, output_path)
                    finally:
                        sys.stdout = original_stdout
                    
                    # Save results
                    self.analyzer.add_result(filename, stats)
                    self.analyzer.save_results(self.results_file)
                    stats = self._ensure_serializable(stats)
                    
                    return output_path, stats, "\n".join(log_output)
                except Exception as e:
                    error_msg = f"Error during compression: {e}"
                    traceback.print_exc()
                    return None, {"error": str(e)}, "\n".join(log_output + [error_msg])
            
            def decompress_file_basic(file):
                """
                Basic decompression for a .ambc file
                """
                if file is None:
                    return None, {"error": "No file provided"}, "Error: No file provided"
                
                log_output = []
                try:
                    file_path = file.name
                    filename = os.path.basename(file_path)
                    base_name = os.path.splitext(filename)[0]
                    output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_decompressed")
                    
                    log_output.append(f"Starting decompression of {filename}...")
                    
                    class LogCapture:
                        def __init__(self, log_list):
                            self.log_list = log_list
                            self.orig_stdout = sys.stdout
                        def write(self, message):
                            if message.strip():
                                self.log_list.append(message.strip())
                                self.orig_stdout.write(message)
                        def flush(self):
                            self.orig_stdout.flush()
                    
                    orig_stdout = sys.stdout
                    logger = LogCapture(log_output)
                    sys.stdout = logger
                    try:
                        stats = self.compressor.decompress(file_path, output_path)
                    finally:
                        sys.stdout = orig_stdout
                    
                    stats = self._ensure_serializable(stats)
                    
                    return output_path, stats, "\n".join(log_output)
                except Exception as e:
                    error_msg = f"Error during decompression: {e}"
                    traceback.print_exc()
                    return None, {"error": str(e)}, "\n".join(log_output + [error_msg])
            
            # Link UI
            compress_btn.click(
                compress_file_basic,
                inputs=[input_file],
                outputs=[output_file, compression_stats, compress_log]
            )
            decompress_btn.click(
                decompress_file_basic,
                inputs=[compressed_file],
                outputs=[decompressed_file, decompression_stats, decompress_log]
            )
        
        demo.launch()

    def format_file_size(self, size_bytes):
        """
        Format file size in a user-friendly manner
        """
        if size_bytes==0:
            return "0 B"
        units= ["B","KB","MB","GB","TB"]
        i=0
        while size_bytes>=1024 and i< len(units)-1:
            size_bytes/=1024.0
            i+=1
        return f"{size_bytes:.1f} {units[i]}"


# Legacy fallback
class GradioInterface(EnhancedGradioInterface):
    """Legacy interface class for backward compatibility"""
    pass


if __name__=="__main__":
    interface = EnhancedGradioInterface()
    interface.run()
