#!/usr/bin/env python3
"""
Basic test script for the adaptive compression algorithm.
Performs compression and decompression tests on generated test data.
"""

import os
import sys
import tempfile
import hashlib

from adaptive_compressor import AdaptiveCompressor

def test_basic_compression():
    """
    Basic test for compression and decompression of different data patterns.
    """
    print("\n===== BASIC COMPRESSION TEST =====")
    
    # Create a temporary directory for test files
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "basic_test.bin")
    compressed_file = os.path.join(temp_dir, "basic_test.ambc")
    decompressed_file = os.path.join(temp_dir, "basic_test_decompressed.bin")
    
    # Generate test data with multiple patterns
    test_data = bytearray()
    
    # 1. Repeated data - good for RLE
    print("Generating test data with multiple patterns...")
    test_data.extend(b'A' * 1000)
    
    # 2. Text data - good for dictionary/Huffman compression
    for i in range(50):
        test_data.extend(f"This is test sentence {i} with some repetition. ".encode('utf-8'))
    
    # 3. Binary data with small variations - good for Delta encoding
    base = 100
    for i in range(1000):
        test_data.append((base + i % 20) % 256)
    
    # 4. Random data - challenging for compression
    try:
        import random
        random_data = bytes(random.randint(0, 255) for _ in range(1000))
        test_data.extend(random_data)
    except Exception as e:
        print(f"Error generating random data: {e}")
        # Add some pseudo-random data instead
        test_data.extend(b''.join(bytes([i % 256]) for i in range(1000)))
    
    # Write test data to file
    with open(test_file, 'wb') as f:
        f.write(test_data)
    
    print(f"Created test file: {test_file}")
    print(f"Test data size: {len(test_data)} bytes")
    
    # Calculate MD5 hash of original data for later verification
    original_md5 = hashlib.md5(test_data).hexdigest()
    print(f"Original MD5: {original_md5}")
    
    try:
        # Create compressor with different chunk sizes to test adaptivity
        for chunk_size in [512, 1024, 4096]:
            print(f"\nTesting with chunk size: {chunk_size}")
            
            # Create compressor
            compressor = AdaptiveCompressor(initial_chunk_size=chunk_size)
            
            # Compress
            print("Compressing...")
            stats = compressor.compress(test_file, compressed_file)
            
            print(f"Compressed {stats['original_size']} bytes to {stats['compressed_size']} bytes")
            print(f"Compression ratio: {stats['ratio']:.4f}")
            print(f"Space saving: {stats['percent_reduction']:.2f}%")
            
            # Decompress
            print("\nDecompressing...")
            try:
                decomp_stats = compressor.decompress(compressed_file, decompressed_file)
                
                # Verify the decompressed file
                with open(decompressed_file, 'rb') as f:
                    decompressed_data = f.read()
                
                # Check size
                if len(decompressed_data) != len(test_data):
                    print(f"❌ Size mismatch: Original {len(test_data)}, Decompressed {len(decompressed_data)}")
                
                # Check content with MD5
                decompressed_md5 = hashlib.md5(decompressed_data).hexdigest()
                print(f"Decompressed MD5: {decompressed_md5}")
                
                if decompressed_md5 == original_md5:
                    print("✅ Success: Decompressed file matches original")
                else:
                    print("❌ Error: Decompressed file does not match original")
                    
                    # Find where they differ
                    diff_count = 0
                    for i in range(min(len(test_data), len(decompressed_data))):
                        if test_data[i] != decompressed_data[i]:
                            if diff_count < 5:  # Only show first few differences
                                print(f"  Difference at byte {i}:")
                                print(f"    Original: {test_data[i]:02X}")
                                print(f"    Decompressed: {decompressed_data[i]:02X}")
                            diff_count += 1
                    
                    print(f"  Total differences: {diff_count} bytes")
            
            except Exception as e:
                print(f"❌ Decompression error: {e}")
                import traceback
                traceback.print_exc()
    
    finally:
        # Clean up test files
        for file in [test_file, compressed_file, decompressed_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    print(f"Cleaned up: {file}")
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")

if __name__ == "__main__":
    test_basic_compression()
