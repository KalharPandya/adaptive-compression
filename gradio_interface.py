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