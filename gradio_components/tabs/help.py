import gradio_components as gr

def create_help_tab():
    """
    Create the Help tab with usage instructions
    
    Returns:
        gr.Tab: The created Help tab
    """
    with gr.Tab("Help") as help_tab:
        gr.Markdown("""
        ## Help & Documentation
        
        ### Basic Usage
        
        1. **Compress a File**:
           - Go to the "Compress" tab
           - Upload a file using the "Input File" selector
           - Click "Compress File"
           - Download the compressed `.ambc` file when ready
           
        2. **Decompress a File**:
           - Go to the "Decompress" tab
           - Upload a `.ambc` file using the "Compressed .ambc File" selector
           - Click "Decompress File"
           - Download the decompressed file when ready
           
        3. **Analyze Compression Performance**:
           - Go to the "Analysis" tab
           - Click "Generate Analysis"
           - Explore the different visualization tabs to understand compression performance
           
        ### Advanced Settings
        
        - **Chunk Size**: Controls the size of data segments for analysis and compression
          - Smaller chunks (512-4096 bytes): Better for varied data with changing patterns
          - Larger chunks (8192-65536 bytes): Better for homogeneous data, faster processing
          
        - **Multithreading**: Enables parallel processing for faster compression
          - Recommended for large files on systems with multiple CPU cores
          - May increase memory usage
          
        ### Troubleshooting
        
        - **Compression is slow**: Try increasing chunk size or enabling multithreading
        - **Compressed file is larger than expected**: Some data types are already compressed or have high entropy
        - **Error during decompression**: Ensure the file is a valid `.ambc` file
        - **Analysis shows no data**: Compression history may be empty or corrupted
        """)
                
    return help_tab
