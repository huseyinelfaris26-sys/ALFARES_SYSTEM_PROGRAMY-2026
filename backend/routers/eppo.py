from fastapi import APIRouter

from services.eppo_service import (
    search_name
)

router = APIRouter()


@router.get("/eppo/search")
def search(name: str):

    return search_name(name)
