import os
import sys
import time
import tempfile
import json
import traceback
import hashlib
import gradio as gr
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io

from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

# Try to import the compatibility layer
try:
    from compression_fix import get_compatible_methods
    COMPAT_AVAILABLE = True
except ImportError:
    COMPAT_AVAILABLE = False

class GradioInterface:
    """
    Gradio interface for the adaptive compression algorithm
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

    def _get_available_methods(self):
        """
        Get information about available compression methods
        
        Returns:
            str: HTML-formatted information about available methods
        """
        methods_info = []
        try:
            compressor = AdaptiveCompressor()
            method_count = len(compressor.compression_methods)
            methods_info.append(f"<p>Total compression methods available: {method_count}</p>")
            
            if hasattr(compressor, 'FORMAT_VERSION'):
                methods_info.append(f"<p>Compressor format version: {compressor.FORMAT_VERSION}</p>")
            
            # Group by type
            basic = []
            advanced = []
            compatible = []
            
            for method in compressor.compression_methods:
                method_name = compressor.method_names.get(str(method.type_id), f"Method {method.type_id}")
                if hasattr(method, '__class__') and 'Compatible' in method.__class__.__name__:
                    compatible.append(method_name)
                elif method.type_id in [1, 2, 3, 4]:
                    basic.append(method_name)
                elif method.type_id != 255:  # Skip "No Compression"
                    advanced.append(method_name)
            
            if basic:
                methods_info.append("<p><b>Basic methods:</b> " + ", ".join(basic) + "</p>")
            if advanced:
                methods_info.append("<p><b>Advanced methods:</b> " + ", ".join(advanced) + "</p>")
            if compatible:
                methods_info.append("<p><b>Compatible methods:</b> " + ", ".join(compatible) + "</p>")
            
            if COMPAT_AVAILABLE:
                methods_info.append("<p><b>Compatibility layer is available</b> for improved decompression reliability.</p>")
        except Exception as e:
            methods_info.append(f"<p>Error getting method information: {e}</p>")
        
        return "".join(methods_info)
    
    def run(self):
        """
        Start the Gradio interface
        """
        with gr.Blocks(title=self.title) as demo:
            gr.Markdown(f"# {self.title}")
            gr.Markdown("""
            This app demonstrates an adaptive compression algorithm that uses different 
            compression techniques for different parts of a file based on which technique 
            would be most efficient for that particular data pattern.
            """)
            
            with gr.Tab("Compress"):
                with gr.Row():
                    with gr.Column():
                        input_file = gr.File(label="Input File")
                        
                        with gr.Row():
                            chunk_size = gr.Slider(
                                minimum=512, 
                                maximum=65536, 
                                value=4096, 
                                step=512, 
                                label="Chunk Size (bytes)"
                            )
                            
                            use_compat = gr.Checkbox(
                                label="Use Compatible Methods",
                                value=True,
                                interactive=COMPAT_AVAILABLE,
                                info="Use more reliable compression methods for better decompression"
                            )
                            
                        with gr.Row():
                            marker_length = gr.Slider(
                                minimum=3,
                                maximum=32,
                                value=16,
                                step=1,
                                label="Max Marker Length (bits)",
                                info="Maximum size of the marker to search for"
                            )
                            
                            smart_chunking = gr.Checkbox(
                                label="Smart Chunk Sizing",
                                value=True,
                                info="Dynamically adjust chunk sizes based on data patterns"
                            )
                        
                        compress_btn = gr.Button("Compress File", variant="primary")
                        
                        # Method information
                        gr.HTML(self._get_available_methods())
                        
                    with gr.Column():
                        output_file = gr.File(label="Compressed File")
                        compression_stats = gr.JSON(label="Compression Statistics")
                        compress_log = gr.Textbox(label="Compression Log", lines=15)
            
            with gr.Tab("Decompress"):
                with gr.Row():
                    with gr.Column():
                        compressed_file = gr.File(label="Compressed File")
                        decompress_btn = gr.Button("Decompress File", variant="primary")
                    
                    with gr.Column():
                        decompressed_file = gr.File(label="Decompressed File")
                        decompression_stats = gr.JSON(label="Decompression Statistics")
                        decompress_log = gr.Textbox(label="Decompression Log", lines=15)
            
            with gr.Tab("Analysis"):
                with gr.Row():
                    analyze_btn = gr.Button("Generate Analysis", variant="primary")
                
                with gr.Row():
                    summary_stats = gr.JSON(label="Summary Statistics")
                
                with gr.Row():
                    with gr.Column():
                        ratio_plot = gr.Plot(label="Compression Ratio by File Type and Size")
                    
                    with gr.Column():
                        method_plot = gr.Plot(label="Compression Method Usage")
                
                with gr.Row():
                    with gr.Column():
                        size_plot = gr.Plot(label="Size Comparison by File Type")
                    
                    with gr.Column():
                        throughput_plot = gr.Plot(label="Compression Throughput by File Type")
                        
                with gr.Row():
                    gr.Markdown("""
                    ### Analysis Details
                    - **Compression Ratio**: Lower is better. Shows how much files were compressed relative to original size.
                    - **Method Usage**: Shows which compression methods were most effective for different file types.
                    - **Size Comparison**: Direct comparison of original vs. compressed file sizes.
                    - **Throughput**: Shows compression speed in MB/s for different file types.
                    
                    Files are grouped by extension and sorted by size for easier comparison.
                    """)
            
            # Define compression function
            def compress_file(file, chunk_size, use_compat, marker_length, smart_chunking):
                if file is None:
                    return None, {"error": "No file provided"}, "Error: No file provided"
                
                try:
                    file_path = file.name
                    filename = os.path.basename(file_path)
                    
                    # Create output file path
                    output_path = os.path.join(tempfile.gettempdir(), f"{filename}.ambc")
                    
                    log_output = []
                    log_output.append(f"Starting compression of {filename}...")
                    log_output.append(f"Chunk size: {chunk_size} bytes")
                    log_output.append(f"Using compatible methods: {use_compat}")
                    log_output.append(f"Maximum marker length: {marker_length} bits")
                    log_output.append(f"Smart chunk sizing: {smart_chunking}")
                    
                    # Create custom log capture
                    class LogCapture:
                        def __init__(self, log_list):
                            self.log_list = log_list
                            self.original_stdout = sys.stdout
                            
                        def write(self, message):
                            if message.strip():
                                self.log_list.append(message.strip())
                                # Directly write to original stdout to avoid recursion
                                self.original_stdout.write(message)
                                
                        def flush(self):
                            self.original_stdout.flush()
                    
                    # Redirect stdout temporarily to capture logs
                    original_stdout = sys.stdout
                    log_capture = LogCapture(log_output)
                    sys.stdout = log_capture
                    
                    try:
                        # Create compressor with specified parameters
                        compressor = AdaptiveCompressor(
                            initial_chunk_size=chunk_size,
                            chunk_size=None if smart_chunking else chunk_size,
                            marker_max_length=marker_length
                        )
                        
                        # Set compatibility mode if requested
                        if hasattr(compressor, 'use_compat_methods') and use_compat:
                            compressor.use_compat_methods = use_compat
                        
                        # Compress the file
                        stats = compressor.compress(file_path, output_path)
                    finally:
                        # Reset stdout
                        sys.stdout = original_stdout
                    
                    # Post-process statistics to make sure all keys are strings
                    stats = self._ensure_serializable(stats)
                    
                    # Add file metadata for improved reporting
                    stats['extension'] = os.path.splitext(filename)[1].lower() or 'unknown'
                    stats['filename_no_ext'] = os.path.splitext(filename)[0]
                    stats['filename'] = filename
                    
                    # Format sizes for display
                    stats['size_label'] = self._format_file_size(stats['original_size'])
                    
                    # Add timestamp
                    stats['timestamp'] = time.time()
                    
                    # Add to analyzer
                    self.analyzer.add_result(filename, stats)
                    self.analyzer.save_results(self.results_file)
                    
                    # Add summary to log
                    log_output.append("\nCompression Results:")
                    log_output.append(f"Original size: {stats['original_size']} bytes ({self._format_file_size(stats['original_size'])})")
                    log_output.append(f"Compressed size: {stats['compressed_size']} bytes ({self._format_file_size(stats['compressed_size'])})")
                    log_output.append(f"Compression ratio: {stats['ratio']:.4f}")
                    log_output.append(f"Space saving: {stats['percent_reduction']:.2f}%")
                    
                    # Show detailed overhead breakdown
                    total_overhead = stats.get('overhead_bytes', 0)
                    header_size = stats['chunk_stats'].get('header_size', 0)
                    marker_overhead = total_overhead - header_size
                    
                    log_output.append(f"Total overhead: {total_overhead} bytes ({total_overhead/stats['compressed_size']*100:.2f}% of compressed size)")
                    log_output.append(f"  Header: {header_size} bytes")
                    log_output.append(f"  Markers/packages: {marker_overhead} bytes")
                    
                    if 'compressed_chunks' in stats['chunk_stats'] and stats['chunk_stats']['compressed_chunks'] > 0:
                        log_output.append(f"\nCompression applied to {stats['chunk_stats']['compressed_chunks']} of {stats['chunk_stats']['total_chunks']} chunks")
                        
                        # If some data was compressed, show compression efficiency
                        if 'compression_efficiency' in stats:
                            log_output.append(f"Compression efficiency: {stats['compression_efficiency']:.4f}")
                    else:
                        log_output.append("\nNo compression was applied (all data kept as raw)")
                    
                    # Add method usage to log
                    method_names = {
                        "1": "RLE",
                        "2": "Dictionary",
                        "3": "Huffman",
                        "4": "Delta",
                        "5": "DEFLATE",
                        "6": "BZIP2",
                        "7": "LZMA",
                        "8": "ZStandard",
                        "9": "LZ4",
                        "10": "Brotli",
                        "11": "LZHAM",
                        "255": "No Compression"
                    }
                    
                    log_output.append("\nCompression Method Usage:")
                    for method_id, count in stats['chunk_stats']['method_usage'].items():
                        if count > 0:
                            method_name = method_names.get(method_id, f"Method {method_id}")
                            log_output.append(f"{method_name}: {count} chunks")
                    
                    return output_path, stats, "\n".join(log_output)
                
                except Exception as e:
                    error_msg = f"Error during compression: {str(e)}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    return None, {"error": str(e)}, error_msg
            
            # Define decompression function
            def decompress_file(file):
                if file is None:
                    return None, {"error": "No file provided"}, "Error: No file provided"
                
                try:
                    file_path = file.name
                    filename = os.path.basename(file_path)
                    base_name = os.path.splitext(filename)[0]
                    
                    # Create output file path
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
                                # Directly write to original stdout to avoid recursion
                                self.original_stdout.write(message)
                                
                        def flush(self):
                            self.original_stdout.flush()
                    
                    # Redirect stdout temporarily to capture logs
                    original_stdout = sys.stdout
                    log_capture = LogCapture(log_output)
                    sys.stdout = log_capture
                    
                    try:
                        # Get format information if possible
                        try:
                            with open(file_path, 'rb') as f:
                                header = f.read(9)  # Read enough for magic number and version
                                if len(header) >= 5 and header[:4] == b'AMBC':
                                    format_version = header[4]
                                    log_output.append(f"File format version: {format_version}")
                        except Exception as e:
                            log_output.append(f"Could not read format version: {e}")
                        
                        # Create compressor
                        compressor = AdaptiveCompressor()
                        
                        # Decompress the file
                        stats = compressor.decompress(file_path, output_path)
                    finally:
                        # Reset stdout
                        sys.stdout = original_stdout
                    
                    # Post-process statistics to make sure all keys are strings
                    stats = self._ensure_serializable(stats)
                    
                    # Calculate MD5 hash of decompressed file
                    with open(output_path, 'rb') as f:
                        decompressed_md5 = hashlib.md5(f.read()).hexdigest()
                        stats['md5_hash'] = decompressed_md5
                    
                    # Add summary to log
                    log_output.append("\nDecompression Results:")
                    log_output.append(f"Compressed size: {stats['compressed_size']} bytes ({self._format_file_size(stats['compressed_size'])})")
                    log_output.append(f"Decompressed size: {stats['decompressed_size']} bytes ({self._format_file_size(stats['decompressed_size'])})")
                    log_output.append(f"Decompression time: {stats['elapsed_time']:.4f} seconds")
                    log_output.append(f"Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
                    log_output.append(f"MD5 hash: {decompressed_md5}")
                    
                    return output_path, stats, "\n".join(log_output)
                
                except Exception as e:
                    error_msg = f"Error during decompression: {str(e)}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    return None, {"error": str(e)}, error_msg
            
            # Define analysis function
            def generate_analysis():
                try:
                    # Get summary statistics
                    summary = self.analyzer.get_summary_stats()
                    
                    # Make sure all keys are strings for JSON compatibility
                    summary = self._ensure_serializable(summary)
                    
                    # Generate plots
                    ratio_fig = self.analyzer.plot_compression_ratio()
                    method_fig = self.analyzer.plot_method_usage()
                    size_fig = self.analyzer.plot_size_comparison()
                    throughput_fig = self.analyzer.plot_throughput()
                    
                    return (
                        summary,
                        ratio_fig if ratio_fig else None,
                        method_fig if method_fig else None,
                        size_fig if size_fig else None,
                        throughput_fig if throughput_fig else None
                    )
                
                except Exception as e:
                    print(f"Error during analysis: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return (
                        {"error": str(e)},
                        None, None, None, None
                    )
            
            # Connect buttons to functions
            compress_btn.click(
                compress_file, 
                inputs=[input_file, chunk_size, use_compat, marker_length, smart_chunking], 
                outputs=[output_file, compression_stats, compress_log]
            )
            
            decompress_btn.click(
                decompress_file, 
                inputs=[compressed_file], 
                outputs=[decompressed_file, decompression_stats, decompress_log]
            )
            
            analyze_btn.click(
                generate_analysis,
                inputs=[],
                outputs=[summary_stats, ratio_plot, method_plot, size_plot, throughput_plot]
            )
        
        # Launch the interface
        demo.launch()

    def _format_file_size(self, size_bytes):
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
        # For the enhanced interface, we'll import the relevant modules from the gradio package
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from gradio.main import run_interface
            run_interface()
        except ImportError as e:
            print(f"Error importing enhanced interface: {e}")
            print("Falling back to basic interface...")
            # Fall back to basic interface if enhanced interface can't be loaded
            interface = GradioInterface(self.title)
            interface.run()
            
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


if __name__ == "__main__":
    # Create and run the Gradio interface
    interface = GradioInterface()
    interface.run()