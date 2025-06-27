"""
Setup script for Terminal Continue Monitor

Provides package installation and distribution configuration.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="terminal-continue-monitor",
    version="1.0.0",
    author="dbbuilder",
    author_email="",
    description="Automated terminal session activity monitor for Windows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbbuilder/terminalcontinue",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Terminals",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "build": [
            "setuptools>=69.0.2",
            "wheel>=0.42.0",
            "pyinstaller>=6.2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "terminal-monitor=src.terminal_monitor:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.yml", "*.md", "*.txt"],
    },
    include_package_data=True,
    keywords="terminal, monitoring, automation, windows, inactivity, session",
    project_urls={
        "Bug Reports": "https://github.com/dbbuilder/terminalcontinue/issues",
        "Source": "https://github.com/dbbuilder/terminalcontinue",
        "Documentation": "https://github.com/dbbuilder/terminalcontinue#readme",
    },
)
