#!/usr/bin/env python3
"""
Utility script to rename the gradio directory to gui_modules and update imports
to fix the import conflict with the system-installed gradio module.
"""

import os
import sys
import shutil

def rename_directory():
    """Rename the gradio directory to gui_modules"""
    # Get the base directory (where this script is located)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Source and destination directories
    gradio_dir = os.path.join(base_dir, 'gradio')
    gui_modules_dir = os.path.join(base_dir, 'gui_modules')
    
    # Check if the gradio directory exists
    if not os.path.exists(gradio_dir):
        print(f"Error: {gradio_dir} does not exist")
        return False
    
    # Check if the destination already exists
    if os.path.exists(gui_modules_dir):
        print(f"Warning: {gui_modules_dir} already exists. Please remove it first.")
        return False
    
    # Create the new directory
    try:
        # Copy the files instead of renaming to avoid git issues
        shutil.copytree(gradio_dir, gui_modules_dir)
        print(f"Successfully copied {gradio_dir} to {gui_modules_dir}")
        return True
    except Exception as e:
        print(f"Error copying directory: {e}")
        return False

def update_imports():
    """Update import statements in the copied files"""
    # Get the base directory (where this script is located)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gui_modules_dir = os.path.join(base_dir, 'gui_modules')
    
    # Check if the gui_modules directory exists
    if not os.path.exists(gui_modules_dir):
        print(f"Error: {gui_modules_dir} does not exist")
        return False
    
    # Function to update imports in a file
    def update_file_imports(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace import statements
        updated_content = content.replace("from .tabs.", "from .tabs.")
        updated_content = updated_content.replace("from gradio.main", "from gui_modules.main")
        updated_content = updated_content.replace("from gradio import", "from gui_modules import")
        updated_content = updated_content.replace("import gradio as gr", "import gradio as gr")
        
        # Don't modify actual gradio imports, just the relative ones
        
        if content != updated_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Updated imports in {file_path}")
    
    # Process Python files in the gui_modules directory
    for root, _, files in os.walk(gui_modules_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_file_imports(file_path)
    
    # Also update main.py to use the new module name
    main_py_path = os.path.join(base_dir, 'main.py')
    if os.path.exists(main_py_path):
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update imports in main.py
        updated_content = content.replace("from gradio.main import", "from gui_modules.main import")
        updated_content = updated_content.replace("sys.path.append(os.path.dirname", 
                                                 "# Ensure gui_modules is in the path\n    sys.path.append(os.path.dirname")
        
        if content != updated_content:
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Updated imports in {main_py_path}")
    
    return True

if __name__ == "__main__":
    print("Starting directory rename process...")
    if rename_directory():
        print("Directory renamed successfully.")
        print("Updating imports...")
        if update_imports():
            print("Imports updated successfully.")
            print("\nNext steps:")
            print("1. Run 'python test_basic_compression.py' to verify compression/decompression works")
            print("2. Run 'python main.py gui' to use the basic GUI")
            print("3. If needed, update more imports manually")
        else:
            print("Failed to update imports.")
    else:
        print("Directory rename failed.")
