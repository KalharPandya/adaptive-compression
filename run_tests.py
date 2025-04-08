#!/usr/bin/env python3

import os
import sys
import unittest
import argparse

def run_tests(test_modules=None):
    """
    Run tests for the adaptive compression project
    
    Args:
        test_modules (list): List of test modules to run, or None for all tests
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Get all test modules if none specified
    if test_modules is None:
        test_dir = "tests"
        test_modules = []
        
        for file in os.listdir(test_dir):
            if file.startswith("test_") and file.endswith(".py"):
                module = file[:-3]  # Remove .py extension
                test_modules.append(module)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests from each module
    for module_name in test_modules:
        try:
            # Import the module
            module_path = f"tests.{module_name}"
            module = __import__(module_path, fromlist=["*"])
            
            # Add tests from this module
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"Added tests from {module_path}")
        except ImportError as e:
            print(f"Error importing {module_name}: {e}")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """
    Main entry point for running tests
    """
    parser = argparse.ArgumentParser(description="Run tests for adaptive compression")
    parser.add_argument(
        "--modules", 
        nargs="*", 
        help="Specific test modules to run (without .py extension)"
    )
    parser.add_argument(
        "--interfaces", 
        action="store_true", 
        help="Run only interface tests"
    )
    
    args = parser.parse_args()
    
    if args.interfaces:
        modules = ["test_interfaces"]
    else:
        modules = args.modules
    
    success = run_tests(modules)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
