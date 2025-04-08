#!/usr/bin/env python3

import os
import sys
import unittest
import random
from bitarray import bitarray

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marker_finder import MarkerFinder


class TestMarkerFinder(unittest.TestCase):
    """Test the MarkerFinder class"""
    
    def test_simple_marker(self):
        """Test marker finding with a simple pattern"""
        # Create a simple test data with a predictable pattern
        test_data = b'ABC' * 100
        
        finder = MarkerFinder(max_marker_length=16)
        marker_bytes, marker_length = finder.find_marker(test_data)
        
        # Verify the marker doesn't appear in the data
        self._verify_marker_not_present(test_data, marker_bytes, marker_length)
        
        print(f"✓ Found marker of length {marker_length} bits for simple pattern")
    
    def test_random_data(self):
        """Test marker finding with random data"""
        # Create random test data
        test_data = bytes(random.randint(0, 255) for _ in range(1000))
        
        finder = MarkerFinder(max_marker_length=16)
        marker_bytes, marker_length = finder.find_marker(test_data)
        
        # Verify the marker doesn't appear in the data
        self._verify_marker_not_present(test_data, marker_bytes, marker_length)
        
        print(f"✓ Found marker of length {marker_length} bits for random data")
    
    def test_sampling(self):
        """Test marker finding with sampling enabled"""
        # Create a larger dataset to test sampling
        test_data = bytes(random.randint(0, 255) for _ in range(10000))
        
        finder = MarkerFinder(max_marker_length=16)
        marker_bytes, marker_length = finder.find_marker(test_data, sample_size=1000)
        
        # Verify the marker doesn't appear in the full data
        self._verify_marker_not_present(test_data, marker_bytes, marker_length)
        
        print(f"✓ Found marker of length {marker_length} bits using sampling")
    
    def test_marker_length_limit(self):
        """Test that marker length doesn't exceed the max_marker_length"""
        # Create various test datasets
        test_datasets = [
            b'A' * 1000,                   # Repeated single byte
            b'AB' * 500,                   # Repeated pattern
            bytes(range(256)) * 4,         # All possible byte values
            bytes(random.randint(0, 255) for _ in range(2000))  # Random
        ]
        
        max_length = 24
        finder = MarkerFinder(max_marker_length=max_length)
        
        for i, data in enumerate(test_datasets):
            marker_bytes, marker_length = finder.find_marker(data)
            
            # Verify the marker length is within limits
            self.assertLessEqual(marker_length, max_length, 
                               f"Marker length {marker_length} exceeds max {max_length} for dataset {i}")
            
            # Verify the marker doesn't appear in the data
            self._verify_marker_not_present(data, marker_bytes, marker_length)
            
            print(f"✓ Dataset {i}: Found marker of length {marker_length} bits within limit")
    
    def _verify_marker_not_present(self, data, marker_bytes, marker_length):
        """Verify that the marker is not present in the data"""
        # Convert marker to bitarray
        marker_bits = bitarray()
        marker_bits.frombytes(marker_bytes)
        
        # Extract just the significant bits
        marker_pattern = marker_bits[:marker_length].to01()
        
        # Convert data to bitarray
        data_bits = bitarray()
        data_bits.frombytes(data)
        data_str = data_bits.to01()
        
        # Check that the marker doesn't appear in the data
        self.assertNotIn(marker_pattern, data_str, 
                       f"Marker '{marker_pattern}' appears in the data!")


if __name__ == "__main__":
    unittest.main()
