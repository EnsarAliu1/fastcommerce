from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.users.schemas.user import UserResponse, UserCreate
from app.modules.users.schemas.auth import TokenResponse, LoginRequest
from app.modules.users.services import users as users_service
from app.modules.users.services import auth as auth_services
from app.db import get_db
from app import models
from app.modules.users.dependencies import get_current_user

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
    user: LoginRequest,
    db: Session = Depends(get_db)
):
    return auth_services.login_user(
        user,
        db
    )


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: models.User = Depends(get_current_user)
):
    return current_user
