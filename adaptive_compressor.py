import os
import time
import struct
import hashlib
import random
from bitarray import bitarray
import numpy as np
import sys
import concurrent.futures
from tqdm import tqdm

from marker_finder import MarkerFinder
from compression_methods import (
    RLECompression, 
    DictionaryCompression, 
    HuffmanCompression, 
    DeltaCompression,
    NoCompression
)

# Try to import our compatibility layer first
try:
    from compression_fix import get_compatible_methods
    COMPATIBLE_METHODS_AVAILABLE = True
except ImportError:
    COMPATIBLE_METHODS_AVAILABLE = False
    print("Compatible compression methods not available")

# Try to import advanced compression methods
try:
    from advanced_compression import (
        DeflateCompression, 
        Bzip2Compression, 
        LZMACompression,
        HAS_ZSTD,
        HAS_LZ4
    )
    
    ADVANCED_METHODS_AVAILABLE = True
    
    if HAS_ZSTD and not COMPATIBLE_METHODS_AVAILABLE:
        from advanced_compression import ZstdCompression
    
    if HAS_LZ4:
        from advanced_compression import LZ4Compression
        
except ImportError as e:
    ADVANCED_METHODS_AVAILABLE = False
    print(f"Error importing advanced compression methods: {e}")

# Try to import Brotli and LZHAM if compatible versions not available
if not COMPATIBLE_METHODS_AVAILABLE:
    try:
        if os.path.exists('brotli_lzham_compression.py'):
            # First try to import Brotli
            try:
                from brotli_lzham_compression import BrotliCompression, HAS_BROTLI
            except (ImportError, AttributeError) as e:
                print(f"Error importing Brotli: {e}")
                HAS_BROTLI = False
                
            # Then try to import LZHAM separately
            try:
                from brotli_lzham_compression import LZHAMCompression, HAS_LZHAM
            except (ImportError, AttributeError) as e:
                print(f"Error importing LZHAM: {e}")
                HAS_LZHAM = False
        else:
            print("brotli_lzham_compression.py not found")
            HAS_BROTLI = False
            HAS_LZHAM = False
    except Exception as e:
        print(f"Error importing Brotli/LZHAM: {e}")
        HAS_BROTLI = False
        HAS_LZHAM = False

class AdaptiveCompressor:
    """
    Enhanced adaptive compression algorithm that dynamically determines
    optimal chunk sizes and compression methods based on data patterns.
    """
    
    # Magic number to identify our compression format (ASCII 'AMBC')
    MAGIC_NUMBER = b'AMBC'
    
    # Format version - increment when format changes
    FORMAT_VERSION = 2
    
    def __init__(self, initial_chunk_size=4096, marker_max_length=32, sample_size=10000, chunk_size=None):
        """
        Initialize the compressor
        
        Args:
            initial_chunk_size (int): Initial chunk size for compression
            marker_max_length (int): Maximum marker length to consider
            sample_size (int): Number of bytes to sample for marker finding
            chunk_size (int, optional): For backward compatibility with old scripts
        """
        # For backward compatibility
        if chunk_size is not None:
            initial_chunk_size = chunk_size
            
        self.initial_chunk_size = initial_chunk_size
        self.marker_finder = MarkerFinder(marker_max_length)
        self.sample_size = sample_size
        
        # Initialize marker properties
        self.marker_bytes = None
        self.marker_length = 0
        self.marker_pattern = ""
        
        # Initialize progress tracking
        self.progress_callback = None
        
        # Initialize multithreading settings
        self.use_multithreading = False
        self.max_workers = max(1, os.cpu_count() - 1)  # Leave one core free
        
        # Initialize compression methods
        self.compression_methods = []
        self._initialize_compression_methods()
        
        # Create lookup dictionary for decompression
        self.method_lookup = {method.type_id: method for method in self.compression_methods}
        
        # Method names for logging
        self.method_names = {
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
    
    def _initialize_compression_methods(self):
        """Initialize all available compression methods"""
        # Always add basic methods
        self.compression_methods.append(RLECompression())
        self.compression_methods.append(DictionaryCompression())
        self.compression_methods.append(HuffmanCompression())
        self.compression_methods.append(DeltaCompression())
        
        # Try to add compatible versions of problematic methods first
        if COMPATIBLE_METHODS_AVAILABLE:
            compatible_methods = get_compatible_methods()
            for method in compatible_methods:
                self.compression_methods.append(method)
        
        # Add advanced methods if available
        if ADVANCED_METHODS_AVAILABLE:
            # Track available method IDs to avoid duplicates
            existing_method_ids = {method.type_id for method in self.compression_methods}
            
            # Add DEFLATE if available
            self.compression_methods.append(DeflateCompression())
            print("Added DEFLATE compression")
            
            # Add BZIP2 if available
            self.compression_methods.append(Bzip2Compression())
            print("Added BZIP2 compression")
            
            # Add LZMA if available
            self.compression_methods.append(LZMACompression())
            print("Added LZMA compression")
            
            # Add ZStandard if available and not already added as compatible version
            if HAS_ZSTD and 8 not in existing_method_ids:
                self.compression_methods.append(ZstdCompression())
                print("Added ZStandard compression")
            
            # Add LZ4 if available
            if HAS_LZ4:
                self.compression_methods.append(LZ4Compression())
                print("Added LZ4 compression")
        
        # Try to add standard Brotli if not already added as compatible version
        existing_method_ids = {method.type_id for method in self.compression_methods}
        if 10 not in existing_method_ids and 'HAS_BROTLI' in globals() and HAS_BROTLI:
            self.compression_methods.append(BrotliCompression())
            print("Added Brotli compression")
        
        # Try to add LZHAM if available
        if 'HAS_LZHAM' in globals() and HAS_LZHAM:
            self.compression_methods.append(LZHAMCompression())
            print("Added LZHAM compression")
        
        # Always add NoCompression as a fallback
        self.compression_methods.append(NoCompression())
        
        print(f"Total compression methods available: {len(self.compression_methods)}")
    
    def enable_multithreading(self, max_workers=None):
        """
        Enable multithreading for compression
        
        Args:
            max_workers (int, optional): Maximum number of worker threads
        """
        self.use_multithreading = True
        if max_workers:
            self.max_workers = max_workers
        print(f"Multithreading enabled with {self.max_workers} workers")
    
    def disable_multithreading(self):
        """Disable multithreading for compression"""
        self.use_multithreading = False
        print("Multithreading disabled")
    
    def set_progress_callback(self, callback):
        """
        Set a callback function for progress updates
        
        Args:
            callback: Function taking (stage_name, current_value, total_value, current_chunk, total_chunks)
        """
        self.progress_callback = callback
    
    def _update_progress(self, stage, current, total, current_chunk=None, total_chunks=None):
        """
        Update progress if a callback is set
        
        Args:
            stage (str): Current stage of processing
            current (int): Current progress value
            total (int): Total expected value
            current_chunk (int, optional): Current chunk number
            total_chunks (int, optional): Total number of chunks
        """
        if self.progress_callback:
            self.progress_callback(stage, current, total, current_chunk, total_chunks)
    
    def _init_marker(self, marker_bytes, marker_length):
        """
        Initialize marker properties for consistent handling
        
        Args:
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
        """
        self.marker_bytes = marker_bytes
        self.marker_length = marker_length
        
        # Extract the actual marker bit pattern
        marker_bits = bitarray()
        marker_bits.frombytes(marker_bytes)
        # Ensure we only use exactly marker_length bits
        marker_bits = marker_bits[:marker_length]
        self.marker_pattern = marker_bits.to01()
        
        # Debug - print the actual pattern as binary and hex
        print(f"Raw marker pattern: {self.marker_pattern}")
        marker_int = int(self.marker_pattern, 2)
        print(f"As integer: {marker_int}, hex: {hex(marker_int)}")
        
        # For consistent handling, calculate the properly aligned marker bytes
        if marker_length <= 8:
            # For small markers (≤8 bits), use one byte with marker bits left-aligned
            marker_int = int(self.marker_pattern, 2) << (8 - marker_length)
            self.marker_bytes_aligned = bytes([marker_int])
            
            # Also create a mask for matching only the relevant bits during decompression
            # Ensure the value stays within the valid byte range (0-255)
            mask_value = (0xFF >> marker_length) << marker_length & 0xFF
            self.marker_mask = bytes([mask_value])
        else:
            # For longer markers, use multiple bytes
            # First pad to full bytes
            padded_bits = bitarray(self.marker_pattern)
            while len(padded_bits) % 8 != 0:
                padded_bits.append(0)  # Pad with zeros
                
            self.marker_bytes_aligned = padded_bits.tobytes()
            self.marker_mask = b'\xFF' * len(self.marker_bytes_aligned)
        
        print(f"Initialized marker: length={marker_length} bits, pattern={self.marker_pattern}, " + 
            f"aligned_bytes={self.marker_bytes_aligned.hex()}")
        
        # Calculate the number of bytes needed for the marker
        self.marker_byte_length = (marker_length + 7) // 8
    
    def compress(self, input_file, output_file):
        """
        Compress a file using the adaptive compression algorithm
        
        Args:
            input_file (str): Path to the input file
            output_file (str): Path to write the compressed file
            
        Returns:
            dict: Compression statistics
        """
        start_time = time.time()
        
        # Read the input file
        with open(input_file, 'rb') as f:
            file_data = f.read()
        
        self._update_progress("Reading File", len(file_data), len(file_data))
        
        # Calculate checksum
        checksum = hashlib.md5(file_data).digest()
        self._update_progress("Calculating Checksum", 1, 1)
        
        # Find a marker that doesn't appear in the file
        self._update_progress("Finding Marker", 0, 1)
        marker_bytes, marker_length = self._find_marker(
            file_data, sample_size=self.sample_size
        )
        self._update_progress("Finding Marker", 1, 1)
        
        # Initialize marker properties
        self._init_marker(marker_bytes, marker_length)
        
        # Create the header
        self._update_progress("Creating Header", 0, 1)
        header = self._create_header(marker_bytes, marker_length, checksum, len(file_data))
        header_size = len(header)
        self._update_progress("Creating Header", 1, 1)
        
        # Compress the file data
        self._update_progress("Compressing Data", 0, len(file_data))
        compressed_data = self._adaptive_compress(file_data, marker_bytes, marker_length)
        self._update_progress("Compressing Data", len(file_data), len(file_data))
        
        # Update the header with compressed size
        header = self._update_header_compressed_size(header, len(compressed_data))
        
        # Update overhead statistics to include header
        if 'overhead_bytes' in self.chunk_stats:
            self.chunk_stats['overhead_bytes'] += header_size
            self.chunk_stats['header_size'] = header_size
        
        # Write the compressed file
        self._update_progress("Writing File", 0, len(header) + len(compressed_data))
        with open(output_file, 'wb') as f:
            f.write(header)
            f.write(compressed_data)
        self._update_progress("Writing File", len(header) + len(compressed_data), len(header) + len(compressed_data))
        
        # Calculate compression stats
        stats = self._calculate_compression_stats(
            len(file_data), len(header) + len(compressed_data), time.time() - start_time
        )
        
        return stats
    
    def decompress(self, input_file, output_file):
        """
        Decompress a file that was compressed using this algorithm
        
        Args:
            input_file (str): Path to the compressed file
            output_file (str): Path to write the decompressed file
            
        Returns:
            dict: Decompression statistics
        """
        start_time = time.time()
        
        # Read the compressed file
        self._update_progress("Reading File", 0, 1)
        with open(input_file, 'rb') as f:
            compressed_data = f.read()
        self._update_progress("Reading File", 1, 1)
        
        # Parse the header
        self._update_progress("Parsing Header", 0, 1)
        try:
            header_info = self._parse_header(compressed_data)
        except Exception as e:
            print(f"Error parsing header: {e}")
            raise ValueError(f"Invalid compressed file format: {e}")
        self._update_progress("Parsing Header", 1, 1)
        
        # Initialize marker properties
        self._init_marker(header_info['marker_bytes'], header_info['marker_length'])
        
        # Extract the compressed data (skip header)
        data_to_decompress = compressed_data[header_info['header_size']:]
        
        print(f"\nDecompression started. File size: {len(compressed_data)} bytes")
        print(f"Header size: {header_info['header_size']} bytes")
        print(f"Marker length: {header_info['marker_length']} bits")
        print(f"Original size: {header_info['original_size']} bytes")
        
        # Decompress the data
        self._update_progress("Decompressing", 0, header_info['original_size'])
        decompressed_data = self._adaptive_decompress(
            data_to_decompress, 
            header_info['marker_bytes'], 
            header_info['marker_length'],
            header_info['original_size']
        )
        self._update_progress("Decompressing", header_info['original_size'], header_info['original_size'])
        
        # Write the decompressed file
        self._update_progress("Writing File", 0, len(decompressed_data))
        with open(output_file, 'wb') as f:
            f.write(decompressed_data)
        self._update_progress("Writing File", len(decompressed_data), len(decompressed_data))
        
        # Verify checksum
        self._update_progress("Verifying Checksum", 0, 1)
        actual_checksum = hashlib.md5(decompressed_data).digest()
        expected_checksum = header_info['checksum']
        
        if actual_checksum != expected_checksum:
            print(f"\nChecksum verification failed!")
            print(f"Expected checksum: {expected_checksum.hex()}")
            print(f"Actual checksum:   {actual_checksum.hex()}")
            print(f"Decompressed size: {len(decompressed_data)}, Original size: {header_info['original_size']}")
            
            raise ValueError("Checksum verification failed! File may be corrupted.")
        self._update_progress("Verifying Checksum", 1, 1)
        
        # Calculate decompression stats
        stats = self._calculate_decompression_stats(
            len(compressed_data), len(decompressed_data), time.time() - start_time
        )
        
        return stats

    def _find_marker(self, file_data, sample_size=None):
        """
        Find a marker that doesn't appear in the file data
        
        Args:
            file_data (bytes): The data to search
            sample_size (int, optional): Size of sample to use
            
        Returns:
            tuple: (marker_bytes, marker_length)
        """
        # If we have a MarkerFinder instance, use it
        if hasattr(self, 'marker_finder') and self.marker_finder:
            return self.marker_finder.find_marker(file_data, sample_size)
            
        # Use our own implementation
        data_to_check = file_data
        if sample_size and len(file_data) > sample_size:
            # Sample evenly throughout the file for better representation
            step = len(file_data) // sample_size
            sampled_data = bytearray()
            for i in range(0, len(file_data), step):
                sampled_data.extend(file_data[i:i+1])
            data_to_check = bytes(sampled_data[:sample_size])
            print(f"Finding marker using {len(data_to_check)} bytes sampled from a {len(file_data)} byte file")
            print(f"Sampling every {step} bytes at {len(data_to_check)} points")
        else:
            print(f"Finding marker in entire file ({len(file_data)} bytes)")
            
        # Start with small markers (fast to check) and increase length if needed
        for marker_length in range(1, 17):  # 1-16 bits
            possible_patterns = 2**marker_length
            print(f"Checking markers of length {marker_length} bits ({possible_patterns} possibilities)")
            
            # Track time for performance monitoring
            check_start_time = time.time()
            
            # Use a sliding window approach for efficiency
            found = np.zeros(possible_patterns, dtype=bool)
            
            # Convert data to bits for easier checking
            bits = bitarray()
            bits.frombytes(data_to_check)
            
            # Check all bit windows of marker_length in the file
            for i in range(len(bits) - marker_length + 1):
                # Extract the window and convert to an integer
                window = bits[i:i+marker_length]
                window_str = window.to01()
                value = int(window_str, 2)
                
                # Mark this pattern as found
                if value < possible_patterns:
                    found[value] = True
            
            # Calculate what percentage of possible patterns were found
            patterns_found = np.sum(found)
            coverage_percent = (patterns_found / possible_patterns) * 100
            
            check_time = time.time() - check_start_time
            print(f"  Found {patterns_found} of {possible_patterns} patterns ({coverage_percent:.2f}%) in {check_time:.4f} seconds")
            
            # Check if any markers weren't found
            for i in range(possible_patterns):
                if not found[i]:
                    # Convert the integer to a bit string
                    marker_str = bin(i)[2:].zfill(marker_length)
                    
                    # Create marker bits
                    marker_bits = bitarray(marker_str)
                    
                    # For small markers, ensure they're in the most significant bits
                    if marker_length <= 8:
                        # Put the marker bits at the start of the first byte
                        # First pad to 8 bits to ensure alignment
                        while len(marker_bits) < 8:
                            marker_bits.append(0)
                        marker_bytes = marker_bits.tobytes()
                    else:
                        # For longer markers, pad to byte boundary
                        padding = 8 - (marker_length % 8) if marker_length % 8 else 0
                        padded_bits = marker_bits + bitarray('0' * padding)
                        marker_bytes = padded_bits.tobytes()
                    
                    elapsed_time = time.time() - check_start_time
                    print(f"Found marker of length {marker_length} bits in {elapsed_time:.4f} seconds")
                    print(f"Marker binary: {marker_str}")
                    print(f"Marker hex: {marker_bytes.hex()}")
                    
                    return marker_bytes, marker_length
                    
        # If we reach here, we couldn't find a marker with reasonable length
        # This is very unlikely, but we handle it by using a very long marker
        print("Could not find a short unique marker - using a 32-bit marker")
        # Use a pattern that's very unlikely to occur in data
        marker_bits = bitarray('11111111111111110000000000000000')  # 16 ones followed by 16 zeros
        return marker_bits.tobytes(), 32
    
    def _create_header(self, marker_bytes, marker_length, checksum, original_size):
        """
        Create the header for the compressed file
        
        Args:
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
            checksum (bytes): MD5 checksum of the original file
            original_size (int): Size of the original file in bytes
            
        Returns:
            bytes: The header
        """
        # Format:
        # [Magic Number: 4 bytes]
        # [Format Version: 1 byte]
        # [Header Size: 4 bytes] - will be filled in later
        # [Marker Length: 1 byte] - in bits
        # [Marker: variable] - padded to byte boundary
        # [Checksum Type: 1 byte] - 1 for MD5
        # [Checksum: 16 bytes] - MD5 digest
        # [Original File Size: 8 bytes]
        # [Compressed File Size: 8 bytes] - will be filled in later
        
        header = bytearray()
        
        # Magic number
        header.extend(self.MAGIC_NUMBER)
        
        # Format version
        header.append(self.FORMAT_VERSION)
        
        # Header size placeholder (will be filled in later)
        header.extend(b'\x00\x00\x00\x00')
        
        # Marker length (in bits)
        header.append(marker_length)
        
        # Marker bytes (padded to byte boundary)
        header.extend(marker_bytes)
        
        # Checksum type (1 = MD5)
        header.append(1)
        
        # Checksum (MD5 = 16 bytes)
        header.extend(checksum)
        
        # Original file size
        header.extend(struct.pack('<Q', original_size))
        
        # Compressed file size placeholder (will be filled in later)
        header.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # Calculate header size and update the placeholder
        header_size = len(header)
        header[5:9] = struct.pack('<I', header_size)
        
        return bytes(header)
    
    def _update_header_compressed_size(self, header, compressed_size):
        """
        Update the header with the compressed file size
        
        Args:
            header (bytes): The original header
            compressed_size (int): The size of the compressed data
            
        Returns:
            bytes: The updated header
        """
        header = bytearray(header)
        
        # Update compressed file size
        # It's located at the end of the header (last 8 bytes)
        header[-8:] = struct.pack('<Q', compressed_size)
        
        return bytes(header)
    
    def _parse_header(self, compressed_data):
        """
        Parse the header from the compressed file
        
        Args:
            compressed_data (bytes): The compressed file data
            
        Returns:
            dict: Header information
        """
        # Check magic number
        if compressed_data[:4] != self.MAGIC_NUMBER:
            raise ValueError("Invalid file format: Magic number doesn't match")
        
        # Read format version
        format_version = compressed_data[4]
        if format_version > self.FORMAT_VERSION:
            raise ValueError(f"Unsupported format version: {format_version}")
        
        # Read header size
        header_size = struct.unpack('<I', compressed_data[5:9])[0]
        
        # Read marker length
        marker_length = compressed_data[9]
        
        # Calculate marker bytes size (rounded up to the nearest byte)
        marker_bytes_size = (marker_length + 7) // 8
        
        # Read marker bytes
        marker_bytes = compressed_data[10:10+marker_bytes_size]
        
        # Read checksum type
        checksum_type = compressed_data[10+marker_bytes_size]
        
        # Read checksum
        checksum_size = 16 if checksum_type == 1 else 0  # Only MD5 supported for now
        checksum = compressed_data[11+marker_bytes_size:11+marker_bytes_size+checksum_size]
        
        # Read original file size
        original_size_pos = 11 + marker_bytes_size + checksum_size
        original_size = struct.unpack('<Q', compressed_data[original_size_pos:original_size_pos+8])[0]
        
        # Read compressed file size
        compressed_size_pos = original_size_pos + 8
        compressed_size = struct.unpack('<Q', compressed_data[compressed_size_pos:compressed_size_pos+8])[0]
        
        return {
            'format_version': format_version,
            'header_size': header_size,
            'marker_length': marker_length,
            'marker_bytes': marker_bytes,
            'checksum_type': checksum_type,
            'checksum': checksum,
            'original_size': original_size,
            'compressed_size': compressed_size
        }
    
    def _adaptive_compress(self, file_data, marker_bytes, marker_length):
        """
        Compress the file data using adaptive methods
        
        Args:
            file_data (bytes): The data to compress
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
            
        Returns:
            bytes: Compressed data
        """
        # Store the marker for later use during decompression
        self.marker_bytes = marker_bytes
        self.marker_length = marker_length
        
        # Statistics
        self.chunk_stats = {
            'total_chunks': 0,
            'compressed_chunks': 0,
            'raw_chunks': 0,
            'method_usage': {method.type_id: 0 for method in self.compression_methods},
            'bytes_saved': 0,
            'original_size': len(file_data),
            'compressed_size_without_overhead': 0,
            'overhead_bytes': 0
        }
        
        print(f"\nAdaptive compression started for {len(file_data)} bytes")
        print(f"Using marker of length {marker_length} bits: {marker_bytes.hex()}")
        
        # Process the file with dynamic chunk sizing
        position = 0
        compressed = bytearray()
        chunks = []
        total_chunks_estimate = (len(file_data) + self.initial_chunk_size - 1) // self.initial_chunk_size
        
        print(f"Starting adaptive chunk determination...")
        
        # First pass: determine optimal chunks
        with tqdm(total=len(file_data), desc="Analyzing data", unit="B", unit_scale=True) as pbar:
            while position < len(file_data):
                # Determine optimal chunk size and method for this position
                chunk_size, best_method_id = self._determine_optimal_chunk(file_data, position)
                
                # Store chunk information
                chunks.append((position, chunk_size, best_method_id))
                
                # Update progress
                position += chunk_size
                pbar.update(chunk_size)
        
        # Second pass: process chunks with the determined methods
        if self.use_multithreading and len(chunks) > 1:
            print(f"Processing {len(chunks)} chunks with multithreading ({self.max_workers} workers)")
            compressed_chunks = self._compress_chunks_parallel(file_data, chunks, marker_bytes, marker_length)
        else:
            print(f"Processing {len(chunks)} chunks sequentially")
            compressed_chunks = self._compress_chunks_sequential(file_data, chunks, marker_bytes, marker_length)
        
        # Combine results
        for i, chunk_data in enumerate(compressed_chunks):
            compressed.extend(chunk_data)
            
            # Update progress
            self._update_progress("Compressing", i+1, len(chunks), current_chunk=i+1, total_chunks=len(chunks))
        
        # Add end marker
        end_package = self._create_end_package()
        compressed.extend(end_package)
        self.chunk_stats['overhead_bytes'] += len(end_package)
        
        # Print summary
        print(f"\nCompression completed: {len(file_data)} bytes → {len(compressed)} bytes")
        print(f"Total chunks: {self.chunk_stats['total_chunks']}")
        print(f"  Compressed chunks: {self.chunk_stats['compressed_chunks']}")
        print(f"  Raw chunks: {self.chunk_stats['raw_chunks']}")
        
        # Print method usage summary
        for method_id, count in self.chunk_stats['method_usage'].items():
            if count > 0:
                method_name = self.method_names.get(method_id, f"Method {method_id}")
                if self.chunk_stats['compressed_chunks'] > 0:
                    percent = count/self.chunk_stats['compressed_chunks']*100
                    print(f"  {method_name}: {count} chunks ({percent:.1f}% of compressed)")
                else:
                    print(f"  {method_name}: {count} chunks")
        
        return bytes(compressed)
    
    def _determine_optimal_chunk(self, data, position):
        """
        Dynamically determine the optimal chunk size and compression method
        
        Args:
            data (bytes): The data to analyze
            position (int): Current position in the data
            
        Returns:
            tuple: (optimal_chunk_size, best_method_id)
        """
        # Start with initial chunk size
        base_size = self.initial_chunk_size
        max_size = min(65536, len(data) - position)  # Cap at 64KB or remaining data
        
        # If there's less data left than base size, just use what's left
        if max_size <= base_size:
            # For small remaining chunks, we'll just do a quick analysis
            chunk = data[position:position + max_size]
            method_ids = self._predict_best_methods(chunk, max_methods=2)
            
            # Test the predicted methods
            best_method_id = 255  # Default to no compression
            best_ratio = 1.0
            
            for method_id in method_ids:
                method = self.method_lookup.get(method_id)
                if method and method.should_use(chunk):
                    try:
                        compressed = method.compress(chunk)
                        ratio = len(compressed) / len(chunk)
                        if ratio < best_ratio:
                            best_ratio = ratio
                            best_method_id = method_id
                    except Exception as e:
                        print(f"Error testing method {method_id}: {e}")
            
            return max_size, best_method_id
        
        # Start with base size
        current_size = base_size
        best_method_id = None
        best_ratio = 1.0
        best_size = current_size
        
        # First, test the initial chunk size
        chunk = data[position:position + current_size]
        
        # Predict best methods for this chunk
        method_ids = self._predict_best_methods(chunk, max_methods=3)
        
        # Test the predicted best methods
        for method_id in method_ids:
            method = self.method_lookup.get(method_id)
            if method and method.should_use(chunk):
                try:
                    compressed = method.compress(chunk)
                    ratio = len(compressed) / current_size
                    
                    if ratio < best_ratio:
                        best_ratio = ratio
                        best_method_id = method_id
                        best_size = current_size
                except Exception as e:
                    print(f"Error testing method {method_id}: {e}")
                    continue
        
        # If we found a promising method, try extending the chunk
        if best_method_id is not None and best_ratio < 0.95:  # More conservative ratio threshold
            # Choose increment based on data size
            size_increment = max(1024, base_size // 4)  # At least 1KB, or 1/4 of base size
            
            # Keep track of best size seen so far
            best_extended_ratio = best_ratio
            best_extended_size = best_size
            
            # Test larger sizes
            for extended_size in range(current_size + size_increment, max_size + 1, size_increment):
                # Try increasing chunk size
                next_chunk = data[position:position + extended_size]
                method = self.method_lookup.get(best_method_id)
                
                if not method.should_use(next_chunk):
                    break
                    
                try:
                    extended_compressed = method.compress(next_chunk)
                    extended_ratio = len(extended_compressed) / extended_size
                    
                    # Stop extending if compression efficiency drops significantly
                    if extended_ratio > best_extended_ratio * 1.03:  # Allow only 3% degradation
                        break
                    
                    # Update best extended size if it improved or stayed relatively stable
                    best_extended_ratio = extended_ratio
                    best_extended_size = extended_size
                except Exception:
                    break
            
            return best_extended_size, best_method_id
        else:
            # If no good compression found, use raw data with base size
            # This is more predictable than using varying chunk sizes for uncompressed data
            return base_size, 255  # No compression
    
    def _predict_best_methods(self, data, max_methods=3):
        """
        Analytically predict which compression methods are likely to work best
        
        Args:
            data (bytes): Data to analyze
            max_methods (int): Maximum number of methods to return
            
        Returns:
            list: List of method IDs, ordered by predicted effectiveness
        """
        # Calculate metrics for this data
        entropy = self._calculate_entropy(data)
        repetition_score = self._calculate_repetition_score(data)
        variation_score = self._calculate_variation_score(data)
        text_score = self._calculate_text_score(data)
        
        # If entropy is very high, data may be uncompressible or already compressed
        if entropy > 7.8:
            return [255]  # No compression
        
        # Score each method based on data characteristics
        method_scores = {}
        
        # Prioritize safer methods that we know decompress well
        
        # RLE works best with high repetition
        method_scores[1] = 10.0 * repetition_score - entropy * 1.0
        
        # Dictionary works best with text and moderate repetition
        method_scores[2] = 8.0 * text_score + 4.0 * repetition_score - entropy * 0.8
        
        # Huffman works best with skewed frequency distribution
        method_scores[3] = 10.0 - entropy * 1.2
        
        # Delta works best with small variations
        method_scores[4] = 10.0 * variation_score - entropy * 0.7
        
        # DEFLATE works well on most data
        method_scores[5] = 7.0 - entropy * 0.8 + text_score * 3.0
        
        # BZIP2 works best on text
        method_scores[6] = 7.5 * text_score - entropy * 0.6
        
        # LZMA works best on highly structured data
        method_scores[7] = 6.0 - entropy * 0.6 + repetition_score * 2.0
        
        # ZStandard - balanced for text and binary
        method_scores[8] = 6.0 - entropy * 0.7 + text_score * 2.0 + repetition_score * 2.0
        
        # LZ4 - fastest with decent compression
        method_scores[9] = 5.0 - entropy * 0.6 + repetition_score * 1.5
        
        # Brotli - good for text
        method_scores[10] = 7.0 * text_score - entropy * 0.5
        
        # LZHAM - good for binary data
        method_scores[11] = 5.0 - entropy * 0.6 + (1.0 - text_score) * 3.0
        
        # Get available methods from the compressor
        available_methods = {method.type_id for method in self.compression_methods}
        
        # Adjust scoring based on safety of methods
        for method_id in available_methods:
            # Safer/more reliable methods get a bonus
            if method_id in [1, 2, 3, 4, 6]:  # RLE, Dictionary, Huffman, Delta, BZIP2
                method_scores[method_id] = method_scores.get(method_id, 0) + 2.0
                
            # Methods that have had issues get a penalty if they're not the compatible versions
            # Assume compatible versions start with method ID 100+
            if method_id in [8, 10]:  # ZStandard, Brotli
                compatible_ids = [m.type_id for m in self.compression_methods if hasattr(m, '__class__') and 
                                 ('Compatible' in m.__class__.__name__)]
                if method_id not in compatible_ids:
                    method_scores[method_id] = method_scores.get(method_id, 0) - 3.0
                
        # Filter out methods that aren't available
        method_scores = {k: v for k, v in method_scores.items() if k in available_methods}
        
        # Sort methods by score (highest first)
        sorted_methods = sorted(method_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Add NoCompression as a fallback if needed
        result = [method_id for method_id, _ in sorted_methods[:max_methods]]
        if 255 not in result:
            result.append(255)
        
        return result
    
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
    
    def _calculate_repetition_score(self, data):
        """
        Calculate repetition score (0.0-1.0)
        A higher score means more repeated sequences
        """
        if len(data) < 4:
            return 0.0
        
        # Sample the data if it's large
        if len(data) > 1000:
            sample_step = len(data) // 1000
            sampled_data = bytearray()
            for i in range(0, len(data), sample_step):
                sampled_data.extend(data[i:i+1])
            data = bytes(sampled_data[:1000])
        
        repeats = 0
        for i in range(len(data) - 1):
            if data[i] == data[i+1]:
                repeats += 1
        
        return repeats / (len(data) - 1)
    
    def _calculate_variation_score(self, data):
        """
        Calculate small variation score (0.0-1.0)
        A higher score means more small variations between adjacent bytes
        """
        if len(data) < 4:
            return 0.0
        
        # Sample the data if it's large
        if len(data) > 1000:
            sample_step = len(data) // 1000
            sampled_data = bytearray()
            for i in range(0, len(data), sample_step):
                sampled_data.extend(data[i:i+1])
            data = bytes(sampled_data[:1000])
        
        small_deltas = 0
        for i in range(len(data) - 1):
            delta = abs(data[i] - data[i+1])
            if delta < 32:  # Small delta
                small_deltas += 1
        
        return small_deltas / (len(data) - 1)
    
    def _calculate_text_score(self, data):
        """
        Calculate how likely this is text data (0.0-1.0)
        A higher score means more printable ASCII characters
        """
        if not data:
            return 0.0
            
        # Sample the data if it's large
        if len(data) > 1000:
            sample_step = len(data) // 1000
            sampled_data = bytearray()
            for i in range(0, len(data), sample_step):
                sampled_data.extend(data[i:i+1])
            data = bytes(sampled_data[:1000])
        
        text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9, 10, 13))
        return text_chars / len(data)
    
    def _compress_chunks_sequential(self, file_data, chunks, marker_bytes, marker_length):
        """
        Compress chunks sequentially
        
        Args:
            file_data (bytes): Original file data
            chunks (list): List of (position, size, method_id) tuples
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
            
        Returns:
            list: List of compressed chunks
        """
        results = []
        total_chunks = len(chunks)
        
        for chunk_index, (position, size, method_id) in enumerate(chunks):
            # Get the chunk data
            chunk_data = file_data[position:position + size]
            
            # Update progress
            self._update_progress("Compressing", position, len(file_data), 
                                 current_chunk=chunk_index+1, total_chunks=total_chunks)
            
            # Process this chunk
            package_data, stats = self._process_chunk(
                chunk_data, method_id, chunk_index, total_chunks
            )
            
            # Update statistics
            self.chunk_stats['total_chunks'] += 1
            
            if stats['compressed']:
                self.chunk_stats['compressed_chunks'] += 1
                self.chunk_stats['method_usage'][stats['method_id']] += 1
                self.chunk_stats['compressed_size_without_overhead'] += stats['compressed_size']
                self.chunk_stats['overhead_bytes'] += stats['overhead']
                self.chunk_stats['bytes_saved'] += stats['bytes_saved']
            else:
                self.chunk_stats['raw_chunks'] += 1
            
            # Add to results
            results.append(package_data)
        
        return results
    
    def _compress_chunks_parallel(self, file_data, chunks, marker_bytes, marker_length):
        """
        Compress chunks in parallel using multithreading
        
        Args:
            file_data (bytes): Original file data
            chunks (list): List of (position, size, method_id) tuples
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
            
        Returns:
            list: List of compressed chunks
        """
        results = [None] * len(chunks)
        total_chunks = len(chunks)
        
        # Create a progress bar
        progress_bar = tqdm(total=total_chunks, desc="Processing chunks", unit="chunk")
        
        def process_chunk_with_update(chunk_index):
            """Process a chunk and update progress"""
            position, size, method_id = chunks[chunk_index]
            chunk_data = file_data[position:position + size]
            
            # Process the chunk
            package_data, stats = self._process_chunk(
                chunk_data, method_id, chunk_index, total_chunks
            )
            
            # Update progress bar
            progress_bar.update(1)
            
            # Update overall progress if callback is set
            if self.progress_callback:
                processed_chunks = chunk_index + 1
                self._update_progress("Compressing", processed_chunks, total_chunks, 
                                     current_chunk=processed_chunks, total_chunks=total_chunks)
            
            return chunk_index, package_data, stats
        
        # Use ThreadPoolExecutor to process chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chunks for processing
            futures = [
                executor.submit(process_chunk_with_update, i) 
                for i in range(total_chunks)
            ]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    chunk_index, package_data, stats = future.result()
                    results[chunk_index] = package_data
                    
                    # Update statistics - we need a lock here in a real implementation
                    self.chunk_stats['total_chunks'] += 1
                    
                    if stats['compressed']:
                        self.chunk_stats['compressed_chunks'] += 1
                        self.chunk_stats['method_usage'][stats['method_id']] += 1
                        self.chunk_stats['compressed_size_without_overhead'] += stats['compressed_size']
                        self.chunk_stats['overhead_bytes'] += stats['overhead']
                        self.chunk_stats['bytes_saved'] += stats['bytes_saved']
                    else:
                        self.chunk_stats['raw_chunks'] += 1
                    
                except Exception as e:
                    print(f"Error in chunk processing: {e}")
        
        # Close the progress bar
        progress_bar.close()
        
        return results
    
    def _process_chunk(self, chunk_data, method_id, chunk_index, total_chunks):
        """
        Process a single chunk with the specified method
        
        Args:
            chunk_data (bytes): The chunk data
            method_id (int): Method ID to use for compression
            chunk_index (int): The index of this chunk
            total_chunks (int): Total number of chunks
            
        Returns:
            tuple: (compressed_data, stats_dict)
        """
        # Stats for this chunk
        stats = {
            'compressed': False,
            'method_id': None,
            'original_size': len(chunk_data),
            'compressed_size': len(chunk_data),
            'overhead': 0,
            'bytes_saved': 0
        }
        
        # If method_id is 255 (NoCompression) or not available, use raw data
        if method_id == 255 or method_id not in self.method_lookup:
            stats['method_id'] = 255
            
            # Log details for significant chunks
            if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                print(f"Chunk {chunk_index+1}/{total_chunks} processed: {len(chunk_data)} bytes (no compression)")
            
            # Return raw data
            return chunk_data, stats
        
        # Get the compression method
        method = self.method_lookup[method_id]
        
        # Try to compress with the specified method
        try:
            compressed_data = method.compress(chunk_data)
            
            # Calculate overhead for the new package format
            overhead = self._calculate_package_overhead(original_length=len(chunk_data))
            
            # Only use compression if it actually saves space
            if len(compressed_data) + overhead < len(chunk_data):
                # Create compression package
                package = self._create_package(
                    method_id, 
                    compressed_data, 
                    len(chunk_data)
                )
                
                # Update stats
                stats['compressed'] = True
                stats['method_id'] = method_id
                stats['compressed_size'] = len(compressed_data)
                stats['overhead'] = overhead
                stats['bytes_saved'] = len(chunk_data) - (len(compressed_data) + overhead)
                
                # Log details for significant chunks
                if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                    method_name = self.method_names.get(method_id, f"Method {method_id}")
                    ratio = (len(compressed_data) + overhead) / len(chunk_data)
                    print(f"Chunk {chunk_index+1}/{total_chunks} processed:")
                    print(f"  Size: {len(chunk_data)} bytes → {len(compressed_data)} bytes (saved {stats['bytes_saved']} bytes)")
                    print(f"  Method: {method_name} (ratio: {ratio:.4f})")
                
                # Return the package and stats
                return package, stats
            else:
                # Compression not effective, use raw data
                stats['method_id'] = 255
                
                # Log details for significant chunks
                if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                    print(f"Chunk {chunk_index+1}/{total_chunks} processed:")
                    print(f"  Size: {len(chunk_data)} bytes (compression not effective - using raw data)")
                
                # Return raw data
                return chunk_data, stats
                
        except Exception as e:
            # Compression error, use raw data
            print(f"Error compressing chunk {chunk_index} with method {method_id}: {e}")
            stats['method_id'] = 255
            
            # Return raw data
            return chunk_data, stats
    
    def _create_package(self, package_type, data, original_length):
        """
        Create a package with simpler structure and better marker handling
        
        Args:
            package_type (int): Type of compression used
            data (bytes): Compressed data
            original_length (int): Original length of the data
            
        Returns:
            bytes: The compression package
        """
        # The package format is:
        # [marker (1-4 bytes)] [type (1 byte)] [original_length (variable)] [data_length (variable)] [data]
        
        package = bytearray()
        
        # Start marker
        package.extend(self.marker_bytes_aligned)
        
        # Package type
        package.append(package_type)
        
        # Variable-length encoding for original length
        self._encode_variable_length(package, original_length)
        
        # Variable-length encoding for data length
        self._encode_variable_length(package, len(data))
        
        # Compressed data
        package.extend(data)
        
        # Debug output
        marker_hex = self.marker_bytes_aligned.hex()
        print(f"Created package: marker={marker_hex}, type={package_type}, " +
            f"data_len={len(data)}, orig_len={original_length}, " +
            f"package_size={len(package)} bytes")
        
        return bytes(package)
    
    def _create_end_package(self):
        """
        Create an end package
        
        Returns:
            bytes: The end package
        """
        package = bytearray()
        
        # Start marker
        package.extend(self.marker_bytes_aligned)
        
        # Package type 0 (end) - immediately after the marker
        package.append(0)
        
        print(f"Created END package: marker={self.marker_bytes_aligned.hex()}, type=0")
        
        return bytes(package)
    
    def _encode_variable_length(self, buffer, value):
        """
        Encode a variable-length integer into the buffer
        
        Args:
            buffer (bytearray): Buffer to append to
            value (int): Value to encode
        """
        if value < 128:
            buffer.append(value)  # Single byte with MSB=0
        elif value < 16384:  # 2^14
            buffer.append(0x80 | (value & 0x7F))  # First 7 bits with MSB=1
            buffer.append((value >> 7) & 0x7F)    # Next 7 bits with MSB=0
        elif value < 2097152:  # 2^21
            buffer.append(0x80 | (value & 0x7F))        # First 7 bits with MSB=1
            buffer.append(0x80 | ((value >> 7) & 0x7F))  # Next 7 bits with MSB=1
            buffer.append((value >> 14) & 0x7F)         # Final 7 bits with MSB=0
        else:
            buffer.append(0x80 | (value & 0x7F))         # First 7 bits with MSB=1
            buffer.append(0x80 | ((value >> 7) & 0x7F))  # Next 7 bits with MSB=1
            buffer.append(0x80 | ((value >> 14) & 0x7F)) # Next 7 bits with MSB=1
            buffer.append((value >> 21) & 0x7F)         # Final 7 bits with MSB=0
    
    def _read_variable_length_int(self, data, position):
        """
        Read a variable-length integer from the data
        
        Args:
            data (bytes): The data to read from
            position (int): The position to start reading from
            
        Returns:
            tuple: (value, new_position)
        """
        if position >= len(data):
            return 0, position
        
        # Read the first byte
        first_byte = data[position]
        position += 1
        
        # If MSB is 0, this is a single byte value
        if (first_byte & 0x80) == 0:
            return first_byte, position
        
        # This is a multi-byte value
        value = first_byte & 0x7F  # Remove the MSB
        shift = 7
        num_bytes = 1
        
        # Read subsequent bytes until we hit one with MSB=0
        while position < len(data) and num_bytes < 4:  # Maximum 4 bytes
            num_bytes += 1
            byte = data[position]
            position += 1
            
            if (byte & 0x80) == 0:  # Last byte (MSB=0)
                value = value | (byte << shift)
                break
            else:
                value = value | ((byte & 0x7F) << shift)
                shift += 7
        
        return value, position
    
    def _calculate_package_overhead(self, original_length=0):
        """
        Calculate the overhead for a compression package
        
        Args:
            original_length (int): Original length (for variable-length calculation)
            
        Returns:
            int: Overhead in bytes
        """
        # Marker bytes
        marker_byte_length = len(self.marker_bytes_aligned)
        
        # Package type (1 byte)
        overhead = marker_byte_length + 1
        
        # Variable-length encoding for original length
        if original_length < 128:
            overhead += 1
        elif original_length < 16384:
            overhead += 2
        elif original_length < 2097152:
            overhead += 3
        else:
            overhead += 4
            
        # Variable-length encoding for data length (will be same size category as original)
        if original_length < 128:
            overhead += 1
        elif original_length < 16384:
            overhead += 2
        elif original_length < 2097152:
            overhead += 3
        else:
            overhead += 4
            
        return overhead
    
    def _adaptive_decompress(self, compressed_data, marker_bytes, marker_length, original_size):
        """
        Decompress data with simplified logic and better error handling
        
        Args:
            compressed_data (bytes): The compressed data
            marker_bytes (bytes): The marker as bytes
            marker_length (int): Length of the marker in bits
            original_size (int): The original size of the uncompressed data
            
        Returns:
            bytes: Decompressed data
        """
        decompressed = bytearray()
        
        print(f"\nAdaptive decompression started for {len(compressed_data)} bytes")
        print(f"Using marker of length {marker_length} bits: {marker_bytes.hex()}")
        print(f"Using aligned marker bytes: {self.marker_bytes_aligned.hex()}")
        print(f"Expected original size: {original_size} bytes")
        
        # Calculate number of bytes needed for the marker
        marker_size = len(self.marker_bytes_aligned)
        
        # Process data sequentially
        pos = 0
        found_packages = 0
        
        while pos < len(compressed_data):
            # Look for marker
            marker_pos = -1
            for i in range(pos, len(compressed_data) - marker_size + 1):
                if compressed_data[i:i+marker_size] == self.marker_bytes_aligned:
                    marker_pos = i
                    break
            
            if marker_pos == -1:
                # No more markers found
                if pos < len(compressed_data):
                    # Add remaining data as raw
                    remaining = len(compressed_data) - pos
                    print(f"Adding {remaining} bytes of trailing raw data")
                    decompressed.extend(compressed_data[pos:])
                break
            
            # If there's raw data before the marker, add it
            if marker_pos > pos:
                raw_size = marker_pos - pos
                print(f"Adding {raw_size} bytes of raw data")
                decompressed.extend(compressed_data[pos:marker_pos])
            
            # Skip past marker
            pos = marker_pos + marker_size
            
            # Ensure we have at least one byte for the package type
            if pos >= len(compressed_data):
                print("Incomplete package: missing type")
                break
                
            # Read package type
            package_type = compressed_data[pos]
            pos += 1
            
            # Check for end marker
            if package_type == 0:
                print(f"End package found at position {marker_pos}")
                break
                
            # Ensure package type is valid
            if not (1 <= package_type <= 11 or package_type == 255):
                print(f"Invalid package type {package_type}, treating as raw data")
                # Treat this as a false positive marker - add the marker and continue
                decompressed.extend(self.marker_bytes_aligned)
                decompressed.append(package_type)
                continue
                
            # Read variable-length fields
            try:
                # Read original length
                if pos >= len(compressed_data):
                    print("Incomplete package: missing original length")
                    break
                original_length, pos = self._read_variable_length_int(compressed_data, pos)
                
                # Read data length
                if pos >= len(compressed_data):
                    print("Incomplete package: missing data length")
                    break
                data_length, pos = self._read_variable_length_int(compressed_data, pos)
                
                # Check if we have enough data
                if pos + data_length > len(compressed_data):
                    print(f"Incomplete package: expected {data_length} bytes, only {len(compressed_data) - pos} available")
                    # Add what we have as raw data and continue
                    decompressed.extend(compressed_data[pos:])
                    break
                
                # Extract compressed data
                data = compressed_data[pos:pos + data_length]
                pos += data_length
                
                # Get method name for logging
                method_name = self.method_names.get(package_type, f"Unknown ({package_type})")
                print(f"Processing package: type={method_name}, length={data_length}, original={original_length}")
                
                found_packages += 1
                
                # Decompress the chunk
                try:
                    method = self.method_lookup.get(package_type)
                    if method:
                        decompressed_chunk = method.decompress(data, original_length)
                        decompressed.extend(decompressed_chunk)
                    else:
                        print(f"Unknown compression method {package_type}")
                        # If we don't know the method, treat data as raw
                        decompressed.extend(bytes(original_length))
                except Exception as e:
                    print(f"Error decompressing with method {package_type}: {e}")
                    # On error, add zeros for the expected length
                    decompressed.extend(bytes(original_length))
            except Exception as e:
                print(f"Error parsing package: {e}")
                # Move past this position and try to find next marker
                pos = marker_pos + marker_size + 1
        
        print(f"Processed {found_packages} packages")
        
        # Verify the decompressed data length
        if len(decompressed) != original_size:
            print(f"WARNING: Decompressed size ({len(decompressed)}) doesn't match original size ({original_size})")
            if len(decompressed) < original_size:
                # Pad with zeros to match expected size
                padding = original_size - len(decompressed)
                print(f"Padding with {padding} zero bytes")
                decompressed.extend(bytes(padding))
            else:
                # Truncate to expected size
                print(f"Truncating {len(decompressed) - original_size} excess bytes")
                decompressed = decompressed[:original_size]
        
        print(f"Decompression completed: {len(compressed_data)} bytes → {len(decompressed)} bytes")
        
        return bytes(decompressed)
        
    def _validate_marker_position(self, data, pos):
        """
        Validate if a marker position is likely the start of a valid package
        
        Args:
            data (bytes): The data to search
            pos (int): The position of the potential marker
            
        Returns:
            bool: True if this appears to be a valid package marker
        """
        marker_size = len(self.marker_bytes_aligned)
        
        # Make sure we have enough data for at least a marker + package type
        if pos + marker_size >= len(data):
            return False
            
        # Read the potential package type (byte after marker)
        pkg_type = data[pos + marker_size]
        
        # Check if it's an end marker (type 0)
        if pkg_type == 0:
            return True
            
        # Check package type is in a valid range (1-11 or 255)
        if not (1 <= pkg_type <= 11 or pkg_type == 255):
            return False
            
        # For more validation, we could check:
        # 1. If pos + marker_size + 1 + expected_overhead is within data length
        # 2. If there appears to be another marker at an expected position
        
        return True
    
    def _calculate_compression_stats(self, original_size, compressed_size, elapsed_time):
        """
        Calculate compression statistics
        
        Args:
            original_size (int): Size of the original file
            compressed_size (int): Size of the compressed file
            elapsed_time (float): Elapsed time in seconds
            
        Returns:
            dict: Compression statistics
        """
        if original_size == 0:
            ratio = 1.0
            percent_reduction = 0.0
        else:
            ratio = compressed_size / original_size
            percent_reduction = (1.0 - ratio) * 100.0
        
        throughput = original_size / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0
        
        # Calculate details about compression efficiency
        if 'compressed_chunks' in self.chunk_stats and self.chunk_stats['compressed_chunks'] > 0:
            # If we have any compressed chunks
            compressed_data_size = self.chunk_stats.get('compressed_size_without_overhead', 0)
            overhead = self.chunk_stats.get('overhead_bytes', 0)
            
            # Calculate actual compression ratio for just the compressed portions
            original_compressed_size = 0
            for method_id, count in self.chunk_stats['method_usage'].items():
                if method_id != 255 and count > 0:  # Exclude NoCompression
                    # Approximation - we don't track exact size per method
                    method_chunk_size = original_size * (count / self.chunk_stats['total_chunks'])
                    original_compressed_size += method_chunk_size
                    
            if original_compressed_size > 0:
                compression_efficiency = compressed_data_size / original_compressed_size
            else:
                compression_efficiency = 1.0
        else:
            # Nothing was compressed
            compression_efficiency = 1.0
            overhead = compressed_size - original_size
            
        stats = {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': ratio,
            'percent_reduction': percent_reduction,
            'elapsed_time': elapsed_time,
            'throughput_mb_per_sec': throughput,
            'chunk_stats': self.chunk_stats,
            'overhead_bytes': self.chunk_stats.get('overhead_bytes', 0),
            'compression_efficiency': compression_efficiency
        }
        
        return stats
    
    def _calculate_decompression_stats(self, compressed_size, decompressed_size, elapsed_time):
        """
        Calculate decompression statistics
        
        Args:
            compressed_size (int): Size of the compressed file
            decompressed_size (int): Size of the decompressed file
            elapsed_time (float): Elapsed time in seconds
            
        Returns:
            dict: Decompression statistics
        """
        throughput = decompressed_size / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0
        
        stats = {
            'compressed_size': compressed_size,
            'decompressed_size': decompressed_size,
            'elapsed_time': elapsed_time,
            'throughput_mb_per_sec': throughput
        }
        
        return stats


if __name__ == "__main__":
    # Simple test of the AdaptiveCompressor
    def test_adaptive_compressor():
        # Create a test file
        test_file = "test_data.bin"
        output_file = "test_data.ambc"
        decompressed_file = "test_data_decompressed.bin"
        
        # Generate some test data with different patterns
        test_data = bytearray()
        
        # Add some repeated data (good for RLE)
        test_data.extend(b'A' * 1000)
        
        # Add some structured data (good for dictionary-based)
        for i in range(100):
            test_data.extend(b"The quick brown fox jumps over the lazy dog. ")
        
        # Add some random data (challenging to compress)
        test_data.extend(os.urandom(1000))
        
        # Add some data with small variations (good for delta)
        base = 100
        for i in range(1000):
            test_data.append((base + i % 10) % 256)
        
        # Write test data to file
        with open(test_file, 'wb') as f:
            f.write(test_data)
        
        try:
            # Create compressor
            compressor = AdaptiveCompressor(initial_chunk_size=512)
            
            # Compress
            print("Compressing...")
            stats = compressor.compress(test_file, output_file)
            
            print(f"Original size: {stats['original_size']} bytes")
            print(f"Compressed size: {stats['compressed_size']} bytes")
            print(f"Compression ratio: {stats['ratio']:.4f}")
            print(f"Space saving: {stats['percent_reduction']:.2f}%")
            print(f"Elapsed time: {stats['elapsed_time']:.4f} seconds")
            print(f"Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
            
            # Print chunk statistics
            print("\nChunk statistics:")
            print(f"Total chunks: {stats['chunk_stats']['total_chunks']}")
            print("Method usage:")
            for method_id, count in stats['chunk_stats']['method_usage'].items():
                if count > 0:
                    print(f"  Method {method_id}: {count} chunks")
            
            # Decompress
            print("\nDecompressing...")
            decomp_stats = compressor.decompress(output_file, decompressed_file)
            
            print(f"Compressed size: {decomp_stats['compressed_size']} bytes")
            print(f"Decompressed size: {decomp_stats['decompressed_size']} bytes")
            print(f"Elapsed time: {decomp_stats['elapsed_time']:.4f} seconds")
            print(f"Throughput: {decomp_stats['throughput_mb_per_sec']:.2f} MB/s")
            
            # Verify the decompressed file matches the original
            with open(decompressed_file, 'rb') as f:
                decompressed_data = f.read()
            
            if decompressed_data == test_data:
                print("\nSuccessfully verified: decompressed file matches original!")
            else:
                print("\nERROR: decompressed file does not match original!")
        
        finally:
            # Clean up
            for file in [test_file, output_file, decompressed_file]:
                if os.path.exists(file):
                    os.remove(file)
    
    # Run the test
    test_adaptive_compressor()