from fastapi import APIRouter, Request

router=APIRouter(
    prefix='/query',
    tags=['query']
)

@router.post("/")
async def query(
    request: Request
):

    jwt_token = request.headers.get("authorization", "").split(" ")[-1]
    if not token:
        return {"error": "Authorization header or JWT token missing"}
     # mind change - add auth middleare instead