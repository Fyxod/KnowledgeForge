from fastapi import APIRouter
from core.schemas.user import UserCreateModel


router=APIRouter(
    prefix='/user',
    tags=['user']
)

@router.post("/")
async def create_user(user: UserCreateModel):
    
    return {"message": "User created successfully"}