import gradio as gr  # Direct import of gradio

def create_file_format_tab():
    """
    Create the File Format tab with AMBC format documentation
    
    Returns:
        gr.Tab: The created File Format tab
    """
    with gr.Tab("File Format") as format_tab:
        gr.Markdown("""
        ## AMBC File Format
        
        The `.ambc` file format is a custom format designed for adaptive marker-based compression.
        It consists of a header followed by a series of compressed data packages.
        
        ### Header Structure
        
        ```
        ┌────────────┬────────────┬────────────┬────────────┬────────────┬────────────┐
        │   MAGIC    │   SIZE     │  MARKER    │ CHECKSUM   │  ORIG      │   COMP     │
        │  (4 bytes) │  (4 bytes) │  INFO      │  (17 bytes)│  SIZE      │   SIZE     │
        └────────────┴────────────┴────────────┴────────────┴────────────┴────────────┘
        ```
        
        - **MAGIC**: 4-byte signature "AMBC"
        - **SIZE**: Header size (4 bytes)
        - **MARKER INFO**: Marker length and bytes
        - **CHECKSUM**: MD5 hash of original data
        - **ORIG SIZE**: Original file size (8 bytes)
        - **COMP SIZE**: Compressed file size (8 bytes)
        
        ### Package Structure
        
        ```
        ┌────────────┬────────────┬────────────┬────────────┬────────────┐
        │  MARKER    │ METHOD ID  │ COMP SIZE  │ ORIG SIZE  │ COMP DATA  │
        └────────────┴────────────┴────────────┴────────────┴────────────┘
        ```
        
        - **MARKER**: Unique binary pattern
        - **METHOD ID**: Compression method identifier (1 byte)
        - **COMP SIZE**: Compressed data size (variable length)
        - **ORIG SIZE**: Original data size (variable length)
        - **COMP DATA**: Compressed data
        
        ### Compression Methods
        
        | ID  | Method             | Best For                      |
        |-----|--------------------|------------------------------ |
        | 1   | RLE                | Repeated sequences            |
        | 2   | Dictionary         | Recurring patterns            |
        | 3   | Huffman            | Skewed frequencies            |
        | 4   | Delta              | Small variations              |
        | 5   | DEFLATE            | General purpose               |
        | 6   | BZIP2              | Text data                     |
        | 7   | LZMA               | Large redundant data          |
        | 8   | ZStandard          | Most data types               |
        | 9   | LZ4                | Speed-critical data           |
        | 10  | Brotli             | Web content                   |
        | 11  | LZHAM              | Game assets                   |
        | 255 | No Compression     | Already compressed data       |
        """)
        
        with gr.Row():
            with gr.Column():
                gr.Image(value="https://dummyimage.com/500x300/000/fff&text=AMBC+Header+Structure", 
                        label="AMBC Header Structure")
            with gr.Column():
                gr.Image(value="https://dummyimage.com/500x300/000/fff&text=AMBC+Package+Structure", 
                        label="AMBC Package Structure")
                
    return format_tab
