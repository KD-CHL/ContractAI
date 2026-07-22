"""Vercel serverless entry point for ContractGuard FastAPI application."""

import sys
from pathlib import Path

# Add src to path so contract_guard is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contract_guard.main import app  # noqa: E402

# Vercel's Python runtime expects a handler variable
handler = app
