#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
import importlib.util

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the interfaces
try:
    from gradio_interface import GradioInterface
    ORIGINAL_UI_AVAILABLE = True
except ImportError:
    ORIGINAL_UI_AVAILABLE = False
    print("Original GradioInterface not available")

# Check if enhanced interface is available
ENHANCED_UI_AVAILABLE = False
try:
    from gradio_components.interface import EnhancedGradioInterface
    from gradio_components.main import run_interface
    ENHANCED_UI_AVAILABLE = True
except ImportError:
    pass


class TestInterfaces(unittest.TestCase):
    """Test case for both original and enhanced Gradio interfaces"""
    
    @unittest.skipIf(not ORIGINAL_UI_AVAILABLE, "Original UI not available")
    def test_original_interface_creation(self):
        """Test that the original interface can be created"""
        try:
            interface = GradioInterface()
            self.assertIsNotNone(interface)
            self.assertEqual(interface.title, "Adaptive Marker-Based Compression")
            print("\u2713 Original interface created successfully")
        except Exception as e:
            self.fail(f"Original interface creation failed: {e}")
    
    @unittest.skipIf(not ORIGINAL_UI_AVAILABLE, "Original UI not available")
    def test_original_serialization(self):
        """Test that the original interface's serialization works"""
        try:
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
            print("\u2713 Original interface serialization works")
        except Exception as e:
            self.fail(f"Original serialization test failed: {e}")
    
    @unittest.skipIf(not ENHANCED_UI_AVAILABLE, "Enhanced UI not available")
    def test_enhanced_interface_imports(self):
        """Test that the enhanced interface modules can be imported"""
        try:
            from gradio_components.interface import EnhancedGradioInterface
            from gradio_components.utils import create_header, toggle_detailed_stats
            from gradio_components.tabs.about import create_about_tab
            from gradio_components.tabs.compress import create_compress_tab
            from gradio_components.tabs.decompress import create_decompress_tab
            from gradio_components.tabs.analysis import create_analysis_tab
            from gradio_components.tabs.file_format import create_file_format_tab
            from gradio_components.tabs.help import create_help_tab
            
            self.assertTrue(True)  # If we get here, imports worked
            print("\u2713 Enhanced interface modules can be imported")
        except ImportError as e:
            self.fail(f"Enhanced interface imports failed: {e}")
    
    @unittest.skipIf(not ENHANCED_UI_AVAILABLE, "Enhanced UI not available")
    def test_enhanced_interface_creation(self):
        """Test that the enhanced interface can be created"""
        try:
            from gradio_components.interface import EnhancedGradioInterface
            
            interface = EnhancedGradioInterface()
            self.assertIsNotNone(interface)
            self.assertEqual(interface.title, "Adaptive Marker-Based Compression")
            print("\u2713 Enhanced interface created successfully")
        except Exception as e:
            self.fail(f"Enhanced interface creation failed: {e}")


if __name__ == "__main__":
    print("\nTesting Gradio Interfaces\n" + "-"*25)
    unittest.main(verbosity=2)
