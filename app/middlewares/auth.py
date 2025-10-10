import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import Settings
from core.models.user import UserJwtPayload


def normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        included_paths: list[str] = None,
        excluded_routes: list[tuple[str, str]] = None,
    ):
        super().__init__(app)
        self.included_paths = included_paths or []
        self.excluded_routes = excluded_routes or []

    async def dispatch(self, request: Request, call_next):
        path = normalize_path(request.url.path)
        method = request.method.upper()

        print(f"Request path: {path}, method: {method}")

        # Skip auth if (method, path) is excluded
        if (method, path) in self.excluded_routes:
            return await call_next(request)

        # Skip auth if not in included paths
        if not any(path == p or path.startswith(p + "/") for p in self.included_paths):
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("authorization", "")
        jwt_token = (
            auth_header.split(" ")[-1] if auth_header.startswith("Bearer ") else None
        )

        if not jwt_token:
            return JSONResponse(
                {"error": "Authorization header or JWT token missing"},
                status_code=401,
            )

        if not Settings().SECRET_KEY:
            return JSONResponse(
                {"error": "Secret key is not set in the environment"},
                status_code=500,
            )

        # Verify token
        try:
            payload = jwt.decode(jwt_token, Settings().SECRET_KEY, algorithms=["HS256"])
            request.state.user = UserJwtPayload(**payload)
        except ExpiredSignatureError:
            return JSONResponse({"error": "JWT token has expired"}, status_code=401)
        except InvalidTokenError as e:
            return JSONResponse(
                {"error": f"Invalid JWT token: {str(e)}"}, status_code=401
            )
        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to decode JWT token: {str(e)}"}, status_code=400
            )

        return await call_next(request)
