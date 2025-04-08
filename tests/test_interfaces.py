#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
import importlib.util

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the interfaces
from gradio_interface import GradioInterface

# Check if enhanced interface is available
ENHANCED_UI_AVAILABLE = False
try:
    import gradio
    from gradio.main import run_interface as run_enhanced_interface
    ENHANCED_UI_AVAILABLE = True
except ImportError:
    pass


class TestInterfaces(unittest.TestCase):
    """Test case for both original and enhanced Gradio interfaces"""
    
    def test_original_interface_creation(self):
        """Test that the original interface can be created"""
        try:
            interface = GradioInterface()
            self.assertIsNotNone(interface)
            self.assertEqual(interface.title, "Adaptive Marker-Based Compression")
            print("✓ Original interface created successfully")
        except Exception as e:
            self.fail(f"Original interface creation failed: {e}")
    
    def test_original_serialization(self):
        """Test that the original interface's serialization works"""
        interface = GradioInterface()
        test_data = {
            "nested": {"value": 42},
            "list": [1, 2, 3],
            "tuple": (4, 5, 6),
            "set": {7, 8, 9},
            "number": 10,
            "string": "test",
            "boolean": True,
            "none": None
        }
        
        serialized = interface._ensure_serializable(test_data)
        self.assertIsInstance(serialized, dict)
        self.assertIsInstance(serialized["list"], list)
        self.assertIsInstance(serialized["tuple"], tuple)
        self.assertIsInstance(serialized["set"], list)  # Sets should become lists
        print("✓ Original interface serialization works")
    
    @unittest.skipIf(not ENHANCED_UI_AVAILABLE, "Enhanced UI not available")
    def test_enhanced_interface_imports(self):
        """Test that the enhanced interface modules can be imported"""
        try:
            from gradio.interface import EnhancedGradioInterface
            from gradio.utils import create_header, toggle_detailed_stats
            from gradio.tabs.about import create_about_tab
            from gradio.tabs.compress import create_compress_tab
            from gradio.tabs.decompress import create_decompress_tab
            from gradio.tabs.analysis import create_analysis_tab
            from gradio.tabs.file_format import create_file_format_tab
            from gradio.tabs.help import create_help_tab
            
            self.assertTrue(True)  # If we get here, imports worked
            print("✓ Enhanced interface modules can be imported")
        except ImportError as e:
            self.fail(f"Enhanced interface imports failed: {e}")
    
    @unittest.skipIf(not ENHANCED_UI_AVAILABLE, "Enhanced UI not available")
    def test_enhanced_interface_creation(self):
        """Test that the enhanced interface can be created"""
        try:
            from gradio.interface import EnhancedGradioInterface
            
            interface = EnhancedGradioInterface()
            self.assertIsNotNone(interface)
            self.assertEqual(interface.title, "Adaptive Marker-Based Compression")
            print("✓ Enhanced interface created successfully")
        except Exception as e:
            self.fail(f"Enhanced interface creation failed: {e}")


if __name__ == "__main__":
    print("\nTesting Gradio Interfaces\n" + "-"*25)
    unittest.main(verbosity=2)
