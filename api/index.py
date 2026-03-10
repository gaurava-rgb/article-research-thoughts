"""Vercel Python function entrypoint for the Second Brain FastAPI backend.

Vercel requirement: this file must be at api/index.py in the repo root.
The /api/* rewrites in vercel.json route all API requests here.

In local development, Next.js proxies /api/* to http://localhost:8000
(configured in frontend/next.config.ts). This file is used when running
FastAPI directly via `uvicorn api.index:app --port 8000`.
"""
import sys
import os
import traceback

# Add the backend directory to sys.path so `second_brain` package is importable.
# In Vercel's serverless environment, the repo root is the working directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Second Brain API")

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc), "trace": traceback.format_exc()})

# CORS: allow local Next.js dev server.
# In production on Vercel, same-origin (no CORS needed), but this is harmless.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        # Add your Vercel domain here after first deploy, e.g.:
        # "https://your-project.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _include_router():
    """Lazy-import the chat router to avoid loading heavy deps at module import time."""
    from second_brain.chat.router import router
    app.include_router(router, prefix="/api")


_include_router()
