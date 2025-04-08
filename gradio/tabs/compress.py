import gradio as gr
import os
import sys
import tempfile
import time

from ..utils import create_method_chart

def create_compress_tab():
    """
    Create the Compress tab for file compression
    
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
                
                Upload a file and customize compression settings to create a compressed `.ambc` file.
                
                The algorithm will analyze your data patterns and apply the most efficient 
                compression techniques to different sections of your file.
                """)
                inputs["input_file"] = gr.File(label="Input File")
                
                with gr.Accordion("Advanced Settings", open=False):
                    inputs["chunk_size"] = gr.Slider(
                        minimum=512, 
                        maximum=65536, 
                        value=4096, 
                        step=512, 
                        label="Chunk Size (bytes)",
                        info="Larger chunks may improve compression ratio but increase memory usage"
                    )
                    inputs["use_multithreading"] = gr.Checkbox(
                        label="Enable Multithreading", 
                        value=False,
                        info="Uses multiple CPU cores for faster compression"
                    )
                    
                inputs["compress_btn"] = gr.Button("Compress File", variant="primary")
            
            with gr.Column():
                outputs["output_file"] = gr.File(label="Compressed File")
                
                with gr.Accordion("Compression Results", open=True):
                    outputs["result_summary"] = gr.Textbox(
                        label="Summary", 
                        lines=3, 
                        interactive=False
                    )
                    outputs["compression_stats"] = gr.JSON(
                        label="Detailed Statistics",
                        visible=False
                    )
                    outputs["stats_toggle"] = gr.Checkbox(
                        label="Show Detailed Statistics", 
                        value=False
                    )
                    outputs["compress_log"] = gr.Textbox(
                        label="Process Log", 
                        lines=10, 
                        interactive=False
                    )
                
                with gr.Accordion("Method Usage Visualization", open=True):
                    outputs["method_chart"] = gr.Plot(label="Compression Method Distribution")
    
    return compress_tab, inputs, outputs

def compress_file_enhanced(interface, file, chunk_size, use_mt):
    """
    Enhanced compression function with method visualization
    
    Args:
        interface: The EnhancedGradioInterface instance
        file: The file to compress
        chunk_size: Chunk size in bytes
        use_mt: Whether to use multithreading
        
    Returns:
        tuple: Output components for Gradio
    """
    if file is None:
        return None, "No compression performed", {"error": "No file provided"}, False, None, "Error: No file provided"
    
    try:
        file_path = file.name
        filename = os.path.basename(file_path)
        
        # Create output file path
        output_path = os.path.join(tempfile.gettempdir(), f"{filename}.ambc")
        
        log_output = []
        log_output.append(f"Starting compression of {filename}...")
        log_output.append(f"Chunk size: {chunk_size} bytes")
        if use_mt:
            log_output.append("Multithreading enabled")
        
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
            # Create compressor with specified chunk size
            compressor = interface.compressor.__class__(chunk_size=chunk_size)
            if use_mt:
                compressor.enable_multithreading()
            
            # Compress the file
            stats = compressor.compress(file_path, output_path)
        finally:
            # Reset stdout
            sys.stdout = original_stdout
        
        # Post-process statistics to make sure all keys are strings
        stats = interface._ensure_serializable(stats)
        
        # Add file metadata for improved reporting
        stats['extension'] = os.path.splitext(filename)[1].lower() or 'unknown'
        stats['filename_no_ext'] = os.path.splitext(filename)[0]
        
        # Format sizes for display
        stats['size_label'] = interface.format_file_size(stats['original_size'])
        
        # Add to analyzer
        interface.analyzer.add_result(filename, stats)
        interface.analyzer.save_results(interface.results_file)
        
        # Create summary text
        original_size = interface.format_file_size(stats['original_size'])
        compressed_size = interface.format_file_size(stats['compressed_size'])
        ratio = stats['ratio']
        percent_reduction = stats['percent_reduction']
        throughput = stats['throughput_mb_per_sec']
        
        summary = f"Original: {original_size} → Compressed: {compressed_size}\n"
        summary += f"Compression ratio: {ratio:.2f} ({percent_reduction:.1f}% reduction)\n"
        summary += f"Processing speed: {throughput:.2f} MB/s"
        
        # Add summary to log
        log_output.append("\nCompression Results:")
        log_output.append(f"Original size: {stats['original_size']} bytes ({original_size})")
        log_output.append(f"Compressed size: {stats['compressed_size']} bytes ({compressed_size})")
        log_output.append(f"Compression ratio: {ratio:.4f}")
        log_output.append(f"Space saving: {percent_reduction:.2f}%")
        
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
        
        # Create method chart
        method_chart = create_method_chart(stats)
        
        return output_path, summary, stats, True, method_chart, "\n".join(log_output)
    
    except Exception as e:
        error_msg = f"Error during compression: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, "Compression failed", {"error": str(e)}, False, None, error_msg
