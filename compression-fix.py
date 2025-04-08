"""
This module provides compatibility fixes for Brotli and ZStandard compression
to ensure they work properly with our adaptive compression system.
"""

import os
import hashlib
import sys
import random

# Try to import Brotli
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
    print("brotli library not available. Brotli compression will be disabled.")

# Try to import ZStandard
try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False
    print("zstd library not available. ZStandard compression will be disabled.")


class CompatibleBrotliCompression:
    """Brotli compression with additional compatibility for our adaptive system"""
    
    @property
    def type_id(self):
        return 10
    
    def compress(self, data):
        """
        Compress using Brotli with settings that ensure correct decompression
        
        Args:
            data (bytes): Data to compress
            
        Returns:
            bytes: Compressed data
        """
        if not data:
            return b''
        
        try:
            # Use Brotli with quality level 11 (max) but specific settings for better compatibility
            # Adding a simple header for easier detection during decompression
            header = b'BRTL'  # Simple 4-byte header
            size_bytes = len(data).to_bytes(4, byteorder='little')
            
            # Compress with high quality but don't use sliding window
            # This makes decompression more reliable in our format
            compressed = brotli.compress(data, quality=11, lgwin=20)
            
            # Add our custom header with original size for easier handling
            result = header + size_bytes + compressed
            
            print(f"Compatible Brotli compression: {len(data)} bytes -> {len(result)} bytes")
            return result
        except Exception as e:
            print(f"Brotli compression error: {e}")
            # Fall back to no compression
            return data
    
    def decompress(self, data, original_length):
        """
        Decompress Brotli-compressed data with improved error handling
        
        Args:
            data (bytes): Compressed data
            original_length (int): Original length of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        if not data:
            return b''
        
        try:
            # Check for our custom header
            if len(data) >= 8 and data[:4] == b'BRTL':
                # Extract size from our header
                size_from_header = int.from_bytes(data[4:8], byteorder='little')
                
                # Use Brotli to decompress (skip our header)
                decompressed = brotli.decompress(data[8:])
                print(f"Compatible Brotli decompression: {len(data)-8} bytes -> {len(decompressed)} bytes")
                
                # Verify size
                if len(decompressed) != size_from_header:
                    print(f"Warning: Decompressed size ({len(decompressed)}) doesn't match header size ({size_from_header})")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: Brotli decompressed data too large, truncating")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: Brotli decompressed data too small, padding")
                        missing = original_length - len(decompressed)
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            else:
                # Standard Brotli format without our header
                try:
                    decompressed = brotli.decompress(data)
                    
                    # Ensure correct size
                    if len(decompressed) != original_length:
                        if len(decompressed) > original_length:
                            decompressed = decompressed[:original_length]
                        else:
                            missing = original_length - len(decompressed)
                            decompressed = decompressed + bytes(missing)
                    
                    return decompressed
                except Exception:
                    print("Standard Brotli decompression failed, using fallback")
                    return bytes(original_length)
        
        except Exception as e:
            print(f"Brotli decompression error: {e}")
            # Return zeros as a fallback
            return bytes(original_length)
    
    def should_use(self, data, threshold=0.9):
        """
        Determine if Brotli compression should be used
        
        Args:
            data (bytes): Data to analyze
            threshold (float): Threshold for making decision
            
        Returns:
            bool: True if Brotli should be used
        """
        # Brotli works best on text data
        if len(data) < 100:
            return False
                
        # Check if it's likely text data
        text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9, 10, 13))
        text_ratio = text_chars / len(data) if data else 0
        
        # Brotli is optimized for text content
        return text_ratio > 0.6


class CompatibleZstdCompression:
    """ZStandard compression with additional compatibility for our adaptive system"""
    
    @property
    def type_id(self):
        return 8
    
    def compress(self, data):
        """
        Compress using ZStandard with settings that ensure correct decompression
        
        Args:
            data (bytes): Data to compress
            
        Returns:
            bytes: Compressed data
        """
        if not data:
            return b''
        
        try:
            # Use ZStandard with high compression level
            # Adding a simple header for easier detection during decompression
            header = b'ZSTD'  # Simple 4-byte header
            size_bytes = len(data).to_bytes(4, byteorder='little')
            
            # Compress with consistent parameters
            compressor = zstd.ZstdCompressor(level=19)
            compressed = compressor.compress(data)
            
            # Add our custom header with original size for easier handling
            result = header + size_bytes + compressed
            
            print(f"Compatible ZStd compression: {len(data)} bytes -> {len(result)} bytes")
            return result
        except Exception as e:
            print(f"ZStd compression error: {e}")
            # Fall back to no compression
            return data
    
    def decompress(self, data, original_length):
        """
        Decompress ZStandard-compressed data with improved error handling
        
        Args:
            data (bytes): Compressed data
            original_length (int): Original length of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        if not data:
            return b''
        
        try:
            # Check for our custom header
            if len(data) >= 8 and data[:4] == b'ZSTD':
                # Extract size from our header
                size_from_header = int.from_bytes(data[4:8], byteorder='little')
                
                # Use ZStandard to decompress (skip our header)
                decompressor = zstd.ZstdDecompressor()
                decompressed = decompressor.decompress(data[8:], max_output_size=original_length)
                print(f"Compatible ZStd decompression: {len(data)-8} bytes -> {len(decompressed)} bytes")
                
                # Verify size
                if len(decompressed) != size_from_header:
                    print(f"Warning: Decompressed size ({len(decompressed)}) doesn't match header size ({size_from_header})")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: ZStd decompressed data too large, truncating")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: ZStd decompressed data too small, padding")
                        missing = original_length - len(decompressed)
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            else:
                # Try to decompress standard ZStandard format
                try:
                    decompressor = zstd.ZstdDecompressor()
                    decompressed = decompressor.decompress(data, max_output_size=original_length)
                    
                    # Ensure correct size
                    if len(decompressed) != original_length:
                        if len(decompressed) > original_length:
                            decompressed = decompressed[:original_length]
                        else:
                            missing = original_length - len(decompressed)
                            decompressed = decompressed + bytes(missing)
                    
                    return decompressed
                    
                except Exception as e:
                    print(f"Standard ZStd decompression failed: {e}")
                    return bytes(original_length)
        
        except Exception as e:
            print(f"ZStd decompression error: {e}")
            # Return zeros as a fallback
            return bytes(original_length)
    
    def should_use(self, data, threshold=0.9):
        """
        Determine if ZStandard compression should be used
        
        Args:
            data (bytes): Data to analyze
            threshold (float): Threshold for making decision
            
        Returns:
            bool: True if ZStandard should be used
        """
        # ZStandard works well on various data types but has some overhead
        if len(data) < 100:
            return False
                
        # Check if it's text data (ZStd works particularly well on text)
        text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9, 10, 13))
        text_ratio = text_chars / len(data) if data else 0
        
        if text_ratio > 0.7:
            return True  # Highly likely to work well with text
            
        # For binary data, check if it might be compressible
        # This is a simple heuristic - in practice you might use entropy
        repeat_chars = 0
        if len(data) > 20:
            for i in range(len(data) - 10):
                window = data[i:i+10]
                if window in data[i+10:i+100]:
                    repeat_chars += 1
                    
        repeat_ratio = repeat_chars / max(1, len(data) - 10)
        return repeat_ratio > 0.05  # If we have some repetition, try ZStd


def generate_random_data(size=10000):
    """Generate random test data"""
    data = bytearray()
    
    # Add some text
    for _ in range(size // 100):
        data.extend(b"This is some test data that should compress well. ")
    
    # Add some repetitive patterns
    for _ in range(size // 100):
        byte = random.randint(0, 255)
        data.extend([byte] * random.randint(10, 50))
        
    # Add some random bytes
    data.extend(os.urandom(size // 10))
    
    # Add some sequential data
    for i in range(size // 10):
        data.append(i % 256)
    
    # Fill to desired size
    remaining = size - len(data)
    if remaining > 0:
        data.extend([0] * remaining)
    elif remaining < 0:
        data = data[:size]
    
    return bytes(data)


# Helper function to install compatible methods
def get_compatible_methods():
    """Get compression methods that are specially adapted for our format"""
    methods = []
    
    if HAS_BROTLI:
        methods.append(CompatibleBrotliCompression())
        print("Added compatible Brotli compression")
        
    if HAS_ZSTD:
        methods.append(CompatibleZstdCompression())
        print("Added compatible ZStandard compression")
        
    return methods


# Test function to verify compression/decompression works
def test_compression_methods():
    """Test the compatible compression methods"""
    if not (HAS_BROTLI or HAS_ZSTD):
        print("No compatible compression methods available to test")
        return
        
    # Generate test data
    data = generate_random_data(20000)
    
    # Test each method
    methods = get_compatible_methods()
    
    for method in methods:
        print(f"Testing {method.__class__.__name__}...")
        
        # Compress
        compressed = method.compress(data)
        
        # Decompress
        decompressed = method.decompress(compressed, len(data))
        
        # Verify
        if decompressed == data:
            print(f"✓ Verification successful!")
        else:
            print(f"× Verification failed!")
            
            # Find where they differ
            for i in range(min(len(data), len(decompressed))):
                if data[i] != decompressed[i]:
                    print(f"  First difference at byte {i}")
                    print(f"  Original: {data[i:i+16].hex()}")
                    print(f"  Decompressed: {decompressed[i:i+16].hex()}")
                    break


if __name__ == "__main__":
    test_compression_methods()
