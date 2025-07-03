from pydantic import BaseModel, Field, EmailStr

# class User(BaseModel):
#     user_id: str
#     name: str
#     email: str
#     password: str
#     is_active: bool = True


from typing import List, Dict, Literal, Optional
from datetime import datetime
from bson import ObjectId
import uuid


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserCreateModel(BaseModel):
    name: str
    email: EmailStr
    password: str
class ChatMessage(BaseModel):
    type: Literal["agent", "user"]
    message: str
    createdAt: datetime
    updatedAt: datetime

class Thread(BaseModel):
    documents: List[str]
    chats: List[ChatMessage]
    createdAt: datetime
    updatedAt: datetime

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    userId: str
    name: str
    email: EmailStr
    password: str
    is_active: bool = True
    threads: Dict[str, Thread] = {}

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
