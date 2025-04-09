import gradio as gr  # Direct import of gradio

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
           - Optionally adjust the chunk size and multithreading settings
           - Click "Compress File"
           - Download the compressed `.ambc` file when ready
           
        2. **Decompress a File**:
           - Go to the "Decompress" tab
           - Upload a `.ambc` file using the "Compressed .ambc File" selector
           - Optionally set a custom output filename or preserve original extension
           - Click "Decompress File"
           - Download the decompressed file when ready
           
        3. **Analyze Compression Performance**:
           - Go to the "Analysis" tab
           - Click "Generate Analysis"
           - Explore the different visualization tabs to understand compression performance
           
        ### Advanced Settings
        
        - **Chunk Size**: Controls the size of data segments for analysis and compression
          - The size follows the formula 2^(10+k), where k is a power value from 0 to 6
          - Smaller chunks (k=0-1): Better for files with varied data patterns
          - Medium chunks (k=2-3): Good balance for most files
          - Larger chunks (k=4-6): Better for homogeneous data, faster processing
           
        - **Multithreading**: Enables parallel processing for faster compression
          - Recommended for large files on systems with multiple CPU cores
          - May increase memory usage
          
        ### Troubleshooting
        
        - **Compression is slow**: Try increasing chunk size or enabling multithreading
        - **Compressed file is larger than expected**: Some data types are already compressed or have high entropy
        - **Error during decompression**: Ensure the file is a valid `.ambc` file
        - **Analysis shows no data**: Compression history may be empty or corrupted
        - **Filename issues**: Use custom filename option in the decompression tab
        """)
                
    return help_tab
