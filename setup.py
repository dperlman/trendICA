from setuptools import setup, find_packages

setup(
    name="gtrend_api_tools",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "requests",
        "pyyaml",
        "stem",  # for Tor control
        "trendspy",  # for TrendsPy
        "google-search-results",  # for SerpApiPy
    ],
    python_requires=">=3.6",
) 