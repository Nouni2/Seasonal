# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
