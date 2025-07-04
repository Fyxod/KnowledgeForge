import socketio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.middlewares.auth_middleware import auth_middleware

from app.routes import root
from app.socket import sio

fastapi_app = FastAPI()

included_paths = ["/user", "/upload", "/query"]

fastapi_app.add_middleware(auth_middleware, included_paths=included_paths)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.mount("/static", StaticFiles(directory="app/public"), name="static")

fastapi_app.include_router(root.router)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
