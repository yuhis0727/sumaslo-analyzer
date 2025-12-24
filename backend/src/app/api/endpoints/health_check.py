from fastapi import APIRouter

health_check = APIRouter()


@health_check.get("/")
async def health_check_endpoint():
    return {"message": "ok"}
