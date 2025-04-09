# Known Issues and Troubleshooting

This document describes known issues with the current version of the Adaptive Compression Tool and provides workarounds.

## Import Issues with Gradio Components

### Issue Description

When running the application with the enhanced Gradio interface, you may see errors such as:

```
Failed to import .tabs.about: No module named '.tabs'
Failed to import .tabs.compress: No module named '.tabs'
Failed to import .utils: No module named '.utils'
```

This is typically caused by Python's module resolution when importing from subdirectories within the project.

### Workaround

The application includes fallback mechanisms, so it should still work with a basic interface. If you want to use the enhanced interface with all features:

1. Make sure you're running the application from the project root directory:
   ```
   cd /path/to/adaptive-compression
   python main.py
   ```

2. You can also explicitly set the Python path:
   ```
   export PYTHONPATH=$PYTHONPATH:/path/to/adaptive-compression
   python main.py
   ```

3. If you're still having issues, try installing the application as a package:
   ```
   pip install -e .
   ```

## Gradio Version Compatibility

### Issue Description

The enhanced UI requires Gradio version 3.0.0 or higher with Blocks API support. Some features may not work properly with older versions.

### Workaround

Upgrade to the latest version of Gradio:
```
pip install --upgrade gradio>=3.0.0
```

You can also use the `--install-gradio` flag:
```
python main.py gui --install-gradio
```

## Missing Compression Libraries

### Issue Description

You may see messages that certain compression libraries like LZHAM or Brotli are not available.

### Workaround

Install the optional compression libraries for improved performance:
```
pip install zstandard>=0.15.0 lz4>=3.0.0 Brotli>=1.0.9
```

For LZHAM, which requires manual compilation:
1. Visit the LZHAM GitHub repository for installation instructions
2. Alternatively, the compression system will still work without LZHAM, just with fewer available methods

## Memory Issues with Large Files

### Issue Description

When compressing very large files (multiple GB), you may encounter memory errors, especially when using advanced compression methods like LZMA.

### Workaround

1. Use a larger chunk size to reduce overhead:
   ```
   python main.py compress large_file.dat output.ambc --chunk-size 16384
   ```

2. Disable multithreading in the GUI for more predictable memory usage

3. For extremely large files, consider using the command-line interface rather than the GUI

## Circular Import Issues During Development

### Issue Description

When modifying the code, especially in the `gradio_components` directory, you may encounter circular import errors.

### Workaround

1. Use lazy imports in `__init__.py` files
2. Import modules when needed rather than at the top level
3. Use relative imports (`from .module import X`) rather than absolute imports for internal modules

## Bug Reporting

If you encounter issues not described here, please report them on the GitHub repository with:

1. A detailed description of the issue
2. Steps to reproduce
3. Your environment information (OS, Python version, and package versions)
4. Any error messages or logs
