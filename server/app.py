"""
Server entry point for multi-mode deployment.
Exposes the FastAPI app and a callable main() for use as a console script.
"""
import sys
import os

# Ensure the project root is on the path when this module is imported directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401 — re-export for ASGI runners

__all__ = ["app", "main"]


def main():
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860)),
        reload=False,
    )


if __name__ == "__main__":
    main()
