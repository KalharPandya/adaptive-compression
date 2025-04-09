import gradio_components as gr
import os
import sys

def create_analysis_tab():
    """
    Create the Analysis tab for compression performance visualization
    
    Returns:
        tuple: (tab, inputs, outputs)
    """
    inputs = {}
    outputs = {}
    
    with gr.Tab("Analysis") as analysis_tab:
        gr.Markdown("""
        ### Compression Performance Analysis
        
        This section provides comprehensive visualizations and statistics about compression
        performance across different file types and compression methods.
        
        The analysis is based on your compression history, allowing you to understand
        which methods work best for different types of data.
        """)
        
        with gr.Row():
            inputs["analyze_btn"] = gr.Button("Generate Analysis", variant="primary")
            inputs["clear_history_btn"] = gr.Button("Clear History", variant="secondary")
        
        with gr.Row():
            outputs["summary_stats"] = gr.JSON(label="Summary Statistics")
        
        with gr.Tabs() as analysis_tabs:
            with gr.Tab("Compression Ratio"):
                gr.Markdown("""
                **Compression Ratio**: Shows how much each file was compressed relative to its original size.
                Lower values indicate better compression.
                """)
                outputs["ratio_plot"] = gr.Plot(label="Compression Ratio by File Type and Size")
                
            with gr.Tab("Method Usage"):
                gr.Markdown("""
                **Method Usage**: Shows which compression methods were most effective for different file types.
                """)
                outputs["method_plot"] = gr.Plot(label="Compression Method Usage")
                
            with gr.Tab("Size Comparison"):
                gr.Markdown("""
                **Size Comparison**: Direct comparison of original vs. compressed file sizes.
                """)
                outputs["size_plot"] = gr.Plot(label="Size Comparison by File Type")
                
            with gr.Tab("Throughput"):
                gr.Markdown("""
                **Throughput**: Shows compression speed in MB/s for different file types and sizes.
                Higher values indicate faster compression performance.
                """)
                outputs["throughput_plot"] = gr.Plot(label="Compression Throughput by File Type")
                
            with gr.Tab("File Type Summary"):
                gr.Markdown("""
                **File Type Summary**: Aggregates performance metrics by file extension.
                This view helps you understand which file types compress best.
                """)
                outputs["filetype_plot"] = gr.Plot(label="File Type Summary")
    
    return analysis_tab, inputs, outputs

def generate_enhanced_analysis(interface):
    """
    Generate enhanced analysis with additional visualization
    
    Args:
        interface: The EnhancedGradioInterface instance
        
    Returns:
        tuple: Output components for Gradio
    """
    try:
        # Get summary statistics
        summary = interface.analyzer.get_summary_stats()
        
        # Make sure all keys are strings for JSON compatibility
        summary = interface._ensure_serializable(summary)
        
        # Generate plots
        ratio_fig = interface.analyzer.plot_compression_ratio(figsize=(10, 6))
        method_fig = interface.analyzer.plot_method_usage(figsize=(10, 6))
        size_fig = interface.analyzer.plot_size_comparison(figsize=(10, 6))
        throughput_fig = interface.analyzer.plot_throughput(figsize=(10, 6))
        filetype_fig = interface.analyzer.plot_file_type_summary(figsize=(10, 6))
        
        return (
            summary,
            ratio_fig if ratio_fig else None,
            method_fig if method_fig else None,
            size_fig if size_fig else None,
            throughput_fig if throughput_fig else None,
            filetype_fig if filetype_fig else None
        )
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return (
            {"error": str(e)},
            None, None, None, None, None
        )
