"""
Create a new user.

**Input (from frontend):**
    - JSON body matching `UserCreateModel`:
        - name (str): The user's full name.
        - email (str): The user's email address.
        - password (str): The user's password.

**Returns:**
    - JSON object:
        - status (str): "success" if user is created.
        - message (str): Success message.
        - user (UserResponseModel): The created user's data (excluding password and internal IDs).

**Errors:**
    - 400: If the email already exists.
"""

"""
Retrieve a user's information by user ID.

**Input (from frontend):**
    - Path parameter:
        - user_id (str): The unique user ID.
    - Authenticated request (JWT token in headers).

**Returns:**
    - JSON object:
        - status (str): "success" if user is found.
        - message (str): Success message.
        - user (dict): The user's data (excluding password and internal IDs).

**Errors:**
    - 401: If the user is not authenticated.
    - 403: If the authenticated user does not match the requested user_id.
    - 404: If the user is not found.
"""

"""
Authenticate a user and return a JWT token.

**Input (from frontend):**
    - JSON body matching `UserLoginModel`:
        - email (str): The user's email address.
        - password (str): The user's password.

**Returns:**
    - JSON object:
        - status (str): "success" if login is successful.
        - message (str): Success message.
        - user (dict): The user's data (excluding password).
        - token (str): JWT token for authentication.

**Errors:**
    - 404: If the user is not found.
    - 400: If the password is invalid.
"""

import dis
import jwt
import uuid

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
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
def create_user(user_input: UserCreateModel, background_tasks: BackgroundTasks):
    print("Creating user with input:", user_input.model_dump())
    if db.users.find_one({"email": user_input.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    user_dict = user_input.model_dump()
    print("Creating user with input:", user_dict)
    name_filtered = user_dict["name"].strip().lower().replace(" ", "_")
    user_dict["name"] = user_dict["name"].strip().title()
    user_name_d=user_dict["name"]
    user_pass_d=user_dict["password"]
    user_email_d=user_dict["email"]
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
        print("User not found for userId:", user_id)
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "status": "success",
        "message": "User retrieved successfully",
        "user": user,
    }


@router.post("/login")
def login_user(user_input: UserLoginModel, background_tasks: BackgroundTasks):
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