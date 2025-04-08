import numpy as np
from compression_methods import CompressionMethod

# Try to import additional compression libraries
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
    print("brotli library not available. Brotli compression will be disabled.")

try:
    import pylzham
    HAS_LZHAM = True
except ImportError:
    HAS_LZHAM = False
    print("pylzham library not available. LZHAM compression will be disabled.")


# Brotli compression if available
if HAS_BROTLI:
    class BrotliCompression(CompressionMethod):
        """
        Brotli compression method (used by Google for web compression)
        """
        @property
        def type_id(self):
            return 10
        
        def compress(self, data):
            """
            Compress using Brotli
            
            Args:
                data (bytes): Data to compress
                
            Returns:
                bytes: Compressed data
            """
            if not data:
                return b''
            
            try:
                # Use Brotli with quality level 11 (max compression)
                compressed = brotli.compress(data, quality=11)
                print(f"Brotli compression: {len(data)} bytes -> {len(compressed)} bytes")
                return compressed
            except Exception as e:
                print(f"Brotli compression error: {e}")
                # Fall back to no compression
                return data
        
        def decompress(self, data, original_length):
            """
            Decompress Brotli-compressed data
            
            Args:
                data (bytes): Compressed data
                original_length (int): Original length of the uncompressed data
                
            Returns:
                bytes: Decompressed data
            """
            if not data:
                return b''
            
            try:
                # Use Brotli to decompress
                decompressed = brotli.decompress(data)
                print(f"Brotli decompression: {len(data)} bytes -> {len(decompressed)} bytes")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: Brotli decompressed size ({len(decompressed)}) larger than original ({original_length})")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: Brotli decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                        # Pad with zeros if needed
                        missing = original_length - len(decompressed)
                        print(f"Padding with {missing} zero bytes")
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            
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
                
            # Quick check using entropy
            entropy = self._calculate_entropy(data)
            
            # Skip high entropy data
            if entropy > 7.5:
                return False
            
            # Check if it's likely text data
            text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9, 10, 13))
            text_ratio = text_chars / len(data) if data else 0
            
            # Brotli is optimized for text content
            return text_ratio > 0.6
        
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


# LZHAM compression if available
if HAS_LZHAM:
    class LZHAMCompression(CompressionMethod):
        """
        LZHAM compression method (designed for game assets)
        """
        @property
        def type_id(self):
            return 11
        
        def compress(self, data):
            """
            Compress using LZHAM
            
            Args:
                data (bytes): Data to compress
                
            Returns:
                bytes: Compressed data
            """
            if not data:
                return b''
            
            try:
                # Use max compression level
                compressed = pylzham.compress(data, dict_size_log2=23, comp_level=4)
                print(f"LZHAM compression: {len(data)} bytes -> {len(compressed)} bytes")
                return compressed
            except Exception as e:
                print(f"LZHAM compression error: {e}")
                # Fall back to no compression
                return data
        
        def decompress(self, data, original_length):
            """
            Decompress LZHAM-compressed data
            
            Args:
                data (bytes): Compressed data
                original_length (int): Original length of the uncompressed data
                
            Returns:
                bytes: Decompressed data
            """
            if not data:
                return b''
            
            try:
                # Use LZHAM to decompress
                decompressed = pylzham.decompress(data, decompressed_size=original_length)
                print(f"LZHAM decompression: {len(data)} bytes -> {len(decompressed)} bytes")
                
                # Ensure we have the right size
                if len(decompressed) != original_length:
                    if len(decompressed) > original_length:
                        print(f"Warning: LZHAM decompressed size ({len(decompressed)}) larger than original ({original_length})")
                        decompressed = decompressed[:original_length]
                    else:
                        print(f"Warning: LZHAM decompressed size ({len(decompressed)}) smaller than original ({original_length})")
                        # Pad with zeros if needed
                        missing = original_length - len(decompressed)
                        print(f"Padding with {missing} zero bytes")
                        decompressed = decompressed + bytes(missing)
                
                return decompressed
            
            except Exception as e:
                print(f"LZHAM decompression error: {e}")
                # Return zeros as a fallback
                return bytes(original_length)
        
        def should_use(self, data, threshold=0.9):
            """
            Determine if LZHAM compression should be used
            
            Args:
                data (bytes): Data to analyze
                threshold (float): Threshold for making decision
                
            Returns:
                bool: True if LZHAM should be used
            """
            # LZHAM has significant overhead, so not suitable for small chunks
            if len(data) < 2000:
                return False
                
            # Quick check using entropy
            entropy = self._calculate_entropy(data)
            
            # Skip high entropy data
            if entropy > 7.5:
                return False
            
            # LZHAM is good for game assets which often have moderate entropy
            return entropy < 6.5
        
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