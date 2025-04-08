#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
import random

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adaptive_compressor import AdaptiveCompressor


class TestCompression(unittest.TestCase):
    """Test the compression and decompression functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Create test files of different types"""
        cls.test_dir = tempfile.mkdtemp()
        cls.files = {}
        
        # Create a repeated data test file
        repeated_path = os.path.join(cls.test_dir, "repeated.dat")
        with open(repeated_path, "wb") as f:
            f.write(b"A" * 1000 + b"B" * 1000 + b"C" * 1000)
        cls.files["repeated"] = repeated_path
        
        # Create a random data test file
        random_path = os.path.join(cls.test_dir, "random.dat")
        with open(random_path, "wb") as f:
            f.write(bytes([random.randint(0, 255) for _ in range(3000)]))
        cls.files["random"] = random_path
        
        # Create a text data test file
        text_path = os.path.join(cls.test_dir, "text.txt")
        with open(text_path, "w") as f:
            f.write("This is a test text file with some repeating content. " * 30)
        cls.files["text"] = text_path
    
    def test_compression_decompression_cycle(self):
        """Test that files can be compressed and then decompressed correctly"""
        compressor = AdaptiveCompressor()
        
        for name, input_path in self.files.items():
            # Create output paths
            compressed_path = os.path.join(self.test_dir, f"{name}.ambc")
            decompressed_path = os.path.join(self.test_dir, f"{name}_decompressed")
            
            try:
                # Compress the file
                compress_stats = compressor.compress(input_path, compressed_path)
                self.assertTrue(os.path.exists(compressed_path), f"Compressed file not created for {name}")
                
                # Check that the compression produced some results
                self.assertIn('original_size', compress_stats, f"Missing original_size in stats for {name}")
                self.assertIn('compressed_size', compress_stats, f"Missing compressed_size in stats for {name}")
                self.assertIn('ratio', compress_stats, f"Missing ratio in stats for {name}")
                
                # Decompress the file
                decompress_stats = compressor.decompress(compressed_path, decompressed_path)
                self.assertTrue(os.path.exists(decompressed_path), f"Decompressed file not created for {name}")
                
                # Check that the files match
                with open(input_path, "rb") as f1, open(decompressed_path, "rb") as f2:
                    original_data = f1.read()
                    decompressed_data = f2.read()
                    
                    self.assertEqual(len(original_data), len(decompressed_data), 
                                    f"Size mismatch for {name}: {len(original_data)} vs {len(decompressed_data)}")
                    self.assertEqual(original_data, decompressed_data, 
                                    f"Content mismatch for {name}")
                
                print(f"✓ {name}: Compressed {compress_stats['original_size']} → {compress_stats['compressed_size']} bytes, "
                      f"{compress_stats['percent_reduction']:.1f}% reduction, ratio: {compress_stats['ratio']:.3f}")
            
            except Exception as e:
                self.fail(f"Compression/decompression failed for {name}: {e}")
    
    def test_different_chunk_sizes(self):
        """Test compression with different chunk sizes"""
        chunk_sizes = [512, 1024, 4096, 16384]
        results = {}
        
        # Test with text file only
        input_path = self.files["text"]
        
        for chunk_size in chunk_sizes:
            compressor = AdaptiveCompressor(chunk_size=chunk_size)
            compressed_path = os.path.join(self.test_dir, f"text_{chunk_size}.ambc")
            
            try:
                stats = compressor.compress(input_path, compressed_path)
                results[chunk_size] = stats
            except Exception as e:
                self.fail(f"Compression failed with chunk size {chunk_size}: {e}")
        
        # Verify that all compressions succeeded
        for chunk_size, stats in results.items():
            self.assertIn('ratio', stats, f"Missing ratio for chunk size {chunk_size}")
            print(f"✓ Chunk size {chunk_size}: ratio {stats['ratio']:.3f}, {stats['percent_reduction']:.1f}% reduction")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test files"""
        # Remove each test file
        for path in cls.files.values():
            if os.path.exists(path):
                os.unlink(path)
        
        # Remove compressed and decompressed files
        for name in cls.files:
            compressed_path = os.path.join(cls.test_dir, f"{name}.ambc")
            decompressed_path = os.path.join(cls.test_dir, f"{name}_decompressed")
            
            if os.path.exists(compressed_path):
                os.unlink(compressed_path)
            
            if os.path.exists(decompressed_path):
                os.unlink(decompressed_path)
        
        # Additional chunk size test files
        for chunk_size in [512, 1024, 4096, 16384]:
            path = os.path.join(cls.test_dir, f"text_{chunk_size}.ambc")
            if os.path.exists(path):
                os.unlink(path)
        
        # Remove test directory
        try:
            os.rmdir(cls.test_dir)
        except OSError:
            pass  # Directory might not be empty


if __name__ == "__main__":
    unittest.main()
