from app import models
from app.modules.users.schemas.auth import LoginRequest
from fastapi import HTTPException
from app.modules.users.services.users import password_hash
from app.core.security import create_access_token
from sqlalchemy.orm import Session


def login_user(data: LoginRequest, db: Session):
    user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    invalid_credentials = HTTPException(
        status_code=401,
        detail="Invalid email or password",
        headers={"WWW-Authentication": "Bearer"}
    )

    if user is None:
        raise invalid_credentials

    password_is_valid = password_hash.verify(
        data.password,
        user.hashed_password
    )

    if password_is_valid is False:
        raise invalid_credentials

    if user.is_active is False:
        raise HTTPException(
            status_code=403,
            detail="Inactive user"
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
