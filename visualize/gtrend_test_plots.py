import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from gtrend import Trends
import argparse
import sys
from typing import Optional
import os
import plotly.io as pio
import plotly.io.orca  # This might be needed for initialization




def plot_stagger_search(
    stagger_groups: list[list[pd.DataFrame]], 
    title: str = None, 
    show: bool = True, 
    save: bool = True, 
    save_path: str = "./trendplots",
    line_width_scale: float = 1.0
) -> go.Figure:
    """
    Plot staggered search results with overlapping intervals.
    
    Args:
        stagger_groups (list[list[pd.DataFrame]]): List of groups, where each group is a list of DataFrames.
            Each DataFrame should have a datetime index and numeric columns.
        title (str, optional): Custom title for the plot. If None, defaults to "Google Trends"
        show (bool): Whether to display the plot in browser. Defaults to True.
        save (bool): Whether to save the plot as PDF and HTML. Defaults to True.
        save_path (str): Directory path to save the plots. Defaults to "./trendplots".
        line_width_scale (float): Multiplier for line width based on overlap count. Defaults to 1.0.
        
    Returns:
        go.Figure: The plotly figure object
        
    Raises:
        ValueError: If stagger_groups is empty or has invalid structure
        TypeError: If DataFrames don't have datetime index or numeric columns
    """
    # Input validation
    if not stagger_groups:
        raise ValueError("stagger_groups cannot be empty")
    
    if not all(isinstance(group, list) for group in stagger_groups):
        raise ValueError("Each group in stagger_groups must be a list")
        
    if not all(all(isinstance(df, pd.DataFrame) for df in group) for group in stagger_groups):
        raise ValueError("All elements in groups must be pandas DataFrames")
        
    # Validate DataFrame structure
    for group in stagger_groups:
        for df in group:
            if not isinstance(df.index, pd.DatetimeIndex):
                raise TypeError("All DataFrames must have a datetime index")
            if not all(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns):
                raise TypeError("All DataFrame columns must be numeric")
    
    # Create the plot
    fig = go.Figure()
    
    # Colors for different intervals
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
    # Dash patterns for different groups
    dash_patterns = ['solid', 'dot', 'dash', 'dashdot', 'longdash', 'longdashdot']
    
    # Dictionary to track how many times each date has been plotted
    date_counts = {}
    
    for i, group in enumerate(stagger_groups):
        for j, df in enumerate(group):
            # Use interval number (j) for color
            color = colors[j % len(colors)]
            # Use group number (i) for dash pattern
            dash = dash_patterns[i % len(dash_patterns)]
            
            # Plot each column in the DataFrame
            for col in df.columns:
                # Get the dates for this series
                dates = df.index
                values = df[col]
                
                # Find segments with different overlap counts
                segments = []
                current_segment = {'dates': [], 'values': [], 'count': 0}
                
                for date, value in zip(dates, values):
                    # Get current count for this date
                    current_count = date_counts.get(date, 0)
                    
                    if current_count != current_segment['count']:
                        # If we have a previous segment, save it
                        if current_segment['dates']:
                            segments.append(current_segment)
                        # Start new segment
                        current_segment = {
                            'dates': [date],
                            'values': [value],
                            'count': current_count
                        }
                    else:
                        # Add to current segment
                        current_segment['dates'].append(date)
                        current_segment['values'].append(value)
                    
                    # Update count for this date
                    date_counts[date] = current_count + 1
                
                # Add the last segment
                if current_segment['dates']:
                    segments.append(current_segment)
                
                # Plot each segment with appropriate width
                for segment in segments:
                    fig.add_trace(go.Scatter(
                        x=segment['dates'],
                        y=segment['values'],
                        name=f"Group {i+1}, Interval {j+1}, {col}",
                        line=dict(
                            color=color,
                            width=1 + segment['count'],  # Increase width based on overlap count
                            dash=dash
                        ),
                        showlegend=(i == 0 and j == 0)  # Only show legend for first trace
                    ))

    # Update layout
    title = title or "Google Trends"
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Interest",
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    if show:
        if sys.stdout.isatty():
            # If in terminal, show in browser
            fig.show(renderer="browser")
        else:
            # If in notebook or other environment, use default renderer
            fig.show()
            
    if save:
        # Create save directories if they don't exist
        pdf_dir = os.path.join(save_path, "pdf")
        html_dir = os.path.join(save_path, "html")
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)
        
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        base_filename = f"{title}_{current_time}"
        
        # Save as PDF using kaleido engine
        try:
            pdf_path = os.path.join(pdf_dir, f"{base_filename}.pdf")
            print(f"\nSaving PDF to: {pdf_path}")
            pio.write_image(fig, pdf_path, engine='kaleido')
            
            # Verify file was created
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"Plot saved as PDF: {pdf_path}")
                print(f"File size: {file_size} bytes")
            else:
                print(f"Warning: File {pdf_path} was not created despite no error being raised")
        except Exception as e:
            print(f"Error saving PDF: {str(e)}")
            print("If kaleido is not installed, try: pip install -U kaleido")
        
        # Save as HTML
        try:
            html_path = os.path.join(html_dir, f"{base_filename}.html")
            fig.write_html(html_path)
            if os.path.exists(html_path):
                file_size = os.path.getsize(html_path)
                print(f"Plot saved as HTML: {html_path}")
                print(f"File size: {file_size} bytes")
            else:
                print(f"Warning: HTML file {html_path} was not created despite no error being raised")
        except Exception as e:
            print(f"Warning: Could not save plot as HTML: {str(e)}")
            
    return fig


def plot_search(dataframe: pd.DataFrame) -> go.Figure:
    """
    Perform a search and plot the results.
    
    Args:
        search_term (str): The search term to look up
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        stagger (int): Number of overlapping intervals (0 means no overlap)
        scale (bool): Whether to scale overlapping intervals
        combine (str): How to combine multiple columns. Options are "none", "mean", "median", or "mode". Defaults to "none".
        title (str, optional): Custom title for the plot
        show (bool): Whether to display the plot
        save (bool): Whether to save the plot as PDF. Defaults to True.
        save_path (str): Directory path to save the plot. Defaults to "./trendplots".
        
    Returns:
        go.Figure: The plotly figure object
    """
    # Perform the search
    time_range = f"{start_date} {end_date}"
    result = self.trends.search_by_day(
        search_term=search_term,
        time_range=time_range,
        stagger=stagger,
        scale=scale,
        combine=combine,
        raw_groups=combine == "none"
    )
    
    # Create the plot
    fig = go.Figure()
    
    if combine == "none":
        # Colors for different intervals
        colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
        # Dash patterns for different groups
        dash_patterns = ['solid', 'dot', 'dash', 'dashdot', 'longdash', 'longdashdot']
        
        # Dictionary to track how many times each date has been plotted
        date_counts = {}
        
        for i, group in enumerate(result):
            for j, df in enumerate(group):
                # Use interval number (j) for color
                color = colors[j % len(colors)]
                # Use group number (i) for dash pattern
                dash = dash_patterns[i % len(dash_patterns)]
                
                # Plot each column in the DataFrame
                for col in df.columns:
                    # Get the dates for this series
                    dates = df.index
                    values = df[col]
                    
                    # Find segments with different overlap counts
                    segments = []
                    current_segment = {'dates': [], 'values': [], 'count': 0}
                    
                    for date, value in zip(dates, values):
                        # Get current count for this date
                        current_count = date_counts.get(date, 0)
                        
                        if current_count != current_segment['count']:
                            # If we have a previous segment, save it
                            if current_segment['dates']:
                                segments.append(current_segment)
                            # Start new segment
                            current_segment = {
                                'dates': [date],
                                'values': [value],
                                'count': current_count
                            }
                        else:
                            # Add to current segment
                            current_segment['dates'].append(date)
                            current_segment['values'].append(value)
                        
                        # Update count for this date
                        date_counts[date] = current_count + 1
                    
                    # Add the last segment
                    if current_segment['dates']:
                        segments.append(current_segment)
                    
                    # Plot each segment with appropriate width
                    for segment in segments:
                        fig.add_trace(go.Scatter(
                            x=segment['dates'],
                            y=segment['values'],
                            name=f"Group {i+1}, Interval {j+1}, {col}",
                            line=dict(
                                color=color,
                                width=1 + segment['count'],  # Increase width based on overlap count
                                dash=dash
                            ),
                            showlegend=(i == 0 and j == 0)  # Only show legend for first trace
                        ))
    else:
        # Single line plot
        # Get the actual column name from the DataFrame
        column_name = result.columns[0]
        fig.add_trace(go.Scatter(
            x=result.index,
            y=result[column_name],
            name=search_term,
            line=dict(width=2)
        ))
    
    # Update layout
    title = title or f"Google Trends: {search_term}"
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Interest",
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    if show:
        if sys.stdout.isatty():
            # If in terminal, show in browser
            fig.show(renderer="browser")
        else:
            # If in notebook or other environment, use default renderer
            fig.show()
            
    if save:
        # Create save directories if they don't exist
        pdf_dir = os.path.join(save_path, "pdf")
        html_dir = os.path.join(save_path, "html")
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)
        
        # Generate filename based on API, search term, time range, and current time
        api_name = self.api if self.api else "auto"
        safe_search_term = search_term.replace(" ", "_")
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        base_filename = f"{api_name}_{safe_search_term}_{start_date}_to_{end_date}_{current_time}"
        
        # Save as PDF using kaleido engine
        try:
            pdf_path = os.path.join(pdf_dir, f"{base_filename}.pdf")
            print(f"\nSaving PDF to: {pdf_path}")
            pio.write_image(fig, pdf_path, engine='kaleido')
            
            # Verify file was created
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"Plot saved as PDF: {pdf_path}")
                print(f"File size: {file_size} bytes")
            else:
                print(f"Warning: File {pdf_path} was not created despite no error being raised")
        except Exception as e:
            print(f"Error saving PDF: {str(e)}")
            print("If kaleido is not installed, try: pip install -U kaleido")
        
        # Save as HTML
        try:
            html_path = os.path.join(html_dir, f"{base_filename}.html")
            fig.write_html(html_path)
            if os.path.exists(html_path):
                file_size = os.path.getsize(html_path)
                print(f"Plot saved as HTML: {html_path}")
                print(f"File size: {file_size} bytes")
            else:
                print(f"Warning: HTML file {html_path} was not created despite no error being raised")
        except Exception as e:
            print(f"Warning: Could not save plot as HTML: {str(e)}")
    return fig

def main():
    parser = argparse.ArgumentParser(description='Plot Google Trends data')
    parser.add_argument('search_term', nargs='?', default="artificial intelligence", help='Search term to look up (default: "artificial intelligence")')
    parser.add_argument('start_date', nargs='?', default="2023-01-01", help='Start date (YYYY-MM-DD) (default: 2023-01-01)')
    parser.add_argument('end_date', nargs='?', default="2023-09-28", help='End date (YYYY-MM-DD) (default: 270 days from start)')
    parser.add_argument('--stagger', type=int, default=0, help='Number of overlapping intervals')
    parser.add_argument('--no-scale', action='store_false', dest='scale', help='Disable scaling of overlapping intervals')
    parser.add_argument('--combine', type=str, default="median", choices=["none", "mean", "median", "mode"], help='How to combine multiple columns (none, mean, median, or mode)')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making API calls')
    parser.add_argument('--serpapi-key', help='SerpAPI key for making real API calls')
    parser.add_argument('--serpwow-key', help='SerpWow key for making real API calls')
    parser.add_argument('--searchapi-key', help='SearchApi key for making real API calls')
    parser.add_argument('--no-cache', action='store_true', help='Whether to skip cached results (only used with SerpAPI)')
    parser.add_argument('--proxy', help='The proxy to use. If None, no proxy will be used')
    parser.add_argument('--change-identity', action='store_true', help='Whether to change Tor identity between iterations')
    parser.add_argument('--request-delay', type=int, default=4, help='Delay between requests in seconds')
    parser.add_argument('--geo', help='Geographic location for the search (e.g. "US")')
    parser.add_argument('--cat', help='Category for the search')
    parser.add_argument('--title', help='Custom title for the plot')
    parser.add_argument('--verbose', action='store_true', help='Print detailed information about the search process')
    parser.add_argument('--api', choices=['serpapi', 'serpwow', 'searchapi', 'trendspy'], help='Which API to use')
    parser.add_argument('--no-save', action='store_false', dest='save', help='Do not save the plot as PDF')
    parser.add_argument('--save-path', default="./trendplots", help='Directory path to save plots (default: ./trendplots)')
    parser.add_argument('--no-show', action='store_false', dest='show', help='Do not display the plot')
    
    args = parser.parse_args()
    
    plotter = TrendsPlotter(
        serpapi_api_key=args.serpapi_key,
        serpwow_api_key=args.serpwow_key,
        searchapi_api_key=args.searchapi_key,
        no_cache=args.no_cache,
        proxy=args.proxy,
        change_identity=args.change_identity,
        request_delay=args.request_delay,
        geo=args.geo,
        cat=args.cat,
        dry_run=args.dry_run,
        verbose=args.verbose,
        api=args.api
    )
    
    # Call plot_search and ignore the return value
    _ = plotter.plot_search(
        search_term=args.search_term,
        start_date=args.start_date,
        end_date=args.end_date,
        stagger=args.stagger,
        scale=args.scale,
        combine=args.combine,
        title=args.title,
        show=args.show,
        save=args.save,
        save_path=args.save_path
    )

if __name__ == '__main__':
    main() 