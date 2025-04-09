import os
import sys
import time
import argparse
import json
import importlib.util
import matplotlib.pyplot as plt

from marker_finder import MarkerFinder
from compression_methods import (
    RLECompression,
    DictionaryCompression,
    HuffmanCompression,
    DeltaCompression,
    NoCompression
)
from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

# Try to import the compatibility layer if available
try:
    from compression_fix import get_compatible_methods
    COMPAT_AVAILABLE = True
except ImportError:
    COMPAT_AVAILABLE = False

# Check if Gradio is installed and which version we're using
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
            print(f"Using gradio compatibility layer for older version: {getattr(gr, '__version__', 'unknown')}")
        except (ImportError, AttributeError):
            has_blocks = False
            print(f"Warning: Your gradio version {getattr(gr, '__version__', 'unknown')} doesn't support Blocks interface")
except ImportError:
    has_blocks = False
    gr = None
    print("Warning: Gradio is not installed. GUI features will not be available.")

# Try to import both the original and enhanced Gradio interfaces
try:
    from gradio_interface import GradioInterface, EnhancedGradioInterface
    ENHANCED_UI_AVAILABLE = hasattr(EnhancedGradioInterface, 'run')
except ImportError:
    # If EnhancedGradioInterface isn't available, try just the basic interface
    try:
        from gradio_interface import GradioInterface
        ENHANCED_UI_AVAILABLE = False
    except ImportError:
        GradioInterface = None
        ENHANCED_UI_AVAILABLE = False
        print("Warning: No Gradio interfaces found. GUI features will not be available.")


def main():
    """
    Main entry point for the Adaptive Marker-Based Compression program
    """
    parser = argparse.ArgumentParser(
        description="Adaptive Marker-Based Compression Algorithm"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Compress command
    compress_parser = subparsers.add_parser("compress", help="Compress a file")
    compress_parser.add_argument("input", help="Input file to compress")
    compress_parser.add_argument("output", help="Output file path")
    compress_parser.add_argument(
        "--chunk-size", 
        type=int, 
        default=4096, 
        help="Chunk size for compression (default: 4096)"
    )
    
    # Decompress command
    decompress_parser = subparsers.add_parser("decompress", help="Decompress a file")
    decompress_parser.add_argument("input", help="Input file to decompress")
    decompress_parser.add_argument("output", help="Output file path")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze compression results")
    analyze_parser.add_argument(
        "--results-file", 
        default="compression_results/compression_history.json", 
        help="Path to compression results file"
    )
    analyze_parser.add_argument(
        "--output-dir", 
        default="analysis_output", 
        help="Directory to save analysis plots"
    )
    
    # GUI command
    gui_parser = subparsers.add_parser("gui", help="Launch the graphical user interface")
    gui_parser.add_argument(
        "--enhanced", 
        action="store_true",
        help="Use the enhanced modular UI (if available)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "compress":
        compress_file(args.input, args.output, args.chunk_size)
    elif args.command == "decompress":
        decompress_file(args.input, args.output)
    elif args.command == "analyze":
        analyze_results(args.results_file, args.output_dir)
    elif args.command == "gui":
        launch_gui(enhanced=args.enhanced)
    else:
        # If no command is provided, show help
        parser.print_help()


def compress_file(input_path, output_path, chunk_size):
    """
    Compress a file
    
    Args:
        input_path (str): Path to the input file
        output_path (str): Path to the output file
        chunk_size (int): Chunk size for compression
    """
    print(f"Compressing {input_path} to {output_path} with chunk size {chunk_size}...")
    
    try:
        # Create compressor
        compressor = AdaptiveCompressor(chunk_size=chunk_size)
        
        # Compress the file
        stats = compressor.compress(input_path, output_path)
        
        # Print statistics
        print("\nCompression Statistics:")
        print(f"  Original size: {stats['original_size']} bytes")
        print(f"  Compressed size: {stats['compressed_size']} bytes")
        print(f"  Compression ratio: {stats['ratio']:.4f}")
        print(f"  Space saving: {stats['percent_reduction']:.2f}%")
        print(f"  Elapsed time: {stats['elapsed_time']:.4f} seconds")
        print(f"  Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        
        # Print chunk statistics
        print("\nChunk Statistics:")
        print(f"  Total chunks: {stats['chunk_stats']['total_chunks']}")
        print("  Method usage:")
        for method_id, count in stats['chunk_stats']['method_usage'].items():
            if count > 0:
                method_name = get_method_name(method_id)
                print(f"    {method_name}: {count} chunks")
        
        # Save to analyzer
        results_dir = "compression_results"
        os.makedirs(results_dir, exist_ok=True)
        
        analyzer = CompressionAnalyzer()
        results_file = os.path.join(results_dir, "compression_history.json")
        
        if os.path.exists(results_file):
            try:
                analyzer.load_results(results_file)
            except Exception as e:
                print(f"Error loading results: {e}")
        
        analyzer.add_result(input_path, stats)
        analyzer.save_results(results_file)
        
        print(f"\nCompression completed successfully.")
        
        return stats
    
    except Exception as e:
        print(f"Error during compression: {e}")
        sys.exit(1)


def decompress_file(input_path, output_path):
    """
    Decompress a file
    
    Args:
        input_path (str): Path to the input file
        output_path (str): Path to the output file
    """
    print(f"Decompressing {input_path} to {output_path}...")
    
    try:
        # Create compressor
        compressor = AdaptiveCompressor()
        
        # Decompress the file
        stats = compressor.decompress(input_path, output_path)
        
        # Print statistics
        print("\nDecompression Statistics:")
        print(f"  Compressed size: {stats['compressed_size']} bytes")
        print(f"  Decompressed size: {stats['decompressed_size']} bytes")
        print(f"  Elapsed time: {stats['elapsed_time']:.4f} seconds")
        print(f"  Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        
        print(f"\nDecompression completed successfully.")
        
        return stats
    
    except Exception as e:
        print(f"Error during decompression: {e}")
        sys.exit(1)


def analyze_results(results_file, output_dir):
    """
    Analyze compression results
    
    Args:
        results_file (str): Path to the results file
        output_dir (str): Directory to save analysis plots
    """
    print(f"Analyzing compression results from {results_file}...")
    
    try:
        # Create analyzer
        analyzer = CompressionAnalyzer()
        
        # Load results
        analyzer.load_results(results_file)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get summary statistics
        summary = analyzer.get_summary_stats()
        
        # Print summary
        print("\nSummary Statistics:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Save summary to file
        with open(os.path.join(output_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        # Generate and save plots
        plots = [
            ("compression_ratio", analyzer.plot_compression_ratio),
            ("method_usage", analyzer.plot_method_usage),
            ("size_comparison", analyzer.plot_size_comparison),
            ("throughput", analyzer.plot_throughput),
            ("file_type_summary", analyzer.plot_file_type_summary)
        ]
        
        for name, plot_func in plots:
            fig = plot_func()
            if fig:
                plt.figure(fig.number)
                plt.savefig(os.path.join(output_dir, f"{name}.png"))
                plt.close()
                print(f"Saved {name} plot to {output_dir}/{name}.png")
        
        print(f"\nAnalysis completed successfully.")
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


def launch_gui(enhanced=False):
    """
    Launch the graphical user interface
    
    Args:
        enhanced (bool): Whether to use the enhanced modular interface
    """
    # First check if Gradio is installed
    if not has_blocks:
        print("Error: Gradio with Blocks interface is not available.")
        print("Please install or upgrade Gradio: pip install -U gradio")
        sys.exit(1)
    
    if enhanced:
        try:
            # Try importing from the gradio module directory first
            print("Launching enhanced modular GUI...")
            
            # Add the gradio directory to the path if it exists
            gradio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gradio")
            if os.path.isdir(gradio_dir):
                if gradio_dir not in sys.path:
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                
                try:
                    # First try the standard import
                    try:
                        from gradio.main import run_interface
                        run_interface()
                        return
                    except ImportError:
                        pass
                    
                    # Next try importing the enhanced interface directly
                    from gradio_interface import EnhancedGradioInterface
                    interface = EnhancedGradioInterface()
                    interface.run()
                    return
                except ImportError as e:
                    print(f"Error importing enhanced interface: {e}")
                    print("Falling back to standard interface...")
            else:
                print(f"Enhanced GUI modules not found in {gradio_dir}")
                print("Falling back to standard interface...")
        
        except Exception as e:
            print(f"Error launching enhanced GUI: {e}")
            print("Falling back to standard interface...")
    
    # Launch the standard interface
    print("Launching standard GUI...")
    try:
        interface = GradioInterface()
        interface.run()
    except Exception as e:
        print(f"Error launching standard GUI: {e}")
        sys.exit(1)


def get_method_name(method_id):
    """
    Get the name of a compression method from its ID
    
    Args:
        method_id: Method ID (integer or string)
        
    Returns:
        str: Method name
    """
    method_names = {
        1: "Run-Length Encoding (RLE)",
        2: "Dictionary-Based",
        3: "Huffman Coding",
        4: "Delta Encoding",
        5: "DEFLATE",
        6: "BZIP2",
        7: "LZMA",
        8: "ZStandard",
        9: "LZ4",
        10: "Brotli",
        11: "LZHAM",
        255: "No Compression"
    }
    
    # Convert to int if it's a string
    if isinstance(method_id, str):
        try:
            method_id = int(method_id)
        except:
            return f"Method {method_id}"
    
    return method_names.get(method_id, f"Method {method_id}")


if __name__ == "__main__":
    main()