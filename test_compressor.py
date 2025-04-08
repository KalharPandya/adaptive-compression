import os
import random
import tempfile
import matplotlib.pyplot as plt
import numpy as np
from adaptive_compressor import AdaptiveCompressor
from compression_analyzer import CompressionAnalyzer

def generate_test_file(size=100000, pattern_type="mixed"):
    """
    Generate a test file with different patterns
    
    Args:
        size (int): Size of the file in bytes
        pattern_type (str): Type of pattern to generate
                           "random" - completely random bytes
                           "repetitive" - highly repetitive data
                           "structured" - structured data with patterns
                           "sequential" - sequential values with small variations
                           "mixed" - mix of all pattern types
                           "binary" - simulated binary file with headers and data segments
                           "text" - realistic text simulation with formatting
    
    Returns:
        str: Path to the generated file
    """
    test_file = os.path.join(tempfile.gettempdir(), f"test_data_{pattern_type}.bin")
    
    with open(test_file, 'wb') as f:
        if pattern_type == "random":
            # Generate random data
            f.write(bytes(random.randint(0, 255) for _ in range(size)))
            
        elif pattern_type == "repetitive":
            # Generate repetitive data with varying run lengths
            remaining = size
            while remaining > 0:
                # Repeat a byte between 5-200 times
                byte = random.randint(0, 255)
                repeat = min(remaining, random.randint(5, 200))
                f.write(bytes([byte] * repeat))
                remaining -= repeat
                
        elif pattern_type == "structured":
            # Generate structured data with patterns
            patterns = [
                b"The quick brown fox jumps over the lazy dog. ",
                b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. ",
                b"All human beings are born free and equal in dignity and rights. ",
                b"To be or not to be, that is the question. "
            ]
            
            remaining = size
            while remaining > 0:
                pattern = random.choice(patterns)
                if len(pattern) > remaining:
                    pattern = pattern[:remaining]
                f.write(pattern)
                remaining -= len(pattern)
            
        elif pattern_type == "sequential":
            # Generate sequential data with small variations
            base = random.randint(0, 200)  # Start from random base value
            variation = random.randint(2, 8)  # Use different variation ranges
            
            data = bytearray()
            for i in range(size):
                # Create sequential data with small, predictable variations
                value = (base + (i % variation)) % 256
                data.append(value)
            
            f.write(data)
            
        elif pattern_type == "binary":
            # Simulate a binary file with headers and data segments
            
            # File header (fixed structure)
            header = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])  # Like PNG signature
            header.extend([0] * 24)  # Add some zero padding
            
            # Generate several data chunks
            chunks = []
            chunk_count = random.randint(3, 8)
            chunk_size = (size - len(header)) // chunk_count
            
            for i in range(chunk_count):
                chunk_header = bytearray([i, 0, 0, 0])  # Simple chunk header
                chunk_header.extend(struct.pack(">I", chunk_size))  # Size as big-endian uint32
                
                # Chunk data - different pattern per chunk
                chunk_data = bytearray()
                pattern_type = random.choice(["random", "repetitive", "sequential"])
                
                if pattern_type == "random":
                    chunk_data.extend(bytes(random.randint(0, 255) for _ in range(chunk_size - 8)))
                elif pattern_type == "repetitive":
                    byte = random.randint(0, 255)
                    chunk_data.extend([byte] * (chunk_size - 8))
                else:  # sequential
                    base = random.randint(0, 200)
                    chunk_data.extend(((base + j % 10) % 256 for j in range(chunk_size - 8)))
                
                # Checksum for the chunk
                chunk_data.extend([0xFF, 0xFF, 0xFF, 0xFF])  # Dummy checksum
                
                chunks.append(chunk_header + chunk_data)
            
            # Write file
            f.write(header)
            for chunk in chunks:
                f.write(chunk)
                
        elif pattern_type == "text":
            # Generate realistic text data with format markers
            
            # Common text parts
            words = ["the", "be", "to", "of", "and", "a", "in", "that", "have", "I", 
                    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
                    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
                    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what"]
            
            # Generate sentences and paragraphs
            paragraphs = []
            remaining_size = size
            
            while remaining_size > 0:
                # Make a paragraph
                paragraph_size = min(remaining_size, random.randint(200, 800))
                paragraph = bytearray()
                
                # Add sentences to paragraph
                while len(paragraph) < paragraph_size:
                    # Make a sentence
                    sentence_len = random.randint(5, 15)
                    sentence = bytearray()
                    
                    for i in range(sentence_len):
                        word = random.choice(words).encode('utf-8')
                        sentence.extend(word)
                        if i < sentence_len - 1:
                            sentence.append(32)  # space
                    
                    # Add punctuation and space
                    sentence.append(random.choice([46, 33, 63]))  # period, exclamation, question
                    sentence.append(32)  # space
                    
                    # Add to paragraph if it fits
                    if len(paragraph) + len(sentence) <= paragraph_size:
                        paragraph.extend(sentence)
                    else:
                        break
                
                # Add paragraph terminator
                paragraph.append(10)  # newline
                
                paragraphs.append(paragraph)
                remaining_size -= len(paragraph)
            
            # Write all paragraphs
            for paragraph in paragraphs:
                f.write(paragraph)
                
        elif pattern_type == "mixed":
            # Mix of all patterns
            patterns = ["random", "repetitive", "structured", "sequential", "binary"]
            segment_size = size // len(patterns)
            
            for pattern in patterns:
                if pattern == "random":
                    f.write(bytes(random.randint(0, 255) for _ in range(segment_size)))
                elif pattern == "repetitive":
                    remaining = segment_size
                    while remaining > 0:
                        byte = random.randint(0, 255)
                        repeat = min(remaining, random.randint(10, 100))
                        f.write(bytes([byte] * repeat))
                        remaining -= repeat
                elif pattern == "structured":
                    pattern_text = b"This is a structured pattern that should repeat. "
                    repeats = segment_size // len(pattern_text) + 1
                    f.write(pattern_text * repeats)
                    f.truncate(f.tell())
                elif pattern == "sequential":
                    base = 100
                    f.write(bytes((base + i % 10) % 256 for i in range(segment_size)))
                elif pattern == "binary":
                    # Simple binary-like data with repeating header pattern
                    header = bytes([0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF])
                    data_chunks = segment_size // 64  # 64-byte chunks
                    
                    for i in range(data_chunks):
                        f.write(header)
                        # Data part varies
                        if i % 3 == 0:
                            f.write(bytes([i & 0xFF] * 56))  # Repeating byte
                        elif i % 3 == 1:
                            f.write(bytes(random.randint(0, 255) for _ in range(56)))  # Random
                        else:
                            f.write(bytes((base + j) % 256 for j in range(56)))  # Sequential
    
    return test_file

def test_compression(pattern_type="mixed", file_size=100000):
    """
    Test compression and decompression for a specific pattern type
    with enhanced analysis
    
    Args:
        pattern_type (str): Type of pattern to test
        file_size (int): Size of the test file in bytes
    """
    print(f"\n===== Testing {pattern_type.upper()} data pattern =====")
    
    # Generate test file
    test_file = generate_test_file(size=file_size, pattern_type=pattern_type)
    output_file = os.path.join(tempfile.gettempdir(), f"{pattern_type}_compressed.ambc")
    decompressed_file = os.path.join(tempfile.gettempdir(), f"{pattern_type}_decompressed.bin")
    
    try:
        # Create enhanced compressor
        compressor = AdaptiveCompressor(initial_chunk_size=4096)
        
        # Compress the file
        print(f"\nCompressing {test_file}...")
        stats = compressor.compress(test_file, output_file)
        
        # Print statistics
        print("\nCompression Results:")
        print(f"Original size: {stats['original_size']} bytes")
        print(f"Compressed size: {stats['compressed_size']} bytes")
        print(f"Compression ratio: {stats['ratio']:.4f}")
        print(f"Space saving: {stats['percent_reduction']:.2f}%")
        print(f"Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
        
        # Print method usage
        print("\nMethod Usage:")
        method_names = {
            1: "RLE",
            2: "Dictionary",
            3: "Huffman",
            4: "Delta",
            5: "DEFLATE",
            6: "BZIP2",
            7: "LZMA",
            8: "ZStandard",
            9: "LZ4",
            10: "Brotli",
            11: "LZHAM",
            255: "No Compression"
        }
        
        # Sort methods by usage count
        method_usage = [(method_id, count) for method_id, count in stats['chunk_stats']['method_usage'].items() if count > 0]
        method_usage.sort(key=lambda x: x[1], reverse=True)
        
        for method_id, count in method_usage:
            method_name = method_names.get(method_id, f"Method {method_id}")
            total = stats['chunk_stats']['total_chunks']
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"  {method_name}: {count} chunks ({percentage:.1f}%)")
        
        # Decompress the file
        print(f"\nDecompressing {output_file}...")
        try:
            decomp_stats = compressor.decompress(output_file, decompressed_file)
            
            # Verify file integrity
            with open(test_file, 'rb') as f1, open(decompressed_file, 'rb') as f2:
                original_data = f1.read()
                decompressed_data = f2.read()
                
                if len(original_data) != len(decompressed_data):
                    print(f"Size mismatch: Original {len(original_data)} bytes, Decompressed {len(decompressed_data)} bytes")
                
                if original_data == decompressed_data:
                    print("✅ Success: Decompressed file matches original")
                else:
                    # Find where they differ
                    for i in range(min(len(original_data), len(decompressed_data))):
                        if original_data[i] != decompressed_data[i]:
                            print(f"❌ Data mismatch at position {i}:")
                            print(f"   Original: {original_data[i:i+16].hex()}")
                            print(f"   Decompressed: {decompressed_data[i:i+16].hex()}")
                            break
                    print("❌ Decompressed file does not match original")
            
            # Print decompression stats
            print("\nDecompression Stats:")
            print(f"Compressed size: {decomp_stats['compressed_size']} bytes")
            print(f"Decompressed size: {decomp_stats['decompressed_size']} bytes")
            print(f"Elapsed time: {decomp_stats['elapsed_time']:.4f} seconds")
            print(f"Throughput: {decomp_stats['throughput_mb_per_sec']:.2f} MB/s")
            
            # Add to analyzer
            analyzer = CompressionAnalyzer()
            analyzer.add_result(test_file, stats)
            
            # Generate visualization for this test
            plot_compression_comparison(pattern_type, stats)
            
        except Exception as e:
            print(f"Decompression error: {e}")
            import traceback
            traceback.print_exc()
    
    finally:
        # Don't remove the files for debugging
        print(f"Test files are kept for debugging:")
        print(f"  Original: {test_file}")
        print(f"  Compressed: {output_file}")
        print(f"  Decompressed: {decompressed_file}")

def plot_compression_comparison(pattern_type, stats):
    """Create a visualization of the compression results"""
    method_names = {
        1: "RLE",
        2: "Dictionary", 
        3: "Huffman",
        4: "Delta",
        5: "DEFLATE",
        6: "BZIP2",
        7: "LZMA",
        8: "ZStandard",
        9: "LZ4",
        10: "Brotli",
        11: "LZHAM",
        255: "No Compression"
    }
    
    # Create method usage chart
    method_usage = {method_names.get(id, f"Method {id}"): count 
                   for id, count in stats['chunk_stats']['method_usage'].items() 
                   if count > 0}
    
    # Sort methods by usage
    methods = sorted(method_usage.items(), key=lambda x: x[1], reverse=True)
    
    # Create the figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Plot method usage (pie chart)
    labels = [m[0] for m in methods]
    sizes = [m[1] for m in methods]
    colors = plt.cm.tab10(np.arange(len(labels)) % 10)
    
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title(f'Compression Method Usage for {pattern_type.title()} Data')
    ax1.axis('equal')
    
    # Plot file size comparison (bar chart)
    labels = ['Original', 'Compressed']
    sizes = [stats['original_size'], stats['compressed_size']]
    ax2.bar(labels, sizes, color=['steelblue', 'lightgreen'])
    
    # Add value labels on bars
    for i, v in enumerate(sizes):
        ax2.text(i, v * 1.01, f"{v:,} bytes", ha='center')
    
    # Add percent reduction label
    reduction = stats['percent_reduction']
    ax2.text(0.5, max(sizes) * 0.5, f"{reduction:.1f}%\nReduction", 
            ha='center', fontsize=12, fontweight='bold',
            bbox=dict(facecolor='wheat', alpha=0.5))
    
    ax2.set_title(f'File Size Comparison - {pattern_type.title()}')
    ax2.set_ylabel('Size (bytes)')
    
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join(tempfile.gettempdir(), f"{pattern_type}_compression_analysis.png")
    plt.savefig(output_path)
    print(f"Analysis chart saved to: {output_path}")
    plt.close()

def run_full_benchmark():
    """Run comprehensive benchmarks on different data patterns"""
    # Define test patterns and sizes
    patterns = [
        ("random", 500000),
        ("repetitive", 500000),
        ("structured", 500000),
        ("sequential", 500000),
        ("binary", 500000),
        ("text", 500000),
        ("mixed", 500000)
    ]
    
    # Run tests for each pattern
    results = []
    for pattern, size in patterns:
        print(f"\n\n============ TESTING {pattern.upper()} PATTERN ============")
        test_file = generate_test_file(size=size, pattern_type=pattern)
        output_file = os.path.join(tempfile.gettempdir(), f"{pattern}_compressed.ambc")
        
        # Create compressor
        compressor = AdaptiveCompressor(initial_chunk_size=4096)
        
        # Compress the file
        start_time = time.time()
        stats = compressor.compress(test_file, output_file)
        
        # Store results
        results.append({
            'pattern': pattern,
            'size': size,
            'original_size': stats['original_size'],
            'compressed_size': stats['compressed_size'],
            'ratio': stats['ratio'],
            'percent_reduction': stats['percent_reduction'],
            'throughput': stats['throughput_mb_per_sec'],
            'method_usage': {method_names.get(id, f"Method {id}"): count 
                           for id, count in stats['chunk_stats']['method_usage'].items() 
                           if count > 0}
        })
        
        # Clean up
        os.remove(test_file)
        os.remove(output_file)
    
    # Generate comparative visualization
    create_benchmark_visualization(results)

def create_benchmark_visualization(results):
    """Create comparative visualization of benchmark results"""
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Extract data
    patterns = [r['pattern'] for r in results]
    ratios = [r['ratio'] for r in results]
    reductions = [r['percent_reduction'] for r in results]
    
    # Plot compression ratios
    ax1.bar(patterns, ratios, color='steelblue')
    ax1.set_ylabel('Compression Ratio (smaller is better)')
    ax1.set_title('Compression Ratio by Data Pattern')
    
    # Add horizontal line at 1.0 (no compression)
    ax1.axhline(y=1.0, color='red', linestyle='--', alpha=0.7)
    
    # Add percent labels
    for i, ratio in enumerate(ratios):
        if ratio < 0.95:  # Only add labels if there was significant compression
            ax1.text(i, ratio + 0.03, f"{reductions[i]:.1f}%", ha='center')
    
    # Plot method usage across patterns
    all_methods = set()
    for r in results:
        all_methods.update(r['method_usage'].keys())
    
    all_methods = sorted(list(all_methods))
    color_map = {method: plt.cm.tab10(i % 10) for i, method in enumerate(all_methods)}
    
    bottoms = np.zeros(len(patterns))
    for method in all_methods:
        values = []
        for r in results:
            count = r['method_usage'].get(method, 0)
            total = sum(r['method_usage'].values())
            values.append(count / total * 100 if total > 0 else 0)
        
        ax2.bar(patterns, values, bottom=bottoms, label=method, color=color_map[method])
        bottoms += values
    
    ax2.set_ylabel('Method Usage (%)')
    ax2.set_title('Compression Method Distribution by Data Pattern')
    ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=5)
    
    # Add more space for the legend
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2)
    
    # Save figure
    output_path = os.path.join(tempfile.gettempdir(), "compression_benchmark_results.png")
    plt.savefig(output_path)
    print(f"Benchmark results visualization saved to: {output_path}")
    plt.close()

if __name__ == "__main__":
    import sys
    import time
    import struct
    
    if len(sys.argv) > 1:
        # Test specific pattern type
        pattern_type = sys.argv[1]
        file_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
        test_compression(pattern_type, file_size)
    else:
        # Run benchmark for all patterns
        test_compression("structured", 100000)