import gradio as gr  # Direct import of gradio
import os
import sys
import tempfile
import time
import math
import re  # For regex pattern matching
import traceback  # Fixed import

# Import the method chart creation utility from your utils package
from ..utils import create_method_chart

def create_compress_tab():
    """
    Create the Compress tab for file compression.
    
    Returns:
        tuple: (tab, inputs, outputs)
    """
    inputs = {}
    outputs = {}
    
    with gr.Tab("Compress") as compress_tab:
        with gr.Row():
            with gr.Column():
                gr.Markdown("""
                ### Compress Files
                
                Upload a file to create a compressed `.ambc` file.
                
                The algorithm uses a **dynamic chunking** strategy: for each segment, it
                automatically tests various candidate chunk sizes (using a 2^(10+k) formula)
                and multiple compression methods, then chooses the best compression ratio.
                
                **Advanced Settings:**  
                - Optionally specify an initial chunk size (for logging purposes only).
                - Enable multithreading for faster compression.
                """)
                inputs["input_file"] = gr.File(label="Input File")
                
                with gr.Accordion("Advanced Settings", open=True):
                    # Create a dropdown for the initial chunk size
                    k_values = list(range(0, 7))  # k from 0 to 6
                    chunk_size_options = []
                    chunk_size_labels = []
                    for k in k_values:
                        size = 2 ** (10 + k)
                        label = f"{size} bytes (2^{10+k})"
                        chunk_size_options.append(size)
                        chunk_size_labels.append(label)
                    
                    gr.Markdown("""
                    #### Initial Chunk Size (Informational)
                    
                    This value is only used for logging purposes. The dynamic compressor 
                    automatically selects optimal chunk sizes.
                    """)
                    
                    inputs["chunk_size"] = gr.Dropdown(
                        choices=chunk_size_labels,
                        value=chunk_size_labels[2],  # Default to 4096 bytes (k=2)
                        label="Initial Chunk Size",
                        info="This value is only for informational/logging purposes."
                    )
                    
                    inputs["use_multithreading"] = gr.Checkbox(
                        label="Enable Multithreading", 
                        value=False,
                        info="Uses multiple CPU cores for faster compression."
                    )
                
                inputs["compress_btn"] = gr.Button("Compress File", variant="primary")
            
            with gr.Column():
                outputs["output_file"] = gr.File(label="Compressed File")
                with gr.Accordion("Compression Results", open=True):
                    outputs["result_summary"] = gr.Textbox(label="Summary", lines=3, interactive=False)
                    outputs["compression_stats"] = gr.JSON(label="Detailed Statistics", visible=False)
                    outputs["stats_toggle"] = gr.Checkbox(label="Show Detailed Statistics", value=False)
                    outputs["compress_log"] = gr.Textbox(label="Process Log", lines=10, interactive=False)
                with gr.Accordion("Method Usage Visualization", open=True):
                    outputs["method_chart"] = gr.Plot(label="Compression Method Distribution")
    
    return compress_tab, inputs, outputs

def compress_file_enhanced(interface, file, chunk_size_label, use_mt):
    """
    Enhanced compression function with method visualization.
    
    Args:
        interface: An instance of EnhancedGradioInterface.
        file: The file to compress.
        chunk_size_label: Chunk size label from the dropdown (informational).
        use_mt: Boolean indicating whether to enable multithreading.
    
    Returns:
        tuple: (output_file_path, summary string, detailed stats JSON,
                success flag, method chart plot, process log text)
    """
    if file is None:
        return None, "No compression performed", {"error": "No file provided"}, False, None, "Error: No file provided"
    
    try:
        file_path = file.name
        filename = os.path.basename(file_path)
        # Parse initial chunk size (for logging only)
        try:
            if isinstance(chunk_size_label, str):
                chunk_size_str = chunk_size_label.split(" ")[0]
                init_chunk_size = int(chunk_size_str)
                k_match = re.search(r'\(2\^(\d+)\)', chunk_size_label)
                init_k = int(k_match.group(1)) - 10 if k_match else None
            else:
                init_chunk_size = int(chunk_size_label)
                init_k = None
        except Exception as e:
            print(f"Error parsing chunk size: {e}, defaulting to 4096")
            init_chunk_size = 4096
            init_k = 2
        
        output_path = os.path.join(tempfile.gettempdir(), f"{filename}.ambc")
        
        log_output = []
        log_output.append(f"Starting compression of {filename}...")
        log_output.append(f"Initial chunk size (informational): {init_chunk_size} bytes" +
                          (f" (k={init_k}, 2^{10+init_k})" if init_k is not None else ""))
        if use_mt:
            log_output.append("Multithreading enabled")
        
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
        log_capture = LogCapture(log_output)
        sys.stdout = log_capture
        
        try:
            # Create AdaptiveCompressor instance without passing any chunk-size overrides;
            # it will choose dynamically.
            compressor = interface.compressor.__class__()
            if use_mt:
                compressor.enable_multithreading()
            stats = compressor.compress(file_path, output_path)
        finally:
            sys.stdout = original_stdout
        
        stats = interface._ensure_serializable(stats)
        stats['extension'] = os.path.splitext(filename)[1].lower() or 'unknown'
        stats['filename_no_ext'] = os.path.splitext(filename)[0]
        stats['size_label'] = interface.format_file_size(stats['original_size'])
        
        interface.analyzer.add_result(filename, stats)
        interface.analyzer.save_results(interface.results_file)
        
        original_size_str = interface.format_file_size(stats['original_size'])
        compressed_size_str = interface.format_file_size(stats['compressed_size'])
        summary = f"Original: {original_size_str} → Compressed: {compressed_size_str}\n"
        summary += f"Compression ratio: {stats['ratio']:.2f} ({stats['percent_reduction']:.1f}% reduction)\n"
        summary += f"Speed: {stats['throughput_mb_per_sec']:.2f} MB/s"
        
        log_output.append("\nCompression Results:")
        log_output.append(f"Original size: {stats['original_size']} bytes ({original_size_str})")
        log_output.append(f"Compressed size: {stats['compressed_size']} bytes ({compressed_size_str})")
        log_output.append(f"Compression ratio: {stats['ratio']:.4f}")
        log_output.append(f"Space saving: {stats['percent_reduction']:.2f}%")
        
        total_overhead = stats.get('overhead_bytes', 0)
        header_size = stats['chunk_stats'].get('header_size', 0)
        marker_overhead = total_overhead - header_size
        log_output.append(f"Total overhead: {total_overhead} bytes "
                          f"({total_overhead/stats['compressed_size']*100:.2f}% of compressed size)")
        log_output.append(f"  Header: {header_size} bytes")
        log_output.append(f"  Package markers: {marker_overhead} bytes")
        
        if stats['chunk_stats'].get('compressed_chunks', 0) > 0:
            log_output.append(f"\nCompression applied to {stats['chunk_stats']['compressed_chunks']} "
                              f"of {stats['chunk_stats']['total_chunks']} chunks")
            if 'compression_efficiency' in stats:
                log_output.append(f"Compression efficiency: {stats['compression_efficiency']:.4f}")
        else:
            log_output.append("\nNo compression was applied; file stored as raw data.")
        
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
        for mid, count in stats['chunk_stats']['method_usage'].items():
            if count > 0:
                log_output.append(f"{method_names.get(mid, f'Method {mid}')}: {count} chunks")
        
        method_chart = create_method_chart(stats)
        return output_path, summary, stats, True, method_chart, "\n".join(log_output)
    
    except Exception as e:
        error_msg = f"Error during compression: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return None, "Compression failed", {"error": str(e)}, False, None, error_msg
