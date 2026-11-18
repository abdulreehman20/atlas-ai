"""Cloud / CLI entrypoint shim.

FastAPI Cloud and some hosts look for `main:app` at the application directory root.
The real app lives in `app.main`; re-export it here for discovery.
"""

from app.main import app

__all__ = ["app"]
