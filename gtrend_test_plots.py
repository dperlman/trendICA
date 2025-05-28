import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from gtrend import Trends
import argparse
import sys
from typing import Optional
from keys import SERPAPI_API_KEY, SERPWOW_API_KEY, SEARCHAPI_API_KEY
import os
import plotly.io as pio
import plotly.io.orca  # This might be needed for initialization


class TrendsPlotter:
    def __init__(
        self,
        serpapi_api_key: str = SERPAPI_API_KEY,
        serpwow_api_key: str = SERPWOW_API_KEY,
        searchapi_api_key: str = SEARCHAPI_API_KEY,
        no_cache: bool = False,
        proxy: str = None,
        change_identity: bool = True,
        request_delay: int = 4,
        geo: str = None,
        cat: str = None,
        dry_run: bool = False,
        verbose: bool = True,
        api: str = None
    ):
        """
        Initialize the TrendsPlotter with configuration for API access.
        
        Args:
            serpapi_api_key (str, optional): SerpAPI key for making real API calls
            serpwow_api_key (str, optional): SerpWow key for making real API calls
            searchapi_api_key (str, optional): SearchApi key for making real API calls
            no_cache (bool): Whether to skip cached results (only used with SerpAPI)
            proxy (str, optional): The proxy to use. If None, no proxy will be used
            change_identity (bool): Whether to change Tor identity between iterations
            request_delay (int): Delay between requests in seconds
            geo (str, optional): Geographic location for the search (e.g. "US")
            cat (str, optional): Category for the search
            dry_run (bool): If True, no actual API calls will be made
            verbose (bool): If True, prints detailed information about the search process
            api (str, optional): Which API to use ("serpapi", "serpwow", "searchapi", or "trendspy")
        """
        # Store the API choice
        self.api = api
        
        # Create the Trends instance with all parameters
        self.trends = Trends(
            serpapi_api_key=serpapi_api_key,
            serpwow_api_key=serpwow_api_key,
            searchapi_api_key=searchapi_api_key,
            no_cache=no_cache,
            proxy=proxy,
            change_identity=change_identity,
            request_delay=request_delay,
            geo=geo,
            cat=cat,
            dry_run=dry_run,
            verbose=verbose,
            api=api  # Pass the API choice to the Trends class
        )

    def plot_search(
        self,
        search_term: str,
        start_date: str,
        end_date: str,
        stagger: int = 0,
        scale: bool = True,
        combine: str = "none",
        title: str = None,
        show: bool = True,
        save: bool = True,
        save_path: str = "./trendplots"
    ) -> go.Figure:
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