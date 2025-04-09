# Setup Guide for Adaptive Compression Tool

This document provides instructions for setting up and troubleshooting the Adaptive Compression Tool.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/KalharPandya/adaptive-compression.git
   cd adaptive-compression
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Optional: Install additional compression libraries for enhanced performance:
   ```
   pip install zstandard>=0.15.0 lz4>=3.0.0 Brotli>=1.0.9
   ```

## Running the Application

The application provides both a command-line interface and a graphical user interface.

### Command-Line Interface

```
# Compress a file
python main.py compress input_file output_file.ambc --chunk-size 4096

# Decompress a file
python main.py decompress input_file.ambc output_file

# Analyze compression results
python main.py analyze --results-file compression_results/compression_history.json --output-dir analysis_output
```

### Graphical User Interface

```
# Launch the GUI (default)
python main.py

# Alternatively, use the explicit GUI command
python main.py gui

# If Gradio is not installed, you can also install it automatically
python main.py gui --install-gradio
```

## Troubleshooting

### Import Errors

If you encounter import errors related to the Gradio interface, try the following:

1. Ensure Gradio is installed and up to date:
   ```
   pip install --upgrade gradio>=3.0.0
   ```

2. Fix import cycles by making sure the Python path is correctly set:
   ```
   export PYTHONPATH=$PYTHONPATH:/path/to/adaptive-compression
   ```

3. If you see errors about missing modules like `Unable to import gradio_components`, try:
   ```
   python -c "import sys; print(sys.path)"
   ```
   to verify the Python path includes the project directory.

### Compression Method Errors

If you encounter errors related to compression methods:

1. Check which compression libraries are available:
   ```python
   python -c "from compression_fix import check_compression_libraries; print(check_compression_libraries())"
   ```

2. Install the missing compression libraries as recommended above.

3. If an error occurs specifically with one compression method, you can still use the tool with the other methods.

### GUI Not Displaying

If the GUI fails to display:

1. Check if Gradio is properly installed:
   ```
   pip install gradio>=3.0.0
   ```

2. Make sure you have a browser available for the GUI to open in.

3. If you're in a headless environment, try using the command-line interface instead.

## Advanced Customization

### Adding New Compression Methods

To add a new compression method:

1. Create a new class that inherits from `CompressionMethod` in a separate module
2. Implement the required methods: `type_id`, `compress`, `decompress`, and `should_use`
3. Import and register the new method in `compression_fix.py`

### Customizing Chunk Size

The chunk size dramatically affects compression performance:

- Smaller chunks (e.g., 1024 bytes) provide more granular method selection but have higher overhead
- Larger chunks (e.g., 16384 bytes) have less overhead but potentially lower compression efficiency
- The default of 4096 bytes works well for most use cases

Customize the chunk size with the `--chunk-size` parameter when using the CLI, or with the slider in the GUI.

## Contact and Support

If you encounter issues not addressed here, please:

1. Check the existing GitHub issues
2. Open a new issue with detailed information about the problem
3. Include your environment details: OS, Python version, and package versions

For contribution guidelines, please see the repository README.
