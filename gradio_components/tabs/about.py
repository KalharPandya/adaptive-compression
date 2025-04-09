import gradio_components as gr

def create_about_tab():
    """
    Create the About tab with information about the compression algorithm
    
    Returns:
        gr.Tab: The created About tab
    """
    with gr.Tab("About") as about_tab:
        gr.Markdown("""
        ## About Adaptive Marker-Based Compression
        
        This application demonstrates a novel approach to data compression that achieves superior 
        compression ratios by analyzing data patterns at a granular level and applying the most effective
        compression technique to each segment.

        ### Key Features

        - **Adaptive Compression**: Automatically selects the best method for each data chunk
        - **Marker-Based Approach**: Uses unique binary patterns to seamlessly transition between methods
        - **Multiple Techniques**: Incorporates RLE, Dictionary-based, Huffman, Delta, and more
        - **Visual Analytics**: Comprehensive visualizations of compression performance
        - **Cross-Platform Support**: Works on Windows, macOS, and Linux

        ### How It Works

        1. **Marker Finding**: Identifies the shortest binary string not present in your data
        2. **Chunk Analysis**: Divides data into optimal segments and analyzes patterns
        3. **Method Selection**: Tests multiple compression methods on each chunk
        4. **Adaptive Compression**: Applies the best method to each segment
        5. **Package Creation**: Assembles compressed chunks with markers and metadata
        """)
        
        with gr.Row():
            with gr.Column():
                gr.Image(value="https://via.placeholder.com/600x400?text=Adaptive+Compression+Diagram", 
                        label="Adaptive Compression Process")
            with gr.Column():
                gr.Image(value="https://via.placeholder.com/600x400?text=File+Format+Structure", 
                        label="AMBC File Format")
                        
    return about_tab
