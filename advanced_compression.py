import zlib
import bz2
import lzma
import numpy as np
from compression_methods import CompressionMethod
import sys
import os

# Try to import additional compression libraries
try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False
    print("zstd library not available. Zstandard compression will be disabled.")

try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False
    print("lz4 library not available. LZ4 compression will be disabled.")

# Try to import Brotli and LZHAM
try:
    # Check if brotli_lzham_compression.py exists in the current directory
    if os.path.exists("brotli_lzham_compression.py"):
        from brotli_lzham_compression import BrotliCompression, HAS_BROTLI
        if HAS_BROTLI:
            print("Added Brotli compression")
            
        try:
            from brotli_lzham_compression import LZHAMCompression, HAS_LZHAM
            if HAS_LZHAM:
                print("Added LZHAM compression")
        except ImportError:
            HAS_LZHAM = False
    else:
        print("brotli_lzham_compression.py not found in current directory")
        HAS_BROTLI = False
        HAS_LZHAM = False
except ImportError as e:
    print(f"Error importing from brotli_lzham_compression: {e}")
    HAS_BROTLI = False
    HAS_LZHAM = False

class DeflateCompression(CompressionMethod):
    """
    DEFLATE compression method (used in ZIP files)
    """
    @property
    def type_id(self):
        return 5
    
    def compress(self, data):
        """
        Compress using DEFLATE (zlib)
        
        Args:
            data (bytes): Data to compress
            
        Returns:
            bytes: Compressed data
        """
        if not data:
            return b''
        
        # Use zlib with compression level 9 (max compression)
        compressed = zlib.compress(data, level=9)
        print(f"DEFLATE compression: {len(data)} bytes -> {len(compressed)} bytes")
        return compressed
    
    def decompress(self, data, original_length):
        """
        Decompress DEFLATE-compressed data
        
        Args:
            data (bytes): Compressed data
            original_length (int): Original length of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        if not data:
            return b''
        
        try:
            # Use zlib to decompress
            decompressed = zlib.decompress(data)
            print(f"DEFLATE decompression: {len(data)} bytes -> {len(decompressed)} bytes")
            
            # Ensure we have the correct length
            if len(decompressed) != original_length:
                if len(decompressed) > original_length:
                    print(f"Warning: DEFLATE decompressed size ({len(decompressed)}) larger than original ({original_length})")
                    decompressed = decompressed[:original_length]
                else:
                    print(f"Warning: DEFLATE decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                    # Pad with zeros if needed
                    missing = original_length - len(decompressed)
                    decompressed = decompressed + bytes(missing)
            
            return decompressed
        
        except zlib.error as e:
            print(f"DEFLATE decompression error: {e}")
            # Return zeros as a fallback
            return bytes(original_length)
    
    def should_use(self, data, threshold=0.9):
        """
        Determine if DEFLATE compression should be used
        
        Args:
            data (bytes): Data to analyze
            threshold (float): Threshold for making decision
            
        Returns:
            bool: True if DEFLATE should be used
        """
        # DEFLATE works well on most data types
        # For small data chunks, it may not be worth the overhead
        if len(data) < 50:
            return False
            
        # Quick check using entropy - if entropy is high, compression may not help
        entropy = self._calculate_entropy(data)
        
        # If entropy is very high (>7.8), data is likely already compressed or encrypted
        if entropy > 7.8:
            return False
            
        return True
    
    def _calculate_entropy(self, data):
        """Calculate Shannon entropy of the data"""
        if not data:
            return 0.0
            
        # Count byte frequencies
        counts = np.bincount(bytearray(data), minlength=256)
        
        # Calculate probabilities for each byte value
        probabilities = counts / len(data)
        
        # Filter out zero probabilities to avoid log(0)
        probabilities = probabilities[probabilities > 0]
        
        # Calculate entropy: -sum(p * log2(p))
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        return entropy


class Bzip2Compression(CompressionMethod):
    """
    BZIP2 compression method (better compression than DEFLATE, but slower)
    """
    @property
    def type_id(self):
        return 6
    
    def compress(self, data):
        """
        Compress using BZIP2
        
        Args:
            data (bytes): Data to compress
            
        Returns:
            bytes: Compressed data
        """
        if not data:
            return b''
        
        # Use bz2 with compression level 9 (highest)
        compressed = bz2.compress(data, compresslevel=9)
        print(f"BZIP2 compression: {len(data)} bytes -> {len(compressed)} bytes")
        return compressed
    
    def decompress(self, data, original_length):
        """
        Decompress BZIP2-compressed data
        
        Args:
            data (bytes): Compressed data
            original_length (int): Original length of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        if not data:
            return b''
        
        try:
            # Use bz2 to decompress
            decompressed = bz2.decompress(data)
            print(f"BZIP2 decompression: {len(data)} bytes -> {len(decompressed)} bytes")
            
            # Ensure we don't exceed the original length
            if len(decompressed) > original_length:
                print(f"Warning: BZIP2 decompressed size ({len(decompressed)}) larger than original ({original_length})")
                decompressed = decompressed[:original_length]
            elif len(decompressed) < original_length:
                print(f"Warning: BZIP2 decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                # Pad with zeros if needed
                missing = original_length - len(decompressed)
                print(f"Padding with {missing} zero bytes")
                decompressed = decompressed + bytes(missing)
            
            return decompressed
        
        except Exception as e:
            print(f"BZIP2 decompression error: {e}")
            # Return zeros as a fallback
            return bytes(original_length)
    
    def should_use(self, data, threshold=0.9):
        """
        Determine if BZIP2 compression should be used
        
        Args:
            data (bytes): Data to analyze
            threshold (float): Threshold for making decision
            
        Returns:
            bool: True if BZIP2 should be used
        """
        # BZIP2 works best on larger chunks (because of its block size)
        if len(data) < 100:
            return False
            
        # Quick check using entropy - if entropy is high, compression may not help
        entropy = self._calculate_entropy(data)
        
        # If entropy is very high (>7.5), data is likely already compressed or encrypted
        if entropy > 7.5:
            return False
        
        # BZIP2 is most effective for text data
        text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9, 10, 13))
        text_ratio = text_chars / len(data) if data else 0
        
        # If the data is primarily text, bzip2 is a good choice
        if text_ratio > 0.7:
            return True
        
        # For other data, only use if the entropy suggests it's compressible
        return entropy < 6.0
    
    def _calculate_entropy(self, data):
        """Calculate Shannon entropy of the data"""
        if not data:
            return 0.0
            
        # Count byte frequencies
        counts = np.bincount(bytearray(data), minlength=256)
        
        # Calculate probabilities for each byte value
        probabilities = counts / len(data)
        
        # Filter out zero probabilities to avoid log(0)
        probabilities = probabilities[probabilities > 0]
        
        # Calculate entropy: -sum(p * log2(p))
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        return entropy


class LZMACompression(CompressionMethod):
    """
    LZMA compression method (used in 7z files, very high compression ratio)
    """
    @property
    def type_id(self):
        return 7
    
    def compress(self, data):
        """
        Compress using LZMA
        
        Args:
            data (bytes): Data to compress
            
        Returns:
            bytes: Compressed data
        """
        if not data:
            return b''
        
        try:
            # Use lzma with default settings (simpler and more reliable)
            compressed = lzma.compress(data)
            print(f"LZMA compression: {len(data)} bytes -> {len(compressed)} bytes")
            return compressed
        except Exception as e:
            print(f"LZMA compression error: {e}")
            # Fall back to no compression
            return data
    
    def decompress(self, data, original_length):
        """
        Decompress LZMA-compressed data
        
        Args:
            data (bytes): Compressed data
            original_length (int): Original length of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        if not data:
            return b''
        
        try:
            # Use lzma to decompress with standard format
            decompressed = lzma.decompress(data)
            print(f"LZMA decompression: {len(data)} bytes -> {len(decompressed)} bytes")
            
            # Ensure we don't exceed the original length
            if len(decompressed) > original_length:
                print(f"Warning: LZMA decompressed size ({len(decompressed)}) larger than original ({original_length})")
                decompressed = decompressed[:original_length]
            elif len(decompressed) < original_length:
                print(f"Warning: LZMA decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                # Pad with zeros if needed
                missing = original_length - len(decompressed)
                print(f"Padding with {missing} zero bytes")
                decompressed = decompressed + bytes(missing)
            
            return decompressed
        
        except Exception as e:
            print(f"LZMA decompression error: {e}")
            # Return zeros as a fallback
            return bytes(original_length)
    
    def should_use(self, data, threshold=0.9):
        """
        Determine if LZMA compression should be used
        
        Args:
            data (bytes): Data to analyze
            threshold (float): Threshold for making decision
            
        Returns:
            bool: True if LZMA should be used
        """
        # LZMA has high overhead, so not suitable for small chunks
        if len(data) < 1000:
            return False
        
        # Quick check using entropy - if entropy is high, compression may not help
        entropy = self._calculate_entropy(data)
        
        # If entropy is very high (>7.5), data is likely already compressed or encrypted
        if entropy > 7.5:
            return False
        
        # LZMA works best on highly redundant data
        # For very compressible data (low entropy), it's worth the overhead
        return entropy < 5.5
    
    def _calculate_entropy(self, data):
        """Calculate Shannon entropy of the data"""
        if not data:
            return 0.0
            
        # Count byte frequencies
        counts = np.bincount(bytearray(data), minlength=256)
        
        # Calculate probabilities for each byte value
        probabilities = counts / len(data)
        
        # Filter out zero probabilities to avoid log(0)
        probabilities = probabilities[probabilities > 0]
        
        # Calculate entropy: -sum(p * log2(p))
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        return entropy


# Add ZStandard compression if available
if HAS_ZSTD:
    class ZstdCompression(CompressionMethod):
        """
        ZStandard compression method (fast with good compression ratio)
        """
        @property
        def type_id(self):
            return 8
        
        def compress(self, data):
            """
            Compress using ZStandard
            
            Args:
                data (bytes): Data to compress
                
            Returns:
                bytes: Compressed data
            """
            if not data:
                return b''
            
            try:
                # Use ZStandard with high compression level
                compressor = zstd.ZstdCompressor(level=19)  # Maximum compression level
                compressed = compressor.compress(data)
                print(f"ZStd compression: {len(data)} bytes -> {len(compressed)} bytes")
                return compressed
            except Exception as e:
                print(f"ZStd compression error: {e}")
                # Fall back to no compression
                return data
        
        def decompress(self, data, original_length):
            """
            Decompress ZStandard-compressed data
            
            Args:
                data (bytes): Compressed data
                original_length (int): Original length of the uncompressed data
                
            Returns:
                bytes: Decompressed data
            """
            if not data:
                return b''
            
            try:
                # Use ZStandard to decompress
                decompressor = zstd.ZstdDecompressor()
                decompressed = decompressor.decompress(data, max_output_size=original_length)
                print(f"ZStd decompression: {len(data)} bytes -> {len(decompressed)} bytes")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: ZStd decompressed size ({len(decompressed)}) larger than original ({original_length})")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: ZStd decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                        # Pad with zeros if needed
                        missing = original_length - len(decompressed)
                        print(f"Padding with {missing} zero bytes")
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            
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
            # ZStandard works well on all sizes but has some overhead
            if len(data) < 50:
                return False
                
            # Quick check using entropy - if entropy is high, compression may not help
            entropy = self._calculate_entropy(data)
            
            # If entropy is very high (>7.8), data is likely already compressed or encrypted
            if entropy > 7.8:
                return False
                
            return True
        
        def _calculate_entropy(self, data):
            """Calculate Shannon entropy of the data"""
            if not data:
                return 0.0
                
            # Count byte frequencies
            counts = np.bincount(bytearray(data), minlength=256)
            
            # Calculate probabilities for each byte value
            probabilities = counts / len(data)
            
            # Filter out zero probabilities to avoid log(0)
            probabilities = probabilities[probabilities > 0]
            
            # Calculate entropy: -sum(p * log2(p))
            entropy = -np.sum(probabilities * np.log2(probabilities))
            
            return entropy


# Add LZ4 compression if available
if HAS_LZ4:
    class LZ4Compression(CompressionMethod):
        """
        LZ4 compression method (very fast with decent compression ratio)
        """
        @property
        def type_id(self):
            return 9
        
        def compress(self, data):
            """
            Compress using LZ4
            
            Args:
                data (bytes): Data to compress
                
            Returns:
                bytes: Compressed data
            """
            if not data:
                return b''
            
            try:
                # Use LZ4 with high compression level
                compressed = lz4.frame.compress(data, compression_level=9)
                print(f"LZ4 compression: {len(data)} bytes -> {len(compressed)} bytes")
                return compressed
            except Exception as e:
                print(f"LZ4 compression error: {e}")
                # Fall back to no compression
                return data
        
        def decompress(self, data, original_length):
            """
            Decompress LZ4-compressed data
            
            Args:
                data (bytes): Compressed data
                original_length (int): Original length of the uncompressed data
                
            Returns:
                bytes: Decompressed data
            """
            if not data:
                return b''
            
            try:
                # Use LZ4 to decompress
                decompressed = lz4.frame.decompress(data)
                print(f"LZ4 decompression: {len(data)} bytes -> {len(decompressed)} bytes")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: LZ4 decompressed size ({len(decompressed)}) larger than original ({original_length})")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: LZ4 decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                        # Pad with zeros if needed
                        missing = original_length - len(decompressed)
                        print(f"Padding with {missing} zero bytes")
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            
            except Exception as e:
                print(f"LZ4 decompression error: {e}")
                # Return zeros as a fallback
                return bytes(original_length)
        
        def should_use(self, data, threshold=0.9):
            """
            Determine if LZ4 compression should be used
            
            Args:
                data (bytes): Data to analyze
                threshold (float): Threshold for making decision
                
            Returns:
                bool: True if LZ4 should be used
            """
            # LZ4 is very fast and works well on most data
            # For very small data, it may not be efficient
            if len(data) < 32:
                return False
                
            # Quick check using entropy - if entropy is high, compression may not help
            entropy = self._calculate_entropy(data)
            
            # If entropy is very high (>7.8), data is likely already compressed or encrypted
            if entropy > 7.8:
                return False
                
            return True
        
        def _calculate_entropy(self, data):
            """Calculate Shannon entropy of the data"""
            if not data:
                return 0.0
                
            # Count byte frequencies
            counts = np.bincount(bytearray(data), minlength=256)
            
            # Calculate probabilities for each byte value
            probabilities = counts / len(data)
            
            # Filter out zero probabilities to avoid log(0)
            probabilities = probabilities[probabilities > 0]
            
            # Calculate entropy: -sum(p * log2(p))
            entropy = -np.sum(probabilities * np.log2(probabilities))
            
            return entropy