import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.schemas.user import UserJwtPayload
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from core.config import Settings

class auth_middleware(BaseHTTPMiddleware):
    def __init__(self, app, included_paths: list[str] = None):
        super().__init__(app)
        self.included_paths = included_paths or []

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Check if the request path is in the included paths
        if not any(path.startswith(included_path) for included_path in self.included_paths):
            return await call_next(request)
        
        auth_header = request.headers.get("authorization", "")
        jwt_token = auth_header.split(" ")[-1] if auth_header.startswith("Bearer ") else None

        if not jwt_token:
            return JSONResponse(
                {"error": "Authorization header or JWT token missing"},
                status_code=401
            )

        if not Settings().SECRET_KEY:
            return JSONResponse(
                {"error": "Secret key is not set in the environment"},
                status_code=500
            )

        try:
            payload = jwt.decode(jwt_token, Settings().SECRET_KEY, algorithms=["HS256"])
            request.state.user = UserJwtPayload(**payload)
        except ExpiredSignatureError:
            return JSONResponse({"error": "JWT token has expired"}, status_code=401)
        except InvalidTokenError as e:
            return JSONResponse({"error": f"Invalid JWT token: {str(e)}"}, status_code=401)
        except Exception as e:
            return JSONResponse({"error": f"Failed to decode JWT token: {str(e)}"}, status_code=400)

        return await call_next(request)
