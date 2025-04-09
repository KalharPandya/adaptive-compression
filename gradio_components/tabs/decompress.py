import gradio_components as gr
import os
import sys
import tempfile
import time
import re

def create_decompress_tab():
    """
    Create the Decompress tab for file decompression
    
    Returns:
        tuple: (tab, inputs, outputs)
    """
    inputs = {}
    outputs = {}
    
    with gr.Tab("Decompress") as decompress_tab:
        with gr.Row():
            with gr.Column():
                gr.Markdown("""
                ### Decompress Files
                
                Upload a compressed `.ambc` file to restore it to its original form.
                
                The decompression process will automatically detect the compression methods
                used for each segment and apply the appropriate decompression techniques.
                """)
                inputs["compressed_file"] = gr.File(label="Compressed .ambc File")
                inputs["decompress_btn"] = gr.Button("Decompress File", variant="primary")
                
                with gr.Accordion("Output Options", open=False):
                    inputs["preserve_extension"] = gr.Checkbox(
                        label="Preserve Original Extension", 
                        value=True,
                        info="Keep the original file extension if available"
                    )
                    inputs["custom_filename"] = gr.Textbox(
                        label="Custom Output Filename (optional)", 
                        placeholder="Leave empty to use original name"
                    )
            
            with gr.Column():
                outputs["decompressed_file"] = gr.File(label="Decompressed File")
                
                with gr.Accordion("Decompression Results", open=True):
                    outputs["decomp_summary"] = gr.Textbox(
                        label="Summary", 
                        lines=3, 
                        interactive=False
                    )
                    outputs["decompression_stats"] = gr.JSON(
                        label="Detailed Statistics",
                        visible=False
                    )
                    outputs["decomp_stats_toggle"] = gr.Checkbox(
                        label="Show Detailed Statistics", 
                        value=False
                    )
                    outputs["decompress_log"] = gr.Textbox(
                        label="Process Log", 
                        lines=10, 
                        interactive=False
                    )
    
    return decompress_tab, inputs, outputs

def decompress_file_enhanced(interface, file, preserve_extension=True, custom_filename=""):
    """
    Enhanced decompression function with better output
    
    Args:
        interface: The EnhancedGradioInterface instance
        file: File to decompress
        preserve_extension: Whether to preserve the original file extension
        custom_filename: Optional custom filename for the output
        
    Returns:
        tuple: Output components for Gradio
    """
    if file is None:
        return None, "No decompression performed", {"error": "No file provided"}, False, "Error: No file provided"
    
    try:
        file_path = file.name
        filename = os.path.basename(file_path)
        
        # Extract base_name and handle special cases
        if filename.endswith(".ambc"):
            # Standard case: remove .ambc extension
            base_name = filename[:-5]
        else:
            # Non-standard case: use filename as is
            base_name = filename
            
        # Handle special cases where the filename already ends with _decompressed
        base_name = re.sub(r'_decompressed$', '', base_name)
            
        # Use custom filename if provided
        if custom_filename:
            output_filename = custom_filename
        else:
            output_filename = f"{base_name}_decompressed"
        
        # Create output file path
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        log_output = []
        log_output.append(f"Starting decompression of {filename}...")
        log_output.append(f"Output will be saved as: {output_filename}")
        
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
            # Decompress the file
            stats = interface.compressor.decompress(file_path, output_path)
        finally:
            # Reset stdout
            sys.stdout = original_stdout
        
        # Post-process statistics to make sure all keys are strings
        stats = interface._ensure_serializable(stats)
        
        # Create summary text
        compressed_size = interface.format_file_size(stats['compressed_size'])
        decompressed_size = interface.format_file_size(stats['decompressed_size'])
        throughput = stats['throughput_mb_per_sec']
        
        summary = f"Compressed: {compressed_size} → Decompressed: {decompressed_size}\n"
        summary += f"Processing speed: {throughput:.2f} MB/s\n"
        summary += f"Decompression completed successfully"
        
        # Add summary to log
        log_output.append("\nDecompression Results:")
        log_output.append(f"Compressed size: {stats['compressed_size']} bytes ({compressed_size})")
        log_output.append(f"Decompressed size: {stats['decompressed_size']} bytes ({decompressed_size})")
        log_output.append(f"Decompression time: {stats['elapsed_time']:.4f} seconds")
        log_output.append(f"Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        
        return output_path, summary, stats, True, "\n".join(log_output)
    
    except Exception as e:
        error_msg = f"Error during decompression: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, "Decompression failed", {"error": str(e)}, False, error_msg
