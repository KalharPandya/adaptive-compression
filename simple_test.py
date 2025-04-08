import os
import tempfile
import hashlib
import shutil
from adaptive_compressor import AdaptiveCompressor

def test_simple_compression():
    """
    Test compression and decompression with a very simple, controlled dataset
    and additional verification
    """
    print("\n===== Testing Simple Data Pattern =====")
    
    # Backup original compressor if exists
    original_compressor_path = "adaptive_compressor.py.bak"
    if os.path.exists("adaptive_compressor.py") and not os.path.exists(original_compressor_path):
        print("Backing up original adaptive_compressor.py")
        shutil.copy("adaptive_compressor.py", original_compressor_path)
    
    # Generate a simple test file with very predictable content
    test_file = os.path.join(tempfile.gettempdir(), "simple_test.bin")
    with open(test_file, 'wb') as f:
        # Just write 1000 'A's followed by 1000 'B's
        f.write(b'A' * 1000)
        f.write(b'B' * 1000)
    
    output_file = os.path.join(tempfile.gettempdir(), "simple_compressed.ambc")
    decompressed_file = os.path.join(tempfile.gettempdir(), "simple_decompressed.bin")
    
    try:
        # Create compressor
        compressor = AdaptiveCompressor(chunk_size=500)  # Small chunk size for testing
        
        # Make sure we're using the fixed compressor
        print(f"Adaptive Compressor version: {compressor.FORMAT_VERSION if hasattr(compressor, 'FORMAT_VERSION') else 'Original'}")
        
        # Compress the file
        print(f"\nCompressing {test_file}...")
        stats = compressor.compress(test_file, output_file)
        
        # Print statistics
        print("\nCompression Results:")
        print(f"Original size: {stats['original_size']} bytes")
        print(f"Compressed size: {stats['compressed_size']} bytes")
        print(f"Compression ratio: {stats['ratio']:.4f}")
        print(f"Space saving: {stats['percent_reduction']:.2f}%")
        
        # Calculate MD5 hash of original file for verification
        with open(test_file, 'rb') as f:
            original_md5 = hashlib.md5(f.read()).hexdigest()
        print(f"Original file MD5: {original_md5}")
        
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
        for method_id, count in stats['chunk_stats']['method_usage'].items():
            if count > 0:
                method_name = method_names.get(method_id, f"Method {method_id}")
                total = stats['chunk_stats']['total_chunks']
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"  {method_name}: {count} chunks ({percentage:.1f}%)")
        
        # Write compressed data information
        with open(output_file, 'rb') as f:
            compressed_data = f.read()
            compressed_md5 = hashlib.md5(compressed_data).hexdigest()
            print(f"Compressed file size: {len(compressed_data)} bytes")
            print(f"Compressed file MD5: {compressed_md5}")
        
        # Decompress the file with additional verification
        print(f"\nDecompressing {output_file}...")
        try:
            decomp_stats = compressor.decompress(output_file, decompressed_file)
            
            # Verify file integrity
            with open(test_file, 'rb') as f1, open(decompressed_file, 'rb') as f2:
                original_data = f1.read()
                decompressed_data = f2.read()
                
                # Calculate MD5 hash of decompressed file
                decompressed_md5 = hashlib.md5(decompressed_data).hexdigest()
                print(f"Decompressed file MD5: {decompressed_md5}")
                print(f"MD5 match with original: {original_md5 == decompressed_md5}")
                
                if len(original_data) != len(decompressed_data):
                    print(f"Size mismatch: Original {len(original_data)} bytes, Decompressed {len(decompressed_data)} bytes")
                
                if original_data == decompressed_data:
                    print("✅ Success: Decompressed file matches original")
                else:
                    # Find where they differ
                    differences = 0
                    first_diff_pos = -1
                    for i in range(min(len(original_data), len(decompressed_data))):
                        if original_data[i] != decompressed_data[i]:
                            differences += 1
                            if first_diff_pos == -1:
                                first_diff_pos = i
                                print(f"❌ First data mismatch at position {i}:")
                                print(f"   Original: {original_data[i:i+16].hex()}")
                                print(f"   Decompressed: {decompressed_data[i:i+16].hex()}")
                    
                    if differences > 0:
                        print(f"❌ Total differences: {differences}")
                    print("❌ Decompressed file does not match original")
            
            # Print decompression stats
            print("\nDecompression Stats:")
            print(f"Compressed size: {decomp_stats['compressed_size']} bytes")
            print(f"Decompressed size: {decomp_stats['decompressed_size']} bytes")
            print(f"Elapsed time: {decomp_stats['elapsed_time']:.4f} seconds")
            print(f"Throughput: {decomp_stats['throughput_mb_per_sec']:.2f} MB/s")
        
        except Exception as e:
            print(f"Decompression error: {e}")
            import traceback
            traceback.print_exc()
    
    finally:
        # Leave files for inspection
        print(f"Test files are kept for debugging:")
        print(f"  Original: {test_file}")
        print(f"  Compressed: {output_file}")
        print(f"  Decompressed: {decompressed_file}")

if __name__ == "__main__":
    test_simple_compression()