import plotly.graph_objects as go
import sys
import os
import plotly.io as pio
import plotly.io.orca  # This might be needed for initialization

def main():
    # Create a simple line plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[1, 2, 3, 4, 5],
        y=[2, 4, 6, 8, 10],
        name='Test Line'
    ))
    
    # Update layout
    fig.update_layout(
        title='Test Plot',
        xaxis_title='X Axis',
        yaxis_title='Y Axis'
    )
    
    # Show in browser
    if sys.stdout.isatty():
        fig.show(renderer="browser")
    else:
        fig.show()
    
    # Save as PDF
    os.makedirs("./trendplots", exist_ok=True)
    pio.write_image(fig, "./trendplots/minimal_test.pdf", engine='kaleido')

if __name__ == '__main__':
    main() 