# Changelog

## 0.1.1 (April 9, 2025)

### Bug Fixes

- **UI Improvements**:
  - Fixed chunk size selection to use the mathematical formula `2^(10+k)` directly in the UI
  - Added a dropdown for chunk size options instead of a slider for clearer understanding
  - Fixed issues with handling filenames containing "_decompressed" suffixes
  - Improved module loading for the Analysis tab to prevent it from being missing

- **Import Structure**:
  - Fixed circular import issues in the gradio_components module
  - Added better path handling to find module files across different directory structures
  - Improved error handling and fallback mechanisms for failed imports

- **Compatibility**:
  - Enhanced support for different Gradio versions
  - Added compatibility layer for compression libraries
  - Improved error handling for missing dependencies

### Feature Enhancements

- **Decompression**:
  - Added custom filename option for decompressed files
  - Added option to preserve original file extension

- **UI Improvements**:
  - Made the chunk size selection more intuitive with descriptive values
  - Enhanced module loading across different environments

## 0.1.0 (April 8, 2025)

- Initial release
- Basic compression and decompression functionality
- Added visualization of compression method usage
- Created modular Gradio interface
