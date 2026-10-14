from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.users.schemas.user import UserResponse, UserCreate
from app.modules.users.schemas.auth import TokenResponse, LoginRequset
from app.modules.users.services import users as users_service
from app.modules.users.services import auth as auth_services
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


@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user: LoginRequset,
    db: Session = Depends(get_db)
):
    return auth_services.login_user(
        user,
        db
    )
