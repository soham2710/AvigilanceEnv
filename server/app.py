"""
Server entry point — re-exports the FastAPI app from the project root.
Placed here so multi-mode deployment tooling can discover it via server/app.py.
"""
import sys
import os

# Ensure the project root is on the path when this module is imported directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401 — re-export for ASGI runners

__all__ = ["app"]
