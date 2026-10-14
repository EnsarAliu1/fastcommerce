from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.users.schemas.user import UserResponse, UserCreate
from app.modules.users.services import users as users_service
from app.db import get_db

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201
)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    return users_service.register_user(
        user,
        db
    )
