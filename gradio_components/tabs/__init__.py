# Tabs package for Gradio interface

# Make the individual tab modules accessible
__all__ = [
    'about',
    'compress', 
    'decompress',
    'analysis',
    'file_format',
    'help'
]

# Import the modules so they can be accessed directly from the tabs package
# Using try/except for each to avoid cascading failures
try:
    from . import about
except ImportError:
    pass

try:
    from . import compress
except ImportError:
    pass

try:
    from . import decompress
except ImportError:
    pass

try:
    from . import analysis
except ImportError:
    pass

try:
    from . import file_format
except ImportError:
    pass

try:
    from . import help
except ImportError:
    pass
