# -*- coding: utf-8 -*-
"""
Seasonal: Web Application Entry Point
=====================================

Starts the FastAPI server that exposes the Seasonal engine and web UI.
"""

import uvicorn


def main() -> None:
    """
    Start the Seasonal FastAPI application using Uvicorn.

    The application instance `app` is defined in `src.web.server`.
    """
    uvicorn.run(
        "src.web.server:app",  # Import path to the FastAPI app
        host="0.0.0.0",        # Bind on all interfaces
        port=8000,             # Default HTTP port for the development server
        reload=True,           # Enable auto-reload during development
    )


if __name__ == "__main__":
    main()
