import os
import sys
import time
import argparse
import json
import importlib
import importlib.util
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

# Check if Gradio is installed and which version we're using
try:
    import gradio as gr
    
    # Try to get version directly from module if not already found
    if GRADIO_VERSION == "unknown":
        if hasattr(gr, "__version__"):
            GRADIO_VERSION = gr.__version__
            print(f"Detected Gradio version {GRADIO_VERSION} from module attribute")
        else:
            # Try to find version from package metadata
            try:
                # Use importlib.metadata for Python 3.8+
                if sys.version_info >= (3, 8):
                    import importlib.metadata
                    GRADIO_VERSION = importlib.metadata.version("gradio")
                    print(f"Detected Gradio version {GRADIO_VERSION} from importlib.metadata")
            except ImportError:
                GRADIO_VERSION = "unknown"
    
    # Check if Gradio version is new enough to support Blocks
    HAS_BLOCKS = False
    
    if hasattr(gr, 'Blocks'):
        HAS_BLOCKS = True
        print(f"Gradio {GRADIO_VERSION} has native Blocks support")
    # If not, try different approaches for compatibility
    else:
        try:
            # Try direct import from blocks module
            from gradio import blocks
            gr.Blocks = blocks.Blocks
            HAS_BLOCKS = True
            print(f"Used compatibility layer to add Blocks support to Gradio {GRADIO_VERSION}")
        except (ImportError, AttributeError) as e:
            # Log the specific error
            print(f"Failed to import Blocks from gradio.blocks: {str(e)}")
            try:
                # Try to monkey patch with a minimum viable implementation
                from types import SimpleNamespace
                
                class MinimalBlocks:
                    def __init__(self, **kwargs):
                        self.kwargs = kwargs
                    
                    def __enter__(self):
                        return self
                    
                    def __exit__(self, exc_type, exc_val, exc_tb):
                        pass
                    
                    def launch(self, **kwargs):
                        print("WARNING: Using minimal Blocks implementation")
                        print("This is a fallback and may not work correctly")
                        print("Please upgrade Gradio to version 3.0 or later")
                
                # Add minimal implementation to gradio
                gr.Blocks = MinimalBlocks
                HAS_BLOCKS = True
                print("Created minimal Blocks compatibility layer (limited functionality)")
            except Exception as monkey_error:
                print(f"Failed to create minimal Blocks implementation: {str(monkey_error)}")
                HAS_BLOCKS = False
except ImportError as e:
    GRADIO_VERSION = None
    HAS_BLOCKS = False
    gr = None
    print(f"Warning: Gradio is not installed: {e}")
    print("GUI features will not be available.")

# Try to import both the original and enhanced Gradio interfaces
try:
    from gradio_interface import GradioInterface, EnhancedGradioInterface
    ENHANCED_UI_AVAILABLE = hasattr(EnhancedGradioInterface, 'run')
except ImportError as e:
    print(f"Failed to import enhanced interface: {e}")
    # If EnhancedGradioInterface isn't available, try just the basic interface
    try:
        from gradio_interface import GradioInterface
        ENHANCED_UI_AVAILABLE = False
        print("Basic gradio interface is available")
    except ImportError as e:
        print(f"Failed to import basic interface: {e}")
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
    gui_parser.add_argument(
        "--install-gradio",
        action="store_true",
        help="Try to install or upgrade gradio if missing"
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
        # If gradio should be installed if missing
        if hasattr(args, 'install_gradio') and args.install_gradio and (GRADIO_VERSION is None or not HAS_BLOCKS):
            print("Trying to install/upgrade Gradio...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "gradio>=3.0.0"])
                print("Gradio installed or upgraded. Please restart the application.")
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                print(f"Failed to install Gradio: {e}")
                print("Please install manually: pip install --upgrade gradio>=3.0.0")
                sys.exit(1)
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
    if gr is None:
        print("Error: Gradio is not available.")
        print("Please install Gradio: pip install gradio>=3.0.0")
        sys.exit(1)
    
    # Check version
    try:
        version_components = GRADIO_VERSION.split('.')
        major_version = int(version_components[0])
        if major_version < 3 and not HAS_BLOCKS:
            print(f"Warning: Your Gradio version {GRADIO_VERSION} may not support Blocks interface")
    except (ValueError, AttributeError, IndexError):
        # If we can't parse the version, continue anyway
        pass
    
    if not HAS_BLOCKS:
        print("Error: Gradio Blocks interface is not available.")
        print("Please install or upgrade Gradio: pip install -U gradio>=3.0.0")
        sys.exit(1)
    
    if enhanced:
        try:
            # Try importing from the gradio module directory first
            print("Launching enhanced modular GUI...")
            
            # Add the gradio directory to the path if it exists
            gradio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gradio")
            if os.path.isdir(gradio_dir):
                if gradio_dir not in sys.path:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    print(f"Added {os.path.dirname(os.path.abspath(__file__))} to Python path")
                
                try:
                    # First try the standard import
                    try:
                        from gradio.main import run_interface
                        run_interface()
                        return
                    except ImportError as e:
                        print(f"Failed to import run_interface: {e}")
                        pass
                    
                    # Fallback: import the enhanced interface directly
                    try:
                        from gradio_interface import EnhancedGradioInterface
                        interface = EnhancedGradioInterface()
                        interface.run()
                        return
                    except ImportError as e:
                        print(f"Failed to import EnhancedGradioInterface: {e}")
                except Exception as e:
                    print(f"Error importing enhanced interface modules: {e}")
            else:
                print(f"Enhanced GUI modules not found in {gradio_dir}")
                print("Please make sure the 'gradio' directory is in the same folder as main.py")
        
        except Exception as e:
            print(f"Error launching enhanced GUI: {e}")
            print("Falling back to standard interface...")
    
    # Launch the standard interface as fallback
    try:
        print("Launching standard GUI...")
        interface = GradioInterface()
        interface.run()
    except Exception as e:
        print(f"Error launching standard GUI: {e}")
        print("Here's the full error trace to help with debugging:")
        import traceback
        traceback.print_exc()
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