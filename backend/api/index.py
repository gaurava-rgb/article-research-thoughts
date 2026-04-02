"""FastAPI application entry point.

Creates the app and registers all routers.
Used by the test suite and production ASGI server.
"""
from fastapi import FastAPI
from second_brain.chat.router import router

app = FastAPI(title="Second Brain API")
app.include_router(router, prefix="/api")
