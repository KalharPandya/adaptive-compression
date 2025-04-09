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
import math  # We'll use math.log2() to compute k_value

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
    Now updated to avoid scanning for markers inside compressed data.
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
            existing_method_ids = {m.type_id for m in self.compression_methods}
            
            # Add DEFLATE if available
            self.compression_methods.append(DeflateCompression())
            print("Added DEFLATE compression")
            
            # Add BZIP2 if available
            self.compression_methods.append(Bzip2Compression())
            print("Added BZIP2 compression")
            
            # Add LZMA if available
            self.compression_methods.append(LZMACompression())
            print("Added LZMA compression")
            
            # Add ZStandard if available and not already added
            if HAS_ZSTD and 8 not in existing_method_ids:
                self.compression_methods.append(ZstdCompression())
                print("Added ZStandard compression")
            
            # Add LZ4 if available
            if HAS_LZ4:
                self.compression_methods.append(LZ4Compression())
                print("Added LZ4 compression")
        
        # Try to add standard Brotli if not already added
        existing_method_ids = {m.type_id for m in self.compression_methods}
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
        """
        self.use_multithreading = True
        if max_workers:
            self.max_workers = max_workers
        print(f"Multithreading enabled with {self.max_workers} workers")
    
    def disable_multithreading(self):
        """
        Disable multithreading for compression
        """
        self.use_multithreading = False
        print("Multithreading disabled")
    
    def set_progress_callback(self, callback):
        """
        Set a callback function for progress updates
        """
        self.progress_callback = callback
    
    def _update_progress(self, stage, current, total, current_chunk=None, total_chunks=None):
        if self.progress_callback:
            self.progress_callback(stage, current, total, current_chunk, total_chunks)
    
    def _init_marker(self, marker_bytes, marker_length):
        """
        Initialize marker properties for consistent handling
        """
        self.marker_bytes = marker_bytes
        self.marker_length = marker_length
        
        # Extract the actual marker bit pattern
        marker_bits = bitarray()
        marker_bits.frombytes(marker_bytes)
        marker_bits = marker_bits[:marker_length]
        self.marker_pattern = marker_bits.to01()
        
        # Debug
        marker_int = int(self.marker_pattern, 2)
        print(f"Raw marker pattern: {self.marker_pattern}")
        print(f"As integer: {marker_int}, hex: {hex(marker_int)}")
        
        # Calculate the properly aligned marker bytes
        if marker_length <= 8:
            # For small markers (≤8 bits)
            marker_int = int(self.marker_pattern, 2) << (8 - marker_length)
            self.marker_bytes_aligned = bytes([marker_int])
            mask_value = (0xFF >> marker_length) << marker_length & 0xFF
            self.marker_mask = bytes([mask_value])
        else:
            # For longer markers
            padded_bits = bitarray(self.marker_pattern)
            while len(padded_bits) % 8 != 0:
                padded_bits.append(0)
            self.marker_bytes_aligned = padded_bits.tobytes()
            self.marker_mask = b'\xFF' * len(self.marker_bytes_aligned)
        
        print(f"Initialized marker: length={marker_length} bits, "
              f"pattern={self.marker_pattern}, aligned_bytes={self.marker_bytes_aligned.hex()}")
        
        self.marker_byte_length = (marker_length + 7) // 8
    
    def compress(self, input_file, output_file):
        """
        Compress a file using the adaptive compression algorithm
        """
        start_time = time.time()
        
        with open(input_file, 'rb') as f:
            file_data = f.read()
        
        self._update_progress("Reading File", len(file_data), len(file_data))
        
        # Calculate checksum
        checksum = hashlib.md5(file_data).digest()
        self._update_progress("Calculating Checksum", 1, 1)
        
        # Find a marker
        self._update_progress("Finding Marker", 0, 1)
        marker_bytes, marker_length = self._find_marker(file_data, sample_size=self.sample_size)
        self._update_progress("Finding Marker", 1, 1)
        
        # Init marker
        self._init_marker(marker_bytes, marker_length)
        
        # Create header
        self._update_progress("Creating Header", 0, 1)
        header = self._create_header(marker_bytes, marker_length, checksum, len(file_data))
        header_size = len(header)
        self._update_progress("Creating Header", 1, 1)
        
        # Compress data
        self._update_progress("Compressing Data", 0, len(file_data))
        compressed_data = self._adaptive_compress(file_data, marker_bytes, marker_length)
        self._update_progress("Compressing Data", len(file_data), len(file_data))
        
        # Update header with compressed size
        header = self._update_header_compressed_size(header, len(compressed_data))
        
        # Update overhead stats
        if hasattr(self, 'chunk_stats') and 'overhead_bytes' in self.chunk_stats:
            self.chunk_stats['overhead_bytes'] += header_size
            self.chunk_stats['header_size'] = header_size
        
        # Write compressed output
        self._update_progress("Writing File", 0, len(header) + len(compressed_data))
        with open(output_file, 'wb') as f:
            f.write(header)
            f.write(compressed_data)
        self._update_progress("Writing File", len(header) + len(compressed_data),
                              len(header) + len(compressed_data))
        
        # Stats
        stats = self._calculate_compression_stats(
            len(file_data), len(header) + len(compressed_data), time.time() - start_time
        )
        return stats
    
    def decompress(self, input_file, output_file):
        """
        Decompress a file that was compressed using this algorithm
        """
        start_time = time.time()
        
        self._update_progress("Reading File", 0, 1)
        with open(input_file, 'rb') as f:
            compressed_data = f.read()
        self._update_progress("Reading File", 1, 1)
        
        # Parse header
        self._update_progress("Parsing Header", 0, 1)
        try:
            header_info = self._parse_header(compressed_data)
        except Exception as e:
            print(f"Error parsing header: {e}")
            raise ValueError(f"Invalid compressed file format: {e}")
        self._update_progress("Parsing Header", 1, 1)
        
        # Init marker
        self._init_marker(header_info['marker_bytes'], header_info['marker_length'])
        
        # Actual compressed payload
        data_to_decompress = compressed_data[header_info['header_size']:]
        
        print(f"\nDecompression started. File size: {len(compressed_data)} bytes")
        print(f"Header size: {header_info['header_size']} bytes")
        print(f"Marker length: {header_info['marker_length']} bits")
        print(f"Original size: {header_info['original_size']} bytes")
        
        # Decompress
        self._update_progress("Decompressing", 0, header_info['original_size'])
        decompressed_data = self._adaptive_decompress(
            data_to_decompress,
            header_info['marker_bytes'],
            header_info['marker_length'],
            header_info['original_size']
        )
        self._update_progress("Decompressing", header_info['original_size'], header_info['original_size'])
        
        # Write decompressed
        self._update_progress("Writing File", 0, len(decompressed_data))
        with open(output_file, 'wb') as f:
            f.write(decompressed_data)
        self._update_progress("Writing File", len(decompressed_data), len(decompressed_data))
        
        # Checksum
        self._update_progress("Verifying Checksum", 0, 1)
        actual_checksum = hashlib.md5(decompressed_data).digest()
        expected_checksum = header_info['checksum']
        if actual_checksum != expected_checksum:
            print("\nChecksum verification failed!")
            print(f"Expected checksum: {expected_checksum.hex()}")
            print(f"Actual checksum:   {actual_checksum.hex()}")
            print(f"Decompressed size: {len(decompressed_data)}, "
                  f"Original size: {header_info['original_size']}")
            raise ValueError("Checksum verification failed! File may be corrupted.")
        self._update_progress("Verifying Checksum", 1, 1)
        
        # Stats
        stats = self._calculate_decompression_stats(
            len(compressed_data), len(decompressed_data), time.time() - start_time
        )
        return stats

    def _find_marker(self, file_data, sample_size=None):
        """
        Find a marker that doesn't appear in the file data
        """
        if hasattr(self, 'marker_finder') and self.marker_finder:
            return self.marker_finder.find_marker(file_data, sample_size)

        # Otherwise, fallback logic
        data_to_check = file_data
        if sample_size and len(file_data) > sample_size:
            step = len(file_data) // sample_size
            sampled_data = bytearray()
            for i in range(0, len(file_data), step):
                sampled_data.extend(file_data[i:i+1])
            data_to_check = bytes(sampled_data[:sample_size])
            print(f"Finding marker using {len(data_to_check)} bytes sampled "
                  f"from a {len(file_data)} byte file")
            print(f"Sampling every {step} bytes at {len(data_to_check)} points")
        else:
            print(f"Finding marker in entire file ({len(file_data)} bytes)")
        
        for marker_length in range(1, 17):
            possible_patterns = 2 ** marker_length
            print(f"Checking markers of length {marker_length} bits "
                  f"({possible_patterns} possibilities)")
            check_start_time = time.time()
            
            found = np.zeros(possible_patterns, dtype=bool)
            bits = bitarray()
            bits.frombytes(data_to_check)
            
            for i in range(len(bits) - marker_length + 1):
                window = bits[i:i+marker_length]
                value = int(window.to01(), 2)
                if value < possible_patterns:
                    found[value] = True
            
            patterns_found = np.sum(found)
            coverage_percent = (patterns_found / possible_patterns) * 100
            check_time = time.time() - check_start_time
            print(f"  Found {patterns_found} of {possible_patterns} patterns "
                  f"({coverage_percent:.2f}%) in {check_time:.4f} seconds")
            
            for i in range(possible_patterns):
                if not found[i]:
                    marker_str = bin(i)[2:].zfill(marker_length)
                    marker_bits = bitarray(marker_str)
                    if marker_length <= 8:
                        while len(marker_bits) < 8:
                            marker_bits.append(0)
                        marker_bytes = marker_bits.tobytes()
                    else:
                        padding = 8 - (marker_length % 8) if marker_length % 8 else 0
                        padded_bits = marker_bits + bitarray('0' * padding)
                        marker_bytes = padded_bits.tobytes()
                    
                    elapsed_time = time.time() - check_start_time
                    print(f"Found marker of length {marker_length} bits in "
                          f"{elapsed_time:.4f} seconds")
                    print(f"Marker binary: {marker_str}")
                    print(f"Marker hex: {marker_bytes.hex()}")
                    return marker_bytes, marker_length
        
        # Fallback
        print("Could not find a short unique marker - using a 32-bit marker")
        marker_bits = bitarray('11111111111111110000000000000000')
        return marker_bits.tobytes(), 32

    def _create_header(self, marker_bytes, marker_length, checksum, original_size):
        """
        Create the file-level header for the compressed file
        """
        # [Magic (4 bytes)] [Version (1 byte)] [Header Size (4 bytes)]
        # [Marker Length (1 byte)] [Marker bytes]
        # [Checksum Type (1 byte, 1=MD5)] [Checksum (16 bytes)]
        # [Original Size (8 bytes)] [Compressed Size (8 bytes)]
        
        header = bytearray()
        header.extend(self.MAGIC_NUMBER)
        header.append(self.FORMAT_VERSION)
        header.extend(b'\x00\x00\x00\x00')  # header size placeholder
        header.append(marker_length)
        header.extend(marker_bytes)
        header.append(1)  # checksum type = MD5
        header.extend(checksum)
        header.extend(struct.pack('<Q', original_size))
        header.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # placeholder for compressed size
        header_size = len(header)
        header[5:9] = struct.pack('<I', header_size)
        return bytes(header)
    
    def _update_header_compressed_size(self, header, compressed_size):
        """
        Fill in the final compressed file size in the header
        """
        header = bytearray(header)
        header[-8:] = struct.pack('<Q', compressed_size)
        return bytes(header)
    
    def _parse_header(self, compressed_data):
        """
        Parse the header from the compressed file
        """
        if compressed_data[:4] != self.MAGIC_NUMBER:
            raise ValueError("Invalid file format: Magic number doesn't match")
        
        format_version = compressed_data[4]
        if format_version > self.FORMAT_VERSION:
            raise ValueError(f"Unsupported format version: {format_version}")
        
        header_size = struct.unpack('<I', compressed_data[5:9])[0]
        marker_length = compressed_data[9]
        marker_bytes_size = (marker_length + 7) // 8
        marker_bytes = compressed_data[10:10 + marker_bytes_size]
        
        checksum_type = compressed_data[10 + marker_bytes_size]
        checksum_size = 16 if checksum_type == 1 else 0
        checksum = compressed_data[11 + marker_bytes_size : 11 + marker_bytes_size + checksum_size]
        
        original_size_pos = 11 + marker_bytes_size + checksum_size
        original_size = struct.unpack('<Q', compressed_data[original_size_pos : original_size_pos + 8])[0]
        
        compressed_size_pos = original_size_pos + 8
        compressed_size = struct.unpack('<Q', compressed_data[compressed_size_pos : compressed_size_pos + 8])[0]
        
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

    # ------------------------------------------------------------------
    #                ADAPTIVE COMPRESS / DECOMPRESS
    # ------------------------------------------------------------------

    def _adaptive_compress(self, file_data, marker_bytes, marker_length):
        """
        Compress the file data using adaptive methods (in multiple chunks).
        Now writes each chunk with a structured header, so we don't scan
        for markers in the payload.
        """
        self.marker_bytes = marker_bytes
        self.marker_length = marker_length
        
        self.chunk_stats = {
            'total_chunks': 0,
            'compressed_chunks': 0,
            'raw_chunks': 0,
            'method_usage': {m.type_id: 0 for m in self.compression_methods},
            'bytes_saved': 0,
            'original_size': len(file_data),
            'compressed_size_without_overhead': 0,
            'overhead_bytes': 0
        }
        
        print(f"\nAdaptive compression started for {len(file_data)} bytes")
        print(f"Using marker of length {marker_length} bits: {marker_bytes.hex()}")
        
        position = 0
        compressed = bytearray()
        chunks = []
        
        # 1) Determine chunk boundaries and best methods
        with tqdm(total=len(file_data), desc="Analyzing data", unit="B", unit_scale=True) as pbar:
            while position < len(file_data):
                chunk_size, best_method_id = self._determine_optimal_chunk(file_data, position)
                chunks.append((position, chunk_size, best_method_id))
                position += chunk_size
                pbar.update(chunk_size)
        
        # 2) Compress each chunk
        if self.use_multithreading and len(chunks) > 1:
            print(f"Processing {len(chunks)} chunks with multithreading ({self.max_workers} workers)")
            compressed_chunks = self._compress_chunks_parallel(file_data, chunks)
        else:
            print(f"Processing {len(chunks)} chunks sequentially")
            compressed_chunks = self._compress_chunks_sequential(file_data, chunks)
        
        # 3) Concatenate
        for i, chunk_data in enumerate(compressed_chunks):
            compressed.extend(chunk_data)
            self._update_progress("Compressing", i+1, len(chunks), current_chunk=i+1, total_chunks=len(chunks))
        
        # 4) Write an end chunk (package_type=0)
        end_chunk = self._create_end_chunk()
        compressed.extend(end_chunk)
        self.chunk_stats['overhead_bytes'] += len(end_chunk)
        
        print(f"\nCompression completed: {len(file_data)} bytes → {len(compressed)} bytes")
        print(f"Total chunks: {self.chunk_stats['total_chunks']}")
        print(f"  Compressed chunks: {self.chunk_stats['compressed_chunks']}")
        print(f"  Raw chunks: {self.chunk_stats['raw_chunks']}")
        
        for method_id, count in self.chunk_stats['method_usage'].items():
            if count > 0:
                method_name = self.method_names.get(method_id, f"Method {method_id}")
                if self.chunk_stats['compressed_chunks'] > 0:
                    percent = count / self.chunk_stats['compressed_chunks'] * 100
                    print(f"  {method_name}: {count} chunks ({percent:.1f}% of compressed)")
                else:
                    print(f"  {method_name}: {count} chunks")
        
        return bytes(compressed)

    def _adaptive_decompress(self, compressed_data, marker_bytes, marker_length, original_size):
        """
        Decompress the data chunk-by-chunk, using a structured format:
          [marker_bytes_aligned]
          [package_type (1 byte)]
          [k_value (1 byte)]
          [used_bytes_in_chunk (2 bytes, LE)]
          [original_length (4 bytes, LE)]
          [compressed_length (4 bytes, LE)]
          [compressed payload]
          ...
          until package_type=0
        """
        decompressed = bytearray()
        
        print(f"\nAdaptive decompression started for {len(compressed_data)} bytes")
        print(f"Using marker of length {marker_length} bits: {marker_bytes.hex()}")
        print(f"Using aligned marker bytes: {self.marker_bytes_aligned.hex()}")
        print(f"Expected original size: {original_size} bytes")
        
        self.marker_bytes = marker_bytes
        self.marker_length = marker_length
        
        pos = 0
        while True:
            # Ensure enough bytes remain for at least one chunk header
            needed_header = len(self.marker_bytes_aligned) + 1 + 1 + 2 + 4 + 4
            if pos + needed_header > len(compressed_data):
                # No more full chunks
                print("No more chunk headers can be read. Stopping.")
                break
            
            # 1) Read marker
            chunk_marker = compressed_data[pos : pos + len(self.marker_bytes_aligned)]
            if chunk_marker != self.marker_bytes_aligned:
                raise ValueError("Marker mismatch in chunk header.")
            pos += len(self.marker_bytes_aligned)
            
            # 2) package_type
            package_type = compressed_data[pos]
            pos += 1
            
            # 3) k_value
            k_value = compressed_data[pos]
            pos += 1
            
            # 4) used_bytes_in_chunk
            used_bytes_in_chunk = struct.unpack("<H", compressed_data[pos : pos + 2])[0]
            pos += 2
            
            # 5) original_length
            original_len = struct.unpack("<I", compressed_data[pos : pos + 4])[0]
            pos += 4
            
            # 6) compressed_length
            compressed_len = struct.unpack("<I", compressed_data[pos : pos + 4])[0]
            pos += 4
            
            # 7) If package_type == 0 => end chunk
            if package_type == 0:
                print("End-of-stream chunk found.")
                break
            
            # Check boundaries for compressed payload
            if pos + compressed_len > len(compressed_data):
                print("Not enough bytes remain for the declared compressed payload.")
                break
            
            payload = compressed_data[pos : pos + compressed_len]
            pos += compressed_len
            
            # Decompress
            method = self.method_lookup.get(package_type)
            if method is None:
                print(f"Unknown package_type={package_type}, treating as raw. "
                      "This may result in incorrect data.")
                decompressed.extend(payload)
            else:
                # Attempt to decompress
                try:
                    chunk_out = method.decompress(payload, original_len)
                    decompressed.extend(chunk_out)
                except Exception as e:
                    print(f"Error decompressing chunk with method={package_type}: {e}")
                    # fallback: fill with zeros
                    decompressed.extend(bytes(original_len))
            
            if len(decompressed) >= original_size:
                break
        
        # Fix final size
        if len(decompressed) < original_size:
            short_by = original_size - len(decompressed)
            print(f"Result is shorter than expected; padding with {short_by} zero bytes.")
            decompressed.extend(bytes(short_by))
        elif len(decompressed) > original_size:
            over = len(decompressed) - original_size
            print(f"Result is longer than expected; truncating {over} bytes.")
            decompressed = decompressed[:original_size]
        
        print(f"Decompression completed: {len(compressed_data)} bytes → {len(decompressed)} bytes")
        return bytes(decompressed)
    
    # ------------------------------------------------------------------
    #                CHUNK LOGIC (WRITE / READ)
    # ------------------------------------------------------------------
    
    def _create_end_chunk(self):
        """
        Create an end-of-stream chunk (package_type=0).
        Format: marker + [0] + [k_value=0] + [used_bytes_in_chunk=0] + 
                [original_length=0] + [compressed_length=0]
        """
        chunk = bytearray()
        chunk.extend(self.marker_bytes_aligned)
        chunk.append(0)  # package_type=0
        chunk.append(0)  # k_value=0
        chunk.extend(struct.pack("<H", 0))  # used_bytes_in_chunk=0
        chunk.extend(struct.pack("<I", 0))  # original_length=0
        chunk.extend(struct.pack("<I", 0))  # compressed_length=0
        print(f"Created END chunk: marker={self.marker_bytes_aligned.hex()}")
        return chunk

    def _create_chunk(self, package_type, k_value, used_bytes_in_chunk,
                      original_length, compressed_data):
        """
        Create a structured chunk:
          [marker_bytes_aligned]
          [package_type (1 byte)]
          [k_value (1 byte)]
          [used_bytes_in_chunk (2 bytes, LE)]
          [original_length (4 bytes, LE)]
          [compressed_length (4 bytes, LE)]
          [compressed_data]
        """
        chunk = bytearray()
        chunk.extend(self.marker_bytes_aligned)
        chunk.append(package_type)
        chunk.append(k_value)
        chunk.extend(struct.pack("<H", used_bytes_in_chunk))
        chunk.extend(struct.pack("<I", original_length))
        chunk.extend(struct.pack("<I", len(compressed_data)))
        chunk.extend(compressed_data)
        return chunk
    
    def _slab_size(self, k_value):
        """
        Return the slab size = 2^(10 + k_value).
        For example, if k_value=0 => 2^10=1024, if k_value=6 => 2^(10+6)=65536, etc.
        """
        return 2 ** (10 + k_value)

    def _compute_k_value(self, chunk_size):
        """
        Compute an integer k_value such that slab_size = 2^(10 + k_value) >= chunk_size.
        This is just a simple approach. You can refine as needed.
        """
        # maximum chunk_size is 2^(10+some max). We'll clamp if too large.
        if chunk_size < 1024:
            return 0  # i.e. 2^10
        max_k = 16  # or some limit
        k = int(math.ceil(math.log2(chunk_size) - 10))
        if k < 0:
            k = 0
        if k > max_k:
            k = max_k
        return k
    
    # ------------------------------------------------------------------
    #                CHUNK PROCESSING
    # ------------------------------------------------------------------
    
    def _compress_chunks_sequential(self, file_data, chunks):
        results = []
        total_chunks = len(chunks)
        for chunk_index, (position, size, method_id) in enumerate(chunks):
            self._update_progress("Compressing", position, len(file_data),
                                  current_chunk=chunk_index+1, total_chunks=total_chunks)
            
            chunk_data = file_data[position : position + size]
            package_data, stats = self._process_chunk(chunk_data, method_id, chunk_index, total_chunks)
            self.chunk_stats['total_chunks'] += 1
            
            if stats['compressed']:
                self.chunk_stats['compressed_chunks'] += 1
                self.chunk_stats['method_usage'][stats['method_id']] += 1
                self.chunk_stats['compressed_size_without_overhead'] += stats['compressed_size']
                self.chunk_stats['overhead_bytes'] += stats['overhead']
                self.chunk_stats['bytes_saved'] += stats['bytes_saved']
            else:
                self.chunk_stats['raw_chunks'] += 1
            
            results.append(package_data)
        return results
    
    def _compress_chunks_parallel(self, file_data, chunks):
        results = [None] * len(chunks)
        total_chunks = len(chunks)
        progress_bar = tqdm(total=total_chunks, desc="Processing chunks", unit="chunk")
        
        def worker(chunk_index):
            position, size, method_id = chunks[chunk_index]
            chunk_data = file_data[position : position + size]
            package_data, stats = self._process_chunk(chunk_data, method_id, chunk_index, total_chunks)
            progress_bar.update(1)
            if self.progress_callback:
                self._update_progress("Compressing", chunk_index+1, total_chunks,
                                      current_chunk=chunk_index+1, total_chunks=total_chunks)
            return chunk_index, package_data, stats
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(total_chunks)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    i, package_data, stats = future.result()
                    results[i] = package_data
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
                    print(f"Error in parallel chunk processing: {e}")
        progress_bar.close()
        return results
    
    def _process_chunk(self, chunk_data, method_id, chunk_index, total_chunks):
        """
        Actually compress a single chunk; produce the final chunk bytes with our header
        """
        stats = {
            'compressed': False,
            'method_id': 255,
            'original_size': len(chunk_data),
            'compressed_size': len(chunk_data),
            'overhead': 0,
            'bytes_saved': 0
        }
        
        # If method_id not valid or is 255 => no compression
        if method_id not in self.method_lookup or method_id == 255:
            stats['method_id'] = 255
            if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                print(f"Chunk {chunk_index+1}/{total_chunks} processed: {len(chunk_data)} bytes (no compression)")
            # We'll create a chunk with package_type=255 but no compression
            # effectively the "payload" is chunk_data itself
            k_value = self._compute_k_value(len(chunk_data))
            chunk_bytes = self._create_chunk(
                package_type=255,
                k_value=k_value,
                used_bytes_in_chunk=len(chunk_data),
                original_length=len(chunk_data),
                compressed_data=chunk_data
            )
            return chunk_bytes, stats
        
        # Otherwise, compress
        method = self.method_lookup[method_id]
        try:
            compressed_data = method.compress(chunk_data)
            overhead = self._calculate_fixed_overhead()
            
            if len(compressed_data) + overhead < len(chunk_data):
                # Good compression
                stats['compressed'] = True
                stats['method_id'] = method_id
                stats['compressed_size'] = len(compressed_data)
                stats['overhead'] = overhead
                stats['bytes_saved'] = len(chunk_data) - (len(compressed_data) + overhead)
                
                k_value = self._compute_k_value(len(chunk_data))
                chunk_bytes = self._create_chunk(
                    package_type=method_id,
                    k_value=k_value,
                    used_bytes_in_chunk=len(chunk_data),
                    original_length=len(chunk_data),
                    compressed_data=compressed_data
                )
                
                if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                    ratio = (len(compressed_data) + overhead) / len(chunk_data)
                    method_name = self.method_names.get(method_id, f"Method {method_id}")
                    print(f"Chunk {chunk_index+1}/{total_chunks} processed:")
                    print(f"  Size: {len(chunk_data)} → {len(compressed_data)} (saved {stats['bytes_saved']} bytes)")
                    print(f"  Method: {method_name} (ratio: {ratio:.4f})")
                
                return chunk_bytes, stats
            else:
                # Not enough benefit
                stats['method_id'] = 255
                if chunk_index % max(1, total_chunks // 10) == 0 or chunk_index == total_chunks - 1:
                    print(f"Chunk {chunk_index+1}/{total_chunks} processed:")
                    print(f"  Size: {len(chunk_data)} bytes (compression not effective - using raw data)")
                
                k_value = self._compute_k_value(len(chunk_data))
                chunk_bytes = self._create_chunk(
                    package_type=255,
                    k_value=k_value,
                    used_bytes_in_chunk=len(chunk_data),
                    original_length=len(chunk_data),
                    compressed_data=chunk_data
                )
                return chunk_bytes, stats
        except Exception as e:
            print(f"Error compressing chunk {chunk_index+1}/{total_chunks} with method {method_id}: {e}")
            # fallback: raw
            chunk_bytes = self._create_chunk(
                package_type=255,
                k_value=self._compute_k_value(len(chunk_data)),
                used_bytes_in_chunk=len(chunk_data),
                original_length=len(chunk_data),
                compressed_data=chunk_data
            )
            return chunk_bytes, stats
    
    def _calculate_fixed_overhead(self):
        """
        Overhead for each chunk’s header (fixed-size):
          marker_bytes_aligned + 1 byte package_type + 1 byte k_value + 2 bytes used_bytes_in_chunk
          + 4 bytes original_length + 4 bytes compressed_length
        """
        return (len(self.marker_bytes_aligned) + 1 + 1 + 2 + 4 + 4)
    
    # ------------------------------------------------------------------
    #                CHUNK SIZE / METHOD SELECTION
    # ------------------------------------------------------------------
    
    def _determine_optimal_chunk(self, data, position):
        """
        Decide how big the next chunk is, and which method to use
        (similar logic to the old code, but we can feed the chosen chunk_size
        into the slab approach).
        """
        base_size = self.initial_chunk_size
        remaining = len(data) - position
        max_size = min(65536, remaining)
        
        if max_size <= base_size:
            # use what's left
            chunk = data[position : position + max_size]
            method_ids = self._predict_best_methods(chunk, max_methods=2)
            best_method_id = 255
            best_ratio = 1.0
            for mid in method_ids:
                method = self.method_lookup.get(mid)
                if method and method.should_use(chunk):
                    try:
                        comp = method.compress(chunk)
                        ratio = len(comp) / len(chunk)
                        if ratio < best_ratio:
                            best_ratio = ratio
                            best_method_id = mid
                    except:
                        pass
            return max_size, best_method_id
        
        # Otherwise, start with base_size
        chunk = data[position : position + base_size]
        method_ids = self._predict_best_methods(chunk, max_methods=3)
        
        best_method_id = None
        best_ratio = 1.0
        best_size = base_size
        
        for mid in method_ids:
            method = self.method_lookup.get(mid)
            if method and method.should_use(chunk):
                try:
                    comp = method.compress(chunk)
                    ratio = len(comp) / len(chunk)
                    if ratio < best_ratio:
                        best_ratio = ratio
                        best_method_id = mid
                        best_size = base_size
                except:
                    pass
        
        if best_method_id is not None and best_ratio < 0.95:
            size_increment = max(1024, base_size // 4)
            best_extended_ratio = best_ratio
            best_extended_size = best_size
            
            # Try larger sizes
            for s in range(base_size + size_increment, max_size + 1, size_increment):
                nxt = data[position : position + s]
                method = self.method_lookup.get(best_method_id)
                if method and method.should_use(nxt):
                    try:
                        comp2 = method.compress(nxt)
                        ratio2 = len(comp2) / s
                        # If ratio gets significantly worse, stop
                        if ratio2 > best_extended_ratio * 1.03:
                            break
                        best_extended_ratio = ratio2
                        best_extended_size = s
                    except:
                        break
            return best_extended_size, best_method_id
        else:
            # No good compression, just pick base_size raw
            return base_size, 255
    
    def _predict_best_methods(self, data, max_methods=3):
        """
        Heuristic to pick likely best compression methods
        """
        entropy = self._calculate_entropy(data)
        repetition_score = self._calculate_repetition_score(data)
        variation_score = self._calculate_variation_score(data)
        text_score = self._calculate_text_score(data)
        
        if entropy > 7.8:
            return [255]
        
        method_scores = {}
        # RLE
        method_scores[1] = 10.0 * repetition_score - entropy
        # Dictionary
        method_scores[2] = 8.0 * text_score + 4.0 * repetition_score - entropy * 0.8
        # Huffman
        method_scores[3] = 10.0 - 1.2 * entropy
        # Delta
        method_scores[4] = 10.0 * variation_score - 0.7 * entropy
        # DEFLATE
        method_scores[5] = 7.0 - 0.8 * entropy + 3.0 * text_score
        # BZIP2
        method_scores[6] = 7.5 * text_score - 0.6 * entropy
        # LZMA
        method_scores[7] = 6.0 - 0.6 * entropy + 2.0 * repetition_score
        # ZStandard
        method_scores[8] = 6.0 - 0.7 * entropy + 2.0 * text_score + 2.0 * repetition_score
        # LZ4
        method_scores[9] = 5.0 - 0.6 * entropy + 1.5 * repetition_score
        # Brotli
        method_scores[10] = 7.0 * text_score - 0.5 * entropy
        # LZHAM
        method_scores[11] = 5.0 - 0.6 * entropy + 3.0 * (1.0 - text_score)
        
        available = {m.type_id for m in self.compression_methods}
        for mid in available:
            if mid in [1,2,3,4,6]:
                method_scores[mid] = method_scores.get(mid, 0) + 2.0
            if mid in [8,10]:
                compatible_ids = [
                    m.type_id for m in self.compression_methods
                    if hasattr(m, '__class__') and ('Compatible' in m.__class__.__name__)
                ]
                if mid not in compatible_ids:
                    method_scores[mid] = method_scores.get(mid, 0) - 3.0
        
        # Keep only available
        ms = {k:v for k,v in method_scores.items() if k in available}
        # Sort
        sorted_methods = sorted(ms.items(), key=lambda x: x[1], reverse=True)
        result = [mid for mid,_ in sorted_methods[:max_methods]]
        if 255 not in result:
            result.append(255)
        return result

    # ------------------------------------------------------------------
    #                DATA METRICS
    # ------------------------------------------------------------------
    
    def _calculate_entropy(self, data):
        if not data:
            return 0.0
        counts = np.bincount(bytearray(data), minlength=256)
        probabilities = counts / len(data)
        probabilities = probabilities[probabilities > 0]
        return -np.sum(probabilities * np.log2(probabilities))
    
    def _calculate_repetition_score(self, data):
        if len(data) < 4:
            return 0.0
        if len(data) > 1000:
            step = len(data)//1000
            samp = bytearray()
            for i in range(0, len(data), step):
                samp.extend(data[i:i+1])
            data = bytes(samp[:1000])
        repeats = 0
        for i in range(len(data)-1):
            if data[i] == data[i+1]:
                repeats += 1
        return repeats / (len(data) - 1)
    
    def _calculate_variation_score(self, data):
        if len(data) < 4:
            return 0.0
        if len(data) > 1000:
            step = len(data)//1000
            samp = bytearray()
            for i in range(0, len(data), step):
                samp.extend(data[i:i+1])
            data = bytes(samp[:1000])
        small_deltas = 0
        for i in range(len(data)-1):
            if abs(data[i] - data[i+1]) < 32:
                small_deltas += 1
        return small_deltas / (len(data) - 1)
    
    def _calculate_text_score(self, data):
        if not data:
            return 0.0
        if len(data) > 1000:
            step = len(data)//1000
            samp = bytearray()
            for i in range(0, len(data), step):
                samp.extend(data[i:i+1])
            data = bytes(samp[:1000])
        text_chars = sum(1 for b in data if 32 <= b <= 127 or b in (9,10,13))
        return text_chars / len(data)
    
    # ------------------------------------------------------------------
    #                STATS
    # ------------------------------------------------------------------
    
    def _calculate_compression_stats(self, original_size, compressed_size, elapsed_time):
        if original_size == 0:
            ratio = 1.0
            percent_reduction = 0.0
        else:
            ratio = compressed_size / original_size
            percent_reduction = (1.0 - ratio) * 100.0
        
        throughput = (original_size / (1024*1024*elapsed_time)) if elapsed_time > 0 else 0
        
        if self.chunk_stats['compressed_chunks'] > 0:
            compressed_data_size = self.chunk_stats['compressed_size_without_overhead']
            overhead = self.chunk_stats['overhead_bytes']
            # Approximate “original_compressed_size”
            original_compressed_size = 0
            for mid, cnt in self.chunk_stats['method_usage'].items():
                if mid != 255 and cnt > 0:
                    portion = (cnt / self.chunk_stats['total_chunks']) * original_size
                    original_compressed_size += portion
            if original_compressed_size > 0:
                compression_efficiency = compressed_data_size / original_compressed_size
            else:
                compression_efficiency = 1.0
        else:
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
        throughput = (decompressed_size / (1024*1024*elapsed_time)) if elapsed_time > 0 else 0
        return {
            'compressed_size': compressed_size,
            'decompressed_size': decompressed_size,
            'elapsed_time': elapsed_time,
            'throughput_mb_per_sec': throughput
        }


# ----------------------------------------------------------------------
#               Simple Test Harness
# ----------------------------------------------------------------------

if __name__ == "__main__":
    def test_adaptive_compressor():
        test_file = "test_data.bin"
        output_file = "test_data.ambc"
        decompressed_file = "test_data_decompressed.bin"
        
        test_data = bytearray()
        # Repeated data
        test_data.extend(b'A' * 1000)
        # Some text
        for i in range(100):
            test_data.extend(b"The quick brown fox jumps over the lazy dog. ")
        # Random data
        test_data.extend(os.urandom(1000))
        # Small variations
        base = 100
        for i in range(1000):
            test_data.append((base + i % 10) % 256)
        
        with open(test_file, 'wb') as f:
            f.write(test_data)
        
        try:
            compressor = AdaptiveCompressor(initial_chunk_size=512)
            print("Compressing...")
            stats = compressor.compress(test_file, output_file)
            print(f"Original size: {stats['original_size']} bytes")
            print(f"Compressed size: {stats['compressed_size']} bytes")
            print(f"Compression ratio: {stats['ratio']:.4f}")
            print(f"Space saving: {stats['percent_reduction']:.2f}%")
            print(f"Elapsed time: {stats['elapsed_time']:.4f} s")
            print(f"Throughput: {stats['throughput_mb_per_sec']:.2f} MB/s")
            
            print("\nChunk statistics:")
            print(f"Total chunks: {stats['chunk_stats']['total_chunks']}")
            print("Method usage:")
            for mid, count in stats['chunk_stats']['method_usage'].items():
                if count > 0:
                    print(f"  Method {mid}: {count} chunks")
            
            print("\nDecompressing...")
            decomp_stats = compressor.decompress(output_file, decompressed_file)
            print(f"Compressed size: {decomp_stats['compressed_size']} bytes")
            print(f"Decompressed size: {decomp_stats['decompressed_size']} bytes")
            print(f"Elapsed time: {decomp_stats['elapsed_time']:.4f} s")
            print(f"Throughput: {decomp_stats['throughput_mb_per_sec']:.2f} MB/s")
            
            with open(decompressed_file, 'rb') as f:
                decompressed_data = f.read()
            if decompressed_data == test_data:
                print("\nSuccessfully verified: decompressed file matches original!")
            else:
                print("\nERROR: decompressed file does not match original!")
        
        finally:
            for file in [test_file, output_file, decompressed_file]:
                if os.path.exists(file):
                    os.remove(file)
    
    # Run test if invoked directly
    test_adaptive_compressor()
