import gradio_components as gr
import matplotlib.pyplot as plt
import os

def create_header(title):
    """
    Create the header section for the Gradio interface
    
    Args:
        title (str): The title to display
        
    Returns:
        tuple: The created row and column components
    """
    with gr.Row() as header_row:
        with gr.Column(scale=1):
            logo = gr.Image(value="https://via.placeholder.com/150x150?text=AC", shape=(150, 150), label="")
        with gr.Column(scale=4):
            header_title = gr.Markdown(f"# {title}")
            header_desc = gr.Markdown("""
            An intelligent compression algorithm that dynamically selects the optimal compression method 
            for different segments of your data based on their unique patterns and characteristics.
            """)
    
    return header_row

def toggle_detailed_stats(show):
    """
    Toggle visibility of detailed statistics
    
    Args:
        show (bool): Whether to show the statistics
        
    Returns:
        dict: Gradio update object
    """
    return gr.update(visible=show)

def clear_compression_history(interface):
    """
    Clear the compression history
    
    Args:
        interface: The EnhancedGradioInterface instance
        
    Returns:
        str: Status message
    """
    try:
        interface.analyzer.clear_results()
        if os.path.exists(interface.results_file):
            os.remove(interface.results_file)
        return "Compression history has been cleared."
    except Exception as e:
        return f"Error clearing history: {str(e)}"

def create_method_chart(stats):
    """
    Create a pie chart of compression method usage
    
    Args:
        stats (dict): Compression statistics containing method usage info
        
    Returns:
        matplotlib.figure.Figure or None: The created chart, or None if no data
    """
    if not stats or 'chunk_stats' not in stats:
        return None
        
    method_usage = stats.get('chunk_stats', {}).get('method_usage', {})
    if not method_usage:
        return None
        
    # Method names for labels
    method_names = {
        '1': 'RLE', '2': 'Dictionary', '3': 'Huffman', '4': 'Delta',
        '5': 'DEFLATE', '6': 'BZIP2', '7': 'LZMA', '8': 'ZStd',
        '9': 'LZ4', '10': 'Brotli', '11': 'LZHAM', '255': 'No Compression'
    }
    
    # Prepare data for pie chart
    labels = []
    sizes = []
    
    for method_id, count in method_usage.items():
        if count > 0:
            labels.append(method_names.get(str(method_id), f"Method {method_id}"))
            sizes.append(count)
    
    if not sizes:
        return None
        
    # Create pie chart
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.title('Compression Method Distribution')
    
    return fig
