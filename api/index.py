"""Vercel Python entrypoint. Wraps the existing Flask app for the serverless runtime."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app  # noqa: E402

app = create_app()
