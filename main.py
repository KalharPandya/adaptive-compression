import os
import sys
import time
import argparse
import json
import subprocess
import pkg_resources
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
    print("Compatible compression methods not available")

# Get Gradio version using pkg_resources if possible
try:
    GRADIO_VERSION = pkg_resources.get_distribution("gradio").version
    print(f"Detected Gradio version {GRADIO_VERSION} using pkg_resources")
except (pkg_resources.DistributionNotFound, Exception):
    GRADIO_VERSION = "unknown"

# Assume that Gradio is installed properly.
try:
    import gradio_components as gr
except ImportError as e:
    GRADIO_VERSION = None
    gr = None
    print(f"Warning: Gradio is not installed: {e}")
    print("GUI features will not be available.")

# Import the enhanced GUI interface (legacy/basic code removed)
try:
    from gradio_interface import EnhancedGradioInterface
except ImportError as e:
    print(f"Failed to import EnhancedGradioInterface: {e}")
    sys.exit(1)

def main():
    """
    Main entry point for the Adaptive Marker-Based Compression program.
    If no subcommand is provided, the enhanced GUI will be launched by default.
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
    
    # GUI command (optional, since GUI is now the default)
    gui_parser = subparsers.add_parser("gui", help="Launch the graphical user interface")
    gui_parser.add_argument(
        "--install-gradio",
        action="store_true",
        help="Try to install or upgrade Gradio if missing"
    )
    
    args = parser.parse_args()
    
    # If no command is provided, or if 'gui' is the command, launch the enhanced GUI.
    if args.command is None or args.command == "gui":
        # If Gradio is not available or upgrade is requested, try to install Gradio
        if args.command == "gui" and hasattr(args, "install_gradio") and args.install_gradio:
            print("Trying to install/upgrade Gradio...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "gradio>=3.0.0"])
                print("Gradio installed/upgraded. Please restart the application.")
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                print(f"Failed to install Gradio: {e}")
                sys.exit(1)
        print("Launching enhanced GUI...")
        interface = EnhancedGradioInterface()
        interface.run()
        sys.exit(0)
    
    # Execute compress, decompress, or analyze commands
    if args.command == "compress":
        compress_file(args.input, args.output, args.chunk_size)
    elif args.command == "decompress":
        decompress_file(args.input, args.output)
    elif args.command == "analyze":
        analyze_results(args.results_file, args.output_dir)
    else:
        parser.print_help()


def compress_file(input_path, output_path, chunk_size):
    print(f"Compressing {input_path} to {output_path} with chunk size {chunk_size}...")
    try:
        compressor = AdaptiveCompressor(chunk_size=chunk_size)
        stats = compressor.compress(input_path, output_path)
        print("\nCompression Statistics:")
        print(f"  Original size: {stats['original_size']} bytes")
        print(f"  Compressed size: {stats['compressed_size']} bytes")
        print(f"  Compression ratio: {stats['ratio']:.4f}")
        print(f"  Space saving: {stats['percent_reduction']:.2f}%")
        print(f"  Elapsed time: {stats['elapsed_time']:.4f} seconds")
        print(f"  Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        print("\nChunk Statistics:")
        print(f"  Total chunks: {stats['chunk_stats']['total_chunks']}")
        print("  Method usage:")
        for method_id, count in stats['chunk_stats']['method_usage'].items():
            if count > 0:
                print(f"    {get_method_name(method_id)}: {count} chunks")
        
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
        print("\nCompression completed successfully.")
        return stats
    except Exception as e:
        print(f"Error during compression: {e}")
        sys.exit(1)


def decompress_file(input_path, output_path):
    print(f"Decompressing {input_path} to {output_path}...")
    try:
        compressor = AdaptiveCompressor()
        stats = compressor.decompress(input_path, output_path)
        print("\nDecompression Statistics:")
        print(f"  Compressed size: {stats['compressed_size']} bytes")
        print(f"  Decompressed size: {stats['decompressed_size']} bytes")
        print(f"  Elapsed time: {stats['elapsed_time']:.4f} seconds")
        print(f"  Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        print("\nDecompression completed successfully.")
        return stats
    except Exception as e:
        print(f"Error during decompression: {e}")
        sys.exit(1)


def analyze_results(results_file, output_dir):
    print(f"Analyzing compression results from {results_file}...")
    try:
        analyzer = CompressionAnalyzer()
        analyzer.load_results(results_file)
        os.makedirs(output_dir, exist_ok=True)
        summary = analyzer.get_summary_stats()
        print("\nSummary Statistics:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        with open(os.path.join(output_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
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
        print("\nAnalysis completed successfully.")
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


def get_method_name(method_id):
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
    try:
        method_id = int(method_id)
    except:
        return f"Method {method_id}"
    return method_names.get(method_id, f"Method {method_id}")


if __name__ == "__main__":
    main()
