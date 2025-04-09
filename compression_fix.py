"""
Compatibility module for compression methods.
This provides a compatibility layer for different compression libraries.
"""

import os
import sys
import importlib

# Check for available compression libraries
HAS_BROTLI = False
HAS_LZHAM = False
HAS_ZSTD = False
HAS_LZ4 = False

def check_compression_libraries():
    """
    Check which compression libraries are available
    
    Returns:
        dict: Dictionary indicating which libraries are available
    """
    global HAS_BROTLI, HAS_LZHAM, HAS_ZSTD, HAS_LZ4
    
    # Check for Brotli
    try:
        import brotli
        HAS_BROTLI = True
    except ImportError:
        HAS_BROTLI = False
    
    # Check for LZHAM
    try:
        import pylzham
        HAS_LZHAM = True
    except ImportError:
        HAS_LZHAM = False
    
    # Check for ZStandard
    try:
        import zstandard
        HAS_ZSTD = True
    except ImportError:
        HAS_ZSTD = False
    
    # Check for LZ4
    try:
        import lz4.frame
        HAS_LZ4 = True
    except ImportError:
        HAS_LZ4 = False
    
    return {
        'brotli': HAS_BROTLI,
        'lzham': HAS_LZHAM,
        'zstd': HAS_ZSTD,
        'lz4': HAS_LZ4
    }

def get_compatible_methods():
    """
    Get a list of compression methods that are compatible with the current environment.
    
    Returns:
        list: List of compatible compression method instances
    """
    # Import the base methods that are always available
    from compression_methods import (
        RLECompression,
        DictionaryCompression,
        HuffmanCompression,
        DeltaCompression,
        NoCompression
    )
    
    # Start with basic compression methods that don't need external libraries
    methods = [
        RLECompression(),
        DictionaryCompression(),
        HuffmanCompression(),
        DeltaCompression(),
        NoCompression()
    ]
    
    # Check which advanced methods are available
    libs = check_compression_libraries()
    
    # Import advanced methods if available
    try:
        # Try to import the standard library compression methods
        from advanced_compression import (
            DeflateCompression,
            Bzip2Compression,
            LZMACompression
        )
        
        # Add standard library methods
        methods.append(DeflateCompression())
        methods.append(Bzip2Compression())
        methods.append(LZMACompression())
        
        # Try to add ZStandard
        if libs['zstd']:
            from advanced_compression import ZstdCompression
            methods.append(ZstdCompression())
        
        # Try to add LZ4
        if libs['lz4']:
            from advanced_compression import LZ4Compression
            methods.append(LZ4Compression())
        
        # Try to add Brotli
        if libs['brotli']:
            from brotli_lzham_compression import BrotliCompression
            methods.append(BrotliCompression())
        
        # Try to add LZHAM
        if libs['lzham']:
            from brotli_lzham_compression import LZHAMCompression
            methods.append(LZHAMCompression())
            
    except ImportError as e:
        print(f"Warning: Some advanced compression methods couldn't be imported: {e}")
    
    return methods

# Check available libraries on module import
available_libraries = check_compression_libraries()
