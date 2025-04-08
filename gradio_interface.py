import os
import sys
import time
import tempfile
import json
import traceback
import gradio as gr
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io

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
        with gr.Blocks(title=self.title, theme=gr.themes.Soft()) as demo:
            # Header with logo and title
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Image(value="https://via.placeholder.com/150x150?text=AC", shape=(150, 150), label="")
                with gr.Column(scale=4):
                    gr.Markdown(f"# {self.title}")
                    gr.Markdown("""
                    An intelligent compression algorithm that dynamically selects the optimal compression method 
                    for different segments of your data based on their unique patterns and characteristics.
                    """)
            
            # Main tabs
            with gr.Tabs() as tabs:
                # Home/About tab
                with gr.Tab("About") as about_tab:
                    gr.Markdown("""
                    ## About Adaptive Marker-Based Compression
                    
                    This application demonstrates a novel approach to data compression that achieves superior 
                    compression ratios by analyzing data patterns at a granular level and applying the most effective
                    compression technique to each segment.

                    ### Key Features

                    - **Adaptive Compression**: Automatically selects the best method for each data chunk
                    - **Marker-Based Approach**: Uses unique binary patterns to seamlessly transition between methods
                    - **Multiple Techniques**: Incorporates RLE, Dictionary-based, Huffman, Delta, and more
                    - **Visual Analytics**: Comprehensive visualizations of compression performance
                    - **Cross-Platform Support**: Works on Windows, macOS, and Linux

                    ### How It Works

                    1. **Marker Finding**: Identifies the shortest binary string not present in your data
                    2. **Chunk Analysis**: Divides data into optimal segments and analyzes patterns
                    3. **Method Selection**: Tests multiple compression methods on each chunk
                    4. **Adaptive Compression**: Applies the best method to each segment
                    5. **Package Creation**: Assembles compressed chunks with markers and metadata
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Image(value="https://via.placeholder.com/600x400?text=Adaptive+Compression+Diagram", label="Adaptive Compression Process")
                        with gr.Column():
                            gr.Image(value="https://via.placeholder.com/600x400?text=File+Format+Structure", label="AMBC File Format")
                
                # Compress tab
                with gr.Tab("Compress") as compress_tab:
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("""
                            ### Compress Files
                            
                            Upload a file and customize compression settings to create a compressed `.ambc` file.
                            
                            The algorithm will analyze your data patterns and apply the most efficient 
                            compression techniques to different sections of your file.
                            """)
                            input_file = gr.File(label="Input File")
                            
                            with gr.Accordion("Advanced Settings", open=False):
                                chunk_size = gr.Slider(
                                    minimum=512, 
                                    maximum=65536, 
                                    value=4096, 
                                    step=512, 
                                    label="Chunk Size (bytes)",
                                    info="Larger chunks may improve compression ratio but increase memory usage"
                                )
                                use_multithreading = gr.Checkbox(
                                    label="Enable Multithreading", 
                                    value=False,
                                    info="Uses multiple CPU cores for faster compression"
                                )
                                
                            compress_btn = gr.Button("Compress File", variant="primary")
                        
                        with gr.Column():
                            output_file = gr.File(label="Compressed File")
                            
                            with gr.Accordion("Compression Results", open=True):
                                result_summary = gr.Textbox(
                                    label="Summary", 
                                    lines=3, 
                                    interactive=False
                                )
                                compression_stats = gr.JSON(
                                    label="Detailed Statistics",
                                    visible=False
                                )
                                stats_toggle = gr.Checkbox(
                                    label="Show Detailed Statistics", 
                                    value=False
                                )
                                compress_log = gr.Textbox(
                                    label="Process Log", 
                                    lines=10, 
                                    interactive=False
                                )
                            
                            with gr.Accordion("Method Usage Visualization", open=True):
                                method_chart = gr.Plot(label="Compression Method Distribution")
                
                # Decompress tab
                with gr.Tab("Decompress") as decompress_tab:
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("""
                            ### Decompress Files
                            
                            Upload a compressed `.ambc` file to restore it to its original form.
                            
                            The decompression process will automatically detect the compression methods
                            used for each segment and apply the appropriate decompression techniques.
                            """)
                            compressed_file = gr.File(label="Compressed .ambc File")
                            decompress_btn = gr.Button("Decompress File", variant="primary")
                        
                        with gr.Column():
                            decompressed_file = gr.File(label="Decompressed File")
                            
                            with gr.Accordion("Decompression Results", open=True):
                                decomp_summary = gr.Textbox(
                                    label="Summary", 
                                    lines=3, 
                                    interactive=False
                                )
                                decompression_stats = gr.JSON(
                                    label="Detailed Statistics",
                                    visible=False
                                )
                                decomp_stats_toggle = gr.Checkbox(
                                    label="Show Detailed Statistics", 
                                    value=False
                                )
                                decompress_log = gr.Textbox(
                                    label="Process Log", 
                                    lines=10, 
                                    interactive=False
                                )
                                
                # Analysis tab
                with gr.Tab("Analysis") as analysis_tab:
                    gr.Markdown("""
                    ### Compression Performance Analysis
                    
                    This section provides comprehensive visualizations and statistics about compression
                    performance across different file types and compression methods.
                    
                    The analysis is based on your compression history, allowing you to understand
                    which methods work best for different types of data.
                    """)
                    
                    with gr.Row():
                        analyze_btn = gr.Button("Generate Analysis", variant="primary")
                        clear_history_btn = gr.Button("Clear History", variant="secondary")
                    
                    with gr.Row():
                        summary_stats = gr.JSON(label="Summary Statistics")
                    
                    with gr.Tabs() as analysis_tabs:
                        with gr.Tab("Compression Ratio"):
                            gr.Markdown("""
                            **Compression Ratio**: Shows how much each file was compressed relative to its original size.
                            Lower values indicate better compression.
                            """)
                            ratio_plot = gr.Plot(label="Compression Ratio by File Type and Size")
                            
                        with gr.Tab("Method Usage"):
                            gr.Markdown("""
                            **Method Usage**: Shows which compression methods were most effective for different file types.
                            """)
                            method_plot = gr.Plot(label="Compression Method Usage")
                            
                        with gr.Tab("Size Comparison"):
                            gr.Markdown("""
                            **Size Comparison**: Direct comparison of original vs. compressed file sizes.
                            """)
                            size_plot = gr.Plot(label="Size Comparison by File Type")
                            
                        with gr.Tab("Throughput"):
                            gr.Markdown("""
                            **Throughput**: Shows compression speed in MB/s for different file types and sizes.
                            Higher values indicate faster compression performance.
                            """)
                            throughput_plot = gr.Plot(label="Compression Throughput by File Type")
                            
                        with gr.Tab("File Type Summary"):
                            gr.Markdown("""
                            **File Type Summary**: Aggregates performance metrics by file extension.
                            This view helps you understand which file types compress best.
                            """)
                            filetype_plot = gr.Plot(label="File Type Summary")
                
                # Add File Format tab
                with gr.Tab("File Format") as format_tab:
                    gr.Markdown("""
                    ## AMBC File Format
                    
                    The `.ambc` file format is a custom format designed for adaptive marker-based compression.
                    It consists of a header followed by a series of compressed data packages.
                    
                    ### Header Structure
                    
                    ```
                    ┌───────────┬───────────┬───────────┬───────────┬───────────┬───────────┐
                    │   MAGIC   │   SIZE    │  MARKER   │ CHECKSUM  │  ORIG     │   COMP    │
                    │  (4 bytes)│  (4 bytes)│  INFO     │  (17 bytes)│  SIZE    │   SIZE    │
                    └───────────┴───────────┴───────────┴───────────┴───────────┴───────────┘
                    ```
                    
                    - **MAGIC**: 4-byte signature "AMBC"
                    - **SIZE**: Header size (4 bytes)
                    - **MARKER INFO**: Marker length and bytes
                    - **CHECKSUM**: MD5 hash of original data
                    - **ORIG SIZE**: Original file size (8 bytes)
                    - **COMP SIZE**: Compressed file size (8 bytes)
                    
                    ### Package Structure
                    
                    ```
                    ┌───────────┬───────────┬───────────┬───────────┬───────────┐
                    │  MARKER   │ METHOD ID │ COMP SIZE │ ORIG SIZE │ COMP DATA │
                    └───────────┴───────────┴───────────┴───────────┴───────────┘
                    ```
                    
                    - **MARKER**: Unique binary pattern
                    - **METHOD ID**: Compression method identifier (1 byte)
                    - **COMP SIZE**: Compressed data size (variable length)
                    - **ORIG SIZE**: Original data size (variable length)
                    - **COMP DATA**: Compressed data
                    
                    ### Compression Methods
                    
                    | ID  | Method              | Best For                    |
                    |-----|---------------------|----------------------------|
                    | 1   | RLE                 | Repeated sequences         |
                    | 2   | Dictionary          | Recurring patterns         |
                    | 3   | Huffman             | Skewed frequencies         |
                    | 4   | Delta               | Small variations           |
                    | 5   | DEFLATE             | General purpose            |
                    | 6   | BZIP2               | Text data                  |
                    | 7   | LZMA                | Large redundant data       |
                    | 8   | ZStandard           | Most data types            |
                    | 9   | LZ4                 | Speed-critical data        |
                    | 10  | Brotli              | Web content                |
                    | 11  | LZHAM               | Game assets                |
                    | 255 | No Compression      | Already compressed data    |
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Image(value="https://via.placeholder.com/500x300?text=AMBC+Header+Structure", label="AMBC Header Structure")
                        with gr.Column():
                            gr.Image(value="https://via.placeholder.com/500x300?text=AMBC+Package+Structure", label="AMBC Package Structure")
            
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


if __name__ == "__main__":
    # Create and run the enhanced Gradio interface
    interface = EnhancedGradioInterface()
    interface.run()