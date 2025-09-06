"""
Virtual Environment Manager - Python package for comprehensive virtual environment management.

This package provides equivalent functionality to the bash venv.sh script,
offering virtual environment creation, activation, package management, and auto-activation features.
"""

__version__ = "1.0.0"
__author__ = "anhvth5"
try:
    from .manager import VenvManager
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "uv", "rich", "typer", "virtualenv"])
    from .manager import VenvManager

__all__ = ["VenvManager"]