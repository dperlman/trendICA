import numpy as np

def sinc_data(num_zero_crossings: int, max_value: float, min_value: float, num_points: int) -> np.ndarray:
    """
    Generate a sinc-like signal with specified parameters.
    
    Args:
        num_zero_crossings (int): Number of zero crossings on the positive axis only
        max_value (float): Maximum value of the signal
        min_value (float): Minimum value of the signal (will be at the edges)
        num_points (int): Number of points in the output array
        
    Returns:
        np.ndarray: Array of values following a sinc-like pattern
        
    Example:
        >>> data = sinc_data(2, 1.0, 0.0, 100)
        >>> # Returns array of length 100 with:
        >>> # - 2 zero crossings on positive axis
        >>> # - Maximum value of 1.0 at center
        >>> # - Minimum value of 0.0 at edges
    """
    # Create x values from -1 to 1
    x = np.linspace(-1, 1, num_points)
    
    # Scale x by number of zero crossings to fit more cycles
    x_scaled = x * num_zero_crossings
    
    # Generate sinc function
    # Add small epsilon to avoid division by zero
    epsilon = 1e-10
    y = np.sin(np.pi * x_scaled) / (np.pi * x_scaled + epsilon)
    
    # Scale to desired range
    # First scale to 0-1 range (except the first one)
    #y = (y - y.min()) / (y.max() - y.min())
    y = (y - -0.217233) / (y.max() - -0.217233) # this is always the global min value for the sinc function

    # Then scale to desired range
    y = y * (max_value - min_value) + min_value
    
    
    return y

if __name__ == "__main__":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import sys
    
    # Constants
    NUM_POINTS = 1000
    MAX_VALUE = 1.0
    MIN_VALUE = 0.0
    ZERO_CROSSINGS = [1, 2, 3, 4, 5]  # Different numbers of zero crossings to plot
    
    # Create figure
    fig = go.Figure()
    
    # Generate and plot sinc functions for each number of zero crossings
    for n in ZERO_CROSSINGS:
        y = sinc_data(n, MAX_VALUE, MIN_VALUE, NUM_POINTS)
        x = np.linspace(-1, 1, NUM_POINTS)  # Fixed x range from -1 to 1
        
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            name=f"{n} zero crossing{'s' if n != 1 else ''}",
            mode='lines'
        ))
    
    # Update layout
    fig.update_layout(
        title="Sinc Functions with Different Numbers of Zero Crossings",
        xaxis_title="x",
        yaxis_title="y",
        hovermode="x unified",
        showlegend=True,
        template="plotly_white"
    )
    
    # Show in browser
    if sys.stdout.isatty():
        fig.show(renderer="browser")
    else:
        fig.show() 