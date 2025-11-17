import socketio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.middlewares.auth import AuthMiddleware
from app.middlewares.auth_paths import auth_paths

from app.routes import (
    insights,
    query,
    user,
    upload,
    health,
    thread,
    extra,
    strategic_roadmap,
    technical_roadmap,
    documents,
)
from app.socket_handler import sio

fastapi_app = FastAPI()

excluded_routes = [("POST", "/user"), ("POST", "/user/login")]
fastapi_app.add_middleware(
    AuthMiddleware, included_paths=auth_paths, excluded_routes=excluded_routes
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fastapi_app.mount("/static", StaticFiles(directory="app/public"), name="static")


fastapi_app.include_router(query.router)
fastapi_app.include_router(user.router)
fastapi_app.include_router(upload.router)
fastapi_app.include_router(health.router)
fastapi_app.include_router(thread.router)
fastapi_app.include_router(extra.router)
fastapi_app.include_router(strategic_roadmap.router)
fastapi_app.include_router(insights.router)
fastapi_app.include_router(technical_roadmap.router)
fastapi_app.include_router(documents.router)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
