#!/usr/bin/env python3
"""
Run the FastAPI server with auto-reload so Python changes apply immediately.

From project root:
  python run_api.py

Or:
  python -m app.main

For production (no reload), set RELOAD=false:
  RELOAD=false python run_api.py
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    use_reload = os.environ.get("RELOAD", "true").lower() in ("1", "true", "yes")
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=use_reload,
    )

    TESTSTTSTTS
