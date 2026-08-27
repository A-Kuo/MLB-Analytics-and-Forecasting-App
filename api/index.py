"""Vercel Python Function entry point.

Wraps the existing macroservice/api.py FastAPI app under an /api prefix
without touching that file -- it stays fully usable standalone exactly as
its own docstring describes (``uvicorn macroservice.api:app``, unprefixed
routes like /health, /teams). Vercel forwards a request's full original
path (e.g. /api/teams) to whichever function handles it (see vercel.json's
rewrite), so this wrapper mounts the real app at /api to match, rather
than changing macroservice/api.py's route paths.

This phase deliberately does NOT extend macroservice/api.py's route
surface -- that grows alongside real frontend consumers in later phases,
not speculatively ahead of them. See the Phase 1 plan for the explicit
feasibility check this file exists to support: confirming the full
scikit-learn/scipy/pandas dependency set actually fits Vercel's Python
function size/cold-start budget before Phases 2-4 build on top of it.
"""
from fastapi import FastAPI

from macroservice.api import app as macroservice_app

app = FastAPI()
app.mount("/api", macroservice_app)

__all__ = ["app"]
