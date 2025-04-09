#!/usr/bin/env python3
# File Compression Application - Main Entry Point

import os
import sys
import argparse
import importlib.util

# Try to import gradio with version compatibility
try:
    import gradio as gr
    # Check if Blocks is available directly (newer Gradio versions)
    has_blocks = hasattr(gr, 'Blocks')
    # If not, try to import from gradio.blocks (older versions)
    if not has_blocks:
        try:
            from gradio import blocks
            gr.Blocks = blocks.Blocks
            has_blocks = True
        except (ImportError, AttributeError):
            has_blocks = False
except ImportError:
    has_blocks = False

# Import compression modules
from compression_methods import (
    get_available_compression_methods,
    compress_file,
    decompress_file
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='File Compression Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress a file')
    compress_parser.add_argument('input', help='Input file path')
    compress_parser.add_argument('--output', '-o', help='Output file path (default: input.compressed)')
    compress_parser.add_argument('--method', '-m', help='Compression method to use')
    
    # Decompress command
    decompress_parser = subparsers.add_parser('decompress', help='Decompress a file')
    decompress_parser.add_argument('input', help='Input file path')
    decompress_parser.add_argument('--output', '-o', help='Output file path (default: derived from input)')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare compression methods')
    compare_parser.add_argument('input', help='Input file path')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch the graphical interface')
    gui_parser.add_argument('--enhanced', action='store_true', help='Use enhanced modular GUI')
    
    return parser.parse_args()

def launch_basic_gui():
    """Launch a basic Gradio interface."""
    compression_methods = get_available_compression_methods()
    method_names = list(compression_methods.keys())
    
    def compress_func(file_obj, method_name):
        if not file_obj:
            return "No file provided!"
        
        input_path = file_obj.name
        output_path = f"{input_path}.compressed"
        
        try:
            result = compress_file(input_path, output_path, method_name)
            return f"Compressed to {output_path}. Original: {result['original_size']} bytes, Compressed: {result['compressed_size']} bytes, Ratio: {result['ratio']:.2f}%"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def decompress_func(file_obj):
        if not file_obj:
            return "No file provided!"
        
        input_path = file_obj.name
        output_path = input_path + ".decompressed"
        
        try:
            decompress_file(input_path, output_path)
            return f"Decompressed to {output_path}. Success!"
        except Exception as e:
            return f"Error: {str(e)}"
    
    with gr.Blocks(title="File Compression Tool") as app:
        gr.Markdown("# File Compression Tool")
        
        with gr.Tab("Compress"):
            with gr.Row():
                with gr.Column():
                    file_input = gr.File(label="Select file to compress")
                    method_dropdown = gr.Dropdown(choices=method_names, label="Compression Method")
                    compress_btn = gr.Button("Compress")
                with gr.Column():
                    compress_output = gr.Textbox(label="Result", interactive=False)
            
            compress_btn.click(
                fn=compress_func,
                inputs=[file_input, method_dropdown],
                outputs=compress_output
            )
            
        with gr.Tab("Decompress"):
            with gr.Row():
                with gr.Column():
                    decompress_file_input = gr.File(label="Select file to decompress")
                    decompress_btn = gr.Button("Decompress")
                with gr.Column():
                    decompress_output = gr.Textbox(label="Result", interactive=False)
            
            decompress_btn.click(
                fn=decompress_func,
                inputs=[decompress_file_input],
                outputs=decompress_output
            )
    
    app.launch()

def launch_enhanced_gui():
    """Launch an enhanced, modular Gradio interface with more features."""
    # Check if necessary modules are available
    if not has_blocks:
        print("Error launching enhanced GUI: module 'gradio' has no attribute 'Blocks'")
        print("Consider updating your gradio installation: pip install -U gradio")
        return
    
    compression_methods = get_available_compression_methods()
    method_names = list(compression_methods.keys())
    
    # Try to load previous results
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compression_results.txt")
    previous_results = []
    
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip():
                        previous_results.append(line.strip())
            print(f"Loaded {len(previous_results)} previous compression results")
        except Exception as e:
            print(f"Error loading previous results: {e}")
    
    # Remove duplicates while maintaining order
    seen = set()
    unique_results = []
    for item in previous_results:
        if item not in seen:
            seen.add(item)
            unique_results.append(item)
    
    if len(unique_results) != len(previous_results):
        print(f"Loaded {len(unique_results)} results (no duplicates found)")
    
    previous_results = unique_results
    
    def compress_func(file_obj, method_name):
        if not file_obj:
            return "No file provided!", previous_results
        
        input_path = file_obj.name
        output_path = f"{input_path}.{method_name.lower()}"
        
        try:
            result = compress_file(input_path, output_path, method_name)
            result_str = f"File: {os.path.basename(input_path)} | Method: {method_name} | Original: {result['original_size']} bytes | Compressed: {result['compressed_size']} bytes | Ratio: {result['ratio']:.2f}%"
            
            # Save to results file
            with open(results_file, 'a') as f:
                f.write(result_str + '\n')
            
            # Update results list
            updated_results = [result_str] + previous_results
            return f"Compressed to {output_path}. {result_str}", updated_results
        except Exception as e:
            return f"Error: {str(e)}", previous_results
    
    def decompress_func(file_obj):
        if not file_obj:
            return "No file provided!"
        
        input_path = file_obj.name
        output_path = input_path + ".decompressed"
        
        try:
            decompress_file(input_path, output_path)
            return f"Decompressed to {output_path}. Success!"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def compare_methods(file_obj):
        if not file_obj:
            return "No file provided!"
        
        input_path = file_obj.name
        results = []
        
        for method_name in compression_methods:
            try:
                output_path = f"{input_path}.{method_name.lower()}"
                result = compress_file(input_path, output_path, method_name)
                results.append((method_name, result))
            except Exception as e:
                results.append((method_name, {"error": str(e)}))
        
        # Sort by compression ratio (best to worst)
        results.sort(key=lambda x: x[1].get("ratio", float("inf")) if "error" not in x[1] else float("inf"))
        
        output = "Compression Method Comparison:\n\n"
        output += f"File: {os.path.basename(input_path)} ({os.path.getsize(input_path)} bytes)\n\n"
        output += "| Method | Compressed Size | Ratio | Time |\n"
        output += "|--------|----------------|-------|------|\n"
        
        for method_name, result in results:
            if "error" in result:
                output += f"| {method_name} | Error: {result['error']} | - | - |\n"
            else:
                output += f"| {method_name} | {result['compressed_size']} bytes | {result['ratio']:.2f}% | {result.get('time', 'N/A')}s |\n"
        
        return output
    
    with gr.Blocks(title="Advanced File Compression Tool") as app:
        gr.Markdown("# Advanced File Compression Tool")
        
        with gr.Tab("Compress"):
            with gr.Row():
                with gr.Column():
                    file_input = gr.File(label="Select file to compress")
                    method_dropdown = gr.Dropdown(choices=method_names, label="Compression Method")
                    compress_btn = gr.Button("Compress")
                with gr.Column():
                    compress_output = gr.Textbox(label="Result", interactive=False)
            
            gr.Markdown("### Previous Compression Results")
            results_list = gr.Dataframe(
                headers=["Results"],
                datatype=["str"],
                value=[[r] for r in previous_results],
                label="Previous Results"
            )
            
            compress_btn.click(
                fn=compress_func,
                inputs=[file_input, method_dropdown],
                outputs=[compress_output, results_list]
            )
            
        with gr.Tab("Decompress"):
            with gr.Row():
                with gr.Column():
                    decompress_file_input = gr.File(label="Select file to decompress")
                    decompress_btn = gr.Button("Decompress")
                with gr.Column():
                    decompress_output = gr.Textbox(label="Result", interactive=False)
            
            decompress_btn.click(
                fn=decompress_func,
                inputs=[decompress_file_input],
                outputs=decompress_output
            )
        
        with gr.Tab("Compare Methods"):
            with gr.Row():
                with gr.Column():
                    compare_file_input = gr.File(label="Select file to compare methods")
                    compare_btn = gr.Button("Compare All Methods")
                with gr.Column():
                    compare_output = gr.Textbox(label="Comparison Results", interactive=False)
            
            compare_btn.click(
                fn=compare_methods,
                inputs=[compare_file_input],
                outputs=compare_output
            )
    
    app.launch()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Print available compression methods
    compression_methods = get_available_compression_methods()
    print(f"Total compression methods available: {len(compression_methods)}")
    
    if args.command == 'compress':
        output = args.output or args.input + '.compressed'
        method = args.method or list(compression_methods.keys())[0]
        result = compress_file(args.input, output, method)
        print(f"Compressed {args.input} to {output}")
        print(f"Original size: {result['original_size']} bytes")
        print(f"Compressed size: {result['compressed_size']} bytes")
        print(f"Compression ratio: {result['ratio']:.2f}%")
    
    elif args.command == 'decompress':
        output = args.output or args.input + '.decompressed'
        decompress_file(args.input, output)
        print(f"Decompressed {args.input} to {output}")
    
    elif args.command == 'compare':
        print(f"Comparing compression methods for {args.input}:")
        original_size = os.path.getsize(args.input)
        print(f"Original size: {original_size} bytes")
        
        results = []
        for method in compression_methods:
            output = f"{args.input}.{method.lower()}"
            try:
                result = compress_file(args.input, output, method)
                results.append((method, result))
                print(f"{method}: {result['compressed_size']} bytes ({result['ratio']:.2f}%)")
            except Exception as e:
                print(f"{method}: Error - {str(e)}")
        
        # Print best method
        if results:
            best_method = min(results, key=lambda x: x[1]['compressed_size'])
            print(f"\nBest method: {best_method[0]} ({best_method[1]['ratio']:.2f}%)")
    
    elif args.command == 'gui':
        print("Launching GUI...")
        try:
            if args.enhanced:
                print("Launching enhanced modular GUI...")
                launch_enhanced_gui()
            else:
                launch_basic_gui()
        except Exception as e:
            print(f"Error launching GUI: {str(e)}")
    
    else:
        print("Please specify a command. Use --help for options.")

if __name__ == "__main__":
    main()
