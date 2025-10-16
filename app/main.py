import socketio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.middlewares.auth import AuthMiddleware

from app.routes import query, user, upload, health, thread, extra
from app.socket_handler import sio

fastapi_app = FastAPI()

included_paths = ["/user", "/upload", "/query", "/thread", "/extra", "/mindmap", "/wordcloud"]
excluded_routes = [("POST", "/user"), ("POST", "/user/login")]
fastapi_app.add_middleware(
    AuthMiddleware, included_paths=included_paths, excluded_routes=excluded_routes
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

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
