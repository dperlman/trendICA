from setuptools import setup, find_packages

setup(
    name="gtrend_api_tools",
    version="0.1.0_alpha",
    description="Tools for working with Google Trends APIs",
    author="David M. Perlman",
    author_email="omgoleus+gtrend@gmail.com",
    packages=find_packages(include=['gtrend_api_tools', 'gtrend_api_tools.*']),
    package_dir={'': '.'},
    install_requires=[
        "pandas",
        "requests",
        "pyyaml",
    ],
    extras_require={
        'tor': ['stem'],  # for Tor control
        'trendspy': ['trendspy'],  # for TrendsPy
        'serpapi': ['google-search-results'],  # for SerpApiPy
        'all': ['stem', 'trendspy', 'google-search-results'],  # all optional dependencies
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
) 