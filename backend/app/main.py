"""
Compatibility shim - imports the FastAPI app from the package root.
Tests and other modules can import `from app.main import app`.
"""
import sys
import os

# Add the backend directory to the path so we can import the top-level main module
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from main import app  # noqa: F401

__all__ = ["app"]
