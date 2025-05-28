import sys
import subprocess
import pkg_resources

def check_package(package_name):
    try:
        pkg_resources.get_distribution(package_name)
        print(f"✓ {package_name} is installed")
        return True
    except pkg_resources.DistributionNotFound:
        print(f"✗ {package_name} is not installed")
        return False

def check_orca():
    try:
        import plotly.io.orca
        print("✓ orca is installed and importable")
        return True
    except ImportError:
        print("✗ orca is not properly installed")
        return False

def install_package(package_name, use_conda=False):
    print(f"\nAttempting to install {package_name}...")
    try:
        if use_conda:
            subprocess.check_call([sys.executable, "-m", "conda", "install", "-c", "plotly", package_name, "-y"])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", package_name])
        print(f"✓ Successfully installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package_name}: {str(e)}")
        return False

def check_and_install_packages():
    # First check and install plotly and kaleido with pip
    required_packages = {
        'plotly': 'plotly',
        'kaleido': 'kaleido'
    }
    
    all_installed = True
    for package, install_name in required_packages.items():
        if not check_package(package):
            if not install_package(install_name):
                all_installed = False
    
    # Then check and install orca with conda
    if not check_orca():
        print("\nAttempting to install orca using conda...")
        if not install_package('plotly-orca', use_conda=True):
            print("\nFailed to install orca with conda. Please try installing it manually:")
            print("conda install -c plotly plotly-orca")
            all_installed = False
    
    return all_installed

# Check and install required packages
if not check_and_install_packages():
    print("\nSome required packages could not be installed. Please install them manually:")
    print("pip install -U plotly kaleido")
    print("conda install -c plotly plotly-orca")
    sys.exit(1)

import plotly.graph_objects as go
import os
from datetime import datetime
import plotly.io as pio

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
    print("\nDisplaying plot in browser...")
    if sys.stdout.isatty():
        # If in terminal, show in browser
        fig.show(renderer="browser")
    else:
        # If in notebook or other environment, use default renderer
        fig.show()
    
    # Set up save path
    save_path = "./trendplots"
    os.makedirs(save_path, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    base_filename = f"test_plot_{timestamp}"
    
    # Save as HTML
    html_path = os.path.join(save_path, f"{base_filename}.html")
    print(f"\nSaving HTML to: {html_path}")
    try:
        fig.write_html(html_path)
        if os.path.exists(html_path):
            size = os.path.getsize(html_path)
            print(f"HTML saved successfully! File size: {size} bytes")
        else:
            print("Warning: HTML file was not created despite no error")
    except Exception as e:
        print(f"Error saving HTML: {str(e)}")
    
    # Save as PDF
    pdf_path = os.path.join(save_path, f"{base_filename}.pdf")
    print(f"\nSaving PDF to: {pdf_path}")
    
    # Print current working directory and file path
    print(f"Current working directory: {os.getcwd()}")
    print(f"Full PDF path: {os.path.abspath(pdf_path)}")
    
    # Try kaleido first
    try:
        print("\nAttempting to save PDF using kaleido engine...")
        print("Available renderers:", pio.renderers)
        print("Default renderer:", pio.renderers.default)
        
        # Try using pio.write_image instead of fig.write_image
        pio.write_image(fig, pdf_path, engine='kaleido')
        
        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"PDF saved successfully with kaleido! File size: {size} bytes")
        else:
            print("Warning: PDF file was not created with kaleido despite no error")
            print("Checking directory contents:")
            print(os.listdir(save_path))
    except Exception as e:
        print(f"Error saving PDF with kaleido: {str(e)}")
        print("Error type:", type(e).__name__)
        
        # Try orca if kaleido fails
        try:
            print("\nAttempting to save PDF using orca engine...")
            pio.write_image(fig, pdf_path, engine='orca')
            if os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                print(f"PDF saved successfully with orca! File size: {size} bytes")
            else:
                print("Warning: PDF file was not created with orca despite no error")
                print("Checking directory contents:")
                print(os.listdir(save_path))
        except Exception as e:
            print(f"Error saving PDF with orca: {str(e)}")
            print("Error type:", type(e).__name__)

if __name__ == '__main__':
    main() 