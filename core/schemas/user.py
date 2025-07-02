from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    user_id: str
    name: str
    email: str
    password: str
    is_active: bool = True