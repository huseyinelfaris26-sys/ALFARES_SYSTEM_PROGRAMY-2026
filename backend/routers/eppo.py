from fastapi import APIRouter

router = APIRouter()

@router.get("/eppo")

def eppo():

    return {
        "message":
        "eppo running"
    }
