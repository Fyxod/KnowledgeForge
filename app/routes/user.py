from fastapi import APIRouter, HTTPException
from core.schemas.user import UserCreateModel
from core.database import db
from core.utils.bcrypt import hash_password, verify_password
import uuid
from core.schemas.user import UserModel


router = APIRouter(prefix="/user", tags=["user"])


# @router.post("/", response_model=UserModel)
@router.post("/")
def create_user(user_input: UserCreateModel):
    if db.users.find_one({"email": user_input.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    user_dict = user_input.model_dump()
    user_dict["password"] = hash_password(user_dict["password"])
    user_dict["userId"] = f"user_{uuid.uuid4().hex[:6]}"
    user_dict["is_active"] = True
    user_dict["threads"] = {}

    result = db.users.insert_one(user_dict)
    created_user = db.users.find_one({"_id": result.inserted_id})
    return created_user


@router.get("/{user_id}")
def get_user(user_id: str):
    user = db.users.find_one({"userId": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.pop("password", None)
    return user  # yet to modify responses, will do when starting frontend


@router.post("/login")
def login_user(user_input: UserCreateModel):
    user = db.users.find_one({"email": user_input.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user_input.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    user.pop("password", None)
    return user  # yet to modify responses, will do when starting frontend
