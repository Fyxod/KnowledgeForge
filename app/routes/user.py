import uuid
"""
This module defines the FastAPI routes for user management, including user creation, retrieval, and authentication.

Routes:
    - POST /user/ : Create a new user account.
    - GET /user/{user_id} : Retrieve user details for the authenticated user.
    - POST /user/login : Authenticate a user and return a JWT token.

Dependencies:
    - FastAPI for API routing and HTTP exception handling.
    - PyJWT for JWT token encoding.
    - uuid for generating unique user IDs.
    - Custom modules for configuration, database access, user models, and password hashing utilities.

Models:
    - UserCreateModel: Input model for user creation.
    - UserLoginModel: Input model for user login.
    - UserResponseModel: Output model for user data.
    - UserJwtPayload: Model for JWT payload structure.

Utilities:
    - hash_password: Hashes user passwords for secure storage.
    - verify_password: Verifies user passwords during login.

Database:
    - Uses a MongoDB collection (db.users) for storing and retrieving user data.

Security:
    - Passwords are hashed before storage.
    - JWT tokens are used for authentication.
    - Endpoints enforce authentication and authorization checks.

"""
import jwt

from fastapi import APIRouter, HTTPException, Request

from core.config import settings
from core.database import db
from core.models.user import (
    UserCreateModel,
    UserJwtPayload,
    UserLoginModel,
    UserResponseModel,
)
from core.utils.bcrypt import hash_password, verify_password

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/")
def create_user(user_input: UserCreateModel):
    if db.users.find_one({"email": user_input.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    user_dict = user_input.model_dump()
    print("Creating user with input:", user_dict)

    name_filtered = user_dict["name"].strip().lower().replace(" ", "_")
    user_dict["name"] = user_dict["name"].strip().title()
    user_dict["password"] = hash_password(user_dict["password"])
    user_dict["userId"] = f"{name_filtered}_{uuid.uuid4().hex[:6]}"
    user_dict["is_active"] = True
    user_dict["threads"] = {}

    result = db.users.insert_one(user_dict)
    print("User created with ID:", result.inserted_id)

    created_user = db.users.find_one(
        {"_id": result.inserted_id}, {"password": 0, "_id": 0}
    )
    print("Created user:", created_user)
    return {
        "status": "success",
        "message": "User created successfully",
        "user": UserResponseModel(**created_user),
    }


@router.get("/{user_id}")
def get_user(request: Request, user_id: str):
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    if payload.userId != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this user")

    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": "success",
        "message": "User retrieved successfully",
        "user": user,
    }


@router.post("/login")
def login_user(user_input: UserLoginModel):
    user_data = user_input.model_dump()
    print("Login attempt with input:", user_data)

    user = db.users.find_one({"email": user_data["email"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user_data["password"], user["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = jwt.encode(
        UserJwtPayload(
            userId=user["userId"],
            name=user["name"],
            email=user["email"],
            is_active=user.get("is_active", True),
        ).model_dump(),
        key=settings.SECRET_KEY,
        algorithm="HS256",
    )

    user.pop("password", None)
    return {
        "status": "success",
        "message": "User logged in successfully",
        "user": user,
        "token": token,
    }